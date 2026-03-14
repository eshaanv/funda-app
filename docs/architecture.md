# High-Level Invocation Flow

This diagram intentionally stays high level. It shows the one public webhook
endpoint, the immediate `202` acknowledgement returned for every event, and the
extra background flow used for `member.joined`.

```mermaid
sequenceDiagram
    autonumber
    participant KeyAI as Key.ai
    participant Endpoint as Funda App<br/>POST /webhooks/keyai/users
    participant Tasks as Background tasks
    participant Gemini as Gemini enrichment
    participant WABA as Facebook + WhatsApp Business App
    participant Recipient as WhatsApp recipient

    Note over KeyAI,Recipient: Every event is acknowledged immediately; only member.joined enters the background path below.
    KeyAI->>Endpoint: Send typed member webhook payload
    Endpoint-->>KeyAI: Return 202 Accepted
    opt member.joined only
        Endpoint->>Tasks: Queue joined-member background flow
        Tasks->>Gemini: Generate enrichment summary when LinkedIn URL is available
        Gemini-->>Tasks: Summary or no response
        Note over Tasks,WABA: WhatsApp send still runs if enrichment is skipped or fails.
        Tasks->>WABA: Send funda_signup_confirmation template
        WABA-->>Recipient: Deliver automated WhatsApp message
    end
```
