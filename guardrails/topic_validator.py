"""
Topic Validator — Input guardrail.

Validates user-submitted topics before a lecture begins.
Rejects harmful, empty, or inappropriate topics.
"""

import re
from models.schemas import TopicValidationResult


# Topics/keywords that are explicitly blocked
BLOCKED_PATTERNS = [
    r"\bhow\s+to\s+(make|build|create)\s+(a\s+)?(bomb|weapon|explosive|drug)",
    r"\b(kill|murder|harm|hurt|attack)\s+(someone|people|a\s+person)",
    r"\b(hack|exploit|breach)\s+(into|a\s+)",
    r"\b(illegal|illicit)\s+(drug|substance|activity)",
    r"\bself[- ]?harm",
    r"\bsuicid",
    r"\bterroris",
    r"\bchild\s+(abuse|exploitation|pornography)",
]

# Minimum topic length (characters)
MIN_TOPIC_LENGTH = 3

# Maximum topic length (characters) 
MAX_TOPIC_LENGTH = 200


def validate_topic(topic: str) -> TopicValidationResult:
    """
    Validate a user-submitted topic for the lecture.
    
    Checks for:
    - Empty or too-short input
    - Excessively long input
    - Harmful or inappropriate content (regex pattern matching)
    - Basic sanitization (stripping whitespace, normalizing)
    
    Args:
        topic: The raw topic string from the user.
    
    Returns:
        TopicValidationResult with is_valid flag and either the 
        sanitized topic or a rejection reason.
    """
    # Strip whitespace
    cleaned = topic.strip()

    # Check empty / too short
    if not cleaned or len(cleaned) < MIN_TOPIC_LENGTH:
        return TopicValidationResult(
            is_valid=False,
            rejection_reason="Topic is too short. Please provide a meaningful topic "
                           f"(at least {MIN_TOPIC_LENGTH} characters)."
        )

    # Check too long
    if len(cleaned) > MAX_TOPIC_LENGTH:
        return TopicValidationResult(
            is_valid=False,
            rejection_reason=f"Topic is too long (max {MAX_TOPIC_LENGTH} characters). "
                           "Please provide a concise topic description."
        )

    # Check against blocked patterns
    lower_cleaned = cleaned.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, lower_cleaned):
            return TopicValidationResult(
                is_valid=False,
                rejection_reason="This topic contains content that is not appropriate "
                               "for a lecture. Please choose a different topic."
            )

    # Sanitize: collapse multiple spaces, basic normalization
    sanitized = re.sub(r"\s+", " ", cleaned)

    return TopicValidationResult(
        is_valid=True,
        sanitized_topic=sanitized,
    )
