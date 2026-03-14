# Funda App

Minimal FastAPI service for receiving Key.ai webhook calls.

## Run locally

```bash
uv sync
export WHATSAPP_ACCESS_TOKEN=your-token
export WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
uv run uvicorn funda_app.main:app --reload
```

## Validate

```bash
uv run pytest
uv run ruff check .
```

## Run with Docker

```bash
docker build -t funda-app .
docker run --rm -p 8080:8080 funda-app
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

The Key.ai webhook endpoint accepts raw JSON bodies, routes all member events through the payload's `event` field, and returns `202 Accepted`. The `member.joined` event additionally schedules a background WhatsApp template send through the internal registry-backed sender.

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

## Architecture

See [docs/architecture.md](docs/architecture.md) for a Mermaid diagram of the high-level webhook invocation flow.
