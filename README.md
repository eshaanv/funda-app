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

The current webhook flow does not require Google Cloud application default
credentials because the joined-member Gemini enrichment step is disabled.

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

`make test-local-webhook` builds the image if needed, starts a fresh container,
waits for `/health`, then posts the `member.joined` functional test payload.
The container stays up afterward so you can inspect runtime logs.
`make run-local-container` always replaces any existing container with the same
name before starting a fresh one. The local container is started with
`--env-file .env`, so your `.env` file must contain the required integration
settings. If local ADC
credentials exist at `~/.config/gcloud/application_default_credentials.json`,
the Make target also mounts them into the container for Gemini enrichment.

If you need to create or refresh local ADC credentials first:

```bash
make auth
```

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

Make-based image builds now pass `BUILD_IMAGE_FLAGS`, which defaults to
`--pull --no-cache` so local and deploy builds start from a fresh image build.
If you want to allow cached Docker layers for a specific run, override it:

```bash
make run-local-container BUILD_IMAGE_FLAGS=
make deploy BUILD_IMAGE_FLAGS=
```

If you need to log in for local Gemini-backed flows first:

```bash
make auth
```

You can then inspect the running container logs with:

```bash
make logs-local-container
```

You can override the container name and published port if needed:

```bash
make run-local-container LOCAL_CONTAINER_NAME=funda-app-local LOCAL_CONTAINER_PORT=8080
```

If your env file lives elsewhere, override it explicitly:

```bash
make run-local-container LOCAL_CONTAINER_ENV_FILE=.env
```

If your ADC file lives elsewhere, override that path explicitly:

```bash
make run-local-container ADC_SRC="$HOME/.config/gcloud/application_default_credentials.json"
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

## GitHub Actions deploys

Pushes to `develop` now deploy through
[`/.github/workflows/deploy-develop.yml`](.github/workflows/deploy-develop.yml).
The workflow builds the repo Docker image, pushes it to Artifact Registry, and
deploys it to Cloud Run via `make deploy`.

Configure the `develop` GitHub environment with these values before using it:

- Variables: `GOOGLE_CLOUD_PROJECT`, `CLOUD_RUN_LOCATION`,
  `ARTIFACT_REGISTRY_REPOSITORY`, `CLOUD_RUN_SERVICE_NAME`,
  `GCP_SERVICE_ACCOUNT_EMAIL`
- Secret: `GCP_WORKLOAD_IDENTITY_PROVIDER`

The deploy service account needs permission to push images to Artifact
Registry and deploy Cloud Run revisions. The workflow only updates the service
image; runtime env vars and secrets still need to exist on the Cloud Run
service or be managed separately.

For the full one-time Google Cloud setup commands, including service account,
Workload Identity Pool, provider, and IAM bindings, see
[docs/github-actions-gcp-setup.md](docs/github-actions-gcp-setup.md).

Pushes to `main` now deploy through
[`/.github/workflows/deploy-main.yml`](.github/workflows/deploy-main.yml).
That workflow uses the `production` GitHub environment and runs automatically
after the `develop` -> `main` merge completes.

If you promote code by merging `develop` into `main`, protect `main` by
requiring the existing develop deploy check from
[`/.github/workflows/deploy-develop.yml`](.github/workflows/deploy-develop.yml).
That keeps `main` blocked until the exact `develop` head commit has already
deployed successfully to the dev environment.

To enforce it on `main`:

1. Push to `develop` once so the deploy check exists in GitHub.
2. In GitHub, open the `main` branch ruleset or branch protection rule.
3. Enable pull requests before merge.
4. Enable required status checks.
5. Add `deploy-dev` as a required check.
6. Add `require-develop-head` from
   [`/.github/workflows/require-develop-for-main.yml`](.github/workflows/require-develop-for-main.yml)
   as a required check.

This blocks PRs into `main` unless the source branch is exactly `develop`, and
it also blocks merge until the `develop` deploy has already succeeded for that
commit. Once the merge lands on `main`, `deploy-prod` runs against the
`production` GitHub environment.

## Endpoints

- `GET /health`
- `POST /webhooks/keyai/users`

The Key.ai webhook endpoint accepts typed member event payloads, routes all
member events through the payload's `event` field, and returns `202 Accepted`.
Every member event now queues an Attio CRM sync in the background. For
`member.joined`, `member.approved`, and `member.rejected`, the background flow
also sends a WhatsApp template after the CRM sync completes.

## Joined member background flow

`member.joined` currently runs the signup WhatsApp flow after the Attio sync.

- Funda immediately returns `202 Accepted` and runs the rest in a background task.
- The Attio sync mirrors the member into the `Funda Founder Lifecycle` list.
- The joined-member Gemini enrichment step is currently disabled in the webhook
  path.
- The WhatsApp send uses the `funda_signup_confirmation` template.

`member.approved` and `member.rejected` also send WhatsApp after the Attio
sync. `member.removed` and `member.left` currently stop after the background
Attio sync.

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

To inspect the current Attio attribute schema with the same environment values:

```bash
make attio-founder-lifecycle-attributes
make attio-people-attributes
make attio-company-attributes
```

These helpers shell out to `curl` and `jq`, so both need to be available in
your local environment.

## WhatsApp template dispatch

Funda now sends Meta WhatsApp templates for `member.joined`,
`member.approved`, and `member.rejected`. The current template mapping is:

- `member.joined` -> `funda_signup_confirmation`
- `member.approved` -> `funda_membership_approved1`
- `member.rejected` -> `funda_membership_rejected`

The template registry lives in
[`funda_app/services/whatsapp_templates.py`](funda_app/services/whatsapp_templates.py),
and the sender expects these environment variables:

- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_API_VERSION` (optional, defaults to `v25.0`)
- `WHATSAPP_BASE_URL` (optional, defaults to `https://graph.facebook.com`)
- `WHATSAPP_TIMEOUT_SECONDS` (optional, defaults to `10`)

The joined-member Gemini enrichment code remains in the repo, but it is
currently disabled in the webhook background flow.

## Architecture

See [docs/architecture.md](docs/architecture.md) for a Mermaid diagram of the high-level webhook invocation flow.
