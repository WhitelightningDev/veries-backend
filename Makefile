.PHONY: dev test lint format

dev:
	uvicorn veries_backend.app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -q

lint:
	ruff check .

format:
	ruff format .
