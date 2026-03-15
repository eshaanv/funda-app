# Member Webhook Events

## member.joined

**Trigger:** New user joins a community via invite link (any status)

**Payload includes:** Full member info + all onboarding Q&A answers

**Current Funda handling:** Return `202 Accepted`, then queue background Attio
CRM sync and WhatsApp template delivery in that order.

**Validation note:** `questions[]` is required for `member.joined`. Funda rejects
joined payloads without it.

``` json
{
  "event": "member.joined",
  "status": { "old": null, "new": "PENDING" },
  "questions": [
    { "question": "...", "answer": "..." }
  ]
}
```

------------------------------------------------------------------------

## member.approved

**Trigger:** Admin approves a pending member

**Payload includes:** Member info + status change only

**Current Funda handling:** Return `202 Accepted`, then queue background Attio
CRM sync and WhatsApp template delivery.

``` json
{
  "event": "member.approved",
  "status": { "old": "PENDING", "new": "APPROVED" }
}
```

------------------------------------------------------------------------

## member.rejected

**Trigger:** Admin rejects a pending member

**Current Funda handling:** Return `202 Accepted`, then queue background Attio
CRM sync and WhatsApp template delivery.

``` json
{
  "event": "member.rejected",
  "status": { "old": "PENDING", "new": "REJECTED" }
}
```

------------------------------------------------------------------------

## member.removed

**Trigger:** Admin manually removes a member

**Current Funda handling:** Return `202 Accepted`, then queue background Attio
CRM sync only.

``` json
{
  "event": "member.removed",
  "status": { "old": "APPROVED", "new": "REMOVED" }
}
```

------------------------------------------------------------------------

## member.left

**Trigger:** Member requested to leave and scheduler window expired\
(10 minutes in dev / 72 hours in production)

**Current Funda handling:** Return `202 Accepted`, then queue background Attio
CRM sync only.

``` json
{
  "event": "member.left",
  "status": { "old": "APPROVED", "new": "LEFT" }
}
```

------------------------------------------------------------------------

# Common Fields (Present in All Events)

``` json
{
  "event": "...",
  "version": 1,
  "eventId": "uuid",
  "occurredAt": "2026-03-14T...",
  "community": {
    "id": "...",
    "name": "funda"
  },
  "member": {
    "id": "...",
    "firstName": "...",
    "lastName": "...",
    "fullName": "...",
    "email": "...",
    "phone": "..."
  },
  "status": {
    "old": "...",
    "new": "..."
  }
}
```

**Note:** `questions[]` is included **only in `member.joined`**.\
All other events contain only the common fields listed above.

For the current high-level runtime flow, see [architecture.md](architecture.md).
For the current Funda member-facing WhatsApp template standards for these
events, see
[member-webhook-template-standards.md](member-webhook-template-standards.md).
