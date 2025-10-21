import os, sys, json, csv, datetime
from collections import defaultdict

def owner_from_wc(wc: str):
    if not isinstance(wc,str): return "unknown"
    w=wc.lower()
    if w.startswith("0x01") and len(w)==66:
        return "eth1:"+"0x"+w[-40:]
    elif w.startswith("0x00"):
        return "bls:"+w
    return "unknown"

def load_pk2owner(validators_jsonl):
    pk2owner={}
    with open(validators_jsonl) as f:
        for line in f:
            if not line.strip(): continue
            row=json.loads(line)
            v = row.get("validator") or {}
            pk = v.get("pubkey") or v.get("public_key")
            wc = v.get("withdrawal_credentials")
            if pk:
                pk2owner[pk.lower()] = owner_from_wc(wc)
    return pk2owner

def load_inclusion(jsonl):
    # rows like: {"validator_index":"123","included":true,"inclusion_distance":"3",...,"_epoch":..., "_ts":...}
    by_index = defaultdict(lambda: {"att":0,"inc":0,"sum_delay":0})
    with open(jsonl) as f:
        for line in f:
            if not line.strip(): continue
            r=json.loads(line)
            vi = r.get("validator_index")
            if vi is None: continue
            included = bool(r.get("included"))
            by_index[vi]["att"] += 1
            if included:
                by_index[vi]["inc"] += 1
                try:
                    by_index[vi]["sum_delay"] += int(r.get("inclusion_distance") or 0)
                except:
                    pass
    return by_index

def load_owner_stake(owner_hhi_csv):
    # owner,validators,effective_balance_gwei,share
    d={}
    total=0.0
    with open(owner_hhi_csv) as f:
        r=csv.DictReader(f)
        for row in r:
            s=float(row["share"]); d[row["owner"]]=s; total+=s
    return d

def hhi(shares): return sum(s*s for s in shares)

if __name__=="__main__":
    if len(sys.argv)<4:
        print("Usage: python -m src.data.effectiveness_owner_merge <validators_jsonl> <inclusion_jsonl> <owner_hhi_csv>")
        sys.exit(2)
    validators_jsonl, inclusion_jsonl, owner_hhi_csv = sys.argv[1], sys.argv[2], sys.argv[3]

    # map validator index -> pubkey? inclusion uses index, validator snapshot may not give index->pubkey mapping directly
    # We'll build index->owner via a second pass if your validators JSONL has "index".
    idx2owner={}
    with open(validators_jsonl) as f:
        for line in f:
            if not line.strip(): continue
            row=json.loads(line)
            idx = row.get("index") or row.get("validator_index") or row.get("validator",{}).get("index")
            v = row.get("validator") or {}
            wc = v.get("withdrawal_credentials")
            if idx is not None:
                idx2owner[str(idx)] = owner_from_wc(wc)

    inc = load_inclusion(inclusion_jsonl)
    by_owner = defaultdict(lambda: {"att":0,"inc":0,"sum_delay":0})
    for vidx, stats in inc.items():
        owner = idx2owner.get(str(vidx), "unknown")
        by_owner[owner]["att"] += stats["att"]
        by_owner[owner]["inc"] += stats["inc"]
        by_owner[owner]["sum_delay"] += stats["sum_delay"]

    rows=[]
    for owner, s in by_owner.items():
        att=s["att"] or 1
        part = s["inc"]/att
        avg_delay = (s["sum_delay"]/s["inc"]) if s["inc"]>0 else None
        rows.append({"owner":owner,"attestations":att,"included":s["inc"],"participation":part,"avg_inclusion_distance":avg_delay})

    date = datetime.date.today().isoformat()
    out_dir = "data/processed/ethereum"
    os.makedirs(out_dir, exist_ok=True)
    eff_csv = f"{out_dir}/owner_effectiveness_{date}.csv"
    with open(eff_csv,"w") as f:
        f.write("owner,attestations,included,participation,avg_inclusion_distance\n")
        for r in rows:
            aid = "" if r["avg_inclusion_distance"] is None else f"{r['avg_inclusion_distance']:.3f}"
            f.write(f"{r['owner']},{r['attestations']},{r['included']},{r['participation']:.6f},{aid}\n")

    # quality-adjusted HHI: s_adj = s * (1 + beta*(participation-mean))
    # mean participation over owners with data
    have = [r for r in rows if r["attestations"]>0]
    mu = sum(r["participation"] for r in have)/len(have) if have else 0.0

    owner_stake = load_owner_stake(owner_hhi_csv)
    beta = float(os.environ.get("EFFECT_BETA","0.3"))
    adj = {}
    for r in rows:
        s = owner_stake.get(r["owner"], 0.0)
        adj[r["owner"]] = s * (1.0 + beta*(r["participation"] - mu))
    Z = sum(adj.values()) or 1.0
    adj_norm = {k:v/Z for k,v in adj.items()}
    hhi_raw = hhi(list(owner_stake.values()))
    hhi_adj = hhi(list(adj_norm.values()))

    print(f"Saved owner effectiveness → {eff_csv}")
    print(json.dumps({
        "owners_with_effect": len(rows),
        "participation_mean": mu,
        "HHI_raw": hhi_raw,
        "HHI_effect_adjusted": hhi_adj,
        "beta": beta
    }, indent=2))
