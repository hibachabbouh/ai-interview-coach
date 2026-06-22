from pydantic import BaseModel


class BehavioralOutput(BaseModel):
    question_id: str
    question: str
    skill_assessed: str
    difficulty: str