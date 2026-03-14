# Member Webhook Events

## member.joined

**Trigger:** New user joins a community via invite link (any status)

**Payload includes:** Full member info + all onboarding Q&A answers

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

``` json
{
  "event": "member.approved",
  "status": { "old": "PENDING", "new": "APPROVED" }
}
```

------------------------------------------------------------------------

## member.rejected

**Trigger:** Admin rejects a pending member

``` json
{
  "event": "member.rejected",
  "status": { "old": "PENDING", "new": "REJECTED" }
}
```

------------------------------------------------------------------------

## member.removed

**Trigger:** Admin manually removes a member

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
