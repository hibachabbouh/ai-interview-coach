from pydantic import BaseModel
from typing import List


class FusionOutput(BaseModel):
    overall_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]