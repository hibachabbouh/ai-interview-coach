from services.llm_service import chat_for_agent, build_messages
from prompts.evaluation_prompt import EVALUATION_PROMPT
from schemas.evaluation_schema import EvaluationOutput
from graph.state import InterviewState
from utils.json_repair import safe_parse_llm_json
import logging

logger = logging.getLogger(__name__)


def evaluation_node(state: InterviewState):

    question = state.get("question", "")
    answer = state.get("user_answer", "")

    if not answer or not answer.strip():
        return {
            "technical_score": 0.0,
            "communication_score": 0.0,
            "confidence_score": 0.0,
            "overall_score": 0.0,
            "evaluation_overall_score": 0.0,
            "evaluation_strengths": [],
            "evaluation_weaknesses": ["No answer provided"],
        }

    context = f"""
QUESTION:
{question}

ANSWER:
{answer}
"""

    messages = build_messages(EVALUATION_PROMPT, context)

    response = chat_for_agent(
        "evaluation",
        messages,
        session_id=state["session_id"],
        temperature=0.2,
        state=state,
        response_format={"type": "json_object"},
    )

    parsed = safe_parse_llm_json(response) or {}

    output = EvaluationOutput.model_validate(parsed)

    return {
        "evaluation_overall_score": float(output.overall_score),
        "evaluation_strengths": output.strengths,
        "evaluation_weaknesses": output.weaknesses,
        "technical_score": float(output.technical_score),
        "communication_score": float(output.communication_score),
        "confidence_score": float(output.confidence_score),
        "overall_score": float(output.overall_score),
        "metadata": state.get("metadata", {}),
    }
