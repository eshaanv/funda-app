from pydantic import BaseModel


class AdminNotificationBlurbs(BaseModel):
    """
    Structured Gemini output for approved-member admin notifications.

    Args:
        individual_blurb (str): One sentence about the person.
        company_blurb (str): One sentence about the company.
        citations (list[str]): Source URLs used for factual claims.
    """

    individual_blurb: str
    company_blurb: str
    citations: list[str] = []
