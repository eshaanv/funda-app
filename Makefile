ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: format lint build-image push-image deploy

TARGET ?= .
CLOUD_RUN_FLAGS ?=

format:
	uv run ruff format $(TARGET)

lint:
	uv run ruff check --fix $(TARGET)

build-image:
	docker build --platform linux/amd64 -t "$(IMAGE)" .

push-image: build-image
	docker push "$(IMAGE)"

deploy: push-image
	gcloud run deploy "$(SERVICE_NAME)" \
		--image "$(IMAGE)" \
		--region "$(REGION)" \
		--project "$(PROJECT_ID)" \
		--platform managed $(CLOUD_RUN_FLAGS)
