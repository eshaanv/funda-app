ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: format lint build-image push-image deploy

TARGET ?= .
CLOUD_RUN_FLAGS ?= --no-invoker-iam-check

format:
	uv run ruff format $(TARGET)

lint:
	uv run ruff check --fix $(TARGET)

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
