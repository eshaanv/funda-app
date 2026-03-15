.PHONY: auth test-local-webhook run-local-container logs-local-container
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

attio-people-attributes:
	@test -n "$(ATTIO_SELECTED_API_KEY)" || { echo "ATTIO_API_KEY_$(shell printf '%s' $(APP_ENV) | tr '[:lower:]' '[:upper:]') is required"; exit 1; }
	curl --request GET \
		--url "$(ATTIO_BASE_URL)/objects/people/attributes" \
		--header "Authorization: Bearer $(ATTIO_SELECTED_API_KEY)" \
	| jq '.data[] | {title, api_slug, type}'

attio-company-attributes:
	@test -n "$(ATTIO_SELECTED_API_KEY)" || { echo "ATTIO_API_KEY_$(shell printf '%s' $(APP_ENV) | tr '[:lower:]' '[:upper:]') is required"; exit 1; }
	curl --request GET \
		--url "$(ATTIO_BASE_URL)/objects/companies/attributes" \
		--header "Authorization: Bearer $(ATTIO_SELECTED_API_KEY)" \
	| jq '.data[] | {title, api_slug, type}'

test-local-webhook: run-local-container
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
	}; \
	RUN_LOCAL_WEBHOOK_TESTS=1 LOCAL_WEBHOOK_BASE_URL="$(LOCAL_WEBHOOK_BASE_URL)" \
		uv run pytest tests/test_webhooks_functional.py -q

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
