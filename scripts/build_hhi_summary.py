import json, math, pathlib, re, sys
from glob import glob
import pandas as pd

ROOT = pathlib.Path(".")
OUT_MD  = ROOT/"reports/metrics/hhi_summary.md"
OUT_JSON= ROOT/"reports/metrics/hhi_summary.json"

def glob_one(pats):
    for pat in pats:
        hits = sorted(glob(pat))
        if hits:
            return hits[0]
    return None

def read_any(path):
    p = pathlib.Path(path)
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    if p.suffix.lower() in (".parquet",".pq"):
        return pd.read_parquet(p)
    raise ValueError(f"Unsupported file type: {path}")

def find_share_col(df):
    # Flexible: look for a fractional column in [0,1] that isn't an id/name
    candidates = []
    for c in df.columns:
        cl=c.lower()
        if any(k in cl for k in ["share","hhi","fraction","weight"]):
            candidates.append(c)
    # prefer explicit names
    for pref in ["raw_share","share","hhi_share","fraction","weight"]:
        for c in df.columns:
            if c.lower()==pref:
                return c
    # fallback heuristic
    num=df.select_dtypes("number")
    for c in num.columns:
        if num[c].min() >= 0 and num[c].max() <= 1 and num[c].sum() > 0.9 and num[c].sum() < 1.1:
            candidates.append(c)
    if candidates:
        return candidates[0]
    raise KeyError("Could not infer a share column in dataframe")

def hhi_from_shares(s):
    s = pd.Series(s, dtype="float64").dropna().values
    s2 = float((s*s).sum())
    n_eff = (1.0/s2) if s2>0 else math.inf
    return s2, n_eff

def summarize(label, path):
    if not path:
        return {"label":label, "file":None, "HHI":None, "N_eff":None}
    df = read_any(path)
    share_col = find_share_col(df)
    H, N = hhi_from_shares(df[share_col])
    return {"label":label, "file":path, "HHI":H, "N_eff":N}

def main():
    eth_op  = glob_one(["data/processed/ethereum/rated_operator_hhi_*.csv"])
    eth_own = glob_one(["data/processed/ethereum/owner_hhi_*.csv"])
    cosmos  = glob_one(["data/processed/cosmos/cosmoshub_hhi_*.csv"])

    sums = [
        summarize("ETH — Operator level", eth_op),
        summarize("ETH — Owner level",    eth_own),
        summarize("Cosmos Hub",           cosmos),
    ]

    # Write JSON (machine-friendly)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(sums, f, indent=2)

    # Write Markdown (human-friendly)
    lines = ["# Concentration Metrics — HHI Summary\n"]
    for s in sums:
        if s["file"] is None:
            lines.append(f"- {s['label']}: **(file not found)**\n")
        else:
            H=s["HHI"]; N=s["N_eff"]
            lines.append(f"- {s['label']}: HHI ≈ **{H:.6f}** → N_eff ≈ **{N:.2f}**  \n  _Source:_ `{s['file']}`")
    OUT_MD.write_text("\n".join(lines)+"\n", encoding="utf-8")

    print("Wrote", OUT_MD)
    print("Wrote", OUT_JSON)
    for s in sums:
        print(s)
if __name__ == "__main__":
    main()
