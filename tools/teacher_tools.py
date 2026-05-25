"""
Teacher Tools — Tools exclusively available to the Teacher agent.

These tools structure the lesson, pose questions, and evaluate answers.
The Student agent CANNOT access these tools (enforced by tool_permissions guardrail).
"""

import json
from langchain_core.tools import tool
from models.schemas import (
    LessonPlan,
    Segment,
    QuestionPrompt,
    Evaluation,
    Difficulty,
)


@tool
def create_lesson_plan(topic: str, segment_titles: list[str], segment_concepts: list[list[str]], segment_objectives: list[str]) -> str:
    """
    Create a structured lesson plan for the given topic.
    
    This tool validates and structures the Teacher's lesson plan into
    well-defined segments with learning objectives. Must be called at
    the start of every lecture before teaching begins.
    
    Args:
        topic: The topic of the lesson.
        segment_titles: List of titles for each lesson segment (2-5 segments).
        segment_concepts: List of key concept lists, one per segment.
        segment_objectives: List of learning objectives, one per segment.
    
    Returns:
        JSON string of the validated LessonPlan.
    """
    if len(segment_titles) < 2 or len(segment_titles) > 5:
        return json.dumps({"error": "Lesson plan must have between 2 and 5 segments."})

    if len(segment_titles) != len(segment_concepts) or len(segment_titles) != len(segment_objectives):
        return json.dumps({"error": "segment_titles, segment_concepts, and segment_objectives must all have the same length."})

    segments = []
    for title, concepts, objective in zip(segment_titles, segment_concepts, segment_objectives):
        segment = Segment(
            title=title,
            key_concepts=concepts,
            learning_objective=objective,
            estimated_exchanges=3,
        )
        segments.append(segment)

    plan = LessonPlan(
        topic=topic,
        overview=f"A structured lesson on {topic} covering {len(segments)} key areas.",
        segments=segments,
        total_estimated_exchanges=sum(s.estimated_exchanges for s in segments),
    )

    return plan.model_dump_json()


@tool
def pose_question(question: str, difficulty: str, expected_concepts: list[str], segment_index: int, hint: str = "") -> str:
    """
    Pose a comprehension question to check the student's understanding.
    
    This tool structures a question with metadata so the orchestrator
    can route it to either the user or the Student agent for answering.
    
    Args:
        question: The question text to ask.
        difficulty: Difficulty level — one of "easy", "medium", "hard".
        expected_concepts: Key concepts a correct answer should demonstrate.
        segment_index: Which lesson segment this question belongs to (0-indexed).
        hint: Optional hint to provide if the student struggles.
    
    Returns:
        JSON string of the validated QuestionPrompt.
    """
    try:
        diff = Difficulty(difficulty)
    except ValueError:
        return json.dumps({"error": f"Invalid difficulty '{difficulty}'. Must be one of: easy, medium, hard."})

    prompt = QuestionPrompt(
        question=question,
        difficulty=diff,
        hint=hint if hint else None,
        expected_concepts=expected_concepts,
        segment_index=segment_index,
    )

    return prompt.model_dump_json()


@tool
def evaluate_answer(answer: str, question: str, expected_concepts: list[str]) -> str:
    """
    Evaluate an answer given by the Student or the User.
    
    This tool checks the answer against expected concepts and returns
    structured feedback. The Teacher uses this to decide whether to
    re-explain, give hints, or move on.
    
    Note: This tool provides a structural framework for evaluation.
    The Teacher agent uses its own judgment (via the LLM) to fill in
    the qualitative assessment — the tool ensures the output is structured.
    
    Args:
        answer: The answer text to evaluate.
        question: The original question that was asked.
        expected_concepts: Key concepts the answer should demonstrate.
    
    Returns:
        JSON string of the Evaluation result.
    """
    # The actual evaluation logic is handled by the LLM (Teacher agent).
    # This tool provides structure and validation for the output.
    # We return the input data so the Teacher can reason about it
    # and produce a structured evaluation in its response.
    return json.dumps({
        "answer_received": answer,
        "question": question,
        "expected_concepts": expected_concepts,
        "instruction": "Evaluate this answer against the expected concepts. "
                       "Determine if it is correct, assign a score from 0.0 to 1.0, "
                       "provide detailed feedback, note any misconceptions, "
                       "and give the correct explanation."
    })
