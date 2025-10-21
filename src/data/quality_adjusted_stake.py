import csv, sys, json, datetime
from collections import defaultdict

def load_stake_csv(path):
    rows=[]
    with open(path) as f:
        r=csv.DictReader(f)
        for d in r:
            d["share"]=float(d["share"])
            d["effective_balance_gwei"]=float(d["effective_balance_gwei"])
            rows.append(d)
    return rows

def load_mev_csv(path):
    m={}
    with open(path) as f:
        r=csv.DictReader(f)
        for d in r:
            m[d["owner"]]=float(d["share"])
    return m

def hhi(shares):
    return sum(s*s for s in shares)

if __name__=="__main__":
    if len(sys.argv)<4:
        print("Usage: python -m src.data.quality_adjusted_stake <owner_hhi_csv> <mev_owner_csv> <beta>")
        print("Example: python -m src.data.quality_adjusted_stake data/processed/ethereum/owner_hhi_2025-10-21.csv data/processed/ethereum/mev_owner_deliveries_2025-10-21.csv 0.2")
        sys.exit(2)
    stake_csv, mev_csv, beta = sys.argv[1], sys.argv[2], float(sys.argv[3])
    stake=load_stake_csv(stake_csv)
    mev=load_mev_csv(mev_csv)

    # Build dictionary stake by owner (withdrawal-address proxy)
    d={}
    for r in stake:
        d[r["owner"]]=r["share"]

    # Adjust shares: s_adj = s * (1 + beta * mev_share_owner), renormalize
    # This is a toy “quality” bump; feel free to switch the form later.
    adj={}
    for owner,s in d.items():
        q = mev.get(owner, 0.0)
        adj[owner] = s * (1.0 + beta*q)

    Z = sum(adj.values()) or 1.0
    adj_norm = {k:v/Z for k,v in adj.items()}
    hhi_raw = hhi(list(d.values()))
    hhi_adj = hhi(list(adj_norm.values()))

    print(json.dumps({
        "beta": beta,
        "HHI_raw": hhi_raw,
        "HHI_quality_adjusted": hhi_adj
    }, indent=2))
