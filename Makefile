# Autodetect Python (prefer venv)
PYTHON := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; \
elif command -v python >/dev/null 2>&1; then command -v python; \
else command -v python3; fi)

.PHONY: anchors mc-equilibrium

anchors:
	@echo "Using PYTHON=$(PYTHON)"
	@$(PYTHON) scripts/check_anchors.py

# ---- Monte Carlo equilibrium simulation ----
mc-equilibrium:
	@echo "Using PYTHON=$(PYTHON)"
	@$(PYTHON) scripts/sim_mc_equilibrium.py --network ethereum --N 200 --draws 2000 --save-samples || \
	  (echo 'Tip: install scipy for Latin Hypercube, or add --no-lhs'; exit 1)
