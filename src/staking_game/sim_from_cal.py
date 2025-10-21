from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from . import sim as S

def main():
    p = argparse.ArgumentParser(description="Run simulation using calibrated means from params_summary.csv")
    p.add_argument("--params", type=str, default="data/processed/params_summary.csv")
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--R", type=float, default=0.042)
    p.add_argument("--cv", type=float, default=0.6)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=str, default="runs")
    p.add_argument("--plot", action="store_true")
    args = p.parse_args()

    df = pd.read_csv(args.params)
    mean_a = float(df["mean_a"].iloc[0])
    mean_b = float(df["mean_b"].iloc[0])
    mean_gamma = float(df["mean_gamma"].iloc[0])

    results = S.simulate(
        n=args.n, R=args.R,
        mean_a=mean_a, mean_b=mean_b, mean_gamma=mean_gamma,
        cv=args.cv, seed=args.seed,
    )
    outdir = Path(args.out) / "sim_from_cal"
    df_ops = S.save_outputs(results, outdir)
    if args.plot:
        S.plots(df_ops, outdir)

    print(f"[sim-from-cal] a={mean_a:.6f} b={mean_b:.6f} gamma={mean_gamma:.6f}")
    print(f"[sim-from-cal] wrote {outdir}/operators.csv and metrics.txt")
if __name__ == "__main__":
    main()
