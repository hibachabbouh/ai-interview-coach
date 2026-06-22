from services.llm_service import chat_for_agent, build_messages
from prompts.ambiguity_prompt import AMBIGUITY_PROMPT
from schemas.ambiguity_schema import AmbiguityOutput
from graph.state import InterviewState
from utils.json_repair import safe_parse_llm_json


def ambiguity_node(state: InterviewState):

    if state.get("awaiting_answer") and state.get("current_question"):
        return {
            "is_ambiguous": False,
            "missing_fields": [],
            "clarification_question": "",
            "ambiguity_role": None,
            "ambiguity_experience_level": None,
        }

    messages = build_messages(
        AMBIGUITY_PROMPT,
        state["user_input"]
    )

    response = chat_for_agent(
        "ambiguity",
        messages,
        session_id=state["session_id"],
        state=state,
        response_format={"type": "json_object"},
    )

    parsed = safe_parse_llm_json(response) or {}
    output = AmbiguityOutput.model_validate(parsed)

    return {
        "is_ambiguous": output.is_ambiguous,
        "missing_fields": output.missing_fields,
        "clarification_question": output.clarification_question,
        "ambiguity_role": getattr(output, "role", None),
        "ambiguity_experience_level": getattr(output, "experience_level", None),
    }