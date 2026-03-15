# High-Level Invocation Flow

This diagram intentionally stays high level. It shows the one public webhook
endpoint, the immediate `202` acknowledgement returned for every event, the
Attio sync that runs for all member events, and the WhatsApp steps for the
currently supported lifecycle events.

```mermaid
sequenceDiagram
    autonumber
    participant KeyAI as Key.ai
    participant Endpoint as Funda App<br/>POST /webhooks/keyai/users
    participant Tasks as Background tasks
    participant Attio as Attio CRM
    participant WABA as Facebook + WhatsApp Business App
    participant Recipient as WhatsApp recipient

    Note over KeyAI,Recipient: Every event is acknowledged immediately and mirrored to Attio in the background.
    KeyAI->>Endpoint: Send typed member webhook payload
    Endpoint-->>KeyAI: Return 202 Accepted
    Endpoint->>Tasks: Queue member background flow
    Tasks->>Attio: Sync people/company/lifecycle state
    opt member.joined
        Tasks->>WABA: Send funda_signup_confirmation template
        WABA-->>Recipient: Deliver automated WhatsApp message
    end
    opt member.approved
        Tasks->>WABA: Send funda_membership_approved1 template
        WABA-->>Recipient: Deliver automated WhatsApp message
    end
    opt member.rejected
        Tasks->>WABA: Send funda_membership_rejected template
        WABA-->>Recipient: Deliver automated WhatsApp message
    end
```
