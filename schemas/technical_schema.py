from pydantic import BaseModel
from typing import List


class TechnicalOutput(BaseModel):
    question_id: str
    question: str
    difficulty: str  
    topics: List[str]