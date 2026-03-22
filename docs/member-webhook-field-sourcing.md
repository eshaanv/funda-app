# Member Webhook Field Sourcing

This document explains which inbound Key.ai payload fields Funda uses for each
member webhook event, and what fallback behavior applies at runtime.

It reflects the current implementation in
`funda_app/services/keyai_webhooks.py` and
`funda_app/services/keyai_questions.py`.

## Summary

| Event | Attio sync | Member WhatsApp | Admin notification |
| --- | --- | --- | --- |
| `member.joined` | Yes | Yes | No |
| `member.approved` | Yes | Yes | Yes |
| `member.rejected` | Yes | Yes | No |
| `member.removed` | Yes | No | No |
| `member.left` | Yes | No | No |

## Shared Payload Fields Used For All Events

These fields are always used when building the Attio sync request:

| Output | Primary payload field | Fallback |
| --- | --- | --- |
| `event` | `event` | None |
| `event_id` | `eventId` | None |
| `occurred_at` | `occurredAt` | None |
| `community_id` | `community.id` | None |
| `community_name` | `community.name` | None |
| `member_status` | `status.new` | None |
| `person.keyai_member_id` | `member.id` | None |
| `person.email` | `member.email` | None |
| `person.full_name` | `member.fullName` | None |
| `person.first_name` | `member.firstName` | None |
| `person.last_name` | `member.lastName` | None |

## Enrichment Rules

Enrichment sourcing now differs by event type:

| Consumer | Event | Primary source | Fallback | If still missing |
| --- | --- | --- | --- | --- |
| Attio person/company sync | `member.joined` | Webhook payload and `questions[]` | Event-specific payload fallback where implemented | Sync optional field as `None` |
| Attio lifecycle sync | Non-joined events | Existing Attio person record by `member.id` | None | Attio sync fails if person record is missing |
| Member WhatsApp dispatch | `member.joined` | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | Skip WhatsApp dispatch |
| Member WhatsApp dispatch | Non-joined events | Attio member context by `member.id` | None | Skip WhatsApp dispatch |
| Admin notification enrichment | `member.approved` | Attio member context by `member.id` | None | Use `"unknown"` or fixed fallback text |

Important detail:

- Upstream Key.ai docs say `questions[]` is included only on `member.joined`.
- Funda now treats `member.joined` as the enrichment event.
- Later events read canonical enrichment fields from Attio using the stored
  `keyai_member_id`, with no webhook fallback.
- Later events write only the lifecycle entry in Attio; they do not upsert the
  person or company records.

## Joined Event Enrichment Fields

For `member.joined`, Funda still builds the initial enriched profile from the
webhook payload:

| Output | Primary field | Fallback |
| --- | --- | --- |
| `person.phone` | `questions[].semantic_key == "whatsapp_number"` | `member.phone` |
| `person.linkedin_url` | `questions[].semantic_key == "linked_in_url"` | `member.linkedinUrl` |
| `person.job_title` | `questions[].semantic_key == "job_title"` | None |
| `company.name` | `questions[].semantic_key == "company_name"` | None |
| `company.stage` | `questions[].semantic_key == "funding_stage"` | None |

Important detail:

- Funda builds an Attio company payload only when a company name resolves.
- Non-joined events no longer rebuild these optional fields from the sparse
  webhook payload.

## Event By Event

## `member.joined`

### Attio sync

| Output | Primary payload field | Fallback | Notes |
| --- | --- | --- | --- |
| `person.phone` | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | |
| `person.linkedin_url` | `questions[].semantic_key == "linked_in_url"` | `member.linkedinUrl` | |
| `person.job_title` | `questions[].semantic_key == "job_title"` | None | |
| `company.name` | `questions[].semantic_key == "company_name"` | None | Company payload is built when a name resolves |
| `company.stage` | `questions[].semantic_key == "funding_stage"` | None | Included only if company payload is built |
| Lifecycle entry | Event payload status/timestamps | None | Writes lifecycle after person/company upsert |
The shared fields listed above are also used.

### Member WhatsApp

| Output | Primary payload field | Fallback | If missing |
| --- | --- | --- | --- |
| `to` | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | Skip dispatch |
| `template_name` | `event == member.joined` | None | Uses `funda_signup_confirmation` |
| `first_name` template param | `member.firstName` | None | Required by current template metadata |

### Admin notification

Not used for this event.

## `member.approved`

### Attio sync

| Output | Primary Attio field | Fallback | Notes |
| --- | --- | --- | --- |
| Existing person lookup | Attio person by `member.id` | None | Required before writing lifecycle |
| `person.phone` | Attio person `phone_numbers` by `member.id` | None | Read-only enrichment |
| `person.linkedin_url` | Attio person `linkedin` by `member.id` | None | Read-only enrichment |
| `person.job_title` | Attio person `job_title` by `member.id` | None | Read-only enrichment |
| `company.name` | Linked Attio company `name` by `member.id` | None | Read-only enrichment |
| `company.stage` | Linked Attio company `company_stage` by `member.id` | None | Read-only enrichment |
| Lifecycle entry | Event payload status/timestamps | None | Only Attio write for non-joined events |

The shared fields listed above are also used.

### Member WhatsApp

| Output | Primary payload field | Fallback | If missing |
| --- | --- | --- | --- |
| `to` | Attio person `phone_numbers` by `member.id` | None | Skip dispatch |
| `template_name` | `event == member.approved` | None | Uses `funda_membership_approved1` |
| `first_name` template param | `member.firstName` | None | |

### Admin notification

This runs only for `member.approved`.

| Output | Primary payload field | Fallback | Notes |
| --- | --- | --- | --- |
| Admin recipient phone | Runtime setting `new_member_admin_phone` | None | If missing, skip admin notification |
| `full_name` template param | `member.fullName` | None | |
| Member context lookup key | `member.id` | None | Used to load canonical Attio member context |
| Prompt `first_name` | `member.firstName` | None | |
| Prompt `last_name` | `member.lastName` | None | |
| Prompt `linkedin_url` | Attio person `linkedin` by `member.id` | `"unknown"` | |
| Prompt `company_name` | Linked Attio company `name` by `member.id` | None | Missing company triggers fixed fallback notification |
| Prompt `company_stage` | Linked Attio company `company_stage` by `member.id` | `"unknown"` | |
| Prompt `role` | Attio person `job_title` by `member.id` | `"unknown"` | |

Additional fallback behavior for admin notification:

- If Attio company lookup fails or returns no company, the notification uses:
  - `individual_blurb = "{full_name} is an approved member of the Funda community."`
  - `company_blurb = "Company not found"`
- If Gemini returns no response or invalid JSON, the notification uses:
  - `individual_blurb = "{full_name} works at {company_name}."`
  - `company_blurb = "{company_name} is the company associated with this member."`

## `member.rejected`

### Attio sync

| Output | Primary Attio field | Fallback | Notes |
| --- | --- | --- | --- |
| Existing person lookup | Attio person by `member.id` | None | Required before writing lifecycle |
| `person.phone` | Attio person `phone_numbers` by `member.id` | None | Read-only enrichment |
| `person.linkedin_url` | Attio person `linkedin` by `member.id` | None | Read-only enrichment |
| `person.job_title` | Attio person `job_title` by `member.id` | None | Read-only enrichment |
| `company.name` | Linked Attio company `name` by `member.id` | None | Read-only enrichment |
| `company.stage` | Linked Attio company `company_stage` by `member.id` | None | Read-only enrichment |
| Lifecycle entry | Event payload status/timestamps | None | Only Attio write for non-joined events |

The shared fields listed above are also used.

### Member WhatsApp

| Output | Primary payload field | Fallback | If missing |
| --- | --- | --- | --- |
| `to` | Attio person `phone_numbers` by `member.id` | None | Skip dispatch |
| `template_name` | `event == member.rejected` | None | Uses `funda_membership_rejected` |
| `first_name` template param | `member.firstName` | None | |

### Admin notification

Not used for this event.

## `member.removed`

### Attio sync

| Output | Primary Attio field | Fallback | Notes |
| --- | --- | --- | --- |
| Existing person lookup | Attio person by `member.id` | None | Required before writing lifecycle |
| `person.phone` | Attio person `phone_numbers` by `member.id` | None | Read-only enrichment |
| `person.linkedin_url` | Attio person `linkedin` by `member.id` | None | Read-only enrichment |
| `person.job_title` | Attio person `job_title` by `member.id` | None | Read-only enrichment |
| `company.name` | Linked Attio company `name` by `member.id` | None | Read-only enrichment |
| `company.stage` | Linked Attio company `company_stage` by `member.id` | None | Read-only enrichment |
| Lifecycle entry | Event payload status/timestamps | None | Only Attio write for non-joined events |

The shared fields listed above are also used.

### Member WhatsApp

Not used for this event. There is no template mapping, so Funda skips member
WhatsApp dispatch.

### Admin notification

Not used for this event.

## `member.left`

### Attio sync

| Output | Primary Attio field | Fallback | Notes |
| --- | --- | --- | --- |
| Existing person lookup | Attio person by `member.id` | None | Required before writing lifecycle |
| `person.phone` | Attio person `phone_numbers` by `member.id` | None | Read-only enrichment |
| `person.linkedin_url` | Attio person `linkedin` by `member.id` | None | Read-only enrichment |
| `person.job_title` | Attio person `job_title` by `member.id` | None | Read-only enrichment |
| `company.name` | Linked Attio company `name` by `member.id` | None | Read-only enrichment |
| `company.stage` | Linked Attio company `company_stage` by `member.id` | None | Read-only enrichment |
| Lifecycle entry | Event payload status/timestamps | None | Only Attio write for non-joined events |

The shared fields listed above are also used.

### Member WhatsApp

Not used for this event. There is no template mapping, so Funda skips member
WhatsApp dispatch.

### Admin notification

Not used for this event.

## Related Docs

- [member-webhooks-v1.md](member-webhooks-v1.md)
- [member-webhook-template-standards.md](member-webhook-template-standards.md)
- [architecture.md](architecture.md)
