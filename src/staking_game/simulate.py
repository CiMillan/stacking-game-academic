from __future__ import annotations
import argparse, yaml
from pathlib import Path
import pandas as pd
from .model import Operator, optimal_share, normalize_shares
from .plotting import plot_shares

def run(config_path: str, do_plot: bool = False) -> pd.DataFrame:
    cfg = yaml.safe_load(Path(config_path).read_text())
    R = float(cfg["R"])
    ops = [Operator(**o) for o in cfg["operators"]]

    raw = {op.name: optimal_share(R, op.a, op.b, op.gamma) for op in ops}
    shares = normalize_shares(raw)

    df = pd.DataFrame([
        {"operator": op.name, "s_star": shares[op.name], "a": op.a, "b": op.b, "gamma": op.gamma}
        for op in ops
    ]).sort_values("s_star", ascending=False)

    if do_plot:
        plot_shares(df)
    return df

def main():
    ap = argparse.ArgumentParser()
    default_cfg = Path(__file__).resolve().parents[2] / "configs" / "params.yaml"
    ap.add_argument("--config", default=str(default_cfg), help="Path to YAML config")
    ap.add_argument("--plot", action="store_true", help="Show bar chart")
    args = ap.parse_args()
    df = run(args.config, do_plot=args.plot)
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()
