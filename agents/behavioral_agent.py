from services.llm_service import chat_for_agent, build_messages
from prompts.behavioral_prompt import BEHAVIORAL_PROMPT
from schemas.behavioral_schema import BehavioralOutput
from graph.state import InterviewState

from tools.behavioral_tool import BehavioralTool
from utils.json_repair import safe_parse_llm_json

behavioral_tool = BehavioralTool()


def behavioral_node(state: InterviewState):

    
    if state.get("awaiting_answer") and state.get("current_question"):
        return {
            "question": state["current_question"],
            "user_answer": state.get("user_answer", "NO ANSWER PROVIDED"),
            "metadata": state.get("metadata", {}),
        }

   
    role = state.get("role", "unknown")
    experience_level = state.get("experience_level", "unknown")
    asked_questions = state.get("asked_questions", [])

    context_tool = behavioral_tool.run(state["user_input"])

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

CONTEXT:
{context_tool}
{avoid_block}
"""

    messages = build_messages(BEHAVIORAL_PROMPT, context)

    response = chat_for_agent(
        "behavioral",
        messages,
        session_id=state["session_id"],
        state=state,
        response_format={"type": "json_object"},
    )

    parsed = safe_parse_llm_json(response)
    output = BehavioralOutput.model_validate(parsed)

    return {
        "question_id": output.question_id,
        "question": output.question,
        "skill_assessed": output.skill_assessed,
        "difficulty": output.difficulty,
        "role": role,
        "experience_level": experience_level,
        "user_answer": state.get("user_answer", "NO ANSWER PROVIDED"),
        "metadata": state.get("metadata", {}),
    }