import pytest

from funda_app.schemas.webhooks import MemberQuestionPayload
from funda_app.services.keyai_questions import (
    KeyaiQuestionField,
    get_question_answer,
)


def test_get_question_answer_returns_answer_for_linkedin_url() -> None:
    questions = [
        MemberQuestionPayload(question="What is your linked-in url?", answer="https://www.linkedin.com/in/jane"),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.LINKEDIN_URL) == "https://www.linkedin.com/in/jane"


def test_get_question_answer_returns_answer_for_company_name() -> None:
    questions = [
        MemberQuestionPayload(question="What is your company name?", answer="Acme AI"),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.COMPANY_NAME) == "Acme AI"


def test_get_question_answer_returns_answer_for_funding_stage() -> None:
    questions = [
        MemberQuestionPayload(question="What is the funding stage?", answer="Seed"),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.FUNDING_STAGE) == "Seed"


def test_get_question_answer_returns_answer_for_job_title() -> None:
    questions = [
        MemberQuestionPayload(question="What is your job title?", answer="CEO"),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.JOB_TITLE) == "CEO"


def test_get_question_answer_returns_answer_for_company_website_domain() -> None:
    questions = [
        MemberQuestionPayload(question="What is your company website domain?", answer="acme.ai"),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.COMPANY_WEBSITE_DOMAIN) == "acme.ai"


def test_get_question_answer_returns_none_when_questions_is_none() -> None:
    assert get_question_answer(None, KeyaiQuestionField.LINKEDIN_URL) is None


def test_get_question_answer_returns_none_when_no_matching_question() -> None:
    questions = [
        MemberQuestionPayload(question="What is your favourite colour?", answer="blue"),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.JOB_TITLE) is None


def test_get_question_answer_trims_and_returns_empty_as_none() -> None:
    questions = [
        MemberQuestionPayload(question="What is your job title?", answer="   "),
    ]
    assert get_question_answer(questions, KeyaiQuestionField.JOB_TITLE) is None
