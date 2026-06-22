

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field




class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    agent: str = Field(
        default="technical",
        description="Name of the agent to call (must be in AGENT_COMPLEXITY map).",
    )
    user_content: str = Field(
        default="",
        description="User message text (used when `messages` is not provided).",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Override the system prompt (used with user_content).",
    )
    messages: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Full message list. Overrides user_content / system_prompt when set.",
    )
    session_id: str = Field(default="no-session")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1)
    json_mode: bool = Field(
        default=False,
        description="If true, instructs the model to output valid JSON.",
    )
    complexity_override: Optional[Literal["simple", "medium", "complex"]] = Field(
        default=None,
        description="Override the automatic complexity routing.",
    )


class ChatResponse(BaseModel):
    """Body for POST /chat response."""
    reply: str
    agent: str
    model: str
    complexity: str
    session_id: str
    token_usage: Dict[str, Any] = Field(default_factory=dict)




class SearchRequest(BaseModel):
    """Body for POST /search."""
    query: str = Field(..., min_length=1, description="Search query string.")
    domains: Optional[List[str]] = Field(
        default=None,
        description="Restrict results to these domains (Tavily include_domains).",
    )
    max_results: int = Field(default=5, ge=1, le=20)
    search_depth: Literal["basic", "advanced"] = Field(default="basic")


class SearchResult(BaseModel):
    """A single Tavily search result."""
    title: Optional[str] = None
    url: Optional[str] = None
    content: Optional[str] = None
    score: Optional[float] = None


class SearchResponse(BaseModel):
    """Body for POST /search response."""
    query: str
    results: List[Dict[str, Any]]
    cache_hit: bool
    source: Literal["cache", "live"]




class InterviewRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None
    language: Optional[str] = "en"
    turn: Optional[int] = 0
    awaiting_answer: Optional[bool] = False      
    current_question: Optional[str] = None       

    target_question_count: Optional[int] = 5     
    reset_session: Optional[bool] = False         


class InterviewResponse(BaseModel):
    allowed: bool
    guardrail_reason: Optional[str] = None

    question: Optional[str] = None
    awaiting_answer: bool = False

    summary: Optional[str] = None
    final_report: Optional[str] = None
    title: Optional[str] = None
    final_overall_score: Optional[float] = None
    next_steps: Optional[list] = None

    session_id: Optional[str] = None

   
    question_count: Optional[int] = None
    target_question_count: Optional[int] = None
    score_history: Optional[List[float]] = None
    average_score: Optional[float] = None
    session_complete: Optional[bool] = False

    
    role: Optional[str] = None
    experience_level: Optional[str] = None
    company: Optional[str] = None