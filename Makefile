ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: format lint test-local-webhook build-image push-image deploy

TARGET ?= .
CLOUD_RUN_FLAGS ?= --no-invoker-iam-check
LOCAL_WEBHOOK_HOST ?= 127.0.0.1
LOCAL_WEBHOOK_PORT ?= 8000
LOCAL_WEBHOOK_BASE_URL ?= http://$(LOCAL_WEBHOOK_HOST):$(LOCAL_WEBHOOK_PORT)
LOCAL_WEBHOOK_LOG ?= /tmp/funda-app-local-webhook.log

format:
	uv run ruff format $(TARGET)

lint:
	uv run ruff check --fix $(TARGET)

test-local-webhook:
	@echo "Starting local FastAPI server at $(LOCAL_WEBHOOK_BASE_URL)"
	@uv run uvicorn funda_app.main:app --host "$(LOCAL_WEBHOOK_HOST)" --port "$(LOCAL_WEBHOOK_PORT)" >"$(LOCAL_WEBHOOK_LOG)" 2>&1 & \
	PID=$$!; \
	trap 'kill $$PID >/dev/null 2>&1 || true' EXIT INT TERM; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -fsS "$(LOCAL_WEBHOOK_BASE_URL)/health" >/dev/null 2>&1; then \
			break; \
		fi; \
		sleep 1; \
	done; \
	curl -fsS "$(LOCAL_WEBHOOK_BASE_URL)/health" >/dev/null 2>&1 || { \
		echo "Local FastAPI server failed to start. See $(LOCAL_WEBHOOK_LOG)"; \
		exit 1; \
	}; \
	RUN_LOCAL_WEBHOOK_TESTS=1 LOCAL_WEBHOOK_BASE_URL="$(LOCAL_WEBHOOK_BASE_URL)" \
		uv run pytest tests/test_webhooks_functional.py -q

build-image:
	docker buildx build --platform linux/amd64 --load -t "$(IMAGE)" .

push-image: build-image
	docker push "$(IMAGE)"

deploy: push-image
	gcloud run deploy "$(SERVICE_NAME)" \
		--image "$(IMAGE)" \
		--region "$(REGION)" \
		--project "$(PROJECT_ID)" \
		--platform managed $(CLOUD_RUN_FLAGS)
