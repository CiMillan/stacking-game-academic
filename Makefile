PYTHON ?= python3
PIP    ?= $(PYTHON) -m pip

.PHONY: setup fmt lint test sim
setup:
	$(PYTHON) -m venv .venv && . .venv/bin/activate && $(PIP) install -e ".[dev]"

fmt:
	black src tests

lint:
	ruff check src tests || true

test:
	pytest -q --cov=staking_game --cov-report=term-missing

sim:
	$(PYTHON) -m staking_game.simulate --plot
