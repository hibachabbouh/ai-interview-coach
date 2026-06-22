from services.llm_service import chat_for_agent, build_messages
from prompts.guardrail_prompt import GUARDRAIL_PROMPT
from schemas.guardrail_schema import GuardrailOutput
from graph.state import InterviewState
from utils.json_repair import safe_parse_llm_json
from utils.logger import get_logger

logger = get_logger(__name__)


def guardrail_node(state: InterviewState):
    current_question = state.get("current_question")
    user_input = state["user_input"]
    if current_question and state.get("awaiting_answer"):
        guardrail_input = (
            f"CONTEXT: The user is answering an interview question.\n"
            f"QUESTION ASKED: {current_question}\n"
            f"USER ANSWER: {user_input}"
        )
    else:
        guardrail_input = user_input

    messages = build_messages(GUARDRAIL_PROMPT, guardrail_input)

    response = chat_for_agent(
        "guardrail",
        messages,
        session_id=state["session_id"],
        state=state,
        response_format={"type": "json_object"},
    )

    logger.info("GUARDRAIL INPUT: %r", guardrail_input)
    logger.info("GUARDRAIL RAW RESPONSE: %r", response)

    parsed = safe_parse_llm_json(response) or {}
    logger.info("GUARDRAIL PARSED: %s", parsed)

    output = GuardrailOutput.model_validate(parsed)
    logger.info("GUARDRAIL OUTPUT: allowed=%s risk=%s reason=%r",
                output.allowed, output.risk_level, output.reason)
    is_answer_turn = bool(current_question and state.get("awaiting_answer"))
    if is_answer_turn and not output.allowed and output.risk_level != "high":
        logger.warning(
            "GUARDRAIL OVERRIDE: answer wrongly blocked at risk=%s — allowing through.",
            output.risk_level,
        )
        return {
            "allowed": True,
            "risk_level": output.risk_level,
            "guardrail_reason": "",
        }

    return {
        "allowed": output.allowed,
        "risk_level": output.risk_level,
        "guardrail_reason": output.reason,
    }