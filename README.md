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
- `POST /webhooks/keyai/users/{user_id}/status`

Both webhook endpoints currently accept raw JSON bodies and return `202 Accepted`. The WhatsApp send path is a placeholder service boundary that can be replaced later once the provider details are finalized.
