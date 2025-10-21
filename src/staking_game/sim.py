from __future__ import annotations
import argparse
import datetime as dt
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .metrics import gini, nakamoto

def draw_positive_lognormal(n: int, mean: float, cv: float, rng: np.random.Generator) -> np.ndarray:
    """
    Draw lognormal parameters with target arithmetic mean and coefficient of variation (cv = std/mean).
    mean>0, cv>=0. Returns array of length n.
    """
    mean = float(mean)
    cv = max(float(cv), 1e-9)
    # For lognormal: arithmetic mean m = exp(mu + sigma^2/2); variance v = (exp(sigma^2)-1)exp(2mu+sigma^2)
    # CV^2 = exp(sigma^2) - 1  => sigma^2 = ln(1+cv^2)
    sigma2 = np.log(1 + cv**2)
    sigma = np.sqrt(sigma2)
    mu = np.log(mean) - sigma2 / 2.0
    return rng.lognormal(mean=mu, sigma=sigma, size=n)

def equilibrium_shares(Ri: np.ndarray, a: np.ndarray, b: np.ndarray, gamma: np.ndarray) -> np.ndarray:
    """
    Best-response interior solution: s_i* = R_i / (2*(a_i + b_i + gamma_i)).
    Normalized to sum to 1 for a stationary distribution.
    """
    denom = 2.0 * (a + b + gamma)
    raw = np.maximum(Ri / denom, 0.0)
    total = raw.sum()
    if total <= 0:
        # fall back to equal shares to avoid division by zero
        return np.ones_like(raw) / raw.size
    return raw / total

def risk_adjusted_apr(Ri: np.ndarray, a: np.ndarray, b: np.ndarray, gamma: np.ndarray, s: np.ndarray) -> np.ndarray:
    """
    Per-operator risk-adjusted APR proxy from U_i / s_i = R_i - (a_i+b_i+gamma_i)*s_i.
    """
    return Ri - (a + b + gamma) * s

def simulate(
    n: int,
    R: float,
    mean_a: float,
    mean_b: float,
    mean_gamma: float,
    cv: float,
    seed: int | None,
    feedback_iters: int = 0,
    feedback_strength: float = 0.2,
):
    rng = np.random.default_rng(seed)
    # Allow heterogeneity in rewards (small dispersion) if desired later
    Ri = np.full(n, R, dtype=float)

    a = draw_positive_lognormal(n, mean_a, cv, rng)
    b = draw_positive_lognormal(n, mean_b, cv, rng)
    gamma = draw_positive_lognormal(n, mean_gamma, cv, rng)

    s = equilibrium_shares(Ri, a, b, gamma)

    # Optional mild feedback: as shares concentrate, increase b and gamma a bit (shared fate & social penalty)
    for _ in range(max(0, feedback_iters)):
        # exposure factor proportional to s relative to average 1/n
        exposure = s / (1.0 / n)
        b = b * (1.0 + feedback_strength * (exposure - 1.0))
        gamma = gamma * (1.0 + 0.5 * feedback_strength * (exposure - 1.0))
        s = equilibrium_shares(Ri, a, b, gamma)

    apr_ra = risk_adjusted_apr(Ri, a, b, gamma, s)

    results = {
        "shares": s,
        "a": a,
        "b": b,
        "gamma": gamma,
        "R": Ri,
        "apr_ra": apr_ra,
        "gini": gini(s),
        "nakamoto_33": nakamoto(s, threshold=0.33),
        "nakamoto_50": nakamoto(s, threshold=0.50),
        "mean_apr_ra": float(np.sum(s * apr_ra)),
    }
    return results

def save_outputs(results, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({
        "share": results["shares"],
        "a": results["a"],
        "b": results["b"],
        "gamma": results["gamma"],
        "R": results["R"],
        "apr_ra": results["apr_ra"],
    }).sort_values("share", ascending=False).reset_index(drop=True)
    df.to_csv(outdir / "operators.csv", index=False)

    # metrics
    with open(outdir / "metrics.txt", "w") as f:
        f.write(f"Gini: {results['gini']:.4f}\n")
        f.write(f"Nakamoto >33%: {results['nakamoto_33']}\n")
        f.write(f"Nakamoto >50%: {results['nakamoto_50']}\n")
        f.write(f"Mean risk-adjusted APR: {results['mean_apr_ra']*100:.2f}%\n")

    return df

def plots(df: pd.DataFrame, outdir: Path):
    # Top-20 bar
    top = df.head(20)
    plt.figure()
    plt.bar(range(len(top)), top["share"].values)
    plt.xticks(range(len(top)), [f"#{i+1}" for i in range(len(top))], rotation=0)
    plt.ylabel("Stake share")
    plt.title("Top-20 operator shares")
    plt.tight_layout()
    plt.savefig(outdir / "top20_shares.png", dpi=144)

    # Lorenz / cumulative curve
    s = np.sort(df["share"].values)
    cum = np.cumsum(s)
    x = np.linspace(0, 1, len(s))
    plt.figure()
    plt.plot(x, cum, label="Cumulative shares")
    plt.plot([0, 1], [0, 1], linestyle="--", label="Equality line")
    plt.xlabel("Fraction of operators")
    plt.ylabel("Fraction of stake")
    plt.title("Cumulative stake distribution")
    plt.legend()
    plt.tight_layout()
    plt.savefig(outdir / "lorenz.png", dpi=144)

def parse_args():
    p = argparse.ArgumentParser(description="Simulate PoS validator equilibrium shares.")
    p.add_argument("--n", type=int, default=200, help="Number of operators")
    p.add_argument("--R", type=float, default=0.042, help="Nominal gross reward (APR, e.g., 0.042 = 4.2%)")
    p.add_argument("--mean-a", type=float, default=0.02, help="Mean operational convexity a")
    p.add_argument("--mean-b", type=float, default=0.03, help="Mean correlated-risk convexity b")
    p.add_argument("--mean-gamma", type=float, default=0.015, help="Mean social penalty convexity gamma")
    p.add_argument("--cv", type=float, default=0.6, help="Coefficient of variation for (a,b,gamma)")
    p.add_argument("--seed", type=int, default=42, help="RNG seed")
    p.add_argument("--feedback-iters", type=int, default=0, help="Feedback iterations for endogenous b,gamma")
    p.add_argument("--feedback-strength", type=float, default=0.2, help="Strength of feedback (>0)")
    p.add_argument("--out", type=str, default="runs", help="Output base directory")
    p.add_argument("--plot", action="store_true", help="Save figures")
    return p.parse_args()

def main():
    args = parse_args()
    ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outdir = Path(args.out) / f"sim_{ts}"
    results = simulate(
        n=args.n, R=args.R,
        mean_a=args.mean_a, mean_b=args.mean_b, mean_gamma=args.mean_gamma,
        cv=args.cv, seed=args.seed,
        feedback_iters=args.feedback_iters, feedback_strength=args.feedback_strength
    )
    df = save_outputs(results, outdir)
    if args.plot:
        plots(df, outdir)

    # Console summary
    print(f"[sim] wrote {outdir}/operators.csv")
    print(f"[sim] Gini={results['gini']:.3f} | Nk33={results['nakamoto_33']} | Nk50={results['nakamoto_50']} | Mean APR*={results['mean_apr_ra']*100:.2f}%")

if __name__ == "__main__":
    main()
