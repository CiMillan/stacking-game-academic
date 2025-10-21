PY := python3
VENV := .venv
PIP := $(VENV)/bin/pip
PYBIN := $(VENV)/bin/python

.PHONY: venv install dev sim sim-plot lint test nb

venv:
\tpython3 -m venv $(VENV)
\t. $(VENV)/bin/activate; $(PIP) install --upgrade pip

install: venv
\t. $(VENV)/bin/activate; $(PIP) install -e ".[dev]"

dev: install
\t. $(VENV)/bin/activate; python -m ipykernel install --user --name staking-game --display-name "Python (staking-game)"

sim:
\t$(PYBIN) -m staking_game.sim --n 200 --R 0.042 --mean-a 0.020 --mean-b 0.030 --mean-gamma 0.015 --cv 0.6 --seed 42 --out runs

sim-plot:
\t$(PYBIN) -m staking_game.sim --n 200 --R 0.042 --mean-a 0.020 --mean-b 0.030 --mean-gamma 0.015 --cv 0.6 --seed 42 --out runs --plot

lint:
\t. $(VENV)/bin/activate; ruff check src

test:
\t. $(VENV)/bin/activate; pytest -q || true

nb:
\t@echo "Create notebooks in ./notebooks and use kernel: Python (staking-game)"
