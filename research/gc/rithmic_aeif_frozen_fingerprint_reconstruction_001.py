#!/usr/bin/env python3
"""RITHMIC_AEIF_FROZEN_FINGERPRINT_RECONSTRUCTION_001

Fingerprint certification harness for the historical positive Rithmic AEIF lineage.

IMPORTANT:
- This script NEVER reads AMP_GC_OOS_001.
- It does not discover or optimize AEIF parameters.
- It certifies a reconstructed historical event/trade ledger against already-known
  historical fingerprints.

Expected input CSV columns for core/cooldown ledgers:
    time, side, r
Optional:
    signal_time, entry_time, exit_time, event_id

The harness can also compare exact event identity when a reference ledger exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


FINGERPRINTS = {
    "core": {
        "n": 105,
        "ev_r": 0.297,
        "sum_r": None,
        "max_dd_r": None,
    },
    "cooldown30": {
        "n": 92,
        "ev_r": 0.244,
        "sum_r": 22.45,
        "max_dd_r": 5.0,
    },
    "xau_baseline": {
        "n": 51,
        "ev_r": 0.250,
        "sum_r": 12.75,
        "max_dd_r": 3.24,
    },
    "xau_tp3_h240": {
        "n": 51,
        "ev_r": 0.563,
        "sum_r": 28.69,
        "max_dd_r": 3.42,
        "pf": 2.15,
    },
    "xau_tp3_h240_single_position": {
        "n": 46,
        "ev_r": 0.666,
        "sum_r": 30.63,
        "max_dd_r": 3.32,
        "pf": 2.33,
        "max_loss_streak": 4,
    },
}

COUNT_TOL = 1
EV_TOL = 0.01
SUM_TOL = 0.25
DD_TOL = 0.25
PF_TOL = 0.10


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def max_drawdown(r: pd.Series) -> float:
    eq = r.cumsum()
    peak = eq.cummax()
    dd = peak - eq
    return float(dd.max()) if len(dd) else 0.0


def profit_factor(r: pd.Series) -> float:
    gp = float(r[r > 0].sum())
    gl = float(-r[r < 0].sum())
    if gl == 0:
        return math.inf if gp > 0 else 0.0
    return gp / gl


def max_loss_streak(r: pd.Series) -> int:
    cur = best = 0
    for x in r:
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def load_ledger(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"side", "r"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    if "time" not in df.columns and "signal_time" not in df.columns:
        raise ValueError(f"{path}: need time or signal_time for chronological audit")
    tcol = "time" if "time" in df.columns else "signal_time"
    df[tcol] = pd.to_datetime(df[tcol], utc=True, errors="raise")
    df = df.sort_values(tcol, kind="mergesort").reset_index(drop=True)
    df["side"] = df["side"].astype(str).str.upper()
    if not df["side"].isin(["LONG", "SHORT", "BUY", "SELL"]).all():
        bad = df.loc[~df["side"].isin(["LONG", "SHORT", "BUY", "SELL"]), "side"].unique()
        raise ValueError(f"invalid side values: {bad}")
    df["r"] = pd.to_numeric(df["r"], errors="raise")
    return df


def metrics(df: pd.DataFrame) -> dict:
    r = df["r"].astype(float)
    return {
        "n": int(len(df)),
        "ev_r": float(r.mean()) if len(r) else math.nan,
        "sum_r": float(r.sum()),
        "max_dd_r": max_drawdown(r),
        "pf": profit_factor(r),
        "max_loss_streak": max_loss_streak(r),
    }


def check_metric(name: str, observed, target, tol) -> dict:
    if target is None:
        return {"metric": name, "observed": observed, "target": None, "pass": None}
    diff = abs(float(observed) - float(target))
    return {
        "metric": name,
        "observed": observed,
        "target": target,
        "abs_diff": diff,
        "tolerance": tol,
        "pass": bool(diff <= tol),
    }


def certify(stage: str, df: pd.DataFrame) -> dict:
    if stage not in FINGERPRINTS:
        raise KeyError(stage)
    obs = metrics(df)
    tgt = FINGERPRINTS[stage]
    checks = [
        check_metric("n", obs["n"], tgt.get("n"), COUNT_TOL),
        check_metric("ev_r", obs["ev_r"], tgt.get("ev_r"), EV_TOL),
        check_metric("sum_r", obs["sum_r"], tgt.get("sum_r"), SUM_TOL),
        check_metric("max_dd_r", obs["max_dd_r"], tgt.get("max_dd_r"), DD_TOL),
        check_metric("pf", obs["pf"], tgt.get("pf"), PF_TOL),
        check_metric("max_loss_streak", obs["max_loss_streak"], tgt.get("max_loss_streak"), 0),
    ]
    active = [c for c in checks if c["pass"] is not None]
    return {
        "stage": stage,
        "observed": obs,
        "target": tgt,
        "checks": checks,
        "fingerprint_pass": all(c["pass"] for c in active),
    }


def identity_key(df: pd.DataFrame) -> pd.Series:
    time_col = "signal_time" if "signal_time" in df.columns else "time"
    t = pd.to_datetime(df[time_col], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    side = df["side"].replace({"BUY": "LONG", "SELL": "SHORT"})
    return t + "|" + side


def compare_identity(candidate: pd.DataFrame, reference: pd.DataFrame) -> dict:
    a = identity_key(candidate).tolist()
    b = identity_key(reference).tolist()
    aset, bset = set(a), set(b)
    return {
        "candidate_n": len(a),
        "reference_n": len(b),
        "exact_ordered_match": a == b,
        "candidate_only": sorted(aset - bset)[:100],
        "reference_only": sorted(bset - aset)[:100],
        "set_match": aset == bset,
    }


def assert_no_amp_path(paths: list[Path]) -> None:
    forbidden = ("AMP_GC_OOS_001", "AMP_GC_OOS", "AMP_GC_M5_FOOTPRINT")
    for p in paths:
        text = str(p).upper()
        if any(x.upper() in text for x in forbidden):
            raise RuntimeError(f"AMP OOS input is forbidden in reconstruction: {p}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(FINGERPRINTS))
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--reference", type=Path, default=None,
                    help="Optional original historical event ledger for exact identity parity")
    ap.add_argument("--out", type=Path,
                    default=Path("research/gc/RITHMIC_AEIF_FINGERPRINT_RESULT.json"))
    args = ap.parse_args()

    inputs = [args.candidate] + ([args.reference] if args.reference else [])
    assert_no_amp_path(inputs)

    candidate = load_ledger(args.candidate)
    result = certify(args.stage, candidate)
    result["candidate_file"] = str(args.candidate)
    result["candidate_sha256"] = sha256_file(args.candidate)
    result["amp_oos_read"] = False

    if args.reference:
        reference = load_ledger(args.reference)
        result["reference_file"] = str(args.reference)
        result["reference_sha256"] = sha256_file(args.reference)
        result["identity"] = compare_identity(candidate, reference)
        result["certified"] = bool(
            result["fingerprint_pass"] and result["identity"]["exact_ordered_match"]
        )
    else:
        result["identity"] = None
        result["certified"] = False
        result["certification_note"] = (
            "Fingerprint metrics may pass, but exact certification remains false without "
            "an original historical reference ledger/code/config."
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("fingerprint_pass") else 2


if __name__ == "__main__":
    raise SystemExit(main())
