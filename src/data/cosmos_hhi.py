import os, sys, json, datetime
from decimal import Decimal

def iter_jsonl(p):
    with open(p) as f:
        for line in f:
            line=line.strip()
            if line: yield json.loads(line)

def get_power(v):
    tok = v.get("tokens") or "0"
    try:
        return int(tok)
    except:
        try:
            return int(Decimal(v.get("delegator_shares","0")).to_integral_value())
        except:
            return 0

if __name__=="__main__":
    if len(sys.argv)<3:
        print("Usage: python -m src.data.cosmos_hhi <validators_jsonl> <chain_id>")
        sys.exit(2)
    path, chain = sys.argv[1], sys.argv[2]
    rows=[]
    total=0
    for d in iter_jsonl(path):
        v = d if isinstance(d, dict) else {}
        desc = v.get("description") or {}
        name = (desc.get("moniker") or v.get("operator_address") or "unknown").replace(","," ")
        pwr = get_power(v)
        total += pwr
        rows.append((name, pwr))
    rows.sort(key=lambda x: x[1], reverse=True)
    hhi = sum((p/total)**2 for _,p in rows) if total else 0.0

    outdir="data/processed/cosmos"
    os.makedirs(outdir, exist_ok=True)
    date = datetime.date.today().isoformat()
    out = f"{outdir}/{chain}_hhi_{date}.csv"
    with open(out,"w") as f:
        f.write("name,power,share\n")
        for name,p in rows:
            share = (p/total) if total else 0.0
            f.write(f"{name},{p},{share:.12f}\n")

    print(f"\n=== {chain} validator concentration ({date}) ===")
    print(f"Validators: {len(rows)}  Total power: {total}")
    print(f"HHI (by power): {hhi:.6f}  N_eff ≈ {1/hhi if hhi>0 else 0:.1f}")
    print("\nTop 10:")
    for i,(name,p) in enumerate(rows[:10],1):
        pct = 100*(p/total) if total else 0.0
        print(f"{i:2d}. {name:<30} share={pct:6.2f}% power={p}")
    print(f"\nSaved CSV -> {out}")
