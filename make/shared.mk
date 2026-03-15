ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: format lint build-image push-image

TARGET ?= .
BUILD_IMAGE_FLAGS ?= --pull --no-cache

format:
	uv run ruff format $(TARGET)

lint:
	uv run ruff check --fix $(TARGET)

build-image:
	docker buildx build --platform linux/amd64 $(BUILD_IMAGE_FLAGS) --load -t "$(IMAGE)" .

push-image: build-image
	docker push "$(IMAGE)"
