ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: format lint test-local-webhook run-local-container logs-local-container build-image push-image deploy

TARGET ?= .
CLOUD_RUN_FLAGS ?= --no-invoker-iam-check
LOCAL_CONTAINER_NAME ?= funda-app-local
LOCAL_CONTAINER_PORT ?= 8080
LOCAL_WEBHOOK_HOST ?= 127.0.0.1
LOCAL_WEBHOOK_PORT ?= $(LOCAL_CONTAINER_PORT)
LOCAL_WEBHOOK_BASE_URL ?= http://$(LOCAL_WEBHOOK_HOST):$(LOCAL_WEBHOOK_PORT)

format:
	uv run ruff format $(TARGET)

lint:
	uv run ruff check --fix $(TARGET)

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
	@if docker ps --format '{{.Names}}' | grep -Fx "$(LOCAL_CONTAINER_NAME)" >/dev/null; then \
		echo "Local container $(LOCAL_CONTAINER_NAME) is already running."; \
	else \
		docker run -d --rm \
			--name "$(LOCAL_CONTAINER_NAME)" \
			-p "$(LOCAL_CONTAINER_PORT):8080" \
			"$(IMAGE)"; \
	fi

logs-local-container:
	docker logs -f "$(LOCAL_CONTAINER_NAME)"

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
