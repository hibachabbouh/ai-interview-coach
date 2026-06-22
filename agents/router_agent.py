from services.llm_service import chat_for_agent, build_messages
from prompts.router_prompt import ROUTER_PROMPT
from schemas.router_schema import RouterOutput
from graph.state import InterviewState
from utils.json_repair import safe_parse_llm_json


def router_node(state: InterviewState):
    context = f"""
User request:
{state['user_input']}

Known profile:
role: {state.get('role', 'unknown')}
experience: {state.get('experience_level', 'unknown')}
"""

    messages = build_messages(
        ROUTER_PROMPT,
        context
    )

    response = chat_for_agent(
        "router",
        messages,
        session_id=state["session_id"],
        state=state,
        response_format={"type": "json_object"},
    )

    parsed = safe_parse_llm_json(response) or {}

    output = RouterOutput.model_validate(parsed)

    return {
        "route": output.route,
        "route_confidence": output.confidence,
        "metadata": state.get("metadata", {}),
    }
