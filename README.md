# Funda App

Minimal FastAPI service for receiving Key.ai webhook calls.

## Run locally

```bash
uv sync
export WHATSAPP_ACCESS_TOKEN=your-token
export WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
export ATTIO_API_KEY=your-attio-api-key
export ATTIO_FOUNDER_LIFECYCLE_LIST_ID=your-attio-list-id
uv run uvicorn funda_app.main:app --reload
```

For end-to-end `member.joined` processing, the runtime also needs Google Cloud
application default credentials with access to Vertex AI because the background
enrichment step uses Gemini before the WhatsApp send.

## Validate

```bash
uv run pytest
uv run ruff check .
```

## Local webhook functional test

Run the webhook functional test against the detached local container:

```bash
make test-local-webhook
```

`make test-local-webhook` builds the image if needed, starts the container if it
is not already running, waits for `/health`, then posts the `member.joined`
functional test payload. The container stays up afterward so you can inspect
runtime logs.

To tail the local container logs:

```bash
make logs-local-container
```

You can override the target app URL or container settings if needed:

```bash
make test-local-webhook LOCAL_WEBHOOK_BASE_URL=http://127.0.0.1:8080
make run-local-container LOCAL_CONTAINER_NAME=funda-app-local LOCAL_CONTAINER_PORT=8080
```

## Run with Docker

```bash
docker build -t funda-app .
docker run --rm -p 8080:8080 funda-app
```

Or use the Make target to build and run the repo image detached:

```bash
make run-local-container
```

You can then inspect the running container logs with:

```bash
make logs-local-container
```

You can override the container name and published port if needed:

```bash
make run-local-container LOCAL_CONTAINER_NAME=funda-app-local LOCAL_CONTAINER_PORT=8080
```

## Deploy to Cloud Run

```bash
direnv allow
gcloud auth login
gcloud auth configure-docker "$REGION-docker.pkg.dev"
make deploy
```

`make deploy` publishes the service publicly using Cloud Run's recommended `--no-invoker-iam-check` setting.

If you want to keep the service private:

```bash
make deploy CLOUD_RUN_FLAGS=
```

## Endpoints

- `GET /health`
- `POST /webhooks/keyai/users`

The Key.ai webhook endpoint accepts typed member event payloads, routes all
member events through the payload's `event` field, and returns `202 Accepted`.
Every member event now queues an Attio CRM sync in the background. For
`member.joined`, the background flow continues with Gemini enrichment and
WhatsApp template delivery after the CRM sync completes.

## Joined member background flow

`member.joined` is the only event that triggers the full post-acknowledgement
workflow.

- Funda immediately returns `202 Accepted` and runs the rest in a background task.
- The Attio sync mirrors the member into the `Funda Founder Lifecycle` list.
- The enrichment step uses Gemini to generate a short operator summary.
- Enrichment looks for a LinkedIn URL in `member.linkedinUrl` first, then falls
  back to joined-question answers whose prompt contains `linked`.
- Company name and company stage are taken from top-level member fields when
  present, otherwise from joined-question answers.
- If no valid LinkedIn URL is available, enrichment is skipped.
- The WhatsApp send still runs after the enrichment attempt.

All other member events (`approved`, `rejected`, `removed`, `left`) currently
stop after the background Attio sync.

## Attio CRM sync

Every Key.ai member event now mirrors into Attio.

- People are matched in Attio by email address.
- Phone numbers are normalized to E.164 before sync.
- Company name, company stage, and LinkedIn URL use top-level member fields
  first, then fall back to joined-question answers when available.
- Lifecycle state is written to the `Funda Founder Lifecycle` Attio list.

The Attio sync expects these environment variables:

- `ATTIO_API_KEY`
- `ATTIO_FOUNDER_LIFECYCLE_LIST_ID`
- `ATTIO_BASE_URL` (optional, defaults to `https://api.attio.com/v2`)
- `ATTIO_TIMEOUT_SECONDS` (optional, defaults to `10`)

## WhatsApp template dispatch

`member.joined` now schedules an in-process background task that sends the
approved `funda_signup_confirmation` WhatsApp template through Meta's Graph API.
The template registry lives in
[`funda_app/services/whatsapp_templates.py`](funda_app/services/whatsapp_templates.py),
and the sender expects these environment variables:

- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_API_VERSION` (optional, defaults to `v25.0`)
- `WHATSAPP_BASE_URL` (optional, defaults to `https://graph.facebook.com`)
- `WHATSAPP_TIMEOUT_SECONDS` (optional, defaults to `10`)

The enrichment step is separate from the WhatsApp sender. It uses the Gemini
client configured in `funda_app/agents/models.py` and therefore requires Google
credentials with Vertex AI access in any environment where `member.joined`
background tasks should run successfully.

## Architecture

See [docs/architecture.md](docs/architecture.md) for a Mermaid diagram of the high-level webhook invocation flow.
