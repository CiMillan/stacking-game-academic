import pathlib, glob, json
import pandas as pd

ROOT = pathlib.Path(".")
OUT  = ROOT / "reports/simulations/mc_summary.md"

def latest_run_dir(root="runs/ethereum/mc_equilibrium"):
    paths = sorted(glob.glob(f"{root}/*"))
    return pathlib.Path(paths[-1]) if paths else None

def render_markdown_table(df):
    """Render a small DataFrame as GitHub-flavored markdown without requiring tabulate."""
    headers = list(df.columns)
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
    return "\n".join(lines)

def main():
    run = latest_run_dir()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    if not run:
        OUT.write_text("# Monte Carlo — Summary\n\n_No runs found. Run `make mc-equilibrium` first._\n", encoding="utf-8")
        print("No runs found; wrote placeholder summary.")
        return

    q_csv  = run / "quantiles.csv"
    s_csv  = run / "summary.csv"
    meta_j = run / "meta.json"

    if not (q_csv.exists() and s_csv.exists()):
        OUT.write_text(f"# Monte Carlo — Summary\n\n_Run folder missing expected files: {run}_\n", encoding="utf-8")
        print(f"Missing files in {run}")
        return

    q = pd.read_csv(q_csv)
    s = pd.read_csv(s_csv).iloc[0].to_dict()
    meta = {}
    if meta_j.exists():
        try:
            meta = json.loads(meta_j.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    # Format quantiles nicely
    q_fmt = q.copy()
    for col, fmt in [("HHI","{:.6f}"), ("N_eff","{:.2f}"), ("Top1","{:.3f}"), ("Top5","{:.3f}"), ("Top10","{:.3f}")]:
        if col in q_fmt.columns:
            q_fmt[col] = q_fmt[col].map(lambda v: fmt.format(v))

    keep = [c for c in ["HHI","N_eff","Top1","Top5","Top10"] if c in q_fmt.columns]
    table_md = render_markdown_table(q_fmt[["quantile"] + keep])

    # Render summary
    lines = []
    lines.append("# Monte Carlo — Latest Run Summary\n")
    lines.append(f"_Run:_ `{run}`\n")

    if meta:
        args = meta.get("args", {})
        draws = args.get("draws", "—"); N = args.get("N", "—"); seed = args.get("seed", "—")
        lines.append(f"- **Draws:** {draws} · **N (operators):** {N} · **Seed:** {seed}\n")

    lines.append("\n## Medians & Tail Probabilities\n")
    if "HHI_med" in s:   lines.append(f"- Median **HHI**: **{s['HHI_med']:.6f}**")
    if "N_eff_med" in s: lines.append(f"- Median **N_eff**: **{s['N_eff_med']:.2f}**")
    if "Top10_med" in s: lines.append(f"- Median **Top10 share**: **{s['Top10_med']:.3f}**")
    for key in sorted([k for k in s.keys() if k.startswith("P(N_eff<")]):
        lines.append(f"- **{key}**: **{s[key]:.3f}**")

    lines.append("\n## Quantiles (5%, 25%, 50%, 75%, 95%)\n")
    lines.append(table_md)

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
