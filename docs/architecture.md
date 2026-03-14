# High-Level Invocation Flow

This diagram intentionally stays high level. It shows the one public webhook endpoint and the message flow that should happen on each invocation.

```mermaid
sequenceDiagram
    autonumber
    participant KeyAI as Key.ai
    participant Endpoint as Funda App<br/>POST /webhooks/keyai/users
    participant Registry as WhatsApp template registry
    participant WABA as Facebook + WhatsApp Business App
    participant Recipient as WhatsApp recipient

    Note over KeyAI,Recipient: Every webhook invocation follows this flow.
    KeyAI->>Endpoint: Send user webhook payload
    Endpoint-->>KeyAI: Return 202 Accepted
    Endpoint->>Registry: Queue background WhatsApp dispatch for member.joined
    Registry->>WABA: Send approved WhatsApp template with personalized fields
    WABA-->>Recipient: Deliver automated WhatsApp message
```
