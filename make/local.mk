.PHONY: auth _ensure-local-webhook-ready test-local-webhook test-local-webhook-joined test-local-webhook-approved test-local-webhook-rejected test-local-webhook-removed test-local-webhook-left test-local-webhook-firestore test-dev-webhook test-dev-webhook-joined test-dev-webhook-approved test-dev-webhook-rejected test-dev-webhook-removed test-dev-webhook-left test-prod-webhook test-prod-webhook-joined test-prod-webhook-approved test-prod-webhook-rejected test-prod-webhook-removed test-prod-webhook-left run-local-container logs-local-container
.PHONY: attio-founder-lifecycle-attributes attio-people-attributes attio-company-attributes

APP_ENV ?= dev
LOCAL_CONTAINER_NAME ?= funda-app-local
LOCAL_CONTAINER_PORT ?= 8080
LOCAL_CONTAINER_ENV_FILE ?= .env
ADC_SRC ?= $(HOME)/.config/gcloud/application_default_credentials.json
ADC_CONTAINER_PATH ?= /tmp/gcloud/application_default_credentials.json
LOCAL_WEBHOOK_HOST ?= 127.0.0.1
LOCAL_WEBHOOK_PORT ?= $(LOCAL_CONTAINER_PORT)
LOCAL_WEBHOOK_BASE_URL ?= http://$(LOCAL_WEBHOOK_HOST):$(LOCAL_WEBHOOK_PORT)
ATTIO_BASE_URL ?= https://api.attio.com/v2
ATTIO_SELECTED_API_KEY := $(if $(filter prod,$(APP_ENV)),$(ATTIO_API_KEY_PROD),$(ATTIO_API_KEY_DEV))
ATTIO_SELECTED_FOUNDER_LIFECYCLE_LIST_ID := $(if $(filter prod,$(APP_ENV)),$(ATTIO_FOUNDER_LIFECYCLE_LIST_ID_PROD),$(ATTIO_FOUNDER_LIFECYCLE_LIST_ID_DEV))

auth:
	gcloud auth application-default login

attio-founder-lifecycle-attributes:
	@test -n "$(ATTIO_SELECTED_API_KEY)" || { echo "ATTIO_API_KEY_$(shell printf '%s' $(APP_ENV) | tr '[:lower:]' '[:upper:]') is required"; exit 1; }
	@test -n "$(ATTIO_SELECTED_FOUNDER_LIFECYCLE_LIST_ID)" || { echo "ATTIO_FOUNDER_LIFECYCLE_LIST_ID_$(shell printf '%s' $(APP_ENV) | tr '[:lower:]' '[:upper:]') is required"; exit 1; }
	curl --request GET \
		--url "$(ATTIO_BASE_URL)/lists/$(ATTIO_SELECTED_FOUNDER_LIFECYCLE_LIST_ID)/attributes" \
		--header "Authorization: Bearer $(ATTIO_SELECTED_API_KEY)" \
	| jq '.data[] | {title, api_slug, type}'

attio-founder-lifecycle-attributes-dev:
	@$(MAKE) APP_ENV=dev attio-founder-lifecycle-attributes

attio-founder-lifecycle-attributes-prod:
	@$(MAKE) APP_ENV=prod attio-founder-lifecycle-attributes

attio-people-attributes:
	@test -n "$(ATTIO_SELECTED_API_KEY)" || { echo "ATTIO_API_KEY_$(shell printf '%s' $(APP_ENV) | tr '[:lower:]' '[:upper:]') is required"; exit 1; }
	curl --request GET \
		--url "$(ATTIO_BASE_URL)/objects/people/attributes" \
		--header "Authorization: Bearer $(ATTIO_SELECTED_API_KEY)" \
	| jq '.data[] | {title, api_slug, type}'

attio-people-attributes-dev:
	@$(MAKE) APP_ENV=dev attio-people-attributes

attio-people-attributes-prod:
	@$(MAKE) APP_ENV=prod attio-people-attributes

attio-company-attributes:
	@test -n "$(ATTIO_SELECTED_API_KEY)" || { echo "ATTIO_API_KEY_$(shell printf '%s' $(APP_ENV) | tr '[:lower:]' '[:upper:]') is required"; exit 1; }
	curl --request GET \
		--url "$(ATTIO_BASE_URL)/objects/companies/attributes" \
		--header "Authorization: Bearer $(ATTIO_SELECTED_API_KEY)" \
	| jq '.data[] | {title, api_slug, type}'

attio-company-attributes-dev:
	@$(MAKE) APP_ENV=dev attio-company-attributes

attio-company-attributes-prod:
	@$(MAKE) APP_ENV=prod attio-company-attributes

WEBHOOK_PYTEST = RUN_LOCAL_WEBHOOK_TESTS=1 LOCAL_WEBHOOK_BASE_URL="$(LOCAL_WEBHOOK_BASE_URL)" WEBHOOK_TEST_TARGET=local uv run pytest tests/test_webhooks_functional.py -q
WEBHOOK_FIRESTORE_PYTEST = RUN_LOCAL_WEBHOOK_TESTS=1 LOCAL_WEBHOOK_BASE_URL="$(LOCAL_WEBHOOK_BASE_URL)" WEBHOOK_TEST_TARGET=local LOCAL_FIRESTORE_PROJECT_ID="$(if $(LOCAL_FIRESTORE_PROJECT_ID),$(LOCAL_FIRESTORE_PROJECT_ID),$(GOOGLE_CLOUD_PROJECT))" uv run pytest tests/test_webhooks_functional.py -k "test_member_joined_webhook_creates_firestore_idempotency_record[local]" -q
WEBHOOK_PYTEST_DEV = RUN_LOCAL_WEBHOOK_TESTS=1 APP_ENV=dev WEBHOOK_TEST_TARGET=dev uv run pytest tests/test_webhooks_functional.py -k "dev" -q
WEBHOOK_PYTEST_PROD = RUN_LOCAL_WEBHOOK_TESTS=1 APP_ENV=prod WEBHOOK_TEST_TARGET=prod uv run pytest tests/test_webhooks_functional.py -k "prod" -q

_ensure-local-webhook-ready: run-local-container
	@echo "Waiting for local container at $(LOCAL_WEBHOOK_BASE_URL)"
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -fsS "$(LOCAL_WEBHOOK_BASE_URL)/health" >/dev/null 2>&1; then \
			break; \
		fi; \
		sleep 1; \
	done; \
	curl -fsS "$(LOCAL_WEBHOOK_BASE_URL)/health" >/dev/null 2>&1 || { \
		echo "Local container is not healthy. Use 'make logs-local-container' to inspect logs."; \
		exit 1; \
	}

test-local-webhook: _ensure-local-webhook-ready
	$(WEBHOOK_PYTEST)

test-local-webhook-joined: _ensure-local-webhook-ready
	$(WEBHOOK_PYTEST) -k "test_member_joined_webhook[local]"

test-local-webhook-approved: _ensure-local-webhook-ready
	$(WEBHOOK_PYTEST) -k "test_member_approved_webhook[local]"

test-local-webhook-rejected: _ensure-local-webhook-ready
	$(WEBHOOK_PYTEST) -k "test_member_rejected_webhook[local]"

test-local-webhook-removed: _ensure-local-webhook-ready
	$(WEBHOOK_PYTEST) -k "test_member_removed_webhook[local]"

test-local-webhook-left: _ensure-local-webhook-ready
	$(WEBHOOK_PYTEST) -k "test_member_left_webhook[local]"

test-local-webhook-firestore: _ensure-local-webhook-ready
	$(WEBHOOK_FIRESTORE_PYTEST)

test-dev-webhook:
	$(WEBHOOK_PYTEST_DEV)

test-dev-webhook-joined:
	$(WEBHOOK_PYTEST_DEV) -k "test_member_joined_webhook[dev]"

test-dev-webhook-approved:
	$(WEBHOOK_PYTEST_DEV) -k "test_member_approved_webhook[dev]"

test-dev-webhook-rejected:
	$(WEBHOOK_PYTEST_DEV) -k "test_member_rejected_webhook[dev]"

test-dev-webhook-removed:
	$(WEBHOOK_PYTEST_DEV) -k "test_member_removed_webhook[dev]"

test-dev-webhook-left:
	$(WEBHOOK_PYTEST_DEV) -k "test_member_left_webhook[dev]"

test-prod-webhook:
	$(WEBHOOK_PYTEST_PROD)

test-prod-webhook-joined:
	$(WEBHOOK_PYTEST_PROD) -k "test_member_joined_webhook[prod]"

test-prod-webhook-approved:
	$(WEBHOOK_PYTEST_PROD) -k "test_member_approved_webhook[prod]"

test-prod-webhook-rejected:
	$(WEBHOOK_PYTEST_PROD) -k "test_member_rejected_webhook[prod]"

test-prod-webhook-removed:
	$(WEBHOOK_PYTEST_PROD) -k "test_member_removed_webhook[prod]"

test-prod-webhook-left:
	$(WEBHOOK_PYTEST_PROD) -k "test_member_left_webhook[prod]"

run-local-container: build-image
	@if [ ! -f "$(LOCAL_CONTAINER_ENV_FILE)" ]; then \
		echo "Missing $(LOCAL_CONTAINER_ENV_FILE). Create it before starting the local container."; \
		exit 1; \
	else \
		docker rm -f "$(LOCAL_CONTAINER_NAME)" >/dev/null 2>&1 || true; \
		if [ -f "$(ADC_SRC)" ]; then \
			echo "Mounting ADC credentials from $(ADC_SRC)"; \
			docker run -d --rm \
				--name "$(LOCAL_CONTAINER_NAME)" \
				--env-file "$(LOCAL_CONTAINER_ENV_FILE)" \
				-v "$(ADC_SRC):$(ADC_CONTAINER_PATH):ro" \
				-e GOOGLE_APPLICATION_CREDENTIALS="$(ADC_CONTAINER_PATH)" \
				-p "$(LOCAL_CONTAINER_PORT):8080" \
				"$(IMAGE)"; \
		else \
			echo "Warning: ADC file not found at $(ADC_SRC). Gemini enrichment will fail for member.joined."; \
			echo "Run: gcloud auth application-default login"; \
			docker run -d --rm \
				--name "$(LOCAL_CONTAINER_NAME)" \
				--env-file "$(LOCAL_CONTAINER_ENV_FILE)" \
				-p "$(LOCAL_CONTAINER_PORT):8080" \
				"$(IMAGE)"; \
		fi; \
	fi

logs-local-container:
	docker logs -f "$(LOCAL_CONTAINER_NAME)"
