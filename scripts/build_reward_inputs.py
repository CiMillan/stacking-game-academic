import json, os, pathlib, csv, math
from glob import glob
import pandas as pd

ROOT = pathlib.Path(".")

MEV_OWNER = "data/processed/ethereum/mev_owner_deliveries_2025-10-21.csv"
FLASHBOTS = "data/raw/ethereum/mev/flashbots_proposer_delivered_2025-10-21.jsonl"

OUT_MEV_SUMMARY = ROOT/"data/processed/ethereum/mev_summary_2025-10-21.csv"
OUT_REWARD_INPUTS= ROOT/"reports/metrics/reward_inputs.csv"

def read_any(path):
    p = pathlib.Path(path)
    if not p.exists():
        return None
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    if p.suffix.lower() in (".jsonl",".json"):
        rows=[]
        with open(p, "rt", encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line: continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    obj=json.load(open(p,"rt",encoding="utf-8"))
                    rows = obj if isinstance(obj,list) else [obj]
                    break
        return pd.DataFrame(rows)
    return None

def to_num(series):
    return pd.to_numeric(series, errors="coerce")

def detect_value_columns(df):
    """
    Try to find ETH- or WEI-denominated value columns.
    - If a column name contains 'wei', treat as WEI.
    - Else, if name hints 'eth' or 'value', try coercion and see magnitudes.
    Returns (eth_col, wei_col) where either can be None.
    """
    eth_col = None
    wei_col = None
    for c in df.columns:
        lc = c.lower()
        if "wei" in lc:
            wei_col = c
        if ("eth" in lc) or ("value" in lc) or ("amount" in lc) or ("revenue" in lc):
            s = to_num(df[c])
            if s.notna().any():
                # Heuristic: ETH should be "human scale" (<1e6 in most slices)
                if s.max(skipna=True) < 1e6:
                    eth_col = eth_col or c
                else:
                    # large magnitudes likely WEI if not already flagged
                    if wei_col is None: wei_col = c
    return eth_col, wei_col

def wei_to_eth(x):
    try:
        return float(x) / 1e18
    except Exception:
        try:
            return pd.to_numeric(x, errors="coerce") / 1e18
        except Exception:
            return float("nan")

def hhi_sanity(x):  # unused here, but handy if needed later
    s = pd.Series(x, dtype="float64")
    s = s[s.notna()]
    s2 = float((s*s).sum())
    return s2, (1.0/s2 if s2>0 else math.inf)

def main():
    # 1) Owner-level MEV
    df_owner = read_any(MEV_OWNER)
    owner_total_eth = float("nan")
    owner_rows = None
    if df_owner is not None and not df_owner.empty:
        cols = {c.lower(): c for c in df_owner.columns}
        owner_col = None
        for c in ["owner","operator","entity","name"]:
            if c in cols: owner_col = cols[c]; break
        eth_col, wei_col = detect_value_columns(df_owner)
        if eth_col is None and wei_col is not None:
            df_owner["value_eth"] = to_num(df_owner[wei_col]).apply(wei_to_eth)
            eth_col = "value_eth"
        if owner_col and eth_col:
            g = df_owner.groupby(owner_col, dropna=False)[eth_col].sum(min_count=1).reset_index()
            g = g.rename(columns={owner_col:"owner", eth_col:"mev_eth"})
            g["mev_eth"] = to_num(g["mev_eth"])
            owner_total_eth = float(g["mev_eth"].sum(skipna=True))
            owner_rows = g

    # 2) Flashbots proposer-delivered
    df_fb = read_any(FLASHBOTS)
    fb_total_eth = float("nan")
    fb_count = 0
    if df_fb is not None and not df_fb.empty:
        eth_col, wei_col = detect_value_columns(df_fb)
        if eth_col is None and wei_col is not None:
            df_fb["value_eth"] = to_num(df_fb[wei_col]).apply(wei_to_eth)
            eth_col = "value_eth"
        if eth_col in df_fb.columns:
            fb_total_eth = float(to_num(df_fb[eth_col]).sum(skipna=True))
        fb_count = len(df_fb)

    # 3) Save owner totals if available
    if owner_rows is not None:
        OUT_MEV_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        owner_rows.to_csv(OUT_MEV_SUMMARY, index=False)

    # 4) Reward inputs (placeholders + MEV proxy)
    mev_eth = fb_total_eth if not math.isnan(fb_total_eth) else owner_total_eth
    if math.isnan(mev_eth):
        mev_rate = 0.0
    else:
        denom = abs(mev_eth) + 1e-9
        mev_rate = float(mev_eth/denom)

    rows = [{
        "network":"ethereum",
        "as_of":"2025-10-21",
        "issuance_rate_annual": 0.004,   # TODO: replace with spec/realized
        "avg_priority_fee_rate": 0.002,  # TODO: compute from blocks
        "avg_mev_rate": round(mev_rate,6),
        "notes":"MEV rate is a placeholder proxy; normalize to (issuance+tips+mev) later."
    }]
    OUT_REWARD_INPUTS.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT_REWARD_INPUTS, index=False)

    print(f"Wrote {OUT_REWARD_INPUTS}")
    if owner_rows is not None:
        print(f"Wrote {OUT_MEV_SUMMARY}")
    print(json.dumps({
        "owner_total_mev_eth": None if math.isnan(owner_total_eth) else owner_total_eth,
        "flashbots_total_mev_eth": None if math.isnan(fb_total_eth) else fb_total_eth,
        "flashbots_records": fb_count
    }, indent=2))

if __name__ == "__main__":
    main()
