import os, re, json, math, pathlib, sys
from glob import glob
import pandas as pd

ROOT = pathlib.Path(".")
OUT_PARQUET = ROOT/"data/processed/ethereum/participation_weights_by_operator.parquet"
OUT_REPORT  = ROOT/"reports/metrics/participation_adjusted_hhi.md"

def _glob_one(patterns):
    for pat in patterns:
        hits = sorted(glob(pat))
        if hits: return hits[0]
    return None

def hhi_from_shares(x):
    s2 = sum(float(v)**2 for v in x)
    ne = (1.0/s2) if s2>0 else math.inf
    return s2, ne

def read_any(path: str) -> pd.DataFrame:
    p = pathlib.Path(path)
    ext = p.suffix.lower()
    if ext in (".csv",):
        return pd.read_csv(p)
    if ext in (".parquet",".pq"):
        return pd.read_parquet(p)
    if ext in (".jsonl",".json"):
        # try ndjson first
        rows=[]
        with open(p,"rt",encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line: continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    # not ndjson; break to parse as a single JSON
                    rows=None
                    break
        if rows is None:
            obj=json.load(open(p,"rt",encoding="utf-8"))
            if isinstance(obj,list): return pd.DataFrame(obj)
            return pd.json_normalize(obj)
        return pd.DataFrame(rows)
    raise ValueError(f"Unsupported file: {path}")

def detect_sources():
    # Prefer Rated export for performance/participation
    rated_perf = _glob_one(["data/raw/ethereum/rated_nodeOperator_*.jsonl"])
    # Lighthouse-esque effectiveness export (if you produce one later)
    lh_perf    = _glob_one(["data/raw/eth/*lighthouse*.jsonl","data/raw/eth/*effectiveness*.jsonl","data/raw/ethereum/*effectiveness*.jsonl"])
    perf = rated_perf or lh_perf

    # Shares: prefer operator-level
    shares = _glob_one([
        "data/processed/ethereum/rated_operator_hhi_*.csv",
        "data/processed/ethereum/owner_hhi_*.csv"
    ])

    # Optional pubkey→operator map
    opmap = _glob_one(["data/processed/operators_normalized.csv", "data/processed/eth/operator_map.csv"])

    return perf, shares, opmap

def load_performance(perf_path: str) -> pd.DataFrame:
    df = read_any(perf_path)
    cols = {c.lower(): c for c in df.columns}

    # Rated case: columns like operator/name, participation, inclusion distance or effectiveness
    rated_like = any("rated" in perf_path.lower() for _ in [0]) or ("nodeoperator" in perf_path.lower())
    if rated_like or ("rated" in " ".join(cols)):
        # Try to detect operator & participation-ish fields
        op = None
        for cand in ["operator","owner","name","entity","nodeOperator","node_operator"]:
            if cand.lower() in cols: op = cols[cand.lower()]; break
        if op is None:
            # Sometimes Rated includes "metadata.operatorName"
            op_matches = [c for c in df.columns if "operator" in c.lower() or "owner" in c.lower() or "name" in c.lower()]
            op = op_matches[0] if op_matches else None
        # Participation proxies (rate, effectiveness, participation score)
        part = None
        for cand in ["participation","participation_rate","effectiveness","attestation_effectiveness","correctness_rate"]:
            if cand.lower() in cols: part = cols[cand.lower()]; break
        # Inclusion/timeliness proxy
        inc = None
        for cand in ["inclusion_distance","median_inclusion_distance","p95_inclusion_distance","timeliness","head_timeliness"]:
            if cand.lower() in cols: inc = cols[cand.lower()]; break

        if op is None:
            # Fall back: no operator field → leave empty; caller can join an external map
            df["operator"] = None
        else:
            df = df.rename(columns={op:"operator"})
        if part is None: df["participation_rate"] = 1.0
        else:            df = df.rename(columns={part:"participation_rate"})
        if inc is None:  df["inclusion_p95"] = 1.0
        else:
            # If it's not p95, approximate (robust aggregate later)
            df = df.rename(columns={inc:"inclusion_distance"})

        # Aggregate to operator
        if "inclusion_distance" in df.columns:
            g = df.groupby("operator", dropna=False).agg(
                n=("operator","size"),
                participation_rate=("participation_rate","mean"),
                inclusion_p95=("inclusion_distance", lambda x: float(pd.Series(x).quantile(0.95)))
            )
        else:
            g = df.groupby("operator", dropna=False).agg(
                n=("operator","size"),
                participation_rate=("participation_rate","mean")
            )
            g["inclusion_p95"] = 1.0
        return g.reset_index()

    # Lighthouse-like: need pubkey, inclusion_distance, head_correct
    # Attempt to normalize
    def pick(*cands):
        for c in cands:
            if c.lower() in cols: return cols[c.lower()]
        return None

    pub = pick("pubkey","validator_pubkey","validator","validator_public_key")
    inc = pick("inclusion_distance","head_inclusion_distance","inclusion_distance_slots")
    head= pick("head_correct","head")
    if pub is None:
        raise KeyError("Need a pubkey-like field for Lighthouse input")
    df = df.rename(columns={pub:"pubkey"})
    if inc is None: df["inclusion_distance"] = 1.0
    else:           df = df.rename(columns={inc:"inclusion_distance"})
    if head is None: df["head_correct"] = 1
    else:            df = df.rename(columns={head:"head_correct"}).assign(head_correct=lambda d: d["head_correct"].astype(int))

    return df
def main():
    perf_path, shares_path, opmap_path = detect_sources()
    if not perf_path:
        sys.exit("No performance file found. Expected Rated or Lighthouse JSONL under data/raw/ethereum or data/raw/eth.")
    if not shares_path:
        sys.exit("No shares file found. Expected rated_operator_hhi_*.csv or owner_hhi_*.csv under data/processed/ethereum.")

    print(f"Using performance: {perf_path}")
    print(f"Using raw shares:  {shares_path}")

    perf = load_performance(perf_path)

    # If we don't have operator column (e.g., Lighthouse), try to map pubkey→operator
    if "operator" not in perf.columns and opmap_path:
        print(f"Joining operator map: {opmap_path}")
        opmap = read_any(opmap_path)
        opmap = opmap.rename(columns={c:c.lower() for c in opmap.columns})
        if "pubkey" in opmap.columns and "operator" in opmap.columns:
            perf = perf.merge(opmap[["pubkey","operator"]], on="pubkey", how="left")
            perf = perf.dropna(subset=["operator"])
            # Re-aggregate now that operator exists
            if "inclusion_distance" in perf.columns:
                perf = perf.groupby("operator", dropna=False).agg(
                    n=("operator","size"),
                    participation_rate=("head_correct","mean"),
                    inclusion_p95=("inclusion_distance", lambda x: float(pd.Series(x).quantile(0.95)))
                ).reset_index()
            else:
                perf = perf.groupby("operator", dropna=False).agg(
                    n=("operator","size"),
                    participation_rate=("head_correct","mean")
                ).reset_index()
                perf["inclusion_p95"]=1.0
        else:
            print("Operator map found but missing columns pubkey/operator; skipping map.", file=sys.stderr)

    # Participation weight = participation_rate × 1/(1+(p95-1)/4)
    if "participation_rate" not in perf.columns:
        perf["participation_rate"] = 1.0
    if "inclusion_p95" not in perf.columns:
        perf["inclusion_p95"] = 1.0
    perf["participation_score"] = perf["participation_rate"].clip(0,1)
    perf["inclusion_score"] = 1.0 / (1.0 + (perf["inclusion_p95"].clip(lower=1.0) - 1.0)/4.0)
    perf["participation_weight"] = (perf["participation_score"] * perf["inclusion_score"]).clip(0,1)

    # Load shares and normalize column names
    shares = read_any(shares_path).rename(columns={c:c.lower() for c in read_any(shares_path).columns})
    # Expect columns like operator & share; try common variants
    op_col = "operator" if "operator" in shares.columns else ("owner" if "owner" in shares.columns else None)
    share_col = "raw_share"
    if "share" in shares.columns: 
        shares = shares.rename(columns={"share":"raw_share"})
    elif "hhi_share" in shares.columns:
        shares = shares.rename(columns={"hhi_share":"raw_share"})
    elif "raw_share" not in shares.columns:
        # try to find a [0,1] column
        for c in shares.columns:
            if c not in ("operator","owner","name") and shares[c].max()<=1.0 and shares[c].min()>=0.0:
                shares = shares.rename(columns={c:"raw_share"})
                break
    if not op_col or "raw_share" not in shares.columns:
        raise KeyError("Shares file must include an operator-like column and a share fraction (renamed to raw_share).")
    shares = shares.rename(columns={op_col:"operator"})
    shares = shares[["operator","raw_share"]]

    # Merge
    df = shares.merge(perf[["operator","participation_weight","participation_rate","inclusion_p95"]], on="operator", how="left")
    df["participation_weight"] = df["participation_weight"].fillna(1.0)
    df["participation_rate"]   = df["participation_rate"].fillna(1.0)
    df["inclusion_p95"]        = df["inclusion_p95"].fillna(1.0)
    df["weighted"] = df["raw_share"] * df["participation_weight"]
    tot = df["weighted"].sum()
    df["effective_share"] = df["weighted"]/tot if tot>0 else df["raw_share"]

    # HHI
    raw_hhi, raw_ne = hhi_from_shares(df["raw_share"])
    eff_hhi, eff_ne = hhi_from_shares(df["effective_share"])

    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(
        f"# Participation-adjusted HHI — Summary\n\n"
        f"- Raw HHI: **{raw_hhi:.6f}**  →  N_eff ≈ **{raw_ne:.2f}**\n"
        f"- Participation-adjusted HHI: **{eff_hhi:.6f}**  →  N_eff ≈ **{eff_ne:.2f}**\n\n"
        f"**Inputs**: {os.path.relpath(perf_path)} + {os.path.relpath(shares_path)}\n"
        f"**Artifact**: {os.path.relpath(str(OUT_PARQUET))}\n"
    )

    print(json.dumps({
        "raw_HHI": raw_hhi, "raw_N_eff": raw_ne,
        "adj_HHI": eff_hhi, "adj_N_eff": eff_ne,
        "out_parquet": str(OUT_PARQUET), "report": str(OUT_REPORT)
    }, indent=2))

if __name__ == "__main__":
    perf_path, shares_path, opmap_path = detect_sources()
    main()
