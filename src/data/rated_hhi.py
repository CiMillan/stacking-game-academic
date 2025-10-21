import os, sys, json, datetime
from collections import defaultdict

CANDIDATE_BAL_KEYS = [
    "sumEndEpochEffectiveBalance", "sumEffectiveBalance",
    "effectiveBalanceSum", "effective_balance_sum",
    "effective_balance_gwei", "effective_balance"
]

def iter_jsonl(p):
    with open(p, "r") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def get_eff_gwei(d):
    # try multiple keys; fall back to 32e9 * validatorCount if available
    for k in CANDIDATE_BAL_KEYS:
        if k in d:
            try:
                return int(d[k])
            except Exception:
                try:
                    return int(float(d[k]))
                except Exception:
                    pass
    vc = d.get("validatorCount") or d.get("validators") or 0
    try:
        vc = int(vc)
    except Exception:
        vc = 0
    return int(vc * 32_000_000_000)  # approx

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.data.rated_hhi data/raw/ethereum/rated_nodeOperator_YYYY-MM-DD.jsonl")
        sys.exit(2)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Input not found: {path}")
        sys.exit(2)

    by_op = defaultdict(lambda: {"eff":0, "validators":0, "type":None})
    total = 0

    for d in iter_jsonl(path):
        if not isinstance(d, dict):
            continue
        name = d.get("name") or d.get("id") or "unknown"
        etype = d.get("entityType")
        eff = get_eff_gwei(d)
        vc = d.get("validatorCount") or d.get("validators") or 0
        try: vc=int(vc)
        except: vc=0

        by_op[name]["eff"] += eff
        by_op[name]["validators"] += vc
        by_op[name]["type"] = etype
        total += eff

    rows = []
    hhi = 0.0
    for name, s in by_op.items():
        share = (s["eff"]/total) if total else 0.0
        hhi += share*share
        rows.append({
            "name": name,
            "entity_type": s["type"],
            "validators": s["validators"],
            "effective_balance_gwei": s["eff"],
            "share": share
        })
    rows.sort(key=lambda r: r["share"], reverse=True)

    out_dir = "data/processed/ethereum"
    os.makedirs(out_dir, exist_ok=True)
    date = datetime.date.today().isoformat()
    out_csv = os.path.join(out_dir, f"rated_operator_hhi_{date}.csv")
    with open(out_csv, "w") as f:
        f.write("name,entity_type,validators,effective_balance_gwei,share\n")
        for r in rows:
            f.write(f'{r["name"]},{r["entity_type"]},{r["validators"]},{r["effective_balance_gwei"]},{r["share"]:.12f}\n')

    print(f"\n=== Rated operator concentration ({date}) ===")
    print(f"Operators: {len(rows)}")
    print(f"Total effective balance (ETH): {total/1e9:.2f}")
    print(f"HHI (by effective balance): {hhi:.6f}")
    print("\nTop 10 operators:")
    for i, r in enumerate(rows[:10], 1):
        print(f"{i:2d}. {r['name']:<30} share={100*r['share']:6.2f}%  eff={r['effective_balance_gwei']/1e9:,.0f} ETH  validators={r['validators']}")
    print(f"\nSaved CSV -> {out_csv}")
if __name__ == "__main__":
    main()
