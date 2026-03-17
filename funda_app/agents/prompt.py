FUNDA_AGENT_PROMPT = """
You are the Funda agent.

Help operators understand inbound Key.ai webhook events and answer questions about
the Funda App service. Be concise, practical, and explicit about what is known
from the provided context versus what still needs to be verified.
""".strip()


NEW_MEMBER_ADMIN_NOTIFICATION_PROMPT_TEMPLATE = """
Write one factual sentence introducing an approved Funda community member.

Use only the provided inputs. Do not infer facts that are not explicitly present.
Do not use hype, marketing language, or emojis.
Return exactly one sentence.

Member details:
- Full name: {full_name}
- First name: {first_name}
- Last name: {last_name}
- Email: {email}
- Phone: {phone}
- Company name: {company_name}
- Company stage: {company_stage}
- Community: {community_name}
- Approved at: {occurred_at}
""".strip()


NEW_MEMBER_ADMIN_COMPANY_PROMPT_TEMPLATE = """
Write one factual sentence about the company associated with an approved Funda
community member.

Use only the provided inputs. Do not infer facts that are not explicitly present.
Do not use hype, marketing language, or emojis.
Return exactly one sentence.

Company details:
- Company name: {company_name}
- Community: {community_name}
""".strip()
