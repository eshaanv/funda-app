# Member Webhooks v2 – Asks for KeyAI

## Question answer persistence

Funda stores all `questions[]` answers from `member.joined` payloads using
canonical snake_case field names. Semantic keys are matched first. If a known
semantic key is not present, Funda falls back to question type plus keyword
matching.

The same canonical names are used internally, in Firestore, and as Attio
attribute slugs. Attio sync fails if the matching Attio attributes are missing,
so new canonical fields must be created in Attio before enabling the webhook
flow in an environment.

Current canonical answer fields:

- `company_website`
- `job_title`
- `company_name`
- `company_stage`
- `whatsapp_phone_number`
- `member_type`
- `linkedin_url`
- `country_region`
- `full_name`
- `industry_sector`
- `investor_stage`
- `exclusive_benefits_discounts`
- `fund_website`
- `advising_mentoring_founders`
- `fractional_board_roles`
- `organization_firm_name`
- `organization_website_domain`
- `companies_work_with_stage`
- `services_value_offered`
- `keyai_questions`

Firestore stores these canonical answer fields on the latest customer document,
stores them under `question_answers`, and stores the original question records
under `keyai_questions`.

Attio stores canonical answers directly on the person record using the same
attribute slugs. `keyai_questions` is stored as compact JSON so the original
question text, semantic key, type, raw answer, normalized answer, and canonical
key are preserved.
