from services.llm_service import chat_for_agent, build_messages
from prompts.fusion_prompt import FUSION_PROMPT
from schemas.fusion_schema import FusionOutput
from graph.state import InterviewState
from utils.json_repair import safe_parse_llm_json


def fusion_node(state: InterviewState):
    fusion_score = state.get("fusion_overall_score") or 0.0
    eval_score = state.get("evaluation_overall_score") or 0.0

    if fusion_score > 0.0:
        merged_score = (fusion_score + eval_score) / 2.0
    else:
        merged_score = eval_score

    context = f"""
EVALUATION:
Score: {merged_score:.2f}
Strengths: {state.get('evaluation_strengths', [])}
Weaknesses: {state.get('evaluation_weaknesses', [])}
"""

    messages = build_messages(FUSION_PROMPT, context)

    response = chat_for_agent(
        "fusion",
        messages,
        session_id=state["session_id"],
        state=state,
        response_format={"type": "json_object"},
    )

    parsed = safe_parse_llm_json(response) or {}

    output = FusionOutput.model_validate(parsed)

    return {
        "fusion_overall_score": float(output.overall_score),
        "recommendations": output.recommendations,
        "fusion_strengths": output.strengths,
        "fusion_weaknesses": output.weaknesses,
        "metadata": state.get("metadata", {}),
    }
