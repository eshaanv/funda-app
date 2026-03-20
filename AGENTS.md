# Repository Guidelines

## Project Structure & Module Organization

Application code lives in `funda_app/`. Use `funda_app/api/` for FastAPI routes, `funda_app/services/` for integration logic, `funda_app/schemas/` for Pydantic models, `funda_app/utils/` for focused helpers, and `funda_app/agents/` for agent-related prompt and tool code. Keep the app entrypoint in `funda_app/main.py`. Tests live in `tests/`, with unit tests beside functional webhook coverage such as `tests/test_webhooks_functional.py`. Supporting docs are in `docs/`, and repeatable local/cloud workflows are defined in `make/*.mk`.

## Build, Test, and Development Commands

Use `uv` for all Python dependency management, including adding packages with `uv add`.

- `uv sync`: install runtime and dev dependencies into the local environment.
- `uv run uvicorn funda_app.main:app --reload`: run the FastAPI app locally.
- `uv run pytest`: run the test suite.
- `make format`: run repository formatting tasks from `make/shared.mk`.
- `make lint`: run repository linting tasks from `make/shared.mk`.
- `make typecheck`: run repository type checks from `make/shared.mk`.
- `make run-local-container`: build the Docker image and start the app locally with `.env`.
- `make test-webhook WEBHOOK_TYPE=joined`: run a targeted functional webhook test.
- `make deploy`: build, push, and deploy to Cloud Run when cloud env vars are set.

After finishing changes, run `make format`, `make lint`, and `make typecheck` before handing work off.

## Coding Style & Naming Conventions

Target Python 3.12. Use 4-space indentation, explicit functions, and simple control flow over abstraction-heavy designs. Prefer Pydantic models for typed data objects and direct attribute access on those models. Use `snake_case` for modules, functions, and variables; use clear test names like `test_member_joined_webhook`. Keep comments sparse and only add them when intent is not obvious. Add dependencies with `uv add`, not manual `pyproject.toml` edits.

## Testing Guidelines

Write tests with `pytest`. Put shared fixtures in `tests/conftest.py`. Name files `test_*.py` and keep functional or environment-dependent coverage clearly separated from unit tests. For local webhook flows, use the existing Make targets instead of ad hoc scripts so container setup, health checks, and env wiring stay consistent.

## Commit & Pull Request Guidelines

Recent history follows Conventional Commit style, for example `fix(webhooks): ...` and `chore(log): ...`. Always use `type(scope): summary` with a narrow scope. Pull requests should describe the behavioral change, list validation steps run locally, and call out any env var, webhook, or deployment impact. Include request/response examples or screenshots only when they clarify external behavior.

## Security & Configuration Tips

Do not commit `.env`, API keys, or Google Cloud credentials. Local runs expect `.env` plus optional ADC credentials at `~/.config/gcloud/application_default_credentials.json`. When changing webhook or Cloud Run behavior, document any new required variables in `README.md` or `docs/`.
