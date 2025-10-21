PY := python3
VENV := .venv
PIP := $(VENV)/bin/pip
PYBIN := $(VENV)/bin/python

.PHONY: venv install dev data-templates ingest calibrate sim sim-plot sim-from-cal lint test nb

venv:
	python3 -m venv $(VENV)
	. $(VENV)/bin/activate; $(PIP) install --upgrade pip

install: venv
	. $(VENV)/bin/activate; $(PIP) install -e ".[dev]"

dev: install
	. $(VENV)/bin/activate; python -m ipykernel install --user --name staking-game --display-name "Python (staking-game)"

data-templates:
	@echo "Wrote example CSVs to data/raw/... (overwrite with real exports)."

ingest:
	$(PYBIN) -m staking_game.ingest --eth-validators data/raw/ethereum/validators.csv --outdir data/processed

calibrate:
	$(PYBIN) -m staking_game.calibrate --operators data/processed/operators_normalized.csv --R 0.042 --outdir data/processed

sim:
	$(PYBIN) -m staking_game.sim --n 200 --R 0.042 --mean-a 0.020 --mean-b 0.030 --mean-gamma 0.015 --cv 0.6 --seed 42 --out runs

sim-plot:
	$(PYBIN) -m staking_game.sim --n 200 --R 0.042 --mean-a 0.020 --mean-b 0.030 --mean-gamma 0.015 --cv 0.6 --seed 42 --out runs --plot

sim-from-cal:
	$(PYBIN) -m staking_game.sim_from_cal --params data/processed/params_summary.csv --R 0.042 --out runs --plot

lint:
	. $(VENV)/bin/activate; ruff check src

test:
	. $(VENV)/bin/activate; pytest -q || true

nb:
	@echo "Create notebooks in ./notebooks and use kernel: Python (staking-game)"
