import csv, sys, math, json
from pathlib import Path

def load(path):
    rows=[]
    with open(path) as f:
        r=csv.DictReader(f)
        for d in r:
            d["share"]=float(d["share"])
            d["effective_balance_gwei"]=float(d["effective_balance_gwei"])
            d["validators"]=int(d["validators"])
            rows.append(d)
    rows.sort(key=lambda x: x["share"], reverse=True)
    return rows

def gini(shares):
    # classic discrete Gini (population weights equal)
    n=len(shares)
    if n==0: return 0.0
    cum=0.0
    for i,s in enumerate(sorted(shares)):
        cum += (i+1)*s
    return (2*cum)/(n*sum(shares)) - (n+1)/n

def main():
    if len(sys.argv)<2:
        print("Usage: python -m src.data.summarize_concentration <rated_operator_hhi_YYYY-MM-DD.csv>")
        sys.exit(2)
    path=sys.argv[1]
    rows=load(path)
    shares=[r["share"] for r in rows]
    hhi=sum(s*s for s in shares)
    neff = 1.0/hhi if hhi>0 else None

    def topk(k): return sum(shares[:k])

    out = {
        "file": str(Path(path).name),
        "operators": len(rows),
        "HHI": hhi,
        "N_eff": neff,
        "Top1": topk(1),
        "Top3": topk(3),
        "Top5": topk(5),
        "Top10": topk(10),
        "Gini": gini(shares),
    }
    print(json.dumps(out, indent=2))
