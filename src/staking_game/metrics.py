from __future__ import annotations
import numpy as np

def gini(x: np.ndarray) -> float:
    """Gini coefficient for non-negative shares that sum to 1."""
    x = np.asarray(x, dtype=float)
    if np.any(x < 0):
        raise ValueError("Shares must be non-negative.")
    if x.sum() <= 0:
        return 0.0
    x = np.sort(x)
    n = x.size
    cumulative = np.cumsum(x)
    # Relative mean absolute difference formula specialized for shares
    g = (n + 1 - 2 * (cumulative / cumulative[-1]).sum()) / n
    return float(g)

def nakamoto(shares: np.ndarray, threshold: float = 0.33) -> int:
    """
    Minimum number of top operators whose cumulative share >= threshold.
    For threshold=0.5 gives a majority; for 0.33 a blocking coalition.
    """
    s = np.sort(np.asarray(shares, dtype=float))[::-1]
    cum = np.cumsum(s)
    idx = np.searchsorted(cum, threshold, side="left")
    return int(idx + 1) if idx < s.size else s.size
