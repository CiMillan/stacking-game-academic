import os, sys, json, time, datetime, requests
from collections import defaultdict

EPOCHS_BACK = int(os.environ.get("EPOCHS_BACK", "256"))  # ~27h at 12s/slot, 32 slots/epoch
UA = {"User-Agent":"staking-game/0.1"}

def get_head_slot(beacon):
    r = requests.get(f"{beacon}/eth/v1/beacon/headers/head", timeout=20, headers=UA)
    r.raise_for_status()
    j = r.json().get("data", {})
    slot = j.get("slot") or (j.get("header") or {}).get("message", {}).get("slot")
    if slot is None: raise SystemExit("could not get head slot")
    return int(slot)

def get_epoch_from_slot(beacon):
    # 32 slots per epoch on mainnet
    head = get_head_slot(beacon)
    return head // 32

def fetch_inclusion_epoch(beacon, epoch):
    # Lighthouse extension: /lighthouse/validator_inclusion/{epoch}
    url = f"{beacon}/lighthouse/validator_inclusion/{epoch}"
    r = requests.get(url, timeout=20, headers=UA)
    if r.status_code == 404:
        return None  # endpoint not supported by this node
    r.raise_for_status()
    return r.json()  # shape: {"data":[{"validator_index":"123","included":true,...,"inclusion_distance":"..."}]}

def main():
    beacon = os.environ.get("ETH_NODE","https://docs-demo.quiknode.pro").rstrip("/")
    out_jsonl = f"data/processed/ethereum/effectiveness_{datetime.date.today().isoformat()}.jsonl"
    head_epoch = get_epoch_from_slot(beacon)
    start = max(0, head_epoch - EPOCHS_BACK + 1)

    wrote = 0
    unsupported = False
    with open(out_jsonl, "w") as f:
        for epoch in range(start, head_epoch+1):
            data = fetch_inclusion_epoch(beacon, epoch)
            if data is None:
                unsupported = True
                break
            rows = data.get("data") or []
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
            for r in rows:
                r["_epoch"] = epoch
                r["_ts"] = ts
                f.write(json.dumps(r) + "\n")
                wrote += 1
            if epoch % 16 == 0:
                time.sleep(0.15)
    if unsupported:
        os.remove(out_jsonl) if os.path.exists(out_jsonl) else None
        print("This ETH_NODE doesn’t support the Lighthouse inclusion API.")
        print("Set ETH_NODE to a Lighthouse Beacon endpoint and rerun, e.g. your own Lighthouse BN.")
        sys.exit(0)
    print(f"Saved {wrote} inclusion rows → {out_jsonl}")

if __name__=="__main__":
    main()
