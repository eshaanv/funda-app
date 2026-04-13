# Member Webhook Events v2

This document defines the v2 Key.ai member webhook payload shape used by Funda.

## Root object

All member webhook events use a single root object:

```json
{
  "event": "member.joined",
  "version": 2,
  "eventId": "7a3d5e57-4c32-4ae0-9ad8-4b347711f6b1",
  "occurredAt": "2026-04-07T18:42:15.000Z",
  "member": {
    "id": "14b8d602-1eee-11f1-b904-0242ac14000a",
    "email": "member@example.com",
    "phone": "+14155550123",
    "fullName": "Rohan Jain",
    "firstName": "Rohan",
    "lastName": "Jain",
    "linkedinUrl": "https://www.linkedin.com/in/member-profile"
  },
  "community": {
    "id": "b382558c-1ebd-11f1-b36c-0242ac14000a",
    "name": "funda"
  },
  "status": {
    "old": null,
    "new": "PENDING"
  },
  "questions": [
    {
      "semantic_key": "funding_stage",
      "question": "What is the funding stage?",
      "type": "multiple_choice_single",
      "answer": ["Seed"]
    }
  ]
}
```

## Field definitions

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `event` | `string` | Yes | Event name such as `member.joined` |
| `version` | `number` | Yes | Payload version |
| `eventId` | `string` | Yes | Unique event identifier |
| `occurredAt` | `string` | Yes | ISO-8601 timestamp of the event |
| `member` | `object` | Yes | Member details |
| `community` | `object` | Yes | Community details |
| `status` | `object` | Yes | Status transition |
| `questions` | `array<object>` | No | Onboarding questions and answers |

## Member object

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | Member unique ID |
| `email` | `string` | Yes | Member email |
| `phone` | `string` | No | Phone number |
| `fullName` | `string` | Yes | Full name |
| `firstName` | `string` | Yes | First name |
| `lastName` | `string` | No | Last name |
| `linkedinUrl` | `string` | No | LinkedIn profile URL |

## Community object

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | Community ID |
| `name` | `string` | Yes | Community name |

## Status object

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `old` | `string \| null` | No | Previous status |
| `new` | `string` | Yes | New status such as `PENDING` |

## Questions array

Each `questions[]` item has the following shape:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `semantic_key` | `string` | Yes | Stable field identifier |
| `question` | `string` | Yes | User-facing question text |
| `type` | `string` | Yes | Question type |
| `answer` | `string \| string[]` | Yes | User answer |

## Question type and answer shape

The `type` field controls the required shape of `answer`.

| `type` value | `answer` type | Description |
| --- | --- | --- |
| `multiple_choice_single` | `string[]` | Single-select, returned as a one-item array |
| `multiple_choice_multi` | `string[]` | Multi-select, returned as an array of strings |
| `short_text` | `string` | Short free-text answer |
| `long_text` | `string` | Long free-text answer |
| `email` | `string` | Email address |
| `number` | `string` | Numeric value encoded as a string |
| `date` | `string` | ISO-formatted date value |
| `phone_number` | `string` | Phone number |
| `website_url` | `string` | Website URL |
| `country` | `string` | Country name or code |

## Event example

```json
{
  "event": "member.joined",
  "version": 2,
  "eventId": "7a3d5e57-4c32-4ae0-9ad8-4b347711f6b1",
  "occurredAt": "2026-04-07T18:42:15.000Z",
  "member": {
    "id": "14b8d602-1eee-11f1-b904-0242ac14000a",
    "email": "member@example.com",
    "phone": "",
    "fullName": "Rohan Jain",
    "firstName": "Rohan",
    "lastName": "Jain",
    "linkedinUrl": "https://www.linkedin.com/in/member-profile"
  },
  "community": {
    "id": "b382558c-1ebd-11f1-b36c-0242ac14000a",
    "name": "funda"
  },
  "status": {
    "old": null,
    "new": "PENDING"
  },
  "questions": [
    {
      "semantic_key": "linked_in_url",
      "question": "What is your LinkedIn URL?",
      "type": "website_url",
      "answer": "https://www.linkedin.com/in/rohan-jain"
    },
    {
      "semantic_key": "whatsapp_number",
      "question": "What is your WhatsApp number?",
      "type": "phone_number",
      "answer": "+14155550123"
    },
    {
      "semantic_key": "company_name",
      "question": "What is your company name?",
      "type": "short_text",
      "answer": "Acme AI"
    },
    {
      "semantic_key": "company_website_domain",
      "question": "What is your company website?",
      "type": "website_url",
      "answer": "https://acme.ai"
    },
    {
      "semantic_key": "funding_stage",
      "question": "What is the funding stage?",
      "type": "multiple_choice_single",
      "answer": ["Seed"]
    }
  ]
}
```
