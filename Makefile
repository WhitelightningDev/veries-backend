.PHONY: dev test lint format

dev:
\tuvicorn veries_backend.app.main:app --reload --host 0.0.0.0 --port 8000

test:
\tpytest -q

lint:
\truff check .

format:
\truff format .

