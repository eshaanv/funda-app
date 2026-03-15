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


def get_linkedin_url(
    member_linkedin_url: str | None,
    questions: list[MemberQuestionPayload] | None,
) -> str | None:
    """Returns LinkedIn URL from member field or questions, trimmed, or None."""
    if member_linkedin_url and member_linkedin_url.strip():
        return member_linkedin_url.strip()
    value = get_question_answer(questions, KeyaiQuestionField.LINKEDIN_URL)
    if value is None or not value.strip():
        return None
    return value.strip()


def get_company_name(
    member_company_name: str | None,
    questions: list[MemberQuestionPayload] | None,
) -> str | None:
    """Returns company name from member field or questions, trimmed, or None."""
    if member_company_name and member_company_name.strip():
        return member_company_name.strip()
    value = get_question_answer(questions, KeyaiQuestionField.COMPANY_NAME)
    if value is None or not value.strip():
        return None
    return value.strip()


def get_company_stage(
    member_company_stage: str | None,
    questions: list[MemberQuestionPayload] | None,
) -> str | None:
    """Returns company/funding stage from member field or questions, trimmed, or None."""
    if member_company_stage and member_company_stage.strip():
        return member_company_stage.strip()
    value = get_question_answer(questions, KeyaiQuestionField.FUNDING_STAGE)
    if value is None or not value.strip():
        return None
    return value.strip()


def get_job_title(
    questions: list[MemberQuestionPayload] | None,
) -> str | None:
    """Returns job title from questions, or None."""
    return get_question_answer(questions, KeyaiQuestionField.JOB_TITLE)


def get_company_website_domain(
    questions: list[MemberQuestionPayload] | None,
) -> str | None:
    """Returns company website domain from questions, or None."""
    return get_question_answer(questions, KeyaiQuestionField.COMPANY_WEBSITE_DOMAIN)
