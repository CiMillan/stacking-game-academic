from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def read_ethereum_validators(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # standardize columns
    cols = {c.lower(): c for c in df.columns}
    for need in ["operator"]:
        if need not in [c.lower() for c in df.columns]:
            raise ValueError(f"Missing required column '{need}' in {path}")
    # unify names
    ren = {}
    for c in df.columns:
        cl = c.lower()
        if cl in ("share","stake_share","stake_pct","pct"):
            ren[c] = "share"
        elif cl in ("stake","stake_eth","effective_balance_eth","balance_eth"):
            ren[c] = "stake_eth"
        elif cl == "apr":
            ren[c] = "apr"
        elif cl == "missed_rate":
            ren[c] = "missed_rate"
        elif cl == "slashed":
            ren[c] = "slashed"
        elif cl == "client":
            ren[c] = "client"
        elif cl == "region":
            ren[c] = "region"
    df = df.rename(columns=ren)
    # compute shares if missing
    if "share" not in df.columns and "stake_eth" in df.columns:
        total = df["stake_eth"].sum()
        df["share"] = df["stake_eth"] / total if total > 0 else 0.0
    # coerce types
    for c in ("share","apr","missed_rate"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "slashed" in df.columns:
        df["slashed"] = pd.to_numeric(df["slashed"], errors="coerce").fillna(0).astype(int)
    # drop empties and renormalize shares
    df = df.dropna(subset=["operator","share"])
    df = df.sort_values("share", ascending=False).reset_index(drop=True)
    # renormalize to sum to 1
    ssum = df["share"].sum()
    if ssum > 0:
        df["share"] = df["share"] / ssum
    return df

def write_normalized(df: pd.DataFrame, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    df.to_csv(outdir / "operators_normalized.csv", index=False)
    return outdir / "operators_normalized.csv"

def main():
    ap = argparse.ArgumentParser(description="Normalize raw validator CSVs into a unified operators table.")
    ap.add_argument("--eth-validators", type=str, default="data/raw/ethereum/validators.csv",
                    help="Path to Ethereum validators CSV")
    ap.add_argument("--outdir", type=str, default="data/processed", help="Output directory")
    args = ap.parse_args()
    df = read_ethereum_validators(Path(args.eth_validators))
    out = write_normalized(df, Path(args.outdir))
    print(f"[ingest] wrote {out} ({len(df)} operators), top-5 share={df.head(5)['share'].sum():.3f}")
if __name__ == "__main__":
    main()
