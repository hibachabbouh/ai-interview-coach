import os
import time
import asyncio
from typing import AsyncGenerator, Literal, Optional

from dotenv import load_dotenv
from groq import Groq, AsyncGroq, APIError, RateLimitError, APITimeoutError

from utils.logger import get_logger, log_llm_call

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logger = get_logger(__name__)

_LANGFUSE_ENABLED: bool = os.getenv("LANGFUSE_ENABLED", "false").lower() in ("true", "1", "yes")

_langfuse = None
if _LANGFUSE_ENABLED:
    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST"),
        )
        logger.info("Langfuse tracing enabled.")
    except Exception as _lf_exc:
        logger.warning("Langfuse init failed: %s — tracing disabled.", _lf_exc)
        _LANGFUSE_ENABLED = False
        _langfuse = None

Complexity = Literal["simple", "medium", "complex"]

MODELS: dict[Complexity, str] = {
    "simple":  "llama-3.1-8b-instant",
    "medium":  "llama-3.3-70b-versatile",
    "complex": "openai/gpt-oss-120b",
}

AGENT_COMPLEXITY: dict[str, Complexity] = {
    "guardrail":   "simple",
    "ambiguity":   "medium",
    "memory":      "medium",
    "router":      "simple",
    "technical":   "medium",
    "behavioral":  "medium",
    "evaluation":  "complex",
    "fusion":      "complex",
    "report":      "medium",
}

MAX_RETRIES   = 5
RETRY_BACKOFF = 2.0

def _build_client() -> Groq:
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. "
            "Add it to your .env file or export it in your shell."
        )
    return Groq(api_key=GROQ_API_KEY, max_retries=0)

_client: Groq | None = None
_async_client: AsyncGroq | None = None

def get_client() -> Groq:
    global _client
    if _client is None:
        _client = _build_client()
    return _client

def get_async_client() -> AsyncGroq:
    global _async_client
    if _async_client is None:
        if not GROQ_API_KEY:
            raise EnvironmentError("GROQ_API_KEY is not set.")
        _async_client = AsyncGroq(api_key=GROQ_API_KEY, max_retries=0)
    return _async_client

def _accumulate_usage(state: Optional[dict], model: str, usage) -> None:
    if state is None or usage is None:
        return

    meta = state.setdefault("metadata", {})
    token_map: dict = meta.setdefault("token_usage", {})

    bucket = token_map.setdefault(model, {"input": 0, "output": 0})
    bucket["input"]  += getattr(usage, "prompt_tokens",     0) or 0
    bucket["output"] += getattr(usage, "completion_tokens", 0) or 0

def chat(
    messages: list[dict],
    *,
    complexity: Complexity = "medium",
    agent: str = "unknown",
    session_id: str = "no-session",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    override_model: str | None = None,
    response_format: dict | None = None,
    state: Optional[dict] = None,
) -> str:
    model  = override_model or MODELS[complexity]
    client = get_client()

    logger.info("LLM call | agent=%-12s complexity=%-8s model=%s", agent, complexity, model)

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **({"response_format": response_format} if response_format else {}),
            )
            latency_ms = (time.perf_counter() - t0) * 1000

            usage = response.usage
            log_llm_call(
                session_id=session_id,
                agent=agent,
                model=model,
                complexity=complexity,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
            )

            _accumulate_usage(state, model, usage)

            content = response.choices[0].message.content or ""
            logger.debug(
                "LLM ok | agent=%s latency=%.0fms tokens=%s",
                agent, latency_ms,
                f"{usage.total_tokens}" if usage else "?",
            )
            return content

        except RateLimitError as exc:
            wait = RETRY_BACKOFF * attempt
            logger.warning(
                "Rate-limit on attempt %d/%d — waiting %.1fs | model=%s",
                attempt, MAX_RETRIES, wait, model,
            )
            last_error = exc
            time.sleep(wait)

        except APITimeoutError as exc:
            wait = RETRY_BACKOFF * attempt
            logger.warning(
                "Timeout on attempt %d/%d — waiting %.1fs | model=%s",
                attempt, MAX_RETRIES, wait, model,
            )
            last_error = exc
            time.sleep(wait)

        except APIError as exc:
            _code = ""
            if hasattr(exc, "status_code") and exc.status_code == 400:
                _body = getattr(exc, "body", None) or {}
                if isinstance(_body, dict):
                    _code = (_body.get("error") or {}).get("code", "")
            if _code == "json_validate_failed":
                wait = RETRY_BACKOFF * attempt
                logger.warning(
                    "json_validate_failed attempt %d/%d — waiting %.1fs | agent=%s model=%s",
                    attempt, MAX_RETRIES, wait, agent, model,
                )
                last_error = exc
                time.sleep(wait)
                continue
            logger.error("Groq API error | agent=%s | %s", agent, exc)
            raise

    logger.error(
        "All %d retries exhausted | agent=%s model=%s", MAX_RETRIES, agent, model
    )
    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} attempts.") from last_error

async def chat_async(
    messages: list[dict],
    *,
    complexity: Complexity = "medium",
    agent: str = "unknown",
    session_id: str = "no-session",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    override_model: str | None = None,
    response_format: dict | None = None,
    state: Optional[dict] = None,
) -> str:
    model  = override_model or MODELS[complexity]
    client = get_async_client()

    logger.info("LLM async | agent=%-12s complexity=%-8s model=%s", agent, complexity, model)

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.perf_counter()
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **({"response_format": response_format} if response_format else {}),
            )
            latency_ms = (time.perf_counter() - t0) * 1000

            usage = response.usage
            log_llm_call(
                session_id=session_id,
                agent=agent,
                model=model,
                complexity=complexity,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
            )

            _accumulate_usage(state, model, usage)

            content = response.choices[0].message.content or ""
            logger.debug(
                "LLM ok  | agent=%s latency=%.0fms tokens=%s",
                agent, latency_ms,
                f"{usage.total_tokens}" if usage else "?",
            )
            return content

        except RateLimitError as exc:
            wait = RETRY_BACKOFF * attempt
            logger.warning(
                "Rate-limit on attempt %d/%d — waiting %.1fs | model=%s",
                attempt, MAX_RETRIES, wait, model,
            )
            last_error = exc
            await asyncio.sleep(wait)

        except APITimeoutError as exc:
            wait = RETRY_BACKOFF * attempt
            logger.warning(
                "Timeout on attempt %d/%d — waiting %.1fs | model=%s",
                attempt, MAX_RETRIES, wait, model,
            )
            last_error = exc
            await asyncio.sleep(wait)

        except APIError as exc:
            _code = ""
            if hasattr(exc, "status_code") and exc.status_code == 400:
                _body = getattr(exc, "body", None) or {}
                if isinstance(_body, dict):
                    _code = (_body.get("error") or {}).get("code", "")
            if _code == "json_validate_failed":
                wait = RETRY_BACKOFF * attempt
                logger.warning(
                    "json_validate_failed attempt %d/%d — waiting %.1fs | agent=%s model=%s",
                    attempt, MAX_RETRIES, wait, agent, model,
                )
                last_error = exc
                await asyncio.sleep(wait)
                continue
            logger.error("Groq API error | agent=%s | %s", agent, exc)
            raise

    logger.error(
        "All %d retries exhausted | agent=%s model=%s", MAX_RETRIES, agent, model
    )
    raise RuntimeError(
        f"LLM async call failed after {MAX_RETRIES} attempts."
    ) from last_error

def chat_for_agent(
    agent_name: str,
    messages: list[dict],
    session_id: str = "no-session",
    state: Optional[dict] = None,
    **kwargs,
) -> str:
    complexity: Complexity = AGENT_COMPLEXITY.get(agent_name, "medium")
    return chat(
        messages,
        complexity=complexity,
        agent=agent_name,
        session_id=session_id,
        state=state,
        **kwargs,
    )

async def chat_for_agent_async(
    agent_name: str,
    messages: list[dict],
    session_id: str = "no-session",
    state: Optional[dict] = None,
    **kwargs,
) -> str:
    complexity: Complexity = AGENT_COMPLEXITY.get(agent_name, "medium")
    return await chat_async(
        messages,
        complexity=complexity,
        agent=agent_name,
        session_id=session_id,
        state=state,
        **kwargs,
    )

def build_messages(system_prompt: str, user_content: str) -> list[dict]:
    return [
        {"role": "system",  "content": system_prompt},
        {"role": "user",    "content": user_content},
    ]

async def chat_stream_async(
    messages: list[dict],
    *,
    complexity: Complexity = "medium",
    agent: str = "unknown",
    session_id: str = "no-session",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    override_model: str | None = None,
) -> AsyncGenerator[str, None]:
    model = override_model or MODELS[complexity]
    client = get_async_client()

    logger.info(
        "LLM stream | agent=%-12s complexity=%-8s model=%s", agent, complexity, model
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
            return

        except RateLimitError as exc:
            wait = RETRY_BACKOFF * attempt
            logger.warning(
                "Stream rate-limit attempt %d/%d — %.1fs | model=%s",
                attempt, MAX_RETRIES, wait, model,
            )
            if attempt == MAX_RETRIES:
                raise
            await asyncio.sleep(wait)

        except APITimeoutError as exc:
            wait = RETRY_BACKOFF * attempt
            logger.warning(
                "Stream timeout attempt %d/%d — %.1fs | model=%s",
                attempt, MAX_RETRIES, wait, model,
            )
            if attempt == MAX_RETRIES:
                raise
            await asyncio.sleep(wait)

        except APIError as exc:
            logger.error("Stream Groq API error | agent=%s | %s", agent, exc)
            raise