.PHONY: dev test lint format

PYTHON := python3
VENV_PYTHON := .venv/bin/python
ifeq ($(wildcard $(VENV_PYTHON)), $(VENV_PYTHON))
PYTHON := $(VENV_PYTHON)
endif

dev:
	$(PYTHON) -m uvicorn veries_backend.app.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .
