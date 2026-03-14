import logging

from google.genai.types import GenerateContentConfig

from funda_app.agents.models import invoke_gemini
from funda_app.agents.prompt import MEMBER_ENRICHMENT_PROMPT_TEMPLATE
from funda_app.schemas.enrichment import EnrichmentRequest, MemberEnrichmentRecord
from funda_app.schemas.webhooks import MemberJoinedWebhookPayload, MemberQuestionPayload

logger = logging.getLogger(__name__)


def dispatch_member_joined_enrichment(payload: MemberJoinedWebhookPayload) -> None:
    """
    Runs joined-member enrichment and logs the result.

    Args:
        payload (MemberJoinedWebhookPayload): Joined member webhook payload.
    """
    request = build_enrichment_request(payload)

    if request is None:
        logger.info(
            "Member enrichment skipped: member_id=%s event_id=%s reason=missing_linkedin_url",
            payload.member.id,
            payload.eventId,
        )
        return

    logger.info(
        "Member enrichment started: member_id=%s event_id=%s linkedin_url=%s",
        request.member_id,
        request.event_id,
        request.linkedin_url,
    )

    result = enrich_member(request)

    if result.status == "failed":
        logger.error(
            "Member enrichment failed: member_id=%s event_id=%s reason=%s",
            result.member_id,
            result.event_id,
            result.reason,
        )
        return

    logger.info(
        "Member enrichment completed: member_id=%s event_id=%s company_name=%s company_stage=%s summary=%s",
        result.member_id,
        result.event_id,
        result.company_name or "unknown",
        result.company_stage or "unknown",
        result.summary or "",
    )


def build_enrichment_request(
    payload: MemberJoinedWebhookPayload,
) -> EnrichmentRequest | None:
    """
    Builds a normalized enrichment request from a joined-member webhook payload.

    Args:
        payload (MemberJoinedWebhookPayload): Joined member webhook payload.

    Returns:
        EnrichmentRequest | None: Normalized request when LinkedIn is present.
    """
    linkedin_url = _get_linkedin_url(payload)
    if linkedin_url is None:
        return None

    company_name = _get_company_name(payload)
    company_stage = _get_company_stage(payload)

    return EnrichmentRequest(
        member_id=payload.member.id,
        event_id=payload.eventId,
        community_name=payload.community.name,
        occurred_at=payload.occurredAt,
        first_name=payload.member.firstName,
        last_name=payload.member.lastName,
        full_name=payload.member.fullName,
        email=payload.member.email,
        phone=payload.member.phone,
        linkedin_url=linkedin_url,
        company_name=company_name,
        company_stage=company_stage,
    )


def enrich_member(request: EnrichmentRequest) -> MemberEnrichmentRecord:
    """
    Generates a free-text enrichment summary from explicit member inputs.

    Args:
        request (EnrichmentRequest): Normalized enrichment request.

    Returns:
        MemberEnrichmentRecord: Logged enrichment result.
    """
    prompt = MEMBER_ENRICHMENT_PROMPT_TEMPLATE.format(
        full_name=request.full_name,
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        phone=request.phone,
        linkedin_url=request.linkedin_url,
        company_name=request.company_name or "unknown",
        company_stage=request.company_stage or "unknown",
        community_name=request.community_name,
        occurred_at=request.occurred_at.isoformat(),
    )
    summary = invoke_gemini(
        prompt=prompt,
        config=GenerateContentConfig(temperature=0.2),
    )

    if summary is None:
        return MemberEnrichmentRecord(
            member_id=request.member_id,
            event_id=request.event_id,
            status="failed",
            reason="gemini_no_response",
            linkedin_url=request.linkedin_url,
            company_name=request.company_name,
            company_stage=request.company_stage,
        )

    return MemberEnrichmentRecord(
        member_id=request.member_id,
        event_id=request.event_id,
        status="completed",
        linkedin_url=request.linkedin_url,
        company_name=request.company_name,
        company_stage=request.company_stage,
        summary=summary.strip(),
    )


def _get_linkedin_url(payload: MemberJoinedWebhookPayload) -> str | None:
    if payload.member.linkedinUrl:
        candidate = payload.member.linkedinUrl.strip()
        if _is_linkedin_url(candidate):
            return candidate

    question_value = _find_answer(payload.questions, "linked")
    if question_value is None:
        return None

    candidate = question_value.strip()
    if not _is_linkedin_url(candidate):
        return None

    return candidate


def _get_company_name(payload: MemberJoinedWebhookPayload) -> str | None:
    if payload.member.companyName and payload.member.companyName.strip():
        return payload.member.companyName.strip()

    question_value = _find_answer(payload.questions, "company name")
    if question_value is None or not question_value.strip():
        return None

    return question_value.strip()


def _get_company_stage(payload: MemberJoinedWebhookPayload) -> str | None:
    if payload.member.companyStage and payload.member.companyStage.strip():
        return payload.member.companyStage.strip()

    question_value = _find_answer(payload.questions, "funding stage")
    if question_value is None or not question_value.strip():
        return None

    return question_value.strip()


def _find_answer(
    questions: list[MemberQuestionPayload],
    pattern: str,
) -> str | None:
    lowered_pattern = pattern.lower()

    for item in questions:
        if lowered_pattern in item.question.lower():
            return item.answer

    return None


def _is_linkedin_url(value: str) -> bool:
    lowered_value = value.lower()
    return lowered_value.startswith("http") and "linkedin.com" in lowered_value
