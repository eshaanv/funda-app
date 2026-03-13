# Funda App

Minimal FastAPI service for receiving Key.ai webhook calls.

## Run locally

```bash
uv sync
uv run uvicorn funda_app.main:app --reload
```

## Validate

```bash
uv run pytest
uv run ruff check .
```

## Endpoints

- `GET /health`
- `POST /webhooks/keyai/users`
- `POST /webhooks/keyai/users/{user_id}/status`

Both webhook endpoints currently accept raw JSON bodies and return `202 Accepted`. The WhatsApp send path is a placeholder service boundary that can be replaced later once the provider details are finalized.
