"""
Pydantic models for the Private Lecture multi-agent system.

All tool inputs and outputs are defined here as structured schemas,
ensuring validated data flows between agents and tools.
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────

class Difficulty(str, Enum):
    """Difficulty level for questions posed by the Teacher."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Confidence(str, Enum):
    """Confidence level for the Student's answer attempts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MisconceptionType(str, Enum):
    """Types of misconceptions the Student might exhibit."""
    OVERGENERALIZATION = "overgeneralization"      # Applying a rule too broadly
    CONFUSION_SIMILAR = "confusion_with_similar"   # Mixing up related concepts
    PARTIAL_UNDERSTANDING = "partial_understanding" # Gets part right, part wrong
    COMMON_MYTH = "common_myth"                     # Believes a popular but wrong idea
    NONE = "none"                                   # No misconception


# ─── Lesson Planning Models ──────────────────────────────────────────────────

class Segment(BaseModel):
    """A single segment of a lesson plan."""
    title: str = Field(description="Title of this lesson segment")
    key_concepts: list[str] = Field(description="Key concepts to cover in this segment")
    learning_objective: str = Field(description="What the student should understand after this segment")
    estimated_exchanges: int = Field(
        default=3,
        ge=1,
        le=6,
        description="Estimated number of exchanges (teacher messages) for this segment"
    )


class LessonPlan(BaseModel):
    """Structured lesson plan created by the Teacher for a given topic."""
    topic: str = Field(description="The topic of the lesson")
    overview: str = Field(description="Brief overview of what this lesson covers")
    prerequisites: list[str] = Field(
        default_factory=list,
        description="Concepts the student should ideally know before this lesson"
    )
    segments: list[Segment] = Field(
        description="Ordered list of lesson segments",
        min_length=2,
        max_length=5
    )
    total_estimated_exchanges: int = Field(
        description="Total estimated exchanges across all segments"
    )


# ─── Question & Answer Models ────────────────────────────────────────────────

class QuestionPrompt(BaseModel):
    """A question posed by the Teacher to check understanding."""
    question: str = Field(description="The question text")
    difficulty: Difficulty = Field(description="Difficulty level of the question")
    hint: Optional[str] = Field(
        default=None,
        description="Optional hint to help guide the answer"
    )
    expected_concepts: list[str] = Field(
        description="Key concepts that a correct answer should demonstrate"
    )
    segment_index: int = Field(
        ge=0,
        description="Which segment this question belongs to"
    )


class Evaluation(BaseModel):
    """Teacher's evaluation of an answer (from Student or User)."""
    is_correct: bool = Field(description="Whether the answer is substantially correct")
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score from 0.0 (completely wrong) to 1.0 (perfect)"
    )
    feedback: str = Field(description="Detailed feedback on the answer")
    misconception: Optional[str] = Field(
        default=None,
        description="Description of any misconception detected in the answer"
    )
    correct_explanation: str = Field(
        description="The correct answer / explanation for learning purposes"
    )


class StudentAnswer(BaseModel):
    """The Student agent's attempt at answering a question."""
    answer: str = Field(description="The Student's answer text")
    confidence: Confidence = Field(description="How confident the Student is in this answer")
    reasoning: str = Field(description="The Student's reasoning process (may contain errors)")
    is_intentionally_wrong: bool = Field(
        default=False,
        description="Internal flag — whether this answer is deliberately wrong for pedagogical value"
    )


class ClarificationRequest(BaseModel):
    """A clarification question asked by the Student."""
    question: str = Field(description="The clarification question")
    confused_about: str = Field(description="What specific concept is confusing")
    misconception_type: MisconceptionType = Field(
        default=MisconceptionType.NONE,
        description="Type of misconception driving this question, if any"
    )


# ─── Guardrail Models ────────────────────────────────────────────────────────

class TopicValidationResult(BaseModel):
    """Result of validating a user-submitted topic."""
    is_valid: bool = Field(description="Whether the topic is acceptable")
    sanitized_topic: Optional[str] = Field(
        default=None,
        description="Cleaned/normalized version of the topic, if valid"
    )
    rejection_reason: Optional[str] = Field(
        default=None,
        description="Why the topic was rejected, if invalid"
    )


class ScopeCheckResult(BaseModel):
    """Result of checking whether a message stays on-topic."""
    is_on_topic: bool = Field(description="Whether the content stays within the lecture scope")
    original_topic: str = Field(description="The declared lecture topic")
    deviation_description: Optional[str] = Field(
        default=None,
        description="Description of how the content deviates, if it does"
    )


# ─── Orchestrator State ──────────────────────────────────────────────────────

class LectureState(BaseModel):
    """The current state of the lecture, tracked by the orchestrator."""
    topic: str = Field(description="The lecture topic")
    lesson_plan: Optional[LessonPlan] = Field(
        default=None,
        description="The structured lesson plan"
    )
    current_segment_index: int = Field(
        default=0,
        description="Index of the current segment being taught"
    )
    messages: list[dict] = Field(
        default_factory=list,
        description="Full conversation history"
    )
    pending_question: Optional[QuestionPrompt] = Field(
        default=None,
        description="A question currently awaiting an answer"
    )
    waiting_for_user: bool = Field(
        default=False,
        description="Whether the system is waiting for user input on a question"
    )
    question_attempts: int = Field(
        default=0,
        description="Number of attempts on the current question (max 3)"
    )
    lecture_complete: bool = Field(
        default=False,
        description="Whether the lecture has been completed"
    )
    exchanges_in_segment: int = Field(
        default=0,
        description="Number of teacher exchanges in the current segment"
    )
