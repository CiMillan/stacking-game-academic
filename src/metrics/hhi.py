"""
HHI metrics utilities.
- hhi_from_shares(shares): accepts an iterable of stake shares summing to ~1; returns HHI and N_eff.
- load_and_compute_hhi(path, share_col): quick helper for CSV/Parquet with a share column in [0,1].
"""
from __future__ import annotations
from typing import Iterable, Tuple
import math

def hhi_from_shares(shares: Iterable[float]) -> Tuple[float, float]:
    shares = list(shares)
    s2 = sum(x*x for x in shares)
    n_eff = 1.0/s2 if s2 > 0 else math.inf
    return s2, n_eff

def _read_any(path: str):
    import os
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        import pandas as pd
        return pd.read_csv(path)
    elif ext in (".parquet", ".pq"):
        import pandas as pd
        return pd.read_parquet(path)
    elif ext in (".json", ".jsonl"):
        import pandas as pd, json, gzip
        # best-effort jsonl
        rows = []
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt") as f:
            for line in f:
                line=line.strip()
                if line:
                    rows.append(json.loads(line))
        return pd.DataFrame(rows)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def load_and_compute_hhi(path: str, share_col: str="share") -> Tuple[float,float]:
    df = _read_any(path)
    if share_col not in df.columns:
        raise KeyError(f"'{share_col}' not in columns: {list(df.columns)}")
    return hhi_from_shares(df[share_col].astype(float).values)
