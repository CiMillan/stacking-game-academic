from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def estimate_b(df: pd.DataFrame, R: float) -> pd.Series:
    """
    b_i ~ E[loss|event] * Pr(event) * rho_i
    Here, proxy:
      - Pr(event) ~ missed_rate (if available) else 0.01 baseline
      - E[loss|event] ~ 0.10 * R (10% annual reward lost during correlated event)
      - rho_i ~ scaled by operator share (as a rough shared-fate proxy) unless provided
    """
    pr = df["missed_rate"] if "missed_rate" in df.columns else 0.01
    pr = pd.to_numeric(pr, errors="coerce").fillna(0.01).clip(0, 1)
    rho = df["share"].clip(0, 1)  # simplistic proxy; refine with real co-failure correlations if available
    loss = 0.10 * R
    b = loss * pr * rho
    # enforce strictly positive with floor
    return (b + 1e-6)

def estimate_gamma(df: pd.DataFrame) -> pd.Series:
    """
    gamma_i ~ market penalty curvature.
    Proxy from size-aversion: larger operators face stronger marginal penalty.
    Use gamma_i = k * rank_percentile where k=0.02 baseline; refine with delegation elasticity later.
    """
    k = 0.02
    rank = df["share"].rank(ascending=True, pct=True)  # small share -> small gamma, big share -> big gamma
    gamma = k * rank
    return (gamma + 1e-6)

def estimate_a(df: pd.DataFrame, R: float, b: pd.Series, gamma: pd.Series) -> pd.Series:
    """
    From U_i/s_i = R - (a_i + b_i + gamma_i) * s_i  and assuming U_i/s_i ~ observed apr (if present),
    solve for a_i: a_i ~ (R - apr_i)/s_i - b_i - gamma_i.
    If apr missing, use a mild baseline proportional to 0.5 * gamma.
    """
    s = df["share"].clip(lower=1e-6)
    if "apr" in df.columns:
        apr = pd.to_numeric(df["apr"], errors="coerce")
        apr = apr.fillna(apr.median() if not np.isnan(apr.median()) else R)
        est = (R - apr) / s - b - gamma
        # keep positive and reasonable
        est = est.clip(lower=1e-6)
        return est
    else:
        return 0.5 * gamma + 1e-6

def summarize_params(a: pd.Series, b: pd.Series, gamma: pd.Series) -> dict:
    def meanpos(x): return float(np.mean(np.asarray(x, dtype=float)))
    return {
        "mean_a": meanpos(a),
        "mean_b": meanpos(b),
        "mean_gamma": meanpos(gamma)
    }

def main():
    ap = argparse.ArgumentParser(description="Estimate mean (a, b, gamma) from normalized operators table.")
    ap.add_argument("--operators", type=str, default="data/processed/operators_normalized.csv")
    ap.add_argument("--R", type=float, default=0.042, help="Nominal gross reward APR, e.g., 0.042 for 4.2%")
    ap.add_argument("--outdir", type=str, default="data/processed")
    args = ap.parse_args()

    df = pd.read_csv(args.operators)
    b = estimate_b(df, args.R)
    gamma = estimate_gamma(df)
    a = estimate_a(df, args.R, b, gamma)

    params = summarize_params(a, b, gamma)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame({
        "operator": df["operator"],
        "share": df["share"],
        "a": a, "b": b, "gamma": gamma
    }).to_csv(outdir / "operator_params.csv", index=False)
    pd.DataFrame([params]).to_csv(outdir / "params_summary.csv", index=False)

    print(f"[calibrate] mean_a={params['mean_a']:.5f} | mean_b={params['mean_b']:.5f} | mean_gamma={params['mean_gamma']:.5f}")
    print(f"[calibrate] wrote {outdir/'operator_params.csv'} and {outdir/'params_summary.csv'}")

if __name__ == "__main__":
    main()
