from pydantic import BaseModel, Field
from typing import List, Optional


class StructuredData(BaseModel):
    title: str
    summary: str
    overall_score: Optional[float] = Field(default=None)
    strengths: List[str]
    weaknesses: List[str]
    next_steps: List[str]


class ReportOutput(BaseModel):
    markdown_report: str
    structured_data: StructuredData