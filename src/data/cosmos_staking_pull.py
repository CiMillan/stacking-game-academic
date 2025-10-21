import os, sys, json, datetime, time
import requests

def fetch_validators(lcd_base, status="BOND_STATUS_BONDED", limit=200):
    """Page through Cosmos SDK staking validators."""
    base = lcd_base.rstrip("/")
    url = f"{base}/cosmos/staking/v1beta1/validators"
    page_key = None
    out = []
    while True:
        params = {"status": status, "pagination.limit": str(limit)}
        if page_key:
            params["pagination.key"] = page_key
        r = requests.get(url, params=params, timeout=30, headers={"User-Agent":"staking-game/0.1"})
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After","2"))
            time.sleep(min(wait, 10)); continue
        r.raise_for_status()
        j = r.json()
        vals = (j.get("validators") or [])
        out.extend(vals)
        page_key = ((j.get("pagination") or {}).get("next_key"))
        if not page_key:
            break
        time.sleep(0.2)  # be nice
    return out

def save_jsonl(items, outpath):
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
    with open(outpath, "w") as f:
        for d in items:
            if isinstance(d, dict):
                d = {**d, "snapshot_ts": ts}
            else:
                d = {"raw": d, "snapshot_ts": ts}
            f.write(json.dumps(d)+"\n")
    print(f"Saved {len(items)} validators -> {outpath}")

if __name__ == "__main__":
    lcd = os.environ.get("COSMOS_LCD")
    chain = os.environ.get("COSMOS_CHAIN", "cosmoshub")
    if not lcd:
        raise SystemExit("Set COSMOS_LCD to a valid LCD base URL, e.g. https://cosmos-api.polkachu.com")
    data = fetch_validators(lcd)
    out = f"data/raw/cosmos/{chain}_validators_{datetime.date.today()}.jsonl"
    save_jsonl(data, out)
