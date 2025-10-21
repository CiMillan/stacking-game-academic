import json, os, sys, math, datetime
from collections import defaultdict

def iter_jsonl(path):
    with open(path, "r") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def owner_from_withdrawal_creds(wc: str):
    if not isinstance(wc, str):
        return "unknown"
    wc = wc.lower()
    if wc.startswith("0x01") and len(wc) == 66:
        # 0x01 + 11 bytes padding + 20-byte ETH1 address
        # Take the last 40 hex chars as the ETH1 address
        return "eth1:" + "0x" + wc[-40:]
    elif wc.startswith("0x00"):
        # legacy BLS withdrawal; group by the credential itself
        return "bls:" + wc
    return "unknown"

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.data.eth_merge_hhi <validators_jsonl_path>")
        sys.exit(2)
    inpath = sys.argv[1]
    if not os.path.exists(inpath):
        print(f"Input not found: {inpath}")
        sys.exit(2)

    total_eff = 0
    by_owner = defaultdict(lambda: {"validators":0, "effective_balance":0})
    active_statuses = {"active_ongoing","active_exiting","active_slashed","active"}  # be generous

    for row in iter_jsonl(inpath):
        v = row.get("validator") or {}
        status = row.get("status") or v.get("status")
        if status and status not in active_statuses:
            continue
        eff = v.get("effective_balance")
        try:
            eff = int(eff)
        except Exception:
            eff = None
        wc = v.get("withdrawal_credentials")
        owner = owner_from_withdrawal_creds(wc)
        by_owner[owner]["validators"] += 1
        if eff is not None:
            by_owner[owner]["effective_balance"] += eff
            total_eff += eff

    # compute shares & HHI (by effective balance)
    rows = []
    hhi = 0.0
    for owner, stats in by_owner.items():
        share = (stats["effective_balance"] / total_eff) if total_eff else 0.0
        hhi += share * share
        rows.append({
            "owner": owner,
            "validators": stats["validators"],
            "effective_balance_gwei": stats["effective_balance"],
            "share": share
        })

    rows.sort(key=lambda r: r["share"], reverse=True)

    # write CSV
    date_str = datetime.date.today().isoformat()
    out_dir = "data/processed/ethereum"
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, f"owner_hhi_{date_str}.csv")
    with open(out_csv, "w") as f:
        f.write("owner,validators,effective_balance_gwei,share\n")
        for r in rows:
            f.write(f'{r["owner"]},{r["validators"]},{r["effective_balance_gwei"]},{r["share"]:.12f}\n')

    # pretty print summary
    top_k = 10
    print(f"\n=== Concentration summary ({date_str}) ===")
    print(f"Active owners: {len(rows)}")
    print(f"Total effective balance (ETH): {total_eff/1e9:.2f}")
    print(f"HHI (by effective balance): {hhi:.6f}")
    print("\nTop 10 owners by share:")
    for i, r in enumerate(rows[:top_k], 1):
        pct = 100 * r["share"]
        eth = r["effective_balance_gwei"] / 1e9
        print(f"{i:2d}. {r['owner']:<46}  share={pct:6.2f}%  eff_bal={eth:,.0f} ETH  validators={r['validators']}")
    print(f"\nSaved CSV -> {out_csv}")

if __name__ == "__main__":
    main()
