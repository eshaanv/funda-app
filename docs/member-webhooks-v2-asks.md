# Member Webhooks v2 – Asks for KeyAI

## Stable question identifiers

For `member.joined` payloads, we currently match answers by substring-matching the **question text** (e.g. "company name", "linked", "funding stage"). That breaks if question wording changes.

**Ask:** For each item in `questions[]`, include a stable `key` (or `id`) so we can look up answers by key instead of question text.

Example:

```json
"questions": [
  { "key": "company_name", "question": "What's your company name?", "answer": "Acme" },
  { "key": "linkedin_url", "question": "LinkedIn profile URL", "answer": "https://linkedin.com/in/..." }
]
```

Suggested keys for the current application questions: `company_name`, `linkedin_url`, `funding_stage`, `job_title`, `company_website_domain`, `whatsapp_phone_number` (or equivalent). We can align on exact key names.
