.PHONY: setup fmt lint test sim
setup:
	python -m venv .venv && . .venv/bin/activate && pip install -e .[dev]
fmt:
	black src tests
lint:
	ruff check src tests || true
test:
	pytest -q --cov=staking_game --cov-report=term-missing
sim:
	python -m staking_game.simulate --plot
