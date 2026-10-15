#!/usr/bin/env python3
"""LIQCAP_LAB_001 — data acquisition only (no statistics, no signals).

Runs on a GitHub Actions runner (data.binance.vision is reachable there).
Downloads Binance USDT-M BTCUSDT public archives and writes compact files
for the oracle:

  liq_raw_btcusdt.csv.gz      every liquidationSnapshot row (deduplicated)
  liq_5m_btcusdt.csv.gz       5-minute UTC buckets of liquidation notional
  metrics_5m_btcusdt.csv.gz   daily "metrics" archive (OI, L/S ratios, taker ratio)
  klines_5m_btcusdt.csv.gz    5m klines (UM perpetual)
  manifest.json               coverage, row counts, missing days, sha256

Nothing here looks at outcomes. Output is consumed by the preregistered
oracle (SPEC.md) only after the spec is frozen.
"""
import concurrent.futures as cf
import csv
import gzip
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

SYM = os.environ.get("LIQCAP_SYMBOL", "BTCUSDT")
OUT = os.environ.get("LIQCAP_OUT", "liqcap_data")
LIST_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
FILE_URL = "https://data.binance.vision/"
PREFIXES = {
    "liq": f"data/futures/um/daily/liquidationSnapshot/{SYM}/",
    "metrics": f"data/futures/um/daily/metrics/{SYM}/",
    "klines": f"data/futures/um/monthly/klines/{SYM}/5m/",
}
BUCKET_MS = 300_000


def http_get(url, tries=4):
    last = None
    for a in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception as e:  # network hiccup -> retry with backoff
            last = e
            time.sleep(1.5 * (a + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url}: {last}")


def list_keys(prefix):
    keys, marker = [], ""
    ns = "{http://s3.amazonaws.com/doc/2006-03-01/}"
    while True:
        url = f"{LIST_URL}?delimiter=/&prefix={prefix}"
        if marker:
            url += f"&marker={urllib.request.quote(marker)}"
        root = ET.fromstring(http_get(url))
        page = [c.find(f"{ns}Key").text for c in root.findall(f"{ns}Contents")]
        keys += page
        truncated = (root.findtext(f"{ns}IsTruncated") or "false").lower() == "true"
        if not truncated or not page:
            break
        marker = page[-1]
    return sorted(k for k in keys if k.endswith(".zip"))


def read_zip_csv(key):
    data = http_get(FILE_URL + key)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        name = z.namelist()[0]
        text = z.read(name).decode("utf-8", "replace")
    rows = list(csv.reader(io.StringIO(text)))
    return [r for r in rows if r]


def is_header(row):
    return any(re.search("[a-zA-Z_]", c or "") for c in row[:2]) and not re.match(r"^\d", row[0] or "")


def fetch_all(keys, workers=16):
    out = {}
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(read_zip_csv, k): k for k in keys}
        for i, f in enumerate(cf.as_completed(futs), 1):
            out[futs[f]] = f.result()
            if i % 200 == 0:
                print(f"  {i}/{len(keys)}", flush=True)
    return out


def day_of(key):
    m = re.search(r"(\d{4}-\d{2}-\d{2})\.zip$", key)
    return m.group(1) if m else None


def to_ms(v):
    v = float(v)
    if v > 1e15:      # microseconds
        return int(v // 1000)
    if v < 1e11:      # seconds
        return int(v * 1000)
    return int(v)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write_gz(path, header, rows):
    with gzip.open(path, "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = {"symbol": SYM, "generated_utc": datetime.now(timezone.utc).isoformat(), "datasets": {}}

    # ---------------- liquidations ----------------
    print("listing liquidationSnapshot ...", flush=True)
    lkeys = list_keys(PREFIXES["liq"])
    print(f"  {len(lkeys)} daily files", flush=True)
    if not lkeys:
        sys.exit("no liquidationSnapshot files found")
    ldata = fetch_all(lkeys)
    header, seen, raw, total_rows = None, set(), [], 0
    for k in sorted(ldata):
        rows = ldata[k]
        if rows and is_header(rows[0]):
            header = header or [c.strip() for c in rows[0]]
            rows = rows[1:]
        total_rows += len(rows)
        for r in rows:
            t = tuple(r)
            if t in seen:           # archive rows are known to be duplicated
                continue
            seen.add(t)
            raw.append(r)
    if header is None:
        header = ["time", "side", "order_type", "time_in_force", "original_quantity", "price",
                  "average_price", "order_status", "last_fill_quantity", "accumulated_fill_quantity"]
    idx = {c: i for i, c in enumerate(header)}
    need = ["time", "side"]
    for c in need:
        if c not in idx:
            sys.exit(f"liquidation header missing '{c}': {header}")

    def fnum(r, c):
        i = idx.get(c)
        try:
            return float(r[i]) if i is not None and r[i] != "" else 0.0
        except ValueError:
            return 0.0

    buckets = defaultdict(lambda: [0.0, 0.0, 0, 0, 0.0, 0.0])  # longUSD shortUSD longN shortN maxLong maxShort
    raw_out = []
    for r in raw:
        ts = to_ms(r[idx["time"]])
        qty = fnum(r, "accumulated_fill_quantity") or fnum(r, "original_quantity")
        px = fnum(r, "average_price") or fnum(r, "price")
        usd = qty * px
        side = r[idx["side"]].strip().upper()
        b = buckets[(ts // BUCKET_MS) * BUCKET_MS]
        if side == "SELL":          # forced SELL = a LONG was liquidated
            b[0] += usd; b[2] += 1; b[4] = max(b[4], usd)
        elif side == "BUY":         # forced BUY = a SHORT was liquidated
            b[1] += usd; b[3] += 1; b[5] = max(b[5], usd)
        raw_out.append([ts, side, qty, px, round(usd, 2)])
    raw_out.sort(key=lambda x: x[0])
    p = os.path.join(OUT, "liq_raw_btcusdt.csv.gz")
    write_gz(p, ["ts_ms", "side", "qty", "price", "usd"], raw_out)
    p5 = os.path.join(OUT, "liq_5m_btcusdt.csv.gz")
    write_gz(p5, ["bucket_ms", "long_liq_usd", "short_liq_usd", "long_liq_n", "short_liq_n",
                  "max_long_usd", "max_short_usd"],
             [[k, round(v[0], 2), round(v[1], 2), v[2], v[3], round(v[4], 2), round(v[5], 2)]
              for k, v in sorted(buckets.items())])
    ldays = sorted(d for d in (day_of(k) for k in lkeys) if d)
    manifest["datasets"]["liquidations"] = {
        "files": len(lkeys), "first_day": ldays[0], "last_day": ldays[-1],
        "raw_rows": len(raw_out), "duplicate_rows_removed": total_rows - len(raw),
        "source_header": header,
        "sha256": {os.path.basename(p): sha256(p), os.path.basename(p5): sha256(p5)},
    }
    del ldata, raw, seen

    # ---------------- metrics (5m) ----------------
    print("listing metrics ...", flush=True)
    mkeys = list_keys(PREFIXES["metrics"])
    print(f"  {len(mkeys)} daily files", flush=True)
    mdata = fetch_all(mkeys)
    mheader, mrows = None, {}
    for k in sorted(mdata):
        rows = mdata[k]
        if rows and is_header(rows[0]):
            mheader = mheader or [c.strip() for c in rows[0]]
            rows = rows[1:]
        for r in rows:
            mrows[r[0]] = r          # create_time is the first column; dedupe on it
    pm = os.path.join(OUT, "metrics_5m_btcusdt.csv.gz")
    write_gz(pm, mheader or [], [mrows[k] for k in sorted(mrows)])
    mdays = sorted(d for d in (day_of(k) for k in mkeys) if d)
    manifest["datasets"]["metrics"] = {
        "files": len(mkeys), "first_day": mdays[0] if mdays else None,
        "last_day": mdays[-1] if mdays else None, "rows": len(mrows),
        "source_header": mheader, "sha256": {os.path.basename(pm): sha256(pm)},
    }
    del mdata

    # ---------------- klines 5m (monthly) ----------------
    print("listing klines ...", flush=True)
    kkeys = list_keys(PREFIXES["klines"])
    print(f"  {len(kkeys)} monthly files", flush=True)
    kdata = fetch_all(kkeys, workers=8)
    krows = {}
    for k in sorted(kdata):
        rows = kdata[k]
        if rows and is_header(rows[0]):
            rows = rows[1:]
        for r in rows:
            krows[to_ms(r[0])] = [to_ms(r[0])] + r[1:6]
    pk = os.path.join(OUT, "klines_5m_btcusdt.csv.gz")
    write_gz(pk, ["open_ms", "open", "high", "low", "close", "volume"], [krows[k] for k in sorted(krows)])
    manifest["datasets"]["klines_5m"] = {
        "files": len(kkeys), "rows": len(krows),
        "first_ms": min(krows) if krows else None, "last_ms": max(krows) if krows else None,
        "sha256": {os.path.basename(pk): sha256(pk)},
    }

    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
