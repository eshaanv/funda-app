.PHONY: format lint

TARGET ?= .

format:
	uv run ruff format $(TARGET)

lint:
	uv run ruff check --fix $(TARGET)
