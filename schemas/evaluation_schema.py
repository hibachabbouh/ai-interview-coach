from pydantic import BaseModel
from typing import List


class EvaluationOutput(BaseModel):
    technical_score: float
    communication_score: float
    confidence_score: float
    overall_score: float

    strengths: List[str]
    weaknesses: List[str]