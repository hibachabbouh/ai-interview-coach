from typing import Literal
from pydantic import BaseModel, Field


class RouterOutput(BaseModel):
    route: Literal["technical", "behavioral"]
    confidence: float = Field(ge=0.0, le=1.0)