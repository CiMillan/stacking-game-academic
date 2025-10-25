import pathlib, glob, json
import pandas as pd

ROOT = pathlib.Path(".")
OUT  = ROOT / "reports/simulations/mc_summary.md"

def latest_run_dir(root="runs/ethereum/mc_equilibrium"):
    paths = sorted(glob.glob(f"{root}/*"))
    return pathlib.Path(paths[-1]) if paths else None

def main():
    run = latest_run_dir()
    if not run:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text("# Monte Carlo — Summary\n\n_No runs found. Run `make mc-equilibrium` first._\n", encoding="utf-8")
        print("No runs found; wrote placeholder summary.")
        return

    q_csv  = run / "quantiles.csv"
    s_csv  = run / "summary.csv"
    meta_j = run / "meta.json"

    if not (q_csv.exists() and s_csv.exists()):
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(f"# Monte Carlo — Summary\n\n_Run folder missing expected files: {run}_\n", encoding="utf-8")
        print(f"Missing files in {run}")
        return

    q = pd.read_csv(q_csv)
    s = pd.read_csv(s_csv).iloc[0].to_dict()
    meta = {}
    if meta_j.exists():
        try: meta = json.loads(meta_j.read_text(encoding="utf-8"))
        except Exception: meta = {}

    # Render
    lines = []
    lines.append("# Monte Carlo — Latest Run Summary\n")
    lines.append(f"_Run:_ `{run}`\n")
    if meta:
        args = meta.get("args", {})
        draws = args.get("draws", "—"); N = args.get("N", "—"); seed = args.get("seed", "—")
        lines.append(f"- **Draws:** {draws} · **N (operators):** {N} · **Seed:** {seed}\n")

    lines.append("\n## Medians & Tail Probabilities\n")
    lines.append(f"- Median **HHI**: **{s.get('HHI_med', float('nan')):.6f}**")
    lines.append(f"- Median **N_eff**: **{s.get('N_eff_med', float('nan')):.2f}**")
    if 'Top10_med' in s:
        lines.append(f"- Median **Top10 share**: **{s['Top10_med']:.3f}**")
    for key in [k for k in s.keys() if k.startswith("P(N_eff<")]:
        lines.append(f"- **{key}**: **{s[key]:.3f}**")

    lines.append("\n## Quantiles (5%, 25%, 50%, 75%, 95%)\n")
    # Keep only expected columns if present
    keep = [c for c in ["HHI","N_eff","Top1","Top5","Top10"] if c in q.columns]
    q_fmt = q.copy()
    if "HHI" in q_fmt: q_fmt["HHI"] = q_fmt["HHI"].map(lambda v: f"{v:.6f}")
    if "N_eff" in q_fmt: q_fmt["N_eff"] = q_fmt["N_eff"].map(lambda v: f"{v:.2f}")
    for c in ["Top1","Top5","Top10"]:
        if c in q_fmt: q_fmt[c] = q_fmt[c].map(lambda v: f"{v:.3f}")
    try:
    try:
    lines.append(q_fmt[["quantile"]+keep].to_markdown(index=False))
except Exception:
    # markdown fallback if tabulate is missing
    lines.append("\n```\n" + q_fmt[["quantile"]+keep].to_string(index=False) + "\n```")

except Exception:
    # Fallback: simple text table if tabulate is missing
    lines.append("\n```
" + q_fmt[["quantile"]+keep].to_string(index=False) + "\n```")


    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
