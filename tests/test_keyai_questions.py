import pytest
from pydantic import ValidationError

from funda_app.schemas.webhooks import MemberQuestionPayload
from funda_app.services.keyai_questions import (
    KeyaiQuestionField,
    get_canonical_question_answers,
    get_company_website,
    get_keyai_question_records,
    get_question_answer,
)


def test_get_question_answer_returns_answer_for_linkedin_url() -> None:
    questions = [
        MemberQuestionPayload(
            question="What is your linked-in url?",
            answer="https://www.linkedin.com/in/jane",
            type="website_url",
            semantic_key="linked_in_url",
        ),
    ]
    assert (
        get_question_answer(questions, KeyaiQuestionField.LINKEDIN_URL)
        == "https://www.linkedin.com/in/jane"
    )


def test_get_question_answer_returns_answer_for_company_name() -> None:
    questions = [
        MemberQuestionPayload(
            question="What is your company name?",
            answer="Acme AI",
            type="short_text",
            semantic_key="company_name",
        ),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.COMPANY_NAME) == "Acme AI"


def test_get_company_website_returns_answer() -> None:
    questions = [
        MemberQuestionPayload(
            question="What is your company website?",
            answer="https://www.ontra.ai/",
            type="website_url",
            semantic_key="company_website_domain",
        ),
    ]
    assert get_company_website(questions) == "https://www.ontra.ai/"


def test_get_question_answer_returns_answer_for_funding_stage() -> None:
    questions = [
        MemberQuestionPayload(
            question="What is the funding stage?",
            answer=["Seed"],
            type="multiple_choice_single",
            semantic_key="funding_stage",
        ),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.FUNDING_STAGE) == "Seed"


def test_get_question_answer_returns_answer_for_job_title() -> None:
    questions = [
        MemberQuestionPayload(
            question="What is your job title?",
            answer="CEO",
            type="short_text",
            semantic_key="job_title",
        ),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.JOB_TITLE) == "CEO"


def test_get_question_answer_returns_none_when_questions_is_none() -> None:
    assert get_question_answer(None, KeyaiQuestionField.LINKEDIN_URL) is None


def test_get_question_answer_returns_none_when_no_matching_question() -> None:
    questions = [
        MemberQuestionPayload(
            question="What is your favourite colour?",
            answer="blue",
            type="short_text",
            semantic_key="favorite_color",
        ),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.JOB_TITLE) is None


def test_get_question_answer_trims_and_returns_empty_as_none() -> None:
    questions = [
        MemberQuestionPayload(
            question="What is your job title?",
            answer="   ",
            type="short_text",
            semantic_key="job_title",
        ),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.JOB_TITLE) is None


def test_get_question_answer_joins_multi_select_answers() -> None:
    questions = [
        MemberQuestionPayload(
            question="What services do you offer?",
            answer=["Design", "Engineering"],
            type="multiple_choice_multi",
            semantic_key="job_title",
        ),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.JOB_TITLE) == (
        "Design, Engineering"
    )


def test_member_question_payload_rejects_string_answer_for_multiple_choice() -> None:
    with pytest.raises(ValidationError):
        MemberQuestionPayload(
            question="What is the funding stage?",
            answer="Seed",
            type="multiple_choice_single",
            semantic_key="funding_stage",
        )


def test_member_question_payload_rejects_array_answer_for_non_multiple_choice() -> None:
    with pytest.raises(ValidationError):
        MemberQuestionPayload(
            question="What is your company name?",
            answer=["Acme AI"],
            type="short_text",
            semantic_key="company_name",
        )


def test_get_canonical_question_answers_matches_updated_question_keywords() -> None:
    questions = [
        MemberQuestionPayload(
            question="Job Title / Role",
            answer="Partner",
            type="short_text",
            semantic_key="keyai_job_role",
        ),
        MemberQuestionPayload(
            question="Organization / Firm Name",
            answer="Acme Capital",
            type="short_text",
            semantic_key="keyai_organization",
        ),
        MemberQuestionPayload(
            question="Organization Website Domain",
            answer="acme.capital",
            type="short_text",
            semantic_key="keyai_organization_website",
        ),
        MemberQuestionPayload(
            question="Fund Website?",
            answer="https://fund.example",
            type="short_text",
            semantic_key="keyai_fund_site",
        ),
        MemberQuestionPayload(
            question="Which stage do you invest in?",
            answer=["Seed", "Series A"],
            type="multiple_choice_multi",
            semantic_key="keyai_investor_stage",
        ),
        MemberQuestionPayload(
            question="What services or value do you offer to FUNDA members?",
            answer="Founder office hours",
            type="short_text",
            semantic_key="keyai_services",
        ),
    ]

    answers = get_canonical_question_answers(questions)

    assert answers["job_title"] == "Partner"
    assert answers["organization_firm_name"] == "Acme Capital"
    assert answers["organization_website_domain"] == "acme.capital"
    assert answers["fund_website"] == "https://fund.example"
    assert answers["investor_stage"] == "Seed, Series A"
    assert answers["services_value_offered"] == "Founder office hours"


def test_get_canonical_question_answers_keeps_company_and_fund_websites_separate() -> (
    None
):
    questions = [
        MemberQuestionPayload(
            question="Company Website Domain",
            answer="company.example",
            type="short_text",
            semantic_key="unknown_company_site",
        ),
        MemberQuestionPayload(
            question="Fund Website?",
            answer="fund.example",
            type="short_text",
            semantic_key="unknown_fund_site",
        ),
    ]

    answers = get_canonical_question_answers(questions)

    assert answers["company_website"] == "company.example"
    assert answers["fund_website"] == "fund.example"


def test_get_canonical_question_answers_prefers_semantic_key_over_keywords() -> None:
    questions = [
        MemberQuestionPayload(
            question="Random prompt",
            answer="Canonical Company",
            type="short_text",
            semantic_key="company_name",
        ),
        MemberQuestionPayload(
            question="Company Name?",
            answer="Keyword Company",
            type="short_text",
            semantic_key="unknown_company_name",
        ),
    ]

    answers = get_canonical_question_answers(questions)

    assert answers["company_name"] == "Canonical Company"


def test_get_keyai_question_records_preserves_raw_questions_with_canonical_keys() -> (
    None
):
    questions = [
        MemberQuestionPayload(
            question="Open to fractional or board roles?",
            answer="Yes",
            type="short_text",
            semantic_key="board_roles",
        ),
    ]

    records = get_keyai_question_records(questions)

    assert records == [
        {
            "canonical_key": "fractional_board_roles",
            "semantic_key": "board_roles",
            "question": "Open to fractional or board roles?",
            "type": "short_text",
            "answer": "Yes",
            "normalized_answer": "Yes",
        }
    ]
