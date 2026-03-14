ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: format lint build-image push-image

TARGET ?= .

format:
	uv run ruff format $(TARGET)

lint:
	uv run ruff check --fix $(TARGET)

build-image:
	docker buildx build --platform linux/amd64 --load -t "$(IMAGE)" .

push-image: build-image
	docker push "$(IMAGE)"
