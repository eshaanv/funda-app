# GitHub Actions GCP Setup

This document captures the Google Cloud setup used by
[`/.github/workflows/deploy-develop.yml`](../.github/workflows/deploy-develop.yml)
so the same pattern can be repeated for production later.

It covers:

- the deployer service account used by GitHub Actions
- the Workload Identity Pool and Provider used for GitHub OIDC
- the IAM bindings required to push images and deploy Cloud Run

## Variables

Set these before running the commands below:

```bash
PROJECT_ID="stai-485819"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
POOL_ID="github"
PROVIDER_ID="funda-app"
REPO_OWNER="eshaanv"
REPO_NAME="funda-app"
REGION="us-central1"
REPOSITORY="funda-app"
DEPLOYER_SA_NAME="github-deploy"
DEPLOYER_SA_EMAIL="${DEPLOYER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
RUNTIME_SA_EMAIL="223110395358-compute@developer.gserviceaccount.com"
```

Adjust `REGION`, `REPOSITORY`, and `RUNTIME_SA_EMAIL` to match the target
environment. For production, use a different provider ID, runtime service
account, or repository values if needed.

## 1. Create The GitHub Deployer Service Account

```bash
gcloud iam service-accounts create "$DEPLOYER_SA_NAME" \
  --project "$PROJECT_ID" \
  --display-name="GitHub deployer"
```

## 2. Grant The Deployer Service Account Deploy Permissions

This workflow builds and pushes a container image to Artifact Registry and then
deploys it to Cloud Run, so the deployer service account needs:

- `roles/run.admin`
- `roles/artifactregistry.writer`

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA_EMAIL}" \
  --role="roles/run.admin"

gcloud artifacts repositories add-iam-policy-binding "$REPOSITORY" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --member="serviceAccount:${DEPLOYER_SA_EMAIL}" \
  --role="roles/artifactregistry.writer"
```

## 3. Let The Deployer Attach The Cloud Run Runtime Service Account

Cloud Run deploys create or update revisions that run as a runtime service
account. The deployer service account therefore needs
`roles/iam.serviceAccountUser` on that runtime service account.

```bash
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA_EMAIL" \
  --project "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"
```

## 4. Create The Workload Identity Pool

```bash
gcloud iam workload-identity-pools create "$POOL_ID" \
  --project="$PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions pool"
```

## 5. Create The Workload Identity Provider

This trusts GitHub Actions OIDC tokens and restricts the provider to the
`eshaanv/funda-app` repository.

```bash
gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="$POOL_ID" \
  --display-name="GitHub provider for funda-app" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository=='${REPO_OWNER}/${REPO_NAME}'"
```

## 6. Allow The GitHub Repo To Impersonate The Deployer Service Account

This is the binding that lets GitHub Actions become the deployer service
account without storing a long-lived JSON key.

```bash
gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA_EMAIL" \
  --project "$PROJECT_ID" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO_OWNER}/${REPO_NAME}" \
  --role="roles/iam.workloadIdentityUser"
```

## 7. GitHub Environment Configuration

For the `develop` GitHub environment, set:

Variables:

- `GOOGLE_CLOUD_PROJECT`
- `CLOUD_RUN_LOCATION`
- `ARTIFACT_REGISTRY_REPOSITORY`
- `CLOUD_RUN_SERVICE_NAME`
- `GCP_SERVICE_ACCOUNT_EMAIL`

Secret:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`

The `production` GitHub environment used by
[`/.github/workflows/deploy-main.yml`](../.github/workflows/deploy-main.yml)
uses the same variable and secret names. Point them at the production project,
region, Artifact Registry repository, Cloud Run service, deployer service
account, and workload identity provider values.

Set `GCP_WORKLOAD_IDENTITY_PROVIDER` to:

```text
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID
```

With the values above, that becomes:

```text
projects/223110395358/locations/global/workloadIdentityPools/github/providers/funda-app
```

## Production Reuse

For production, repeat the same flow with production-specific values:

- a production deployer service account
- a production runtime service account
- a production GitHub environment
- optionally a separate pool or provider if you want stricter isolation

Keeping the deployer and runtime identities separate per environment makes IAM
auditing and rollback safer.
