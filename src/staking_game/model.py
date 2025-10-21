from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Operator:
    name: str
    a: float   # ops convexity
    b: float   # correlated risk convexity
    gamma: float  # market penalty convexity

@dataclass
class Params:
    R: float
    operators: List[Operator]

def optimal_share(R: float, a: float, b: float, gamma: float) -> float:
    denom = 2.0 * (a + b + gamma)
    if denom <= 0:
        raise ValueError("Convexity must be positive: a+b+gamma > 0")
    return R / denom

def normalize_shares(shares: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(v, 0.0) for v in shares.values())
    if total == 0:
        return {k: 0.0 for k in shares}
    return {k: v / total for k, v in shares.items()}
