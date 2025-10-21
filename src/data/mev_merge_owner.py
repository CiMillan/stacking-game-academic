import os, sys, json, glob, datetime
from collections import defaultdict

# Candidate keys used for proposer pubkey across relay APIs
PROP_KEYS = ["proposer_pubkey","proposerPubkey","proposer_public_key","proposerPublicKey"]

def load_validator_owner_map(validators_jsonl):
    def owner_from_wc(wc: str):
        if not isinstance(wc,str): return "unknown"
        w=wc.lower()
        if w.startswith("0x01") and len(w)==66:
            return "eth1:"+"0x"+w[-40:]
        elif w.startswith("0x00"):
            return "bls:"+w
        return "unknown"

    pk2owner={}
    with open(validators_jsonl) as f:
        for line in f:
            if not line.strip(): continue
            row=json.loads(line)
            v=row.get("validator") or {}
            pk=v.get("pubkey") or v.get("public_key")
            wc=v.get("withdrawal_credentials")
            if pk:
                pk2owner[pk.lower()]=owner_from_wc(wc)
    return pk2owner

def iter_mev_delivered(json_path):
    # Accept list or object roots
    data=json.load(open(json_path))
    if isinstance(data, dict):
        # some relays return {"data":[...]} or {"result":[...]}
        for key in ("data","result","results","payload","items"):
            if key in data and isinstance(data[key], list):
                data = data[key]; break
        if isinstance(data, dict):
            data=[data]
    if not isinstance(data, list):
        return
    for rec in data:
        if not isinstance(rec, dict): continue
        pk=None
        for k in PROP_KEYS:
            if k in rec:
                pk = rec[k]; break
        if not pk:
            # sometimes nested under "header" or "message"
            hdr = rec.get("header") or rec.get("message") or {}
            for k in PROP_KEYS:
                if k in hdr:
                    pk = hdr[k]; break
        if pk:
            yield pk.lower(), rec

def main():
    if len(sys.argv)<3:
        print("Usage: python -m src.data.mev_merge_owner <validators_jsonl> <mev_glob_pattern>")
        print("Example: python -m src.data.mev_merge_owner data/raw/ethereum/validators_2025-10-21.jsonl 'data/raw/ethereum/mev/*_2025-10-21.json'")
        sys.exit(2)

    validators_jsonl = sys.argv[1]
    pattern = sys.argv[2]
    pk2owner = load_validator_owner_map(validators_jsonl)

    by_owner = defaultdict(lambda: {"delivered_count":0, "records":0})
    total=0

    files = sorted(glob.glob(pattern))
    for fp in files:
        for pk,rec in iter_mev_delivered(fp):
            total+=1
            owner = pk2owner.get(pk, "unknown")
            by_owner[owner]["delivered_count"] += 1
            by_owner[owner]["records"] += 1

    # Compute shares
    rows=[]
    for owner, s in by_owner.items():
        share = (s["delivered_count"]/total) if total>0 else 0.0
        rows.append({"owner":owner, "delivered":s["delivered_count"], "share":share})

    rows.sort(key=lambda r: r["share"], reverse=True)

    out_dir="data/processed/ethereum"
    os.makedirs(out_dir, exist_ok=True)
    date=datetime.date.today().isoformat()
    out_csv=f"{out_dir}/mev_owner_deliveries_{date}.csv"
    with open(out_csv,"w") as f:
        f.write("owner,delivered,share\n")
        for r in rows:
            f.write(f'{r["owner"]},{r["delivered"]},{r["share"]:.12f}\n')

    print(f"\n=== MEV proposer-payload deliveries by owner ({date}) ===")
    print(f"Files parsed: {len(files)}; total records: {total}")
    print("Top 10 owners by delivered share:")
    for i,r in enumerate(rows[:10],1):
        print(f"{i:2d}. {r['owner']:<46} delivered={r['delivered']:7d}  share={100*r['share']:6.2f}%")
    print(f"\nSaved CSV -> {out_csv}")

if __name__=="__main__":
    main()
