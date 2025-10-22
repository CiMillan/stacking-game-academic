# Reproducing Results without Paid APIs (BigQuery + Lighthouse)

This guide explains how to reproduce most of the ETH/Cosmos concentration and MEV analyses **without using rated.network or relay APIs**.  
It uses only **Google BigQuery public datasets** and (optionally) a **Lighthouse** Beacon node.

---

## 0) Setup (free-tier friendly)

1. Make a free GCP project → enable **BigQuery**.  
2. Optional CLI auth:
   ```bash
   gcloud auth application-default login
Always limit queries with:

sql
Copy code
WHERE DATE(block_timestamp) >= ...
to stay in the free tier.

1) Public datasets
Layer	Dataset	What it contains
Execution	bigquery-public-data.crypto_ethereum.*	blocks, transactions, logs, token_transfers, traces
MEV-Boost	eden-data-public.mev_boost.*	payloads & bids, builders, proposers
Labels	eden-data-public.ethereum_auxiliary.tags_pubkey	partial pubkey→name tags
Consensus	(none public yet)	run Lighthouse for validator inclusion metrics

2) Example: MEV deliveries per proposer
sql
Copy code
SELECT
  DATE(p.block_timestamp) AS d,
  COALESCE(t.tag, p.proposer_pubkey) AS proposer_label,
  COUNT(*) AS delivered_blocks,
  SUM(p.value_wei) AS total_value_wei
FROM `eden-data-public.mev_boost.payloads` p
LEFT JOIN `eden-data-public.ethereum_auxiliary.tags_pubkey` t
  ON LOWER(t.pubkey)=LOWER(p.proposer_pubkey)
WHERE DATE(p.block_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY 1,2
ORDER BY d, delivered_blocks DESC;
CLI version:

bash
Copy code
bq query --nouse_legacy_sql --format=csv \
'SELECT DATE(block_timestamp) d, proposer_pubkey, COUNT(*) delivered
 FROM `eden-data-public.mev_boost.payloads`
 WHERE DATE(block_timestamp)>=DATE_SUB(CURRENT_DATE(),INTERVAL 7 DAY)
 GROUP BY 1,2' > data/processed/ethereum/mev_deliveries.csv
3) Compute HHI in SQL
sql
Copy code
WITH shares AS (
  SELECT
    proposer_pubkey,
    SAFE_DIVIDE(COUNT(*), SUM(COUNT(*)) OVER()) AS share
  FROM `eden-data-public.mev_boost.payloads`
  WHERE DATE(block_timestamp) BETWEEN '2025-10-01' AND '2025-10-21'
  GROUP BY 1
)
SELECT SUM(share*share) AS hhi, 1/SUM(share*share) AS n_effective FROM shares;
4) Execution-layer checks
Blocks/day & gas:

sql
Copy code
SELECT DATE(timestamp) d, COUNT(*) blocks, AVG(gas_used) avg_gas
FROM `bigquery-public-data.crypto_ethereum.blocks`
WHERE DATE(timestamp)>=DATE_SUB(CURRENT_DATE(),INTERVAL 30 DAY)
GROUP BY 1 ORDER BY 1;
Token transfers (e.g. stETH):

sql
Copy code
SELECT DATE(block_timestamp) d, COUNT(*) transfers
FROM `bigquery-public-data.crypto_ethereum.token_transfers`
WHERE token_address='0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
  AND DATE(block_timestamp)>=DATE_SUB(CURRENT_DATE(),INTERVAL 30 DAY)
GROUP BY 1 ORDER BY 1;
5) When you do need Lighthouse
For attestation inclusion (participation rate, inclusion distance):

bash
Copy code
export ETH_NODE="https://your-lighthouse-endpoint"
curl -s "$ETH_NODE/lighthouse/validator_inclusion/123456" | jq .
Our repo’s src/data/eth_effectiveness_pull.py expects this endpoint to exist.

6) BigQuery vs Lighthouse
Capability	BigQuery	Lighthouse
MEV-Boost payload history	✅	❌
Execution layer data	✅	❌
Validator registry	❌	✅
Attestation effectiveness	❌	✅
Pubkey labeling	⚠️ partial	❌

7) Optional Makefile helper
make
Copy code
.PHONY: bq-mev
bq-mev:
	@mkdir -p data/processed/ethereum
	bq query --nouse_legacy_sql --format=csv --quiet \
	'SELECT DATE(block_timestamp) d, proposer_pubkey, COUNT(*) delivered
	 FROM `eden-data-public.mev_boost.payloads`
	 WHERE DATE(block_timestamp)>=DATE_SUB(CURRENT_DATE(),INTERVAL 7 DAY)
	 GROUP BY 1,2' \
	> data/processed/ethereum/mev_deliveries.csv
	@echo "Saved CSV -> data/processed/ethereum/mev_deliveries.csv"
Takeaway:
BigQuery is perfect for MEV & execution-layer analytics at scale.
Lighthouse (or another consensus node) is required for validator effectiveness.
