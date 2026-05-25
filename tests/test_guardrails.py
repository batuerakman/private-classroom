"""
Tests for the guardrail system.

Tests that input validation, scope checking, and tool permissions
work correctly and actually block invalid inputs.
"""

import pytest
from guardrails.topic_validator import validate_topic
from guardrails.tool_permissions import validate_tool_call, get_tools_for_agent


# ─── Topic Validator Tests ─────────────────────────────────────────────────────

class TestTopicValidator:
    """Tests for the input guardrail (topic validation)."""

    def test_valid_topic(self):
        """Normal topics should be accepted."""
        result = validate_topic("Bohr's atom model")
        assert result.is_valid is True
        assert result.sanitized_topic == "Bohr's atom model"

    def test_valid_topic_with_extra_spaces(self):
        """Topics with extra whitespace should be sanitized."""
        result = validate_topic("  quantum   mechanics  ")
        assert result.is_valid is True
        assert result.sanitized_topic == "quantum mechanics"

    def test_empty_topic(self):
        """Empty topics should be rejected."""
        result = validate_topic("")
        assert result.is_valid is False
        assert "too short" in result.rejection_reason.lower()

    def test_too_short_topic(self):
        """Very short topics should be rejected."""
        result = validate_topic("ab")
        assert result.is_valid is False

    def test_too_long_topic(self):
        """Excessively long topics should be rejected."""
        result = validate_topic("a" * 201)
        assert result.is_valid is False
        assert "too long" in result.rejection_reason.lower()

    def test_harmful_topic_weapons(self):
        """Topics about creating weapons should be rejected."""
        result = validate_topic("how to make a bomb")
        assert result.is_valid is False
        assert "not appropriate" in result.rejection_reason.lower()

    def test_harmful_topic_self_harm(self):
        """Topics about self-harm should be rejected."""
        result = validate_topic("methods of self-harm")
        assert result.is_valid is False

    def test_harmful_topic_hacking(self):
        """Topics about hacking into systems should be rejected."""
        result = validate_topic("hack into a bank system")
        assert result.is_valid is False

    def test_whitespace_only(self):
        """Whitespace-only input should be rejected."""
        result = validate_topic("   ")
        assert result.is_valid is False

    def test_legitimate_chemistry(self):
        """Legitimate chemistry topics should NOT be blocked."""
        result = validate_topic("chemical reactions in organic chemistry")
        assert result.is_valid is True

    def test_legitimate_security(self):
        """Legitimate cybersecurity topics should NOT be blocked."""
        result = validate_topic("principles of cybersecurity")
        assert result.is_valid is True


# ─── Tool Permission Tests ─────────────────────────────────────────────────────

class TestToolPermissions:
    """Tests for the tool-level guardrail."""

    def test_teacher_can_use_teacher_tools(self):
        """Teacher should have access to its own tools."""
        assert validate_tool_call("teacher", "create_lesson_plan") is True
        assert validate_tool_call("teacher", "pose_question") is True
        assert validate_tool_call("teacher", "evaluate_answer") is True

    def test_teacher_cannot_use_student_tools(self):
        """Teacher should NOT have access to Student tools."""
        assert validate_tool_call("teacher", "attempt_answer") is False
        assert validate_tool_call("teacher", "ask_clarification") is False

    def test_student_can_use_student_tools(self):
        """Student should have access to its own tools."""
        assert validate_tool_call("student", "attempt_answer") is True
        assert validate_tool_call("student", "ask_clarification") is True

    def test_student_cannot_use_teacher_tools(self):
        """Student should NOT have access to Teacher tools."""
        assert validate_tool_call("student", "create_lesson_plan") is False
        assert validate_tool_call("student", "pose_question") is False
        assert validate_tool_call("student", "evaluate_answer") is False

    def test_unknown_agent_denied(self):
        """Unknown agent roles should be denied all tools."""
        assert validate_tool_call("hacker", "create_lesson_plan") is False
        assert validate_tool_call("", "attempt_answer") is False

    def test_unknown_tool_denied(self):
        """Unknown tool names should be denied for any agent."""
        assert validate_tool_call("teacher", "delete_everything") is False
        assert validate_tool_call("student", "run_code") is False

    def test_get_tools_for_teacher(self):
        """get_tools_for_agent should return correct tools for teacher."""
        tools = get_tools_for_agent("teacher")
        tool_names = {t.name for t in tools}
        assert tool_names == {"create_lesson_plan", "pose_question", "evaluate_answer"}

    def test_get_tools_for_student(self):
        """get_tools_for_agent should return correct tools for student."""
        tools = get_tools_for_agent("student")
        tool_names = {t.name for t in tools}
        assert tool_names == {"attempt_answer", "ask_clarification"}

    def test_get_tools_for_unknown_raises(self):
        """get_tools_for_agent should raise ValueError for unknown roles."""
        with pytest.raises(ValueError):
            get_tools_for_agent("admin")
