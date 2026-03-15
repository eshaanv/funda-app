# Funda Member Lifecycle Template Standards

This document defines the member-facing WhatsApp templates Funda should have
for each Key.ai member webhook event defined in
[member-webhooks-v1.md](member-webhooks-v1.md).

## Current Repo Constraints

- The current implementation sends WhatsApp for `member.joined`,
  `member.approved`, and `member.rejected`.
- The template registry now includes `funda_signup_confirmation`,
  `funda_membership_approved1`, and `funda_membership_rejected`.
- The sender currently supports body text parameters only. It does not yet
  support buttons, media, or headers.

Because of that, the simplest rollout is a set of `UTILITY` templates with one
body parameter: `first_name`.

## Standard Template Set

| Priority | Event | Status change | Standard template | Category | Parameters | Standard |
| --- | --- | --- | --- | --- | --- | --- |
| Core | `member.joined` | `null -> PENDING` | `funda_signup_confirmation` | `UTILITY` | `first_name` | Keep this template, but make the copy clearly say the member is pending review. |
| Core | `member.approved` | `PENDING -> APPROVED` | `funda_membership_approved1` | `UTILITY` | `first_name` | This template is currently wired for approval events. |
| Core | `member.rejected` | `PENDING -> REJECTED` | `funda_membership_rejected` | `UTILITY` | `first_name` | This template is currently wired for rejection events. |

## Standard Copy

### member.joined

**Template name:** `funda_signup_confirmation`

**Why:** Confirms receipt and sets the right expectation that the person is not
approved yet.

**Standard copy:**

```text
Hi {{1}}, thanks for applying to join Funda. We have received your request and it is now under review. We will message you again once there is an update.
```

**Notes:** The current template name is acceptable, but the copy should read as
"application received" rather than "welcome in".

### member.approved

**Template name:** `funda_membership_approved1`

**Why:** This is the highest-value follow-up after `member.joined`. It closes
the loop and confirms the member is now in.

**Standard copy:**

```text
Hi {{1}}, your Funda membership has been approved. Welcome to the Funda community. We are glad to have you here.
```

**Notes:** If Funda wants to send next steps or an onboarding link later, that
would likely need button support or a second template.

### member.rejected

**Template name:** `funda_membership_rejected`

**Why:** Without this, applicants who were reviewed but not approved receive no
outcome message.

**Standard copy:**

```text
Hi {{1}}, thanks for your interest in Funda. We reviewed your request and cannot approve membership at this time.
```

**Notes:** Keep the message short and neutral. Avoid detailed reasons unless
there is a clear policy for them.

## Current Rollout Order

1. Keep `funda_signup_confirmation` for `member.joined`, but tighten the copy
   so it clearly means "request received and pending review."
2. Keep `funda_membership_approved1` wired to `member.approved`.
3. Keep `funda_membership_rejected` wired to `member.rejected`.

## Implementation Notes For This Repo

The repo already has:

- New `WhatsAppTemplateName` enum values in
  `funda_app/schemas/whatsapp.py`.
- New template definitions in
  `funda_app/services/whatsapp_templates.py`.

The repo also already has:

- Event-to-template mapping in
  `funda_app/services/keyai_webhooks.py` for `member.joined`,
  `member.approved`, and `member.rejected`.

Today, `member.removed` and `member.left` do not trigger WhatsApp dispatch.
