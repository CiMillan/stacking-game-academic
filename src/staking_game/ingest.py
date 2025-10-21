from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def read_ethereum_validators(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    # require operator column (any case)
    lower = {c.lower(): c for c in df.columns}
    if "operator" not in lower:
        raise ValueError(f"Missing required column 'operator' in {path}")
    # rename commonly used columns
    ren = {}
    for c in df.columns:
        cl = c.lower()
        if cl in ("share","stake_share","stake_pct","pct"):
            ren[c] = "share"
        elif cl in ("stake","stake_eth","effective_balance_eth","balance_eth","stake_ether"):
            ren[c] = "stake_eth"
        elif cl == "apr":
            ren[c] = "apr"
        elif cl in ("missed_rate","miss_rate","missed"):
            ren[c] = "missed_rate"
        elif cl == "slashed":
            ren[c] = "slashed"
        elif cl == "client":
            ren[c] = "client"
        elif cl == "region":
            ren[c] = "region"
    df = df.rename(columns=ren)

    # coerce numeric
    for c in ("share","stake_eth","apr","missed_rate"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # compute shares if missing OR not usable
    need_share = False
    if "share" not in df.columns:
        need_share = True
    else:
        # if share exists but is all NaN or non-positive, recompute
        if df["share"].isna().all() or (pd.to_numeric(df["share"], errors="coerce").fillna(0) <= 0).all():
            need_share = True

    if need_share:
        if "stake_eth" not in df.columns:
            raise ValueError("No 'share' and no 'stake_eth' to compute from.")
        total = pd.to_numeric(df["stake_eth"], errors="coerce").sum()
        df["share"] = pd.to_numeric(df["stake_eth"], errors="coerce") / total if total > 0 else np.nan

    # tidy + filter
    df = df[["operator","share"] + [c for c in ("stake_eth","apr","client","region","missed_rate","slashed") if c in df.columns]]
    df = df.dropna(subset=["operator","share"])
    df = df[df["share"] > 0]
    df = df.sort_values("share", ascending=False).reset_index(drop=True)
    # renormalize to 1
    ssum = df["share"].sum()
    if ssum > 0:
        df["share"] = df["share"] / ssum
    return df

def write_normalized(df: pd.DataFrame, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "operators_normalized.csv"
    df.to_csv(out, index=False)
    return out

def main():
    ap = argparse.ArgumentParser(description="Normalize raw validator CSVs into a unified operators table.")
    ap.add_argument("--eth-validators", type=str, default="data/raw/ethereum/validators.csv",
                    help="Path to Ethereum validators CSV")
    ap.add_argument("--outdir", type=str, default="data/processed", help="Output directory")
    args = ap.parse_args()

    df = read_ethereum_validators(Path(args.eth_validators))
    out = write_normalized(df, Path(args.outdir))
    top5 = df.head(5)["share"].sum() if not df.empty else 0.0
    print(f"[ingest] wrote {out} ({len(df)} operators), top-5 share={top5:.3f}")

if __name__ == "__main__":
    main()
