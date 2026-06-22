from pydantic import BaseModel
from typing import Optional


class GuardrailOutput(BaseModel):
    allowed: bool
    risk_level: str = "low"        
    reason: Optional[str] = ""     