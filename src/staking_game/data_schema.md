# Data Schema (minimal)

We normalize raw exports into these CSVs:

1) data/raw/ethereum/validators.csv
   - operator (str)         # operator/entity name (Lido, Coinbase, etc.)
   - validator_index (int)  # optional; "-" allowed
   - stake_eth (float)      # effective balance per validator or aggregated
   - share (float)          # operator stake share in [0,1]; we compute if not present
   - apr (float)            # realized nominal APR (0.042 means 4.2%); optional
   - client (str)           # e.g., Prysm, Lighthouse, etc. (optional)
   - region (str)           # optional (ISO country/region/asn)
   - missed_rate (float)    # fraction of duties missed (0..1), optional
   - slashed (int)          # 0/1 aggregated recent indicator (optional)

2) data/raw/ethereum/delegations.csv (optional, for γ elasticity)
   - date (YYYY-MM-DD)
   - operator (str)
   - net_inflow_eth (float)
   - share (float)

3) data/raw/mev/relay_stats.csv (optional)
   - date
   - relay (str)
   - blocks (int)
   - mev_median_eth (float)

4) data/raw/cosmos/validators.csv (optional, Cosmos Hub)
   - operator (str)
   - stake (float)
   - share (float)
   - apr (float)
   - missed_rate (float)

Notes:
- Supply at least ethereum/validators.csv with (operator, stake_eth) OR (operator, share).
- If 'share' is missing, we compute shares from stake.
