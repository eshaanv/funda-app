"""
Key.ai application question extraction by semantic key.
"""

from enum import StrEnum
import re
from typing import Any

from funda_app.schemas.webhooks import MemberQuestionPayload


class KeyaiQuestionField(StrEnum):
    """Fixed Key.ai application question fields."""

    LINKEDIN_URL = "linked_in_url"
    WHATSAPP_PHONE_NUMBER = "whatsapp_phone_number"
    COMPANY_NAME = "company_name"
    COMPANY_WEBSITE = "company_website"
    JOB_TITLE = "job_title"
    COMPANY_STAGE = "company_stage"
    FUNDING_STAGE = "company_stage"
    MEMBER_TYPE = "member_type"
    COUNTRY_REGION = "country_region"
    FULL_NAME = "full_name"
    INDUSTRY_SECTOR = "industry_sector"
    INVESTOR_STAGE = "investor_stage"
    EXCLUSIVE_BENEFITS_DISCOUNTS = "exclusive_benefits_discounts"
    FUND_WEBSITE = "fund_website"
    ADVISING_MENTORING_FOUNDERS = "advising_mentoring_founders"
    FRACTIONAL_BOARD_ROLES = "fractional_board_roles"
    ORGANIZATION_FIRM_NAME = "organization_firm_name"
    ORGANIZATION_WEBSITE_DOMAIN = "organization_website_domain"
    COMPANIES_WORK_WITH_STAGE = "companies_work_with_stage"
    SERVICES_VALUE_OFFERED = "services_value_offered"


class QuestionFieldDefinition(StrEnum):
    """Question matching modes."""

    SEMANTIC_KEY = "semantic_key"
    KEYWORDS = "keywords"


QUESTION_FIELD_SEMANTIC_KEYS: dict[KeyaiQuestionField, tuple[str, ...]] = {
    KeyaiQuestionField.LINKEDIN_URL: ("linked_in_url", "linkedin_url"),
    KeyaiQuestionField.WHATSAPP_PHONE_NUMBER: (
        "whatsapp_number",
        "whatsapp_phone_number",
    ),
    KeyaiQuestionField.COMPANY_NAME: ("company_name",),
    KeyaiQuestionField.COMPANY_WEBSITE: (
        "company_website",
        "company_website_domain",
    ),
    KeyaiQuestionField.JOB_TITLE: ("job_title",),
    KeyaiQuestionField.COMPANY_STAGE: ("funding_stage", "company_stage"),
    KeyaiQuestionField.MEMBER_TYPE: ("member_type",),
    KeyaiQuestionField.COUNTRY_REGION: ("country_region",),
    KeyaiQuestionField.FULL_NAME: ("full_name",),
    KeyaiQuestionField.INDUSTRY_SECTOR: ("industry_sector",),
    KeyaiQuestionField.INVESTOR_STAGE: ("investor_stage",),
    KeyaiQuestionField.EXCLUSIVE_BENEFITS_DISCOUNTS: ("exclusive_benefits_discounts",),
    KeyaiQuestionField.FUND_WEBSITE: ("fund_website",),
    KeyaiQuestionField.ADVISING_MENTORING_FOUNDERS: ("advising_mentoring_founders",),
    KeyaiQuestionField.FRACTIONAL_BOARD_ROLES: ("fractional_board_roles",),
    KeyaiQuestionField.ORGANIZATION_FIRM_NAME: ("organization_firm_name",),
    KeyaiQuestionField.ORGANIZATION_WEBSITE_DOMAIN: ("organization_website_domain",),
    KeyaiQuestionField.COMPANIES_WORK_WITH_STAGE: ("companies_work_with_stage",),
    KeyaiQuestionField.SERVICES_VALUE_OFFERED: ("services_value_offered",),
}

QUESTION_FIELD_TYPES: dict[KeyaiQuestionField, tuple[str, ...]] = {
    KeyaiQuestionField.LINKEDIN_URL: ("website_url",),
    KeyaiQuestionField.WHATSAPP_PHONE_NUMBER: ("phone_number",),
    KeyaiQuestionField.COMPANY_NAME: ("short_text",),
    KeyaiQuestionField.COMPANY_WEBSITE: ("website_url", "short_text"),
    KeyaiQuestionField.JOB_TITLE: ("short_text",),
    KeyaiQuestionField.COMPANY_STAGE: ("multiple_choice_single", "short_text"),
    KeyaiQuestionField.MEMBER_TYPE: ("multiple_choice_single",),
    KeyaiQuestionField.COUNTRY_REGION: ("country",),
    KeyaiQuestionField.FULL_NAME: ("short_text",),
    KeyaiQuestionField.INDUSTRY_SECTOR: ("short_text",),
    KeyaiQuestionField.INVESTOR_STAGE: ("multiple_choice_multi",),
    KeyaiQuestionField.EXCLUSIVE_BENEFITS_DISCOUNTS: ("short_text",),
    KeyaiQuestionField.FUND_WEBSITE: ("short_text", "website_url"),
    KeyaiQuestionField.ADVISING_MENTORING_FOUNDERS: ("short_text",),
    KeyaiQuestionField.FRACTIONAL_BOARD_ROLES: ("short_text",),
    KeyaiQuestionField.ORGANIZATION_FIRM_NAME: ("short_text",),
    KeyaiQuestionField.ORGANIZATION_WEBSITE_DOMAIN: ("short_text", "website_url"),
    KeyaiQuestionField.COMPANIES_WORK_WITH_STAGE: ("short_text",),
    KeyaiQuestionField.SERVICES_VALUE_OFFERED: ("short_text",),
}

QUESTION_FIELD_KEYWORDS: dict[KeyaiQuestionField, tuple[tuple[str, ...], ...]] = {
    KeyaiQuestionField.LINKEDIN_URL: (("linked", "in", "url"),),
    KeyaiQuestionField.WHATSAPP_PHONE_NUMBER: (("whatsapp", "number"),),
    KeyaiQuestionField.COMPANY_NAME: (("company", "name"),),
    KeyaiQuestionField.COMPANY_WEBSITE: (("company", "website", "domain"),),
    KeyaiQuestionField.JOB_TITLE: (
        ("job", "title"),
        ("job", "title", "role"),
        ("current", "title", "function"),
    ),
    KeyaiQuestionField.COMPANY_STAGE: (
        ("funding", "stage"),
        ("company", "stage", "size"),
    ),
    KeyaiQuestionField.MEMBER_TYPE: (("describes", "best"),),
    KeyaiQuestionField.COUNTRY_REGION: (("country", "region"),),
    KeyaiQuestionField.FULL_NAME: (("full", "name"),),
    KeyaiQuestionField.INDUSTRY_SECTOR: (("industry", "sector"),),
    KeyaiQuestionField.INVESTOR_STAGE: (("stage", "invest"),),
    KeyaiQuestionField.EXCLUSIVE_BENEFITS_DISCOUNTS: (
        ("offering", "exclusive", "benefits", "discounts", "funda"),
    ),
    KeyaiQuestionField.FUND_WEBSITE: (("fund", "website"),),
    KeyaiQuestionField.ADVISING_MENTORING_FOUNDERS: (
        ("advising", "mentoring", "founders"),
    ),
    KeyaiQuestionField.FRACTIONAL_BOARD_ROLES: (("fractional", "board", "roles"),),
    KeyaiQuestionField.ORGANIZATION_FIRM_NAME: (("organization", "firm", "name"),),
    KeyaiQuestionField.ORGANIZATION_WEBSITE_DOMAIN: (
        ("organization", "website", "domain"),
    ),
    KeyaiQuestionField.COMPANIES_WORK_WITH_STAGE: (("stage", "companies", "work"),),
    KeyaiQuestionField.SERVICES_VALUE_OFFERED: (
        ("services", "value", "funda", "members"),
    ),
}


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

    return get_canonical_question_answers(questions).get(field.value)


def get_canonical_question_answers(
    questions: list[MemberQuestionPayload] | None,
) -> dict[str, str]:
    """
    Returns all question answers keyed by canonical Funda field name.

    Args:
        questions: List of question/answer pairs from the webhook payload.

    Returns:
        dict[str, str]: Canonical field names mapped to normalized answers.
    """
    if questions is None:
        return {}

    answers: dict[str, str] = {}

    for item in questions:
        answer = _normalize_question_answer(item)
        if answer is None:
            continue

        field = _field_for_item(item)
        if field is not None:
            _add_answer(answers=answers, key=field.value, answer=answer)

    for item in questions:
        answer = _normalize_question_answer(item)
        if answer is None:
            continue

        field = _field_for_item(item)
        key = field.value if field is not None else _fallback_question_key(item)
        if key not in answers:
            _add_answer(answers=answers, key=key, answer=answer)

    return answers


def get_keyai_question_records(
    questions: list[MemberQuestionPayload] | None,
) -> list[dict[str, Any]]:
    """
    Returns the full Key.ai questions payload with canonical keys attached.

    Args:
        questions: List of question/answer pairs from the webhook payload.

    Returns:
        list[dict[str, Any]]: Question records suitable for Firestore or JSON.
    """
    if questions is None:
        return []

    records: list[dict[str, Any]] = []
    for item in questions:
        field = _field_for_item(item)
        records.append(
            {
                "canonical_key": (
                    field.value if field is not None else _fallback_question_key(item)
                ),
                "semantic_key": item.semantic_key,
                "question": item.question,
                "type": item.type.value,
                "answer": item.answer,
                "normalized_answer": _normalize_question_answer(item),
            }
        )

    return records


def _normalize_question_answer(item: MemberQuestionPayload) -> str | None:
    """
    Normalizes a question answer into a trimmed string for downstream use.

    Args:
        item: Question payload to normalize.

    Returns:
        A trimmed string value, or None when the answer is empty.
    """
    if isinstance(item.answer, str):
        value = item.answer.strip()
        return value if value else None

    if item.answer is None:
        return None

    values = [value.strip() for value in item.answer if value.strip()]
    if not values:
        return None
    return ", ".join(values)


def _field_for_semantic_key(semantic_key: str) -> KeyaiQuestionField | None:
    normalized_key = _slugify(semantic_key)
    for field, semantic_keys in QUESTION_FIELD_SEMANTIC_KEYS.items():
        if normalized_key in semantic_keys:
            return field

    return None


def _field_for_item(item: MemberQuestionPayload) -> KeyaiQuestionField | None:
    semantic_field = _field_for_semantic_key(item.semantic_key)
    keyword_field = _field_for_keywords(item)
    if keyword_field is not None:
        return keyword_field

    return semantic_field


def _field_for_keywords(item: MemberQuestionPayload) -> KeyaiQuestionField | None:
    question_type = item.type.value
    normalized_question = _normalize_text(item.question)
    for field, keyword_sets in QUESTION_FIELD_KEYWORDS.items():
        if question_type not in QUESTION_FIELD_TYPES[field]:
            continue

        for keywords in keyword_sets:
            if all(keyword in normalized_question for keyword in keywords):
                return field

    return None


def _fallback_question_key(item: MemberQuestionPayload) -> str:
    semantic_key = _slugify(item.semantic_key)
    if semantic_key:
        return semantic_key

    return _slugify(item.question)


def _add_answer(answers: dict[str, str], key: str, answer: str) -> None:
    existing_answer = answers.get(key)
    if existing_answer is None:
        answers[key] = answer
        return

    if answer == existing_answer or answer in existing_answer.split("\n"):
        return

    answers[key] = f"{existing_answer}\n{answer}"


def _normalize_text(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _slugify(value: str) -> str:
    return "_".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


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
    value = get_question_answer(questions, KeyaiQuestionField.COMPANY_STAGE)
    if value is None or not value.strip():
        return None
    return value.strip()


def get_company_website(
    questions: list[MemberQuestionPayload] | None,
) -> str | None:
    """Returns company website from questions, trimmed, or None."""
    value = get_question_answer(questions, KeyaiQuestionField.COMPANY_WEBSITE)
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
