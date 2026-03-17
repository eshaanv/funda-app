FUNDA_AGENT_PROMPT = """
You are the Funda agent.

Help operators understand inbound Key.ai webhook events and answer questions about
the Funda App service. Be concise, practical, and explicit about what is known
from the provided context versus what still needs to be verified.
""".strip()


NEW_MEMBER_ADMIN_MEMBER_PROMPT_TEMPLATE = """
Write one informative sentence about this person.

Use the provided inputs and any relevant public web results available to you to
produce the most informative sentence you can.
Do not infer facts that are not explicitly present.
Do not use hype, marketing language, or emojis.
Return exactly one sentence.

Member details:
- Full name: {full_name}
- First name: {first_name}
- Last name: {last_name}
- LinkedIn URL: {linkedin_url}
- Company name: {company_name}
- Company stage: {company_stage}
- Approved at: {occurred_at}
""".strip()


NEW_MEMBER_ADMIN_COMPANY_PROMPT_TEMPLATE = """
Write one informative sentence about a company.

Use the provided inputs and any relevant public web results available to you to
produce the most informative sentence you can.
Do not infer facts that are not explicitly present.
Do not use hype, marketing language, or emojis.
Return exactly one sentence.

Company details:
- Company name: {company_name}
- Company stage: {company_stage}
""".strip()
