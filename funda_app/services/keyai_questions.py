"""
Hardcoded Key.ai application question definitions and extraction.

The six questions in the member application payload are fixed. This module
provides a single source of truth for matching question text and extracting
answers.
"""

from enum import StrEnum

from funda_app.schemas.webhooks import MemberQuestionPayload


class KeyaiQuestionField(StrEnum):
    """Fixed Key.ai application question fields."""

    LINKEDIN_URL = "linkedin_url"
    WHATSAPP_PHONE_NUMBER = "whatsapp_phone_number"
    COMPANY_NAME = "company_name"
    COMPANY_WEBSITE_DOMAIN = "company_website_domain"
    JOB_TITLE = "job_title"
    FUNDING_STAGE = "funding_stage"


# Substring(s) used to match incoming question text (case-insensitive).
# First match wins; order does not matter for uniqueness.
_KEYAI_QUESTION_PATTERNS: dict[KeyaiQuestionField, list[str]] = {
    KeyaiQuestionField.LINKEDIN_URL: ["linked"],
    KeyaiQuestionField.WHATSAPP_PHONE_NUMBER: ["whatsapp"],
    KeyaiQuestionField.COMPANY_NAME: ["company name"],
    KeyaiQuestionField.COMPANY_WEBSITE_DOMAIN: ["website", "domain"],
    KeyaiQuestionField.JOB_TITLE: ["job title"],
    KeyaiQuestionField.FUNDING_STAGE: ["funding stage"],
}


def get_question_answer(
    questions: list[MemberQuestionPayload] | None,
    field: KeyaiQuestionField,
) -> str | None:
    """
    Returns the answer for a given Key.ai question field, or None if not found.

    Matches payload question text against hardcoded patterns for the six
    fixed application questions.

    Args:
        questions: List of question/answer pairs from the webhook payload.
        field: Which fixed question to look up.

    Returns:
        The trimmed answer string, or None when the question is absent or
        the answer is empty after stripping.
    """
    if questions is None:
        return None

    patterns = _KEYAI_QUESTION_PATTERNS.get(field, [])
    for item in questions:
        lowered_question = item.question.lower()
        for pattern in patterns:
            if pattern.lower() in lowered_question:
                value = (item.answer or "").strip()
                return value if value else None

    return None
