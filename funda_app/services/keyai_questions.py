"""
Key.ai application question extraction by semantic key.
"""

from enum import StrEnum

from funda_app.schemas.webhooks import MemberQuestionPayload


class KeyaiQuestionField(StrEnum):
    """Fixed Key.ai application question fields."""

    LINKEDIN_URL = "linked_in_url"
    WHATSAPP_PHONE_NUMBER = "whatsapp_number"
    COMPANY_NAME = "company_name"
    COMPANY_WEBSITE_DOMAIN = "company_website_domain"
    JOB_TITLE = "job_title"
    FUNDING_STAGE = "funding_stage"


def get_question_answer(
    questions: list[MemberQuestionPayload] | None,
    field: KeyaiQuestionField,
) -> str | None:
    """
    Returns the answer for a given Key.ai question field, or None if not found.

    Matches payload question semantic keys against the fixed question fields.

    Args:
        questions: List of question/answer pairs from the webhook payload.
        field: Which fixed question to look up.

    Returns:
        The trimmed answer string, or None when the question is absent or
        the answer is empty after stripping.
    """
    if questions is None:
        return None

    for item in questions:
        if item.semantic_key == field.value:
            value = (item.answer or "").strip()
            return value if value else None

    return None


def get_linkedin_url(
    questions: list[MemberQuestionPayload] | None,
) -> str | None:
    """Returns LinkedIn URL from questions, trimmed, or None."""
    value = get_question_answer(questions, KeyaiQuestionField.LINKEDIN_URL)
    if value is None or not value.strip():
        return None
    return value.strip()


def get_company_name(
    questions: list[MemberQuestionPayload] | None,
) -> str | None:
    """Returns company name from questions, trimmed, or None."""
    value = get_question_answer(questions, KeyaiQuestionField.COMPANY_NAME)
    if value is None or not value.strip():
        return None
    return value.strip()


def get_company_stage(
    questions: list[MemberQuestionPayload] | None,
) -> str | None:
    """Returns company/funding stage from questions, trimmed, or None."""
    value = get_question_answer(questions, KeyaiQuestionField.FUNDING_STAGE)
    if value is None or not value.strip():
        return None
    return value.strip()


def get_whatsapp_phone_number(
    questions: list[MemberQuestionPayload] | None,
) -> str | None:
    """Returns WhatsApp phone number from questions, trimmed, or None."""
    value = get_question_answer(questions, KeyaiQuestionField.WHATSAPP_PHONE_NUMBER)
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
