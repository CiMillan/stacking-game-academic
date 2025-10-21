import os, requests, json, datetime, sys, time

API = "https://api.rated.network/v1/eth/entities/summaries"

def fetch_entities(token, entity_type="nodeOperator", page_size=200, start_offset=0, max_pages=None):
    headers = {"Authorization": f"Bearer {token}"}
    offset = start_offset
    all_rows = []
    pages = 0

    while True:
        params = {"entityType": entity_type, "limit": page_size, "offset": offset}
        attempt = 0
        while True:
            r = requests.get(API, headers=headers, params=params, timeout=60)
            if r.status_code == 401:
                print("rated_pull: 401 Unauthorized — check/rotate RATED_TOKEN.")
                return all_rows
            if r.status_code == 429:
                # Backoff: honor Retry-After if present, else exponential
                retry_after = r.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = int(retry_after)
                    except:
                        wait = 10
                else:
                    wait = min(60, 2 ** min(attempt, 5))
                print(f"rated_pull: 429 Too Many Requests — sleeping {wait}s (offset={offset})")
                time.sleep(wait)
                attempt += 1
                continue
            r.raise_for_status()
            break

        j = r.json()
        results = j.get("results") or []
        # Flatten one level defensively
        flat = []
        for part in results:
            if isinstance(part, list):
                flat.extend(part)
            else:
                flat.append(part)

        all_rows.extend(flat)
        pages += 1

        # Progress logging + checkpoint
        print(f"rated_pull: got {len(flat)} rows @ offset={offset}")
        with open("data/raw/ethereum/.rated_checkpoint.txt", "w") as cp:
            cp.write(json.dumps({"entityType": entity_type, "offset": offset + page_size, "ts": time.time()}))

        # Stop conditions
        nxt = j.get("next")
        if not nxt or len(flat) < page_size:
            break
        offset += page_size
        if max_pages and pages >= max_pages:
            print(f"rated_pull: reached max_pages={max_pages}, stopping early at offset={offset}")
            break

        # Gentle pacing between pages
        time.sleep(0.3)

    return all_rows

def save_jsonl(rows, outpath):
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
    written = 0
    with open(outpath, "w") as f:
        for d in rows:
            if isinstance(d, dict):
                d = dict(d); d["snapshot_ts"] = ts
            else:
                d = {"raw": d, "snapshot_ts": ts}
            f.write(json.dumps(d) + "\n")
            written += 1
    print(f"Saved {written} entities -> {outpath}")

if __name__ == "__main__":
    token = os.environ.get("RATED_TOKEN")
    if not token:
        print("rated_pull: RATED_TOKEN not set — skipping Rated fetch.")
        sys.exit(0)
    entity = os.environ.get("RATED_ENTITY_TYPE", "nodeOperator")
    page_size = int(os.environ.get("RATED_PAGE_SIZE", "200"))
    start_offset = int(os.environ.get("RATED_START_OFFSET", "0"))
    max_pages = int(os.environ.get("RATED_MAX_PAGES", "0")) or None

    out = f"data/raw/ethereum/rated_{entity}_{datetime.date.today()}.jsonl"
    rows = fetch_entities(token, entity_type=entity, page_size=page_size, start_offset=start_offset, max_pages=max_pages)
    if rows:
        save_jsonl(rows, out)
    else:
        print("rated_pull: no data saved.")
    sys.exit(0)
