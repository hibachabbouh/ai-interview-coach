from langgraph.graph import StateGraph, END

from graph.state import InterviewState
from services.llm_service import _langfuse, _LANGFUSE_ENABLED

from agents.guardrail_agent import guardrail_node
from agents.ambiguity_agent import ambiguity_node
from agents.memory_agent import memory_node
from agents.router_agent import router_node

from agents.technical_agent import technical_node
from agents.behavioral_agent import behavioral_node

from agents.evaluation_agent import evaluation_node
from agents.fusion_agent import fusion_node
from agents.report_agent import report_node

from agents.profile_merge_agent import profile_merge_node

builder = StateGraph(InterviewState)

builder.add_node("guardrail", guardrail_node)

builder.add_node("ambiguity", ambiguity_node)
builder.add_node("profile_merge", profile_merge_node)

builder.add_node("router", router_node)

builder.add_node("technical", technical_node)
builder.add_node("behavioral", behavioral_node)

builder.add_node("evaluation", evaluation_node)
builder.add_node("fusion", fusion_node)
builder.add_node("report", report_node)

builder.set_entry_point("guardrail")

def guardrail_route(state: InterviewState):
    if not state.get("allowed", True):
        return "report"
    return "ambiguity"

def route_interview(state: InterviewState):
    route = state.get("route", "technical")
    if route == "behavioral":
        return "behavioral"
    return "technical"

builder.add_conditional_edges(
    "guardrail",
    guardrail_route,
    {
        "ambiguity": "ambiguity",
        "report": "report",
    },
)

builder.add_edge("ambiguity", "profile_merge")

builder.add_edge("profile_merge", "router")

builder.add_conditional_edges(
    "router",
    route_interview,
    {
        "technical": "technical",
        "behavioral": "behavioral",
    },
)

def has_answer(state: InterviewState):
    answer = state.get("user_answer", "")
    if answer and answer.strip() and answer != "NO ANSWER PROVIDED":
        return "evaluate"
    return "end"

builder.add_conditional_edges(
    "technical",
    has_answer,
    {"evaluate": "evaluation", "end": END},
)
builder.add_conditional_edges(
    "behavioral",
    has_answer,
    {"evaluate": "evaluation", "end": END},
)
builder.add_edge("evaluation", "fusion")
builder.add_edge("fusion", "report")
builder.add_edge("report", END)

interview_graph = builder.compile()
if _LANGFUSE_ENABLED and _langfuse:
    _langfuse.flush()