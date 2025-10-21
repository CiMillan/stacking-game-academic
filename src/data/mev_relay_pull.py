import os, sys, json, time, datetime, requests

CFG = "data/config/mev_endpoints.txt"
SLOTS_BACK = int(os.environ.get("MEV_SLOTS_BACK", "2048"))

def load_endpoints(path=CFG):
    eps=[]
    with open(path) as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith("#"): continue
            parts=line.split()
            if len(parts)<2: continue
            name, url = parts[0], parts[1].rstrip("/")
            eps.append((name,url))
    return eps

def get_head_slot(beacon_base):
    url = f"{beacon_base.rstrip('/')}/eth/v1/beacon/headers/head"
    r = requests.get(url, timeout=20, headers={"User-Agent":"staking-game/0.1"})
    r.raise_for_status()
    j = r.json()
    # try common shapes
    if isinstance(j, dict):
        d = j.get("data") or j
        if isinstance(d, dict):
            # Teku/Lighthouse styles
            slot = d.get("slot") or (d.get("header") or {}).get("message", {}).get("slot")
            if slot is None:
                slot = (d.get("message") or {}).get("slot")
            if slot is not None:
                return int(slot)
    raise SystemExit(f"Could not determine head slot from {url}")

def fetch_slot(url_base, slot, tries=3):
    q = f"{url_base}/relay/v1/data/bidtraces/proposer_payload_delivered?slot={slot}"
    for i in range(tries):
        try:
            r = requests.get(q, timeout=20, headers={"User-Agent":"staking-game/0.1"})
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After","2"))
                time.sleep(min(wait, 10)); continue
            if r.status_code == 404:
                return None  # relay has no record for this slot
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if i == tries-1: raise
            time.sleep(0.5*(i+1))
    return None

if __name__=="__main__":
    beacon = os.environ.get("ETH_NODE", "https://docs-demo.quiknode.pro")
    endpoints = load_endpoints()
    head = get_head_slot(beacon)
    start = max(0, head - SLOTS_BACK + 1)
    date = datetime.date.today().isoformat()
    os.makedirs("data/raw/ethereum/mev", exist_ok=True)

    print(f"Head slot={head}; scraping [{start}, {head}] from {len(endpoints)} relay(s) ...")

    for name, base in endpoints:
        out = f"data/raw/ethereum/mev/{name}_{date}.jsonl"
        written=0
        with open(out,"w") as f:
            for slot in range(start, head+1):
                data = fetch_slot(base, slot)
                if not data: 
                    continue
                # normalize to list
                if isinstance(data, dict):
                    arr = data.get("data") if isinstance(data.get("data"), list) else [data]
                else:
                    arr = data if isinstance(data, list) else [data]
                for rec in arr:
                    rec["_slot"] = slot
                    f.write(json.dumps(rec)+"\n")
                    written += 1
                if slot % 200 == 0:
                    time.sleep(0.2)  # be nice
        print(f"Saved {written} records → {out}")
