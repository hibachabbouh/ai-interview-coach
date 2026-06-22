from pydantic import BaseModel, Field
from typing import List, Optional


class AmbiguityOutput(BaseModel):
    is_ambiguous: bool
    missing_fields: List[str] = Field(default_factory=list)
    clarification_question: Optional[str] = ""
    role: Optional[str] = None
    experience_level: Optional[str] = None
    company: Optional[str] = None