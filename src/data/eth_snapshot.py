import os, requests, json, datetime, time

CANDIDATE_PATHS = [
    "/eth/v1/beacon/states/head/validators",
    "/api/v1/beacon/states/head/validators",
]

def fetch_validators(base):
    base = base.rstrip("/")
    last_err = None
    for path in CANDIDATE_PATHS:
        url = f"{base}{path}"
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent":"staking-game/0.1"})
            r.raise_for_status()
            j = r.json()
            return j["data"] if isinstance(j, dict) and "data" in j else j
        except Exception as e:
            last_err = e
            time.sleep(0.3)
    raise SystemExit(f"All validator paths failed against {base}: {last_err}")

def save_jsonl(rows, outpath):
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "w") as f:
        for d in rows:
            d["snapshot_ts"] = ts
            f.write(json.dumps(d) + "\n")
    print(f"Saved {len(rows)} validators -> {outpath}")

if __name__ == "__main__":
    endpoint = os.environ.get("ETH_NODE", "https://lodestar-mainnet.chainsafe.io")
    out = f"data/raw/ethereum/validators_{datetime.date.today()}.jsonl"
    rows = fetch_validators(endpoint)
    save_jsonl(rows, out)
