from typing import List, Optional
from pydantic import BaseModel, Field


class RoutingDecision(BaseModel):
    """Output of the Coordinator's routing step."""

    topic: str = Field(..., description="The core topic the student wants to study")
    subtopic: Optional[str] = Field(None, description="A narrower focus within the topic, if any")
    level: str = Field("beginner", description="beginner | intermediate | advanced")
    clarification_needed: bool = Field(
        False, description="True if the request is too vague/ambiguous to proceed"
    )
    clarification_question: Optional[str] = Field(
        None, description="Question to ask the student if clarification_needed is True"
    )


class QuizQuestion(BaseModel):
    id: int
    question: str
    choices: Optional[List[str]] = Field(
        None, description="Multiple-choice options, if applicable. Null for short-answer questions."
    )
    correct_answer: str
    explanation: str = Field(..., description="Why this is the correct answer, used later for feedback")
    difficulty: str = Field("beginner", description="beginner | intermediate | advanced")


class QuizSet(BaseModel):
    topic: str
    questions: List[QuizQuestion]


class AnswerFeedback(BaseModel):
    question_id: int
    student_answer: str
    is_correct: bool
    feedback: str


class EvaluationResult(BaseModel):
    topic: str
    score_percent: float
    feedback_items: List[AnswerFeedback]
    weak_areas: List[str] = Field(default_factory=list)
    recommend_reteach: bool = False
    encouragement: str
