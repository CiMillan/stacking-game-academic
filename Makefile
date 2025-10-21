PY ?= python3
ETH_NODE ?= https://docs-demo.quiknode.pro
RATED_TOKEN ?=
COSMOS_CHAIN ?= cosmoshub
COSMOS_LCD ?= https://cosmos-api.polkachu.com

.PHONY: eth-snapshot
eth-snapshot:
	ETH_NODE=$(ETH_NODE) $(PY) -m src.data.eth_snapshot
	RATED_TOKEN=$(RATED_TOKEN) $(PY) -m src.data.rated_pull

.PHONY: hhi
hhi:
	$(PY) -m src.data.eth_merge_hhi data/raw/ethereum/validators_$(shell date -u +%F).jsonl

.PHONY: rated-hhi
rated-hhi:
	$(PY) -m src.data.rated_hhi data/raw/ethereum/rated_nodeOperator_$(shell date -u +%F).jsonl

.PHONY: hhi-all
hhi-all: hhi rated-hhi

.PHONY: rated-summarize
rated-summarize:
	$(PY) -m src.data.summarize_concentration data/processed/ethereum/rated_operator_hhi_$(shell date -u +%F).csv

.PHONY: calibrate-penalty
calibrate-penalty:
	$(PY) -m src.data.calibrate_penalty 0.027255 0.0961 0.25 1.0 1.0

.PHONY: mev-pull
mev-pull:
	$(PY) -m src.data.mev_relay_pull


.PHONY: mev-merge
mev-merge:
	@if ls data/raw/ethereum/mev/*_$(shell date -u +%F).jsonl >/dev/null 2>&1; then \
	  $(PY) -m src.data.mev_merge_owner data/raw/ethereum/validators_$(shell date -u +%F).jsonl 'data/raw/ethereum/mev/*_$(shell date -u +%F).jsonl'; \
	else \
	  echo "mev-merge: skipped (no MEV files yet). Run 'make mev-pull' or wait for your scraper."; \
	fi


.PHONY: stake-quality
stake-quality:
	$(PY) -m src.data.quality_adjusted_stake data/processed/ethereum/owner_hhi_$(shell date -u +%F).csv data/processed/ethereum/mev_owner_deliveries_$(shell date -u +%F).csv 0.2

.PHONY: cosmos-snapshot
cosmos-snapshot:
	COSMOS_CHAIN=$(COSMOS_CHAIN) COSMOS_LCD=$(COSMOS_LCD) $(PY) -m src.data.cosmos_staking_pull

.PHONY: cosmos-hhi
cosmos-hhi:
	$(PY) -m src.data.cosmos_hhi data/raw/cosmos/$(COSMOS_CHAIN)_validators_$(shell date -u +%F).jsonl $(COSMOS_CHAIN)

.PHONY: daily
daily: eth-snapshot hhi rated-hhi cosmos-snapshot cosmos-hhi

.PHONY: daily-plus-mev
daily-plus-mev: daily mev-merge stake-quality

.PHONY: eth-effect
eth-effect:
	ETH_NODE=$(ETH_NODE) EPOCHS_BACK=256 $(PY) -m src.data.eth_effectiveness_pull


.PHONY: effect-merge
effect-merge:
	@if [ ! -f data/processed/ethereum/effectiveness_$(shell date -u +%F).jsonl ]; then \
	  echo "effect-merge: skipped (no effectiveness file). Run 'make eth-effect' with a Lighthouse endpoint first."; \
	else \
	  $(PY) -m src.data.effectiveness_owner_merge data/raw/ethereum/validators_$(shell date -u +%F).jsonl data/processed/ethereum/effectiveness_$(shell date -u +%F).jsonl data/processed/ethereum/owner_hhi_$(shell date -u +%F).csv; \
	fi


.PHONY: daily
daily: eth-snapshot hhi rated-hhi cosmos-snapshot cosmos-hhi mev-pull mev-merge stake-quality effect-merge
