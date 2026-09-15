#!/usr/bin/env python3
"""AMP_GC_FEED_AUDIT_001

Downloads all AMP_GC_HISTORY_EXPORTER_001 GCEZ26 runs from GitHub release tag GC,
audits META/CHUNKS/TICKS, and compares the exact overlapping historical trade stream.
No strategy logic. No AEIF retuning. Data-parity only.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import sys
import urllib.request
import zipfile
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

OWNER = "chepigga"
REPO = "ResearchOS"
TAG = "GC"
API = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{TAG}"
OUTDIR = Path("research/gc/_audit_work")
REPORT_MD = Path("research/gc/AMP_GC_FEED_AUDIT_001.md")
REPORT_JSON = Path("research/gc/AMP_GC_FEED_AUDIT_001.json")
PREFIX = "AMP_GC_HISTORY_EXPORTER_001_GCEZ26_"

RUN_RE = re.compile(
    r"^AMP_GC_HISTORY_EXPORTER_001_GCEZ26_"
    r"(?P<from>\d{8}_\d{6})__(?P<to>\d{8}_\d{6})_"
    r"(?P<kind>META\.csv|CHUNKS\.csv|TICKS\.csv\.zip)$"
)

CANON_FIELDS = [
    "time_msc", "bid", "ask", "last", "volume", "volume_real", "flags",
    "aggressor", "is_buy", "is_sell", "is_last", "is_volume", "is_bid", "is_ask",
]


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "ResearchOS-GC-Audit/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def download(url: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "ResearchOS-GC-Audit/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, dst.open("wb") as f:
        shutil.copyfileobj(r, f, length=1024 * 1024)


def read_meta(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        rows = list(rd)
    if rows and len(rows[0]) >= 2 and rows[0][0].strip().lower() == "key":
        rows = rows[1:]
    for row in rows:
        if len(row) >= 2:
            out[row[0].strip()] = row[1].strip()
    return out


def as_int(v: str | None, default: int = 0) -> int:
    try:
        return int(v or default)
    except Exception:
        return default


def as_float(v: str | None, default: float = 0.0) -> float:
    try:
        return float(v or default)
    except Exception:
        return default


@dataclass
class ChunkAudit:
    rows: int = 0
    failed_chunks: int = 0
    nonzero_copy_errors: int = 0
    request_gaps: int = 0
    request_overlaps: int = 0
    sum_ticks: int = 0
    first_from_msc: int = 0
    last_to_msc: int = 0


def audit_chunks(path: Path) -> ChunkAudit:
    a = ChunkAudit()
    prev_to = None
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for row in rd:
            a.rows += 1
            frm = as_int(row.get("request_from_msc") or row.get("from_msc"))
            to = as_int(row.get("request_to_msc") or row.get("to_msc"))
            ticks = as_int(row.get("ticks"), -1)
            err = as_int(row.get("copy_error"), 0)
            if a.rows == 1:
                a.first_from_msc = frm
            a.last_to_msc = to
            if ticks < 0:
                a.failed_chunks += 1
            else:
                a.sum_ticks += ticks
            if err != 0:
                a.nonzero_copy_errors += 1
            if prev_to is not None:
                if frm > prev_to + 1:
                    a.request_gaps += 1
                elif frm <= prev_to:
                    a.request_overlaps += 1
            prev_to = to
    return a


@dataclass
class TickAudit:
    rows: int = 0
    first_time_msc: int = 0
    last_time_msc: int = 0
    seq_errors: int = 0
    non_monotonic: int = 0
    buy_ticks: int = 0
    sell_ticks: int = 0
    both_ticks: int = 0
    none_ticks: int = 0
    zero_volume_ticks: int = 0
    nonpositive_last: int = 0
    inverted_bbo: int = 0
    exact_adj_duplicates: int = 0
    same_millisecond_adjacent: int = 0
    total_volume: float = 0.0
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    delta_volume: float = 0.0
    min_last: float = 0.0
    max_last: float = 0.0
    flags_top: List[Tuple[str, int]] | None = None
    top_gaps_ms: List[int] | None = None


def tick_reader(zip_path: Path) -> Iterable[dict]:
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise RuntimeError(f"Expected exactly one CSV in {zip_path.name}, found {names}")
        with zf.open(names[0], "r") as raw:
            txt = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            yield from csv.DictReader(txt)


def vol_of(row: dict) -> float:
    vr = as_float(row.get("volume_real"), 0.0)
    if vr > 0:
        return vr
    return float(as_int(row.get("volume"), 0))


def audit_ticks(zip_path: Path) -> TickAudit:
    a = TickAudit(flags_top=[], top_gaps_ms=[])
    flags = Counter()
    top_gaps: List[int] = []
    prev_seq = None
    prev_t = None
    prev_canon = None
    min_last = None
    max_last = None

    for row in tick_reader(zip_path):
        a.rows += 1
        seq = as_int(row.get("seq"))
        t = as_int(row.get("time_msc"))
        last = as_float(row.get("last"))
        bid = as_float(row.get("bid"))
        ask = as_float(row.get("ask"))
        vol = vol_of(row)
        buy = row.get("is_buy", "0") == "1"
        sell = row.get("is_sell", "0") == "1"

        if a.rows == 1:
            a.first_time_msc = t
        a.last_time_msc = t

        if prev_seq is not None and seq != prev_seq + 1:
            a.seq_errors += 1
        if prev_t is not None:
            if t < prev_t:
                a.non_monotonic += 1
            gap = t - prev_t
            if gap == 0:
                a.same_millisecond_adjacent += 1
            if gap > 0:
                top_gaps.append(gap)
                if len(top_gaps) > 50:
                    top_gaps.sort(reverse=True)
                    del top_gaps[25:]

        canon = tuple(row.get(k, "") for k in CANON_FIELDS)
        if prev_canon is not None and canon == prev_canon:
            a.exact_adj_duplicates += 1
        prev_canon = canon

        if buy:
            a.buy_ticks += 1
            a.buy_volume += vol
        if sell:
            a.sell_ticks += 1
            a.sell_volume += vol
        if buy and sell:
            a.both_ticks += 1
        if not buy and not sell:
            a.none_ticks += 1
        if vol <= 0:
            a.zero_volume_ticks += 1
        if last <= 0:
            a.nonpositive_last += 1
        if bid > 0 and ask > 0 and bid > ask:
            a.inverted_bbo += 1

        a.total_volume += vol
        flags[row.get("flags", "")] += 1
        min_last = last if min_last is None else min(min_last, last)
        max_last = last if max_last is None else max(max_last, last)

        prev_seq = seq
        prev_t = t

    a.delta_volume = a.buy_volume - a.sell_volume
    a.min_last = 0.0 if min_last is None else min_last
    a.max_last = 0.0 if max_last is None else max_last
    a.flags_top = flags.most_common(10)
    a.top_gaps_ms = sorted(top_gaps, reverse=True)[:20]
    return a


def overlap_digest(zip_path: Path, lo: int, hi: int) -> Tuple[int, str]:
    h = hashlib.sha256()
    n = 0
    for row in tick_reader(zip_path):
        t = as_int(row.get("time_msc"))
        if t < lo:
            continue
        if t > hi:
            break
        payload = "\x1f".join(row.get(k, "") for k in CANON_FIELDS).encode("utf-8")
        h.update(payload)
        h.update(b"\n")
        n += 1
    return n, h.hexdigest()


def pct(n: int, d: int) -> float:
    return 0.0 if d == 0 else 100.0 * n / d


def run_id_from_match(m: re.Match) -> str:
    return f"{m.group('from')}__{m.group('to')}"


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    release = get_json(API)
    assets = release.get("assets", [])

    runs: Dict[str, Dict[str, dict]] = {}
    for asset in assets:
        name = asset.get("name", "")
        m = RUN_RE.match(name)
        if not m:
            continue
        rid = run_id_from_match(m)
        runs.setdefault(rid, {})[m.group("kind")] = asset

    complete_asset_sets = {
        rid: kinds for rid, kinds in runs.items()
        if {"META.csv", "CHUNKS.csv", "TICKS.csv.zip"}.issubset(kinds)
    }
    if len(complete_asset_sets) < 2:
        raise RuntimeError(f"Need >=2 complete exports, found {list(complete_asset_sets)}")

    results = {}
    for rid, kinds in sorted(complete_asset_sets.items()):
        local = {}
        for kind, asset in kinds.items():
            dst = OUTDIR / asset["name"]
            download(asset["browser_download_url"], dst)
            local[kind] = dst

        meta = read_meta(local["META.csv"])
        chunks = audit_chunks(local["CHUNKS.csv"])
        ticks = audit_ticks(local["TICKS.csv.zip"])

        classified = ticks.buy_ticks + ticks.sell_ticks - ticks.both_ticks
        coverage = pct(classified, ticks.rows)
        expected_meta = as_int(meta.get("total_ticks"), -1)

        base_pass = all([
            meta.get("status") == "COMPLETE",
            ticks.rows > 0,
            ticks.seq_errors == 0,
            ticks.non_monotonic == 0,
            chunks.failed_chunks == 0,
            chunks.nonzero_copy_errors == 0,
            chunks.request_gaps == 0,
            chunks.request_overlaps == 0,
            chunks.sum_ticks == ticks.rows,
            expected_meta == ticks.rows,
            coverage >= 99.0,
        ])

        results[rid] = {
            "meta": meta,
            "chunks": asdict(chunks),
            "ticks": asdict(ticks),
            "aggressor_coverage_pct": coverage,
            "base_pass": base_pass,
            "asset_sha256": {
                kind: asset.get("digest", "") for kind, asset in kinds.items()
            },
            "asset_size": {
                kind: asset.get("size", 0) for kind, asset in kinds.items()
            },
        }

    # Compare the two latest complete runs exactly over their common interval.
    ids = sorted(results)
    rid_a, rid_b = ids[-2], ids[-1]
    a = results[rid_a]
    b = results[rid_b]
    lo = max(a["ticks"]["first_time_msc"], b["ticks"]["first_time_msc"])
    hi = min(a["ticks"]["last_time_msc"], b["ticks"]["last_time_msc"])

    zip_a = OUTDIR / complete_asset_sets[rid_a]["TICKS.csv.zip"]["name"]
    zip_b = OUTDIR / complete_asset_sets[rid_b]["TICKS.csv.zip"]["name"]
    n_a, hash_a = overlap_digest(zip_a, lo, hi)
    n_b, hash_b = overlap_digest(zip_b, lo, hi)
    exact_overlap = (n_a == n_b and hash_a == hash_b and n_a > 0)

    comparison = {
        "run_a": rid_a,
        "run_b": rid_b,
        "overlap_from_msc": lo,
        "overlap_to_msc": hi,
        "overlap_rows_a": n_a,
        "overlap_rows_b": n_b,
        "overlap_sha256_a": hash_a,
        "overlap_sha256_b": hash_b,
        "exact_overlap_match": exact_overlap,
    }

    # Prefer the later run if both are clean and overlap is byte-for-byte canonical-equivalent.
    canonical = rid_b if (a["base_pass"] and b["base_pass"] and exact_overlap) else None
    overall = bool(canonical)

    payload = {
        "lab": "AMP_GC_FEED_AUDIT_001",
        "release": release.get("html_url", ""),
        "runs": results,
        "comparison": comparison,
        "overall_pass": overall,
        "canonical_run": canonical,
    }
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    lines: List[str] = []
    lines.append("# AMP_GC_FEED_AUDIT_001")
    lines.append("")
    lines.append("Scope: **AMP/CQG GCEZ26 historical feed parity only. NO AEIF RETUNING. NO TRADING.**")
    lines.append("")
    lines.append(f"## Verdict: {'PASS' if overall else 'FAIL / INVESTIGATE'}")
    lines.append("")
    lines.append(f"Canonical run: **{canonical or 'NONE'}**")
    lines.append("")
    lines.append("| Run | Version | Chunk h | Status | Tick rows | BUY | SELL | NONE | Aggressor coverage | Chunk failures | Seq errors | Non-monotonic | Base |")
    lines.append("|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for rid in ids:
        r = results[rid]
        m = r["meta"]
        t = r["ticks"]
        c = r["chunks"]
        lines.append(
            f"| `{rid}` | {m.get('version','?')} | {m.get('chunk_hours','?')} | {m.get('status','?')} | "
            f"{t['rows']:,} | {t['buy_ticks']:,} | {t['sell_ticks']:,} | {t['none_ticks']:,} | "
            f"{r['aggressor_coverage_pct']:.4f}% | {c['failed_chunks']} | {t['seq_errors']} | "
            f"{t['non_monotonic']} | {'PASS' if r['base_pass'] else 'FAIL'} |"
        )

    lines.append("")
    lines.append("## Reproducibility on exact overlap")
    lines.append("")
    lines.append(f"- Overlap: `{lo}` → `{hi}`")
    lines.append(f"- Rows A/B: **{n_a:,} / {n_b:,}**")
    lines.append(f"- SHA256 A: `{hash_a}`")
    lines.append(f"- SHA256 B: `{hash_b}`")
    lines.append(f"- Exact canonical tick-stream match: **{'YES' if exact_overlap else 'NO'}**")

    lines.append("")
    lines.append("## Per-run diagnostics")
    for rid in ids:
        r = results[rid]
        t = r["ticks"]
        c = r["chunks"]
        m = r["meta"]
        lines.append("")
        lines.append(f"### `{rid}`")
        lines.append(f"- META status/version: `{m.get('status','?')}` / `{m.get('version','?')}`")
        lines.append(f"- Requested: `{m.get('requested_from_text','?')}` → `{m.get('requested_to_text','?')}`")
        lines.append(f"- Exported tick time_msc: `{t['first_time_msc']}` → `{t['last_time_msc']}`")
        lines.append(f"- Rows / CHUNKS sum / META total: **{t['rows']:,} / {c['sum_ticks']:,} / {as_int(m.get('total_ticks'),-1):,}**")
        lines.append(f"- Volume BUY / SELL / delta: **{t['buy_volume']:.0f} / {t['sell_volume']:.0f} / {t['delta_volume']:.0f}**")
        lines.append(f"- Last price min/max: **{t['min_last']} / {t['max_last']}**")
        lines.append(f"- Exact adjacent duplicates preserved: **{t['exact_adj_duplicates']:,}**")
        lines.append(f"- Same-ms adjacent prints: **{t['same_millisecond_adjacent']:,}**")
        lines.append(f"- Zero-volume / nonpositive-last / inverted-BBO: **{t['zero_volume_ticks']} / {t['nonpositive_last']} / {t['inverted_bbo']}**")
        lines.append(f"- Request gaps/overlaps: **{c['request_gaps']} / {c['request_overlaps']}**")
        lines.append(f"- Top time gaps ms (includes scheduled market closures): `{t['top_gaps_ms'][:10]}`")
        lines.append(f"- Top flag values: `{t['flags_top']}`")

    lines.append("")
    lines.append("## Acceptance rule")
    lines.append("")
    lines.append("PASS requires COMPLETE metadata, non-empty data, exact seq ordering, monotonic timestamps, contiguous chunk requests, no failed/error chunks, TICKS=CHUNKS=META row parity, >=99% aggressor classification, and exact SHA256 equality of the normalized tick stream on the common interval between two independent exports.")

    lines.append("")
    lines.append("## Next if PASS")
    lines.append("")
    lines.append("Freeze canonical AMP dataset as `AMP_GC_OOS_001`, aggregate M5 footprint from raw prints, apply the already-frozen AEIF logic unchanged, then test GC→FTMO XAU transfer with frozen SL1 / TP3 / max hold 240m / single-position.")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT_MD.read_text(encoding="utf-8"))
    return 0 if overall else 2


if __name__ == "__main__":
    sys.exit(main())
