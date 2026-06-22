from __future__ import annotations

import json
import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "AI Interview Coach")

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

EXACT_TTL_SECONDS = int(os.getenv("EXACT_TTL_SECONDS", "3600"))
SEMANTIC_TTL_SECONDS = int(os.getenv("SEMANTIC_TTL_SECONDS", "86400"))

_cors_raw = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS_LIST = [origin.strip() for origin in _cors_raw.split(",") if origin.strip()]

from schemas.api_schemas import (
    ChatRequest,
    ChatResponse,
    SearchRequest,
    SearchResponse,
    InterviewRequest,
)
from services import llm_service
from services.search_cache import SearchCache
from services.session_store import SessionStore
from services.tavily_client import live_search
from graph.interview_graph import interview_graph
from utils.logger import get_logger

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.search_cache = SearchCache(
        db_path=CHROMA_DB_PATH,
        collection_name="web_search_cache",
        exact_ttl_seconds=EXACT_TTL_SECONDS,
        semantic_ttl_seconds=SEMANTIC_TTL_SECONDS,
        redis_host=REDIS_HOST,
        redis_port=REDIS_PORT,
        redis_db=REDIS_DB,
        chroma_host=CHROMA_HOST,
        chroma_port=CHROMA_PORT,
    )
    logger.info("SearchCache initialized (%s).", APP_NAME)

    app.state.session_store = SessionStore(
        redis_host=REDIS_HOST,
        redis_port=REDIS_PORT,
        redis_db=REDIS_DB,
    )
    logger.info("SessionStore initialized.")
    yield

app = FastAPI(
    title=APP_NAME,
    description="Multi-agent AI Interview Coach powered by Groq & LangGraph.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", *CORS_ORIGINS_LIST],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Meta"])
def health():
    return {"status": "ok", "app": APP_NAME}

@app.post("/interview", tags=["Interview"])
def interview(req: InterviewRequest):
    store: SessionStore = app.state.session_store
    session_id = req.session_id or str(uuid.uuid4())

    if req.reset_session:
        store.delete(session_id)

    session = store.get(session_id)

    awaiting_answer = req.awaiting_answer or False
    current_question = req.current_question or session.get("current_question")

    role = session.get("role")
    experience_level = session.get("experience_level")
    logger.info("experience_level=%s", experience_level)
    logger.info("request=%s", req.model_dump())
    company = session.get("company")
    route = session.get("route")

    target_question_count = req.target_question_count or session.get("target_question_count", 5)
    question_count = session.get("question_count", 0)
    score_history = session.get("score_history", [])
    asked_questions = session.get("asked_questions", [])

    state = {
        "user_input": req.user_input,
        "session_id": session_id,
        "language": req.language or "en",
        "allowed": True,
        "metadata": {"token_usage": {}},

        "awaiting_answer": awaiting_answer,
        "current_question": current_question,
        "user_answer": req.user_input if awaiting_answer else None,

        "skip_guardrail": False,

        "role": role,
        "experience_level": experience_level,
        "company": company,
        "route": route,

        "question_count": question_count,
        "score_history": score_history,
        "asked_questions": asked_questions,
        "target_question_count": target_question_count,
        "session_complete": False,
    }

    logger.info(
        "Interview request | session=%s turn=%s awaiting=%s q_count=%s/%s profile=(%s,%s,%s)",
        session_id, req.turn, awaiting_answer, question_count, target_question_count,
        role, experience_level, company,
    )
    logger.info("STATE BEFORE GRAPH: awaiting=%s question=%r", state.get("awaiting_answer"), state.get("current_question"))
    try:
        result = interview_graph.invoke(state)
    except Exception as exc:
        logger.error("Graph invocation error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    produced_question = result.get("question")
    produced_answer = result.get("user_answer")
    still_awaiting = bool(produced_question) and not bool(produced_answer)

    merged_role = (
        result.get("ambiguity_role")
        or result.get("role")
        or role
    )
    merged_experience_level = (
        result.get("ambiguity_experience_level")
        or result.get("experience_level")
        or experience_level
    )
    merged_company = (
        result.get("company")
        or company
    )

    session_patch = {
        "role": merged_role,
        "experience_level": merged_experience_level,
        "company": merged_company,
        "route": result.get("route") or route,
        "target_question_count": target_question_count,
    }

    new_question_count = question_count
    new_score_history = list(score_history)

    if still_awaiting and produced_question:
        session_patch["current_question"] = produced_question
        if produced_question not in asked_questions:
            session_patch["asked_questions"] = asked_questions + [produced_question]
        new_question_count = question_count + 1
        session_patch["question_count"] = new_question_count

    elif produced_answer:
        score = result.get("final_overall_score")
        if score is not None:
            new_score_history = score_history + [round(float(score), 3)]
            session_patch["score_history"] = new_score_history
        session_patch["current_question"] = None

    store.update(session_id, session_patch)
    logger.info(
        "SESSION PATCH | role=%s experience_level=%s company=%s",
        session_patch.get("role"),
        session_patch.get("experience_level"),
        session_patch.get("company"),
    )
    logger.info(
        "RESULT profile fields | result.role=%s result.experience_level=%s",
        result.get("role"),
        result.get("experience_level"),
    )

    avg_score = round(sum(new_score_history) / len(new_score_history), 3) if new_score_history else None
    session_complete = (not still_awaiting) and new_question_count >= target_question_count

    return {
        "allowed": result.get("allowed"),
        "guardrail_reason": result.get("guardrail_reason"),

        "question": produced_question,
        "awaiting_answer": still_awaiting,

        "summary": result.get("summary"),
        "final_report": result.get("final_report"),
        "title": result.get("title"),
        "final_overall_score": result.get("final_overall_score"),
        "next_steps": result.get("next_steps"),

        "session_id": session_id,

        "question_count": new_question_count,
        "target_question_count": target_question_count,
        "score_history": new_score_history,
        "average_score": avg_score,
        "session_complete": session_complete,

        "role": session_patch["role"],
        "experience_level": session_patch["experience_level"],
        "company": session_patch["company"],
    }

@app.post("/interview/reset", tags=["Interview"])
def interview_reset(session_id: str = Query(...)):
    store: SessionStore = app.state.session_store
    store.delete(session_id)
    return {"status": "ok", "session_id": session_id}

@app.get("/chat/agents", tags=["Chat"])
def list_agents():
    return {"agents": llm_service.AGENT_COMPLEXITY, "models": llm_service.MODELS}

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(req: ChatRequest):
    if req.messages:
        messages = [m.model_dump() for m in req.messages]
    else:
        messages = llm_service.build_messages(
            req.system_prompt or "You are a helpful assistant.",
            req.user_content,
        )

    state: dict = {}
    response_format = {"type": "json_object"} if req.json_mode else None

    try:
        if req.complexity_override:
            complexity = req.complexity_override
            reply = llm_service.chat(
                messages,
                complexity=complexity,
                agent=req.agent,
                session_id=req.session_id,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                response_format=response_format,
                state=state,
            )
        else:
            complexity = llm_service.AGENT_COMPLEXITY.get(req.agent, "medium")
            reply = llm_service.chat_for_agent(
                req.agent,
                messages,
                session_id=req.session_id,
                state=state,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                response_format=response_format,
            )
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    model = llm_service.MODELS[complexity]
    token_usage = state.get("metadata", {}).get("token_usage", {})

    return ChatResponse(
        reply=reply,
        agent=req.agent,
        model=model,
        complexity=complexity,
        session_id=req.session_id,
        token_usage=token_usage,
    )

@app.get("/chat/stream", tags=["Chat"])
async def chat_stream(
    user_content: str = Query(..., description="The user message to send."),
    agent: str = Query(default="technical", description="Agent name."),
    system_prompt: Optional[str] = Query(default=None),
    session_id: str = Query(default="no-session"),
    temperature: float = Query(default=0.7, ge=0.0, le=2.0),
    max_tokens: int = Query(default=2048, ge=1),
    complexity: Optional[str] = Query(default=None),
):
    messages = llm_service.build_messages(
        system_prompt or "You are a helpful AI interview coach.",
        user_content,
    )
    resolved_complexity = complexity or llm_service.AGENT_COMPLEXITY.get(agent, "medium")

    async def event_generator():
        try:
            async for chunk in llm_service.chat_stream_async(
                messages,
                complexity=resolved_complexity,
                agent=agent,
                session_id=session_id,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                payload = json.dumps({"token": chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
        except EnvironmentError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        except Exception as exc:
            logger.error("SSE stream error: %s", exc)
            yield f"data: {json.dumps({'error': 'Stream error. Please retry.'})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

@app.post("/search", response_model=SearchResponse, tags=["Search"])
def search(req: SearchRequest):
    cache: SearchCache = app.state.search_cache

    cached = cache.lookup(
        req.query,
        domains=req.domains,
        max_results=req.max_results,
        search_depth=req.search_depth,
    )
    if cached is not None:
        return SearchResponse(query=req.query, results=cached, cache_hit=True, source="cache")

    try:
        results = live_search(
            req.query,
            domains=req.domains,
            max_results=req.max_results,
            search_depth=req.search_depth,
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.error("Tavily live search failed: %s", exc)
        raise HTTPException(status_code=502, detail="Live search provider error.")

    cache.save(req.query, results, domains=req.domains,
               max_results=req.max_results, search_depth=req.search_depth)

    return SearchResponse(query=req.query, results=results, cache_hit=False, source="live")