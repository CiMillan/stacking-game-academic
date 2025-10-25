import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from src.models.network_coordination_game import (
    threshold_cascade,
    continuous_equilibrium,  # optional use later
    random_er_graph,         # optional generator mode
)

def load_edgelist_csv(path: Path, undirected: bool = True, weighted: bool = False):
    """
    Expect CSV with columns:
      - src, dst
      - optional: weight
    Node labels can be strings; we map to [0..N-1].
    """
    df = pd.read_csv(path)
    if not {"src","dst"}.issubset(df.columns):
        raise ValueError("Edgelist must have columns: src,dst[,weight].")
    if weighted and "weight" not in df.columns:
        raise ValueError("weighted=True but column 'weight' missing.")
    # Map nodes to indices
    nodes = pd.Index(pd.unique(pd.concat([df["src"], df["dst"]])))
    idx = {n:i for i,n in enumerate(nodes)}
    N = len(nodes)
    A = np.zeros((N, N), dtype=float)
    w = df["weight"].to_numpy() if (weighted and "weight" in df.columns) else np.ones(len(df), dtype=float)
    for (s, d, wt) in zip(df["src"], df["dst"], w):
        i, j = idx[s], idx[d]
        if i == j: 
            continue
        A[i, j] += float(wt)
        if undirected:
            A[j, i] += float(wt)
    # Clean up adjacency
    A = np.nan_to_num(A, nan=0.0, posinf=0.0, neginf=0.0)
    np.fill_diagonal(A, 0.0)
    return A, nodes

def parse_grid(s: str):
    """'0.01,0.03,0.05' -> [0.01,0.03,0.05] ; empty -> []"""
    s = (s or "").strip()
    return [] if not s else [float(x) for x in s.split(",")]

def main():
    ap = argparse.ArgumentParser(description="Monte Carlo network coordination sweeps")
    ap.add_argument("--edgelist", type=Path, help="CSV path with columns src,dst[,weight]")
    ap.add_argument("--generate-er", action="store_true", help="Generate an Erdos–Renyi graph instead of reading CSV")
    ap.add_argument("--n", type=int, default=200, help="ER: number of nodes")
    ap.add_argument("--p", type=float, default=0.03, help="ER: edge probability")
    ap.add_argument("--weighted", action="store_true", help="Treat edgelist as weighted")
    ap.add_argument("--directed", action="store_true", help="Treat edgelist as directed (default undirected)")
    ap.add_argument("--beta-grid", type=str, default="0.01,0.03,0.05", help="Comma list of beta values; used if tau < 0")
    ap.add_argument("--tau-grid", type=str, default="0.2,0.3,0.4", help="Comma list of fractional thresholds in [0,1]")
    ap.add_argument("--trials", type=int, default=200, help="Monte Carlo trials per grid point")
    ap.add_argument("--seed-size", type=int, default=5, help="Number of seed nodes (if >0 overrides seed-frac)")
    ap.add_argument("--seed-frac", type=float, default=0.01, help="Fraction of nodes seeded when seed-size <= 0")
    ap.add_argument("--synchronous", action="store_true", help="Use synchronous updates (monotone)")
    ap.add_argument("--out-dir", type=Path, default=Path("reports/metrics"), help="Output folder")
    ap.add_argument("--label", type=str, default="", help="Optional label to tag outputs")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Load or generate graph
    if args.generate-er:
        A = random_er_graph(args.n, args.p, seed=42)
        nodes = pd.Index([f"n{i}" for i in range(args.n)])
    else:
        if not args.edgelist:
            raise SystemExit("Provide --edgelist CSV or use --generate-er")
        A, nodes = load_edgelist_csv(args.edgelist, undirected=not args.directed, weighted=args.weighted)

    N = A.shape[0]
    deg = A.sum(axis=1)
    beta_vals = parse_grid(args.beta-grid) if hasattr(args, "beta-grid") else parse_grid(args.beta_grid)
    tau_vals  = parse_grid(args.tau_grid)

    rng = np.random.default_rng(123)
    trials_rows = []

    # If tau-grid provided, we run FRACTIONAL thresholds (beta ignored for adoption rule).
    # If tau-grid empty, we use integer thresholds (beta matters via alpha,c,beta).
    run_fractional = len(tau_vals) > 0

    # Fixed alpha,c (not used when fractional thresholds are given)
    alpha = np.zeros(N, dtype=float)
    c     = np.zeros(N, dtype=float)

    grid = tau_vals if run_fractional else beta_vals
    grid_name = "tau" if run_fractional else "beta"

    if not grid:
        raise SystemExit("Supply --tau-grid (fractional) or --beta-grid (integer-threshold mode).")

    # Determine seed count
    if args.seed_size > 0:
        seed_k = args.seed_size
    else:
        seed_k = max(1, int(round(args.seed_frac * N)))

    for gval in grid:
        tau_vec = None
        beta = 1.0
        if run_fractional:
            # same tau for all nodes (customize as needed)
            tau = float(gval)
            tau_vec = np.full(N, tau, dtype=float)
        else:
            beta = float(gval)

        for trial in range(1, args.trials + 1):
            seed = rng.choice(N, size=seed_k, replace=False)
            res = threshold_cascade(
                A, alpha=alpha, c=c, beta=beta, seed=seed,
                fractional_thresholds=tau_vec,
                synchronous=args.synchronous,
            )
            trials_rows.append({
                "grid_param": gval,
                "param_name": grid_name,
                "trial": trial,
                "N": N,
                "E": int(A.sum() / (2 if (not args.directed) else 1)),
                "seed_size": seed_k,
                "adoption_rate": res.adoption_rate,
                "steps": res.steps,
                "converged": int(res.converged),
                "avg_degree": float(deg.mean()),
                "is_fractional": int(run_fractional),
            })

    trials_df = pd.DataFrame(trials_rows)
    label = f"_{args.label}" if args.label else ""
    trials_path = args.out_dir / f"ncg_mc_trials{label}.csv"
    trials_df.to_csv(trials_path, index=False)

    # Summaries by grid value
    def q(s, k): 
        return s.quantile(k)

    grp = trials_df.groupby(["param_name","grid_param"], as_index=False).agg(
        trials=("trial","count"),
        conv_rate=("converged","mean"),
        adopt_mean=("adoption_rate","mean"),
        adopt_q10=("adoption_rate", lambda s: q(s,0.10)),
        adopt_q25=("adoption_rate", lambda s: q(s,0.25)),
        adopt_q50=("adoption_rate", lambda s: q(s,0.50)),
        adopt_q75=("adoption_rate", lambda s: q(s,0.75)),
        adopt_q90=("adoption_rate", lambda s: q(s,0.90)),
        steps_mean=("steps","mean"),
        steps_q75=("steps", lambda s: q(s,0.75)),
        steps_q90=("steps", lambda s: q(s,0.90)),
        N=("N","first"),
        E=("E","first"),
        seed_size=("seed_size","first"),
        avg_degree=("avg_degree","first"),
        is_fractional=("is_fractional","first"),
    ).sort_values(["param_name","grid_param"])

    summary_path = args.out_dir / f"ncg_mc_summary{label}.csv"
    grp.to_csv(summary_path, index=False)

    print(f"Wrote trials → {trials_path}")
    print(f"Wrote summary → {summary_path}")

if __name__ == "__main__":
    main()
