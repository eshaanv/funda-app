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
| `person.job_title` | `questions[].semantic_key == "job_title"` | None |

## Phone Number Rules

Phone number resolution now uses the same precedence across all events:

| Consumer | Primary field | Fallback | If still missing |
| --- | --- | --- | --- |
| Member WhatsApp dispatch | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | Skip WhatsApp dispatch |
| Attio sync | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | Sync `phone=None` |

Important detail:

- Upstream Key.ai docs say `questions[]` is included only on `member.joined`.
- Funda still checks `questions[].whatsapp_number` first on every event.
- If a non-joined payload does not include `questions[]`, Funda falls back to
  `member.phone`.

## LinkedIn And Company Rules

| Consumer | Event | Primary field | Fallback |
| --- | --- | --- | --- |
| Attio `person.linkedin_url` | All events | `questions[].semantic_key == "linked_in_url"` | `member.linkedinUrl` |
| Attio `company.name` | All events | `questions[].semantic_key == "company_name"` | None |
| Attio `company.stage` | All events | `questions[].semantic_key == "funding_stage"` | None |
| Attio `company.company_website` | All events | `questions[].semantic_key == "company_website_domain"` | None |

Important detail:

- Funda builds an Attio company payload for any event only when
  `questions[].company_name` is present.
- Company fields do not fall back to the `member` object because those fields
  are not part of the confirmed webhook payload shape.
- `company_website_domain` still has no `member`-field fallback because there is
  no equivalent field on `member`.

## Event By Event

## `member.joined`

### Attio sync

| Output | Primary payload field | Fallback | Notes |
| --- | --- | --- | --- |
| `person.phone` | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | |
| `person.linkedin_url` | `questions[].semantic_key == "linked_in_url"` | `member.linkedinUrl` | |
| `company.name` | `questions[].semantic_key == "company_name"` | None | Company payload is built when a name resolves |
| `company.stage` | `questions[].semantic_key == "funding_stage"` | None | Included only if company payload is built |
| `company.company_website` | `questions[].semantic_key == "company_website_domain"` | None | Included only if company payload is built |

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

| Output | Primary payload field | Fallback | Notes |
| --- | --- | --- | --- |
| `person.phone` | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | |
| `person.linkedin_url` | `questions[].semantic_key == "linked_in_url"` | `member.linkedinUrl` | |
| `company.name` | `questions[].semantic_key == "company_name"` | None | Company payload is built when a name resolves |
| `company.stage` | `questions[].semantic_key == "funding_stage"` | None | Included only if company payload is built |
| `company.company_website` | `questions[].semantic_key == "company_website_domain"` | None | Included only if company payload is built |

The shared fields listed above are also used.

### Member WhatsApp

| Output | Primary payload field | Fallback | If missing |
| --- | --- | --- | --- |
| `to` | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | Skip dispatch |
| `template_name` | `event == member.approved` | None | Uses `funda_membership_approved1` |
| `first_name` template param | `member.firstName` | None | |

### Admin notification

This runs only for `member.approved`.

| Output | Primary payload field | Fallback | Notes |
| --- | --- | --- | --- |
| Admin recipient phone | Runtime setting `new_member_admin_phone` | None | If missing, skip admin notification |
| `full_name` template param | `member.fullName` | None | |
| Company lookup member ID | `member.id` | None | Used to look up linked company in Attio |
| Prompt `first_name` | `member.firstName` | None | |
| Prompt `last_name` | `member.lastName` | None | |
| Prompt `linkedin_url` | `member.linkedinUrl` | `"unknown"` | |
| Prompt `company_stage` | `questions[].semantic_key == "funding_stage"` | `"unknown"` | |
| Prompt `company_website` | `questions[].semantic_key == "company_website_domain"` | `"unknown"` | |
| Prompt `role` | `questions[].semantic_key == "job_title"` | `"unknown"` | |

Additional fallback behavior for admin notification:

- If Attio company lookup fails or returns no company, the notification uses:
  - `individual_blurb = "{full_name} is an approved member of the Funda community."`
  - `company_blurb = "Company not found"`
- If Gemini returns no response or invalid JSON, the notification uses:
  - `individual_blurb = "{full_name} works at {company_name}."`
  - `company_blurb = "{company_name} is the company associated with this member."`

## `member.rejected`

### Attio sync

| Output | Primary payload field | Fallback | Notes |
| --- | --- | --- | --- |
| `person.phone` | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | |
| `person.linkedin_url` | `questions[].semantic_key == "linked_in_url"` | `member.linkedinUrl` | |
| `company.name` | `questions[].semantic_key == "company_name"` | None | Company payload is built when a name resolves |
| `company.stage` | `questions[].semantic_key == "funding_stage"` | None | Included only if company payload is built |
| `company.company_website` | `questions[].semantic_key == "company_website_domain"` | None | Included only if company payload is built |

The shared fields listed above are also used.

### Member WhatsApp

| Output | Primary payload field | Fallback | If missing |
| --- | --- | --- | --- |
| `to` | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | Skip dispatch |
| `template_name` | `event == member.rejected` | None | Uses `funda_membership_rejected` |
| `first_name` template param | `member.firstName` | None | |

### Admin notification

Not used for this event.

## `member.removed`

### Attio sync

| Output | Primary payload field | Fallback | Notes |
| --- | --- | --- | --- |
| `person.phone` | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | |
| `person.linkedin_url` | `questions[].semantic_key == "linked_in_url"` | `member.linkedinUrl` | |
| `company.name` | `questions[].semantic_key == "company_name"` | None | Company payload is built when a name resolves |
| `company.stage` | `questions[].semantic_key == "funding_stage"` | None | Included only if company payload is built |
| `company.company_website` | `questions[].semantic_key == "company_website_domain"` | None | Included only if company payload is built |

The shared fields listed above are also used.

### Member WhatsApp

Not used for this event. There is no template mapping, so Funda skips member
WhatsApp dispatch.

### Admin notification

Not used for this event.

## `member.left`

### Attio sync

| Output | Primary payload field | Fallback | Notes |
| --- | --- | --- | --- |
| `person.phone` | `questions[].semantic_key == "whatsapp_number"` | `member.phone` | |
| `person.linkedin_url` | `questions[].semantic_key == "linked_in_url"` | `member.linkedinUrl` | |
| `company.name` | `questions[].semantic_key == "company_name"` | None | Company payload is built when a name resolves |
| `company.stage` | `questions[].semantic_key == "funding_stage"` | None | Included only if company payload is built |
| `company.company_website` | `questions[].semantic_key == "company_website_domain"` | None | Included only if company payload is built |

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
