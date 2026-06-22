from services.llm_service import chat_for_agent, build_messages
from prompts.technical_prompt import TECHNICAL_PROMPT
from schemas.technical_schema import TechnicalOutput
from graph.state import InterviewState

from tools.ml_docs_tool import MlDocsTool
from tools.leetcode_tool import LeetcodeTool
from utils.json_repair import safe_parse_llm_json

ml_tool = MlDocsTool()
leetcode_tool = LeetcodeTool()


def technical_node(state: InterviewState):

    if state.get("awaiting_answer") and state.get("current_question"):
        return {
            "question": state["current_question"],
            "user_answer": state.get("user_answer", "NO ANSWER PROVIDED"),
            "metadata": state.get("metadata", {}),
        }

    role = state.get("role", "unknown")
    experience_level = state.get("experience_level", "unknown")
    asked_questions = state.get("asked_questions", [])

    query = state["user_input"]

    ml_context = ml_tool.research(query)
    leetcode_context = leetcode_tool.run(query)

    avoid_block = ""
    if asked_questions:
        avoid_list = "\n".join(f"- {q}" for q in asked_questions[-10:])
        avoid_block = f"""
ALREADY ASKED (do NOT repeat these or close variants):
{avoid_list}
"""

    context = f"""
USER PROFILE:
Role: {role}
Level: {experience_level}

ML CONTEXT:
{ml_context}

LEETCODE CONTEXT:
{leetcode_context}
{avoid_block}
"""

    messages = build_messages(TECHNICAL_PROMPT, context)

    response = chat_for_agent(
        "technical",
        messages,
        session_id=state["session_id"],
        state=state,
        response_format={"type": "json_object"},
    )

    parsed = safe_parse_llm_json(response) or {}
    output = TechnicalOutput.model_validate(parsed)

    return {
        "question_id": output.question_id,
        "question": output.question,
        "difficulty": output.difficulty,
        "topics": output.topics,
        "role": role,
        "experience_level": experience_level,
        "metadata": state.get("metadata", {}),
    }