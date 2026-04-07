import pytest
from pydantic import ValidationError

from funda_app.schemas.webhooks import MemberQuestionPayload
from funda_app.services.keyai_questions import (
    KeyaiQuestionField,
    get_company_website,
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
