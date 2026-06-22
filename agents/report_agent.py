from services.llm_service import chat_for_agent, build_messages
from prompts.report_prompt import REPORT_PROMPT
from schemas.report_schema import ReportOutput
from graph.state import InterviewState
from utils.logger import get_logger
from utils.json_repair import safe_parse_llm_json

logger = get_logger(__name__)


def report_node(state: InterviewState):

    evaluation_score = state.get("evaluation_overall_score") or 0.0
    previous_score = state.get("final_overall_score") or 0.0
    fusion_score = state.get("fusion_overall_score") or 0.0

    if fusion_score > 0.0:
        merged_score = fusion_score
    elif evaluation_score > 0.0 and previous_score > 0.0:
        merged_score = (evaluation_score + previous_score) / 2.0
    elif evaluation_score > 0.0:
        merged_score = evaluation_score
    else:
        merged_score = previous_score
    strengths = state.get("fusion_strengths") or state.get("evaluation_strengths", [])
    weaknesses = state.get("fusion_weaknesses") or state.get("evaluation_weaknesses", [])
    recommendations = state.get("recommendations", [])

    context = f"""
SCORE: {merged_score:.2f}
STRENGTHS: {strengths}
WEAKNESSES: {weaknesses}
RECOMMENDATIONS: {recommendations}
"""

    messages = build_messages(REPORT_PROMPT, context)

    response = chat_for_agent(
        "report",
        messages,
        session_id=state["session_id"],
        state=state,
        response_format={"type": "json_object"},
    )

    parsed = safe_parse_llm_json(response) or {}

    output = ReportOutput.model_validate(parsed)

    final_score = output.structured_data.overall_score or merged_score

    return {
        "final_report": output.markdown_report,
        "title": output.structured_data.title,
        "summary": output.structured_data.summary,
        "final_overall_score": float(final_score),
        "overall_score": float(final_score),
        "next_steps": output.structured_data.next_steps,
        "recommendations": recommendations,
        "fusion_strengths": output.structured_data.strengths,
        "fusion_weaknesses": output.structured_data.weaknesses,
        "metadata": state.get("metadata", {}),
    }
