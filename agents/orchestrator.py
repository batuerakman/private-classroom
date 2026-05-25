"""
Orchestrator — Manages the lecture flow between Teacher, Student, and User.

Uses a simple, explicit turn-taking approach rather than a complex graph.
Each step is clear and debuggable — important for the showcase demo.
"""

import json
import logging
from typing import Optional
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    BaseMessage,
)

from agents.teacher import create_teacher_agent, get_teacher_system_message
from agents.student import create_student_agent, get_student_system_message
from guardrails.tool_permissions import validate_tool_call, get_tools_for_agent

logger = logging.getLogger(__name__)


# ─── Constants ─────────────────────────────────────────────────────────────────

MAX_QUESTION_ATTEMPTS = 3
MAX_EXCHANGES_PER_SEGMENT = 4  # Keeps ~7 min total for 3 segments


# ─── Tool Processing ──────────────────────────────────────────────────────────

def process_tool_calls(response: AIMessage, agent_role: str) -> list[ToolMessage]:
    """
    Process tool calls from an agent response.
    Validates permissions (guardrail) and executes the tools.
    """
    if not hasattr(response, "tool_calls") or not response.tool_calls:
        return []

    tool_messages = []
    tools = {t.name: t for t in get_tools_for_agent(agent_role)}

    for tool_call in response.tool_calls:
        tool_name = tool_call["name"]

        # Guardrail: check tool permissions
        if not validate_tool_call(agent_role, tool_name):
            tool_messages.append(
                ToolMessage(
                    content=json.dumps({
                        "error": f"Permission denied: {agent_role} agent is not allowed to call '{tool_name}'."
                    }),
                    tool_call_id=tool_call["id"],
                )
            )
            continue

        tool = tools.get(tool_name)
        if tool:
            try:
                result = tool.invoke(tool_call["args"])
                tool_messages.append(
                    ToolMessage(content=result, tool_call_id=tool_call["id"])
                )
            except Exception as e:
                tool_messages.append(
                    ToolMessage(
                        content=json.dumps({"error": f"Tool execution failed: {str(e)}"}),
                        tool_call_id=tool_call["id"],
                    )
                )

    return tool_messages


MAX_RETRIES = 3


def _is_malformed(response) -> bool:
    """Check if the response is a malformed function call from Gemini."""
    finish_reason = response.response_metadata.get("finish_reason", "")
    return finish_reason == "MALFORMED_FUNCTION_CALL"


def _extract_text(content) -> str:
    """Extract text from an AIMessage content field (may be str or list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Multipart content — extract text parts
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
        return "\n".join(parts)
    return str(content) if content else ""


def invoke_agent_with_tools(agent, system_msg, conversation, agent_role: str):
    """
    Invoke an agent, process any tool calls, and get the final response.
    Returns (all_raw_messages, display_text) where display_text is the
    agent's final human-readable output.

    Includes retry logic for Gemini's MALFORMED_FUNCTION_CALL errors.
    """
    messages = [system_msg] + conversation

    # Retry loop — Gemini Flash sometimes produces malformed tool calls
    response = None
    for attempt in range(MAX_RETRIES):
        try:
            response = agent.invoke(messages)
        except Exception as e:
            logger.error(f"Error invoking agent. Messages: {messages}")
            print(f"FAILED MESSAGES DUMP: {messages}")
            raise e
            
        finish_reason = response.response_metadata.get("finish_reason", "")
        logger.info(
            f"[{agent_role}] attempt {attempt + 1}: "
            f"content_len={len(_extract_text(response.content))}, "
            f"tool_calls={len(response.tool_calls) if response.tool_calls else 0}, "
            f"finish_reason={finish_reason}"
        )

        if not _is_malformed(response):
            break

        logger.warning(
            f"[{agent_role}] MALFORMED_FUNCTION_CALL on attempt {attempt + 1}, retrying..."
        )
    else:
        # All retries exhausted — fall back to a no-tools call
        logger.error(f"[{agent_role}] All {MAX_RETRIES} attempts returned MALFORMED_FUNCTION_CALL")

    all_messages = [response]
    display_text = _extract_text(response.content)

    # Process tool calls if the agent made any
    tool_results = process_tool_calls(response, agent_role)
    if tool_results:
        all_messages.extend(tool_results)

        # Get follow-up response after tool execution
        follow_up_msgs = messages + all_messages
        follow_up = agent.invoke(follow_up_msgs)
        all_messages.append(follow_up)
        display_text = _extract_text(follow_up.content)
        logger.info(
            f"[{agent_role}] follow-up: content_len={len(display_text)}, "
            f"finish_reason={follow_up.response_metadata.get('finish_reason', '')}"
        )

        # Handle chained tool calls (e.g., lesson plan → then start teaching)
        more_tools = process_tool_calls(follow_up, agent_role)
        if more_tools:
            all_messages.extend(more_tools)
            final = agent.invoke(messages + all_messages)
            all_messages.append(final)
            display_text = _extract_text(final.content)

    return all_messages, display_text.strip()


# ─── Lecture State ─────────────────────────────────────────────────────────────

class LectureState:
    """Tracks the state of an ongoing lecture."""

    def __init__(self, topic: str):
        self.topic = topic
        self.teacher_conversation: list[BaseMessage] = []
        self.student_conversation: list[BaseMessage] = []
        self.lesson_plan_json: Optional[str] = None
        self.current_segment: int = 0
        self.exchanges_in_segment: int = 0
        self.segments_completed: int = 0
        self.pending_question: Optional[str] = None
        self.question_attempts: int = 0
        self.lecture_complete: bool = False

    def to_dict(self):
        """Serialize for session state storage."""
        return {
            "topic": self.topic,
            "teacher_conversation": self.teacher_conversation,
            "student_conversation": self.student_conversation,
            "lesson_plan_json": self.lesson_plan_json,
            "current_segment": self.current_segment,
            "exchanges_in_segment": self.exchanges_in_segment,
            "segments_completed": self.segments_completed,
            "pending_question": self.pending_question,
            "question_attempts": self.question_attempts,
            "lecture_complete": self.lecture_complete,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Deserialize from session state."""
        state = cls(data["topic"])
        state.teacher_conversation = data["teacher_conversation"]
        state.student_conversation = data["student_conversation"]
        state.lesson_plan_json = data["lesson_plan_json"]
        state.current_segment = data["current_segment"]
        state.exchanges_in_segment = data["exchanges_in_segment"]
        state.segments_completed = data["segments_completed"]
        state.pending_question = data["pending_question"]
        state.question_attempts = data["question_attempts"]
        state.lecture_complete = data["lecture_complete"]
        return state

    @property
    def total_segments(self) -> int:
        if self.lesson_plan_json:
            try:
                plan = json.loads(self.lesson_plan_json)
                return len(plan.get("segments", []))
            except (json.JSONDecodeError, KeyError):
                pass
        return 3


# ─── Orchestration Functions ──────────────────────────────────────────────────

def run_teacher_turn(state: LectureState) -> tuple[list[dict], LectureState]:
    """
    Run one Teacher turn. Returns display messages and updated state.
    
    Display messages are [{role: "teacher", content: "..."}]
    """
    teacher_agent = create_teacher_agent()
    teacher_system = get_teacher_system_message()

    # Build context instruction based on lecture state
    if not state.lesson_plan_json:
        context = (
            f"The student wants to learn about: {state.topic}. "
            "First, use the create_lesson_plan tool to structure the lesson into 3 segments. "
            "Then introduce yourself briefly and start teaching the first segment. "
            "Keep your introduction warm but concise."
        )
    elif state.exchanges_in_segment >= MAX_EXCHANGES_PER_SEGMENT:
        context = (
            f"You've been teaching segment {state.current_segment + 1} for a while. "
            "Ask a comprehension question using the pose_question tool to check understanding "
            "before moving on."
        )
    else:
        context = (
            f"Continue teaching about {state.topic}. "
            f"You are on segment {state.current_segment + 1}. "
            "Deliver the next piece of your lesson. Keep it focused — one key idea per message."
        )

    # Add context as a system-level instruction
    context_msg = HumanMessage(content=f"[SYSTEM]: {context}")
    conversation_with_context = state.teacher_conversation + [context_msg]

    raw_messages, display_text = invoke_agent_with_tools(
        teacher_agent, teacher_system, conversation_with_context, "teacher"
    )

    # Update conversation history with both the context prompt and the agent's responses
    state.teacher_conversation.append(context_msg)
    state.teacher_conversation.extend(raw_messages)
    
    if display_text:
        state.student_conversation.append(HumanMessage(content=f"[Professor]: {display_text}"))

    # Check for tool calls to update state
    question_posed = False
    for msg in raw_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "create_lesson_plan":
                    # Find the tool result
                    for tm in raw_messages:
                        if isinstance(tm, ToolMessage) and tm.tool_call_id == tc["id"]:
                            state.lesson_plan_json = tm.content
                            break

                if tc["name"] == "pose_question":
                    for tm in raw_messages:
                        if isinstance(tm, ToolMessage) and tm.tool_call_id == tc["id"]:
                            state.pending_question = tm.content
                            state.question_attempts = 0
                            question_posed = True
                            break

    if not question_posed:
        state.exchanges_in_segment += 1

    display_messages = []
    if display_text:
        display_messages.append({"role": "teacher", "content": display_text})

    return display_messages, state


def run_student_turn(state: LectureState, is_answering: bool = False) -> tuple[list[dict], LectureState]:
    """
    Run one Student turn. Returns display messages and updated state.
    
    If is_answering=True, the student is answering a pending question.
    Otherwise, the student reacts to the teacher's explanation.
    """
    student_agent = create_student_agent()
    student_system = get_student_system_message()

    if is_answering and state.pending_question:
        context = (
            "The Teacher just asked you a question. Use the attempt_answer tool to answer it. "
            "Remember: you should get answers wrong about 40-60% of the time. "
            "Be realistic — sometimes you don't know, sometimes you're partially right, "
            "sometimes you confuse related concepts."
        )
    else:
        context = (
            "The Teacher just explained something. React naturally as a student. "
            "You can either: "
            "1) Ask a clarifying question using the ask_clarification tool (about 50% of the time), or "
            "2) Make a brief comment showing engagement ('Oh, that makes sense!' or 'Hmm, so it's kind of like...'). "
            "Keep it short and natural. Don't repeat what the teacher said."
        )

    context_msg = HumanMessage(content=f"[SYSTEM]: {context}")
    conversation_with_context = state.student_conversation + [context_msg]

    raw_messages, display_text = invoke_agent_with_tools(
        student_agent, student_system, conversation_with_context, "student"
    )

    # Update conversation history
    state.student_conversation.append(context_msg)
    state.student_conversation.extend(raw_messages)

    if display_text:
        state.teacher_conversation.append(HumanMessage(content=f"[Alex (Student)]: {display_text}"))

    display_messages = []
    if display_text:
        display_messages.append({"role": "student", "content": display_text})

    return display_messages, state


def run_teacher_evaluate(state: LectureState, answer: str, answerer: str) -> tuple[list[dict], LectureState]:
    """
    Run the Teacher's evaluation of an answer.
    Returns display messages and updated state.
    """
    teacher_agent = create_teacher_agent()
    teacher_system = get_teacher_system_message()

    context = (
        f"The {answerer} answered your question. Their answer: \"{answer}\". "
        "Evaluate their answer directly and respond to them. "
        "Provide encouraging feedback, correct any misconceptions, and then continue "
        "teaching the next part of the lesson."
    )

    context_msg = HumanMessage(content=f"[SYSTEM]: {context}")
    conversation_with_context = state.teacher_conversation + [context_msg]

    raw_messages, display_text = invoke_agent_with_tools(
        teacher_agent, teacher_system, conversation_with_context, "teacher"
    )

    state.teacher_conversation.append(context_msg)
    state.teacher_conversation.extend(raw_messages)

    if display_text:
        state.student_conversation.append(HumanMessage(content=f"[Professor]: {display_text}"))
    state.pending_question = None
    state.question_attempts = 0

    # Advance segment after a question cycle
    state.segments_completed += 1
    state.current_segment += 1
    state.exchanges_in_segment = 0

    # Check if lecture is complete
    if state.segments_completed >= state.total_segments:
        state.lecture_complete = True

    display_messages = []
    if display_text:
        display_messages.append({"role": "teacher", "content": display_text})

    return display_messages, state


def run_teacher_respond_to_user(state: LectureState, user_message: str) -> tuple[list[dict], LectureState]:
    """
    Run the Teacher's response to a user comment/question.
    """
    teacher_agent = create_teacher_agent()
    teacher_system = get_teacher_system_message()

    user_msg = HumanMessage(content=f"[User]: {user_message}")
    state.teacher_conversation.append(user_msg)
    state.student_conversation.append(user_msg)

    context = (
        f"The user has made a comment or asked a question mid-lecture: \"{user_message}\". "
        "Acknowledge their input warmly, address their question or comment, "
        "and seamlessly guide the conversation back to teaching the current segment of the lesson. "
        "Keep it concise."
    )

    context_msg = HumanMessage(content=f"[SYSTEM]: {context}")
    conversation_with_context = state.teacher_conversation + [context_msg]

    raw_messages, display_text = invoke_agent_with_tools(
        teacher_agent, teacher_system, conversation_with_context, "teacher"
    )

    state.teacher_conversation.append(context_msg)
    state.teacher_conversation.extend(raw_messages)

    if display_text:
        state.student_conversation.append(HumanMessage(content=f"[Professor]: {display_text}"))

    display_messages = []
    if display_text:
        display_messages.append({"role": "teacher", "content": display_text})

    return display_messages, state


def run_wrap_up(state: LectureState) -> tuple[list[dict], LectureState]:
    """
    Wrap up the lecture with a summary.
    """
    teacher_agent = create_teacher_agent()
    teacher_system = get_teacher_system_message()

    context = (
        "You've covered all the planned segments. Wrap up the lecture with: "
        "1) A brief summary of the key points covered. "
        "2) An encouraging closing message. "
        "3) Mention that they can start a new lecture to explore more topics. "
        "Keep it concise and warm."
    )

    context_msg = HumanMessage(content=f"[SYSTEM]: {context}")
    conversation_with_context = state.teacher_conversation + [context_msg]

    raw_messages, display_text = invoke_agent_with_tools(
        teacher_agent, teacher_system, conversation_with_context, "teacher"
    )

    state.teacher_conversation.append(context_msg)
    state.teacher_conversation.extend(raw_messages)

    if display_text:
        state.student_conversation.append(HumanMessage(content=f"[Professor]: {display_text}"))
    state.lecture_complete = True

    display_messages = []
    if display_text:
        display_messages.append({"role": "teacher", "content": display_text})

    return display_messages, state
