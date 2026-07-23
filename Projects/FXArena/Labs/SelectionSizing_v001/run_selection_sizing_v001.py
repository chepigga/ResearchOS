#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import pickle
import shutil
import sys
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
RELEASE = ROOT / "_release_assets"
WORK = ROOT / "_selection_sizing_work"
OUT = ROOT / "FXArena_SelectionSizing_v001_output"
WORK.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE))
from paired_moving_block_sampler import max_drawdown, paired_bootstrap

SEED_SA4 = 2026072304
SEED_SA5 = 2026072305
SEED_SB5_BASE = 2026072310
N_BOOT = 5000
BLOCK_SIZE = 20
N_PERM = 200
TOTAL_GATE = 1848.87 * 1.03
DD_GATE = 14.916


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_once(src: Path, dst: Path) -> None:
    marker = dst / ".complete"
    if marker.exists():
        return
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    with zipfile.ZipFile(src) as zf:
        zf.extractall(dst)
    marker.write_text("ok")


def parse_schedule_entry(entry):
    if isinstance(entry, dict):
        month = entry.get("month") or entry.get("test_month")
        coef = entry.get("coef") or entry.get("coefs") or entry.get("weights")
        intercept = entry.get("intercept")
        mean = entry.get("mean")
        scale = entry.get("scale") or entry.get("std")
        return str(month), np.asarray(coef, float), float(intercept), np.asarray(mean, float), np.asarray(scale, float)
    if isinstance(entry, (list, tuple)) and len(entry) >= 5:
        month, coef, intercept, mean, scale = entry[:5]
        return str(month), np.asarray(coef, float), float(intercept), np.asarray(mean, float), np.asarray(scale, float)
    raise TypeError(f"Unsupported schedule entry: {type(entry)!r} {entry!r}")


def compute_frozen_predictions(meta: pd.DataFrame, x48: np.ndarray, schedule_obj: dict) -> np.ndarray:
    months = pd.to_datetime(meta.decision_3bar_time_unix, unit="s", utc=True).to_period("M").astype(str).to_numpy()
    pred = np.full(len(meta), np.nan, dtype=np.float64)
    for raw in schedule_obj["schedule"]:
        month, coef, intercept, mean, scale = parse_schedule_entry(raw)
        idx = np.flatnonzero(months == month)
        if idx.size == 0:
            continue
        scale = np.where(np.abs(scale) > 1e-12, scale, 1.0)
        pred[idx] = expit(intercept + ((np.asarray(x48[idx], float) - mean) / scale) @ coef)
    return pred


def metrics(trades: pd.DataFrame, net_col: str = "net", gross_col: str = "gross") -> dict:
    if trades.empty:
        return {"N": 0, "total_R": 0.0, "EV": np.nan, "gross_MaxDD_R": 0.0,
                "net_MaxDD_R": 0.0, "negative_months": 0, "months": 0,
                "worst_month_R": np.nan, "all_years_positive": False, "yearly": {}}
    t = trades.sort_values(["entry_t", "episode_id"], kind="mergesort").copy()
    t["month"] = pd.to_datetime(t.entry_t, unit="s", utc=True).dt.to_period("M")
    t["year"] = pd.to_datetime(t.entry_t, unit="s", utc=True).dt.year
    t["day"] = pd.to_datetime(t.entry_t, unit="s", utc=True).dt.floor("D")
    monthly = t.groupby("month")[net_col].sum()
    yearly = t.groupby("year")[net_col].agg(["sum", "mean", "size"])
    daily_n = t.groupby("day").size()
    pos = t.loc[t[net_col] > 0, net_col].sum()
    neg = -t.loc[t[net_col] < 0, net_col].sum()
    return {"N": int(len(t)), "total_R": float(t[net_col].sum()), "EV": float(t[net_col].mean()),
            "WR": float((t[net_col] > 0).mean()), "PF": float(pos / neg) if neg > 0 else float("inf"),
            "gross_MaxDD_R": max_drawdown(t[gross_col].to_numpy()),
            "net_MaxDD_R": max_drawdown(t[net_col].to_numpy()),
            "negative_months": int((monthly < 0).sum()), "months": int(len(monthly)),
            "worst_month_R": float(monthly.min()), "all_years_positive": bool((yearly["sum"] > 0).all()),
            "yearly": {str(y): {"total_R": float(r["sum"]), "EV": float(r["mean"]), "N": int(r["size"])} for y, r in yearly.iterrows()},
            "trades_per_day_mean": float(daily_n.mean()), "trades_per_day_p95": float(daily_n.quantile(.95)),
            "max_trades_day": int(daily_n.max())}


def risk_layer(meta, selected_mask, gross, net, exit_t, hold):
    idx = np.flatnonzero(selected_mask & np.isfinite(net) & np.isfinite(gross))
    order = np.lexsort((meta.episode_id.to_numpy()[idx], meta.entry_t.to_numpy()[idx]))
    idx = idx[order]
    open_ids, accepted = [], []
    day_count = {}
    consecutive_losses = 0
    block_until = 0
    rejected_day = rejected_cooldown = 0
    for i in idx:
        t = int(meta.entry_t.iloc[i]); still = []
        for q in open_ids:
            if int(exit_t[q]) <= t:
                if float(gross[q]) < 0:
                    consecutive_losses += 1
                    if consecutive_losses >= 2: block_until = int(exit_t[q]) + 12 * 3600
                else: consecutive_losses = 0
            else: still.append(q)
        open_ids = still; day = t // 86400
        if day_count.get(day, 0) >= 6:
            rejected_day += 1; continue
        if t < block_until:
            rejected_cooldown += 1; continue
        accepted.append(i); open_ids.append(i); day_count[day] = day_count.get(day, 0) + 1
    a = np.asarray(accepted, dtype=np.int64)
    out = meta.iloc[a][["episode_id", "level_id", "decision_3bar_time_unix", "entry_t"]].copy()
    out["p"] = meta.iloc[a]["p"].to_numpy(); out["gross"] = gross[a]; out["net"] = net[a]
    out["exit_t"] = exit_t[a]; out["hold"] = hold[a]
    audit = {"raw_selected": int(len(idx)), "accepted": int(len(a)),
             "rejected_day_cap": int(rejected_day), "rejected_cooldown": int(rejected_cooldown),
             "day_cap_reject_share_raw": float(rejected_day / len(idx)) if len(idx) else 0.0,
             "cooldown_reject_share_raw": float(rejected_cooldown / len(idx)) if len(idx) else 0.0}
    return out.reset_index(drop=True), audit


def monthly_top_mask(meta, q):
    mask = np.zeros(len(meta), dtype=bool)
    month = pd.to_datetime(meta.decision_3bar_time_unix, unit="s", utc=True).dt.to_period("M")
    for _, idx in meta[np.isfinite(meta.p)].groupby(month, sort=True).groups.items():
        ii = np.asarray(list(idx), dtype=np.int64); k = int(math.ceil((1.0 - q) * len(ii)))
        order = np.lexsort((meta.episode_id.to_numpy()[ii], -meta.p.to_numpy()[ii])); mask[ii[order[:k]]] = True
    return mask


def trailing_thresholds(meta, q, reverse=False):
    z = meta[["episode_id", "decision_3bar_time_unix", "p"]].copy(); z["row"] = np.arange(len(z)); z = z[np.isfinite(z.p)]
    if reverse:
        z = z.sort_values(["decision_3bar_time_unix", "episode_id"], ascending=[False, True], kind="mergesort")
        anchor = int(z.decision_3bar_time_unix.max()); idx = pd.to_datetime(anchor - z.decision_3bar_time_unix.to_numpy(), unit="s", utc=True)
    else:
        z = z.sort_values(["decision_3bar_time_unix", "episode_id"], kind="mergesort")
        idx = pd.to_datetime(z.decision_3bar_time_unix.to_numpy(), unit="s", utc=True)
    series = pd.Series(z.p.to_numpy(), index=idx)
    threshold = series.rolling("90D", closed="left", min_periods=200).quantile(q).to_numpy()
    result = np.full(len(meta), np.nan); result[z.row.to_numpy()] = threshold
    return result


def trailing_mask(meta, q, reverse=False):
    thr = trailing_thresholds(meta, q, reverse=reverse)
    return np.isfinite(thr) & (meta.p.to_numpy() >= thr), thr


def align_paired_events(base, cand, base_net="net", base_gross="gross", cand_net="net", cand_gross="gross"):
    keys = ["entry_t", "episode_id"]
    a = base[keys + [base_net, base_gross]].rename(columns={base_net: "bn", base_gross: "bg"})
    b = cand[keys + [cand_net, cand_gross]].rename(columns={cand_net: "cn", cand_gross: "cg"})
    u = a.merge(b, on=keys, how="outer").fillna({"bn": 0.0, "bg": 0.0, "cn": 0.0, "cg": 0.0})
    u = u.sort_values(keys, kind="mergesort").reset_index(drop=True)
    return u.bn.to_numpy(), u.bg.to_numpy(), u.cn.to_numpy(), u.cg.to_numpy(), u


def calendar_gate(m):
    return bool(m["negative_months"] <= 1 and m["worst_month_R"] >= -3.0 and m["all_years_positive"])


def assign_trailing_terciles(pinned):
    t = pinned.sort_values(["entry_t", "episode_id"], kind="mergesort").copy()
    idx = pd.to_datetime(t.entry_t.to_numpy(), unit="s", utc=True); s = pd.Series(t.p.to_numpy(), index=idx)
    q1 = s.rolling("90D", closed="both", min_periods=1).quantile(1 / 3).to_numpy()
    q2 = s.rolling("90D", closed="both", min_periods=1).quantile(2 / 3).to_numpy()
    tier = np.where(t.p.to_numpy() <= q1, "LOW", np.where(t.p.to_numpy() <= q2, "MID", "HIGH"))
    weight = np.select([tier == "LOW", tier == "MID", tier == "HIGH"], [0.7, 1.0, 1.3]).astype(float)
    t["tier"] = tier; t["weight"] = weight; t["weighted_gross"] = t.gross * weight; t["weighted_net"] = t.net * weight
    return t


def permutation_sizing(tiered):
    rng = np.random.default_rng(SEED_SA4); t = tiered.sort_values(["entry_t", "episode_id"], kind="mergesort").copy()
    months = pd.to_datetime(t.entry_t, unit="s", utc=True).dt.to_period("M").astype(str).to_numpy()
    net, gross, weights = t.net.to_numpy(float), t.gross.to_numpy(float), t.weight.to_numpy(float)
    real_total, base_total = float((net * weights).sum()), float(net.sum()); rows = []
    for iteration in range(N_PERM):
        w = weights.copy()
        for month in np.unique(months):
            ii = np.flatnonzero(months == month); w[ii] = rng.permutation(w[ii])
        rows.append((iteration, float((net * w).sum()), max_drawdown(gross * w)))
    frame = pd.DataFrame(rows, columns=["iteration", "weighted_total_R", "weighted_gross_MaxDD_R"])
    p = float((1 + (frame.weighted_total_R >= real_total).sum()) / (N_PERM + 1))
    summary = {"seed": SEED_SA4, "n_perm": N_PERM, "real_total_R": real_total, "baseline_total_R": base_total,
               "real_advantage_R": real_total - base_total, "null_total_median": float(frame.weighted_total_R.median()),
               "null_total_p95": float(frame.weighted_total_R.quantile(.95)), "null_total_max": float(frame.weighted_total_R.max()),
               "p_empirical": p, "PASS": bool(real_total > frame.weighted_total_R.quantile(.95) and p <= .05)}
    return frame, summary


def reverse_predictions(meta, x48, net, schedule_obj):
    dec = meta.decision_3bar_time_unix.to_numpy(np.int64)
    months = pd.to_datetime(dec, unit="s", utc=True).to_period("M").astype(str).to_numpy(); pred = np.full(len(meta), np.nan)
    for month in [parse_schedule_entry(x)[0] for x in schedule_obj["schedule"]]:
        te = np.flatnonzero(months == month)
        if te.size == 0: continue
        tr = np.flatnonzero(dec >= int((pd.Period(month) + 1).start_time.timestamp()))
        if tr.size < 1000: continue
        scaler = StandardScaler().fit(np.asarray(x48[tr], float)); model = LogisticRegression(C=.5, max_iter=500, solver="lbfgs", tol=1e-4)
        model.fit(scaler.transform(np.asarray(x48[tr], float)), (net[tr] > 0).astype(np.int8))
        pred[te] = model.predict_proba(scaler.transform(np.asarray(x48[te], float)))[:, 1]
    return pred


def write_manifest():
    rows = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.csv":
            rows.append({"file": str(path.relative_to(OUT)), "bytes": path.stat().st_size, "sha256": sha256(path)})
    pd.DataFrame(rows).to_csv(OUT / "MANIFEST_SHA256.csv", index=False)


def main():
    timeout_dir = WORK / "timeout"; extract_once(RELEASE / "FXArena_TimeoutSweep_v009b_FINAL_results.zip", timeout_dir)
    meta = pd.read_pickle(timeout_dir / "meta.pkl").reset_index(drop=True); x48 = np.load(timeout_dir / "X48.npy", mmap_mode="r")
    outcomes = np.load(timeout_dir / "outcomes.npz", mmap_mode="r")
    gross = np.asarray(outcomes["gross"][:, 1, 1, 3], float); net = np.asarray(outcomes["net"][:, 1, 1, 3], float)
    exit_t = np.asarray(outcomes["exit_t"][:, 1, 1, 3], np.int64); hold = np.asarray(outcomes["hold"][:, 1, 1, 3], float)
    with (RELEASE / "weights_schedule_GEOstar_MICRO30_TP2_TO120.pkl").open("rb") as fh: geo_weights = pickle.load(fh)
    pred = compute_frozen_predictions(meta, x48, geo_weights); meta = meta.copy(); meta["p"] = pred
    pinned = pd.read_csv(RELEASE / "trades_GEOstar_MICRO30_TP2_TO120_PINNED.csv.gz").sort_values(["entry_t", "episode_id"], kind="mergesort").reset_index(drop=True)
    idx_by_episode = pd.Series(np.arange(len(meta)), index=meta.episode_id); pi = idx_by_episode.loc[pinned.episode_id].to_numpy()
    p_diff = np.abs(pred[pi] - pinned.p.to_numpy()); gross_diff = np.abs(gross[pi] - pinned.gross.to_numpy()); net_diff = np.abs(net[pi] - pinned.net.to_numpy())
    control = {"N": int(len(pinned)), "total_R": float(pinned.net.sum()), "gross_MaxDD_R": max_drawdown(pinned.gross.to_numpy()),
               "net_MaxDD_R": max_drawdown(pinned.net.to_numpy()), "p_parity_median": float(np.nanmedian(p_diff)),
               "p_parity_max": float(np.nanmax(p_diff)), "gross_outcome_max_absdiff": float(gross_diff.max()), "net_outcome_max_absdiff": float(net_diff.max())}
    control["PASS"] = bool(control["N"] == 3535 and abs(control["gross_MaxDD_R"] - 14.415969148278236) <= .001 and control["p_parity_max"] <= 2e-5 and control["gross_outcome_max_absdiff"] <= 1e-6 and control["net_outcome_max_absdiff"] <= 1e-6)
    (OUT / "control_PINNED.json").write_text(json.dumps(control, indent=2))
    if not control["PASS"]: raise SystemExit(f"CONTROL STOP: {control}")

    tiered = assign_trailing_terciles(pinned); tiered.to_csv(OUT / "trades_A_sizing_tiers.csv.gz", index=False, compression="gzip")
    a_metrics = metrics(tiered, "weighted_net", "weighted_gross")
    tier_diag = tiered.groupby("tier", sort=False).agg(N=("net", "size"), mean_p=("p", "mean"), EV_net=("net", "mean"), weighted_total_R=("weighted_net", "sum"), mean_weight=("weight", "mean")).reindex(["LOW", "MID", "HIGH"]).reset_index()
    tier_diag.to_csv(OUT / "A_tercile_diagnostics.csv", index=False); monotonic = bool(tier_diag.EV_net.is_monotonic_increasing)
    perm_a, sa4 = permutation_sizing(tiered); perm_a.to_csv(OUT / "SA4_permutation200.csv", index=False)
    bn, bg, cn, cg, _ = align_paired_events(pinned, tiered, cand_net="weighted_net", cand_gross="weighted_gross")
    boot_a, sa5 = paired_bootstrap(bn, bg, cn, cg, n_iter=N_BOOT, block_size=BLOCK_SIZE, seed=SEED_SA5); boot_a.to_csv(OUT / "SA5_paired_moving_block_5000.csv", index=False)
    a_gates = {"SA1_total": bool(a_metrics["total_R"] >= TOTAL_GATE), "SA2_gross_DD": bool(a_metrics["gross_MaxDD_R"] <= DD_GATE),
               "SA3_calendar": calendar_gate(a_metrics), "SA4_permutation": bool(sa4["PASS"]), "SA5_paired_bootstrap": bool(sa5["PASS"])}
    a_pass = bool(all(a_gates.values()))
    a_summary = {"implementation_note": "Trailing terciles use selected trades in [t-90d,t], current known p included; no future p.",
                 "realized_mean_weight": float(tiered.weight.mean()), "monotonic_EV_by_tercile": monotonic,
                 "metrics": a_metrics, "gates": a_gates, "PASS": a_pass, "SA4": sa4, "SA5": sa5}
    (OUT / "A_summary.json").write_text(json.dumps(a_summary, indent=2))

    b_rows, b_trades, b_audits = [], {}, {}
    for q in [.97, .96, .95, .94]:
        selected, _ = trailing_mask(meta, q); trades, audit = risk_layer(meta, selected, gross, net, exit_t, hold)
        b_trades[q], b_audits[q] = trades, audit; m = metrics(trades)
        b_rows.append({"q": q, "top_pct": (1-q)*100, **{k:v for k,v in m.items() if k != "yearly"}, **audit})
        trades.to_csv(OUT / f"trades_B_q{q:.2f}.csv.gz", index=False, compression="gzip")
    b_curve = pd.DataFrame(b_rows).sort_values("q", ascending=False); b_curve.to_csv(OUT / "B_threshold_curve.csv", index=False)
    q4 = b_trades[.96]; ids_equal = q4.episode_id.tolist() == pinned.episode_id.tolist()
    b_control = {"required": "trailing q0.96/90d signal-by-signal equals PINNED", "N_trailing_q096": int(len(q4)), "N_PINNED": int(len(pinned)),
                 "ordered_episode_ids_equal": bool(ids_equal), "episode_id_sets_equal": bool(set(q4.episode_id) == set(pinned.episode_id)),
                 "intersection_N": int(len(set(q4.episode_id) & set(pinned.episode_id))), "trailing_total_R": float(q4.net.sum()),
                 "PINNED_total_R": float(pinned.net.sum()), "trailing_gross_MaxDD_R": max_drawdown(q4.gross.to_numpy()), "PINNED_gross_MaxDD_R": max_drawdown(pinned.gross.to_numpy())}
    b_control["PASS"] = bool(ids_equal and abs(b_control["trailing_total_R"] - b_control["PINNED_total_R"]) <= 1e-6 and abs(b_control["trailing_gross_MaxDD_R"] - b_control["PINNED_gross_MaxDD_R"]) <= .001)
    monthly_q4, monthly_audit = risk_layer(meta, monthly_top_mask(meta, .96), gross, net, exit_t, hold)
    b_control["source_monthly_top4"] = {"N": int(len(monthly_q4)), "ordered_episode_ids_equal": bool(monthly_q4.episode_id.tolist() == pinned.episode_id.tolist()),
                                         "total_R": float(monthly_q4.net.sum()), "gross_MaxDD_R": max_drawdown(monthly_q4.gross.to_numpy()), **monthly_audit}
    (OUT / "B_control_q096.json").write_text(json.dumps(b_control, indent=2))

    b_candidate_results = {}; b_winner = None
    if b_control["PASS"]:
        reverse_p = reverse_predictions(meta, x48, net, geo_weights); meta_reverse = meta.copy(); meta_reverse["p"] = reverse_p
        for q in [.97, .95, .94]:
            trades = b_trades[q]; m = metrics(trades); reverse_selected, _ = trailing_mask(meta_reverse, q, reverse=True)
            reverse_trades, reverse_audit = risk_layer(meta_reverse, reverse_selected, gross, net, exit_t, hold)
            fm = pd.to_datetime(trades.entry_t, unit="s", utc=True).dt.to_period("M").astype(str); rm = pd.to_datetime(reverse_trades.entry_t, unit="s", utc=True).dt.to_period("M").astype(str)
            common = sorted(set(fm) & set(rm)); f_total = float(trades[fm.isin(common)].net.sum()); r_total = float(reverse_trades[rm.isin(common)].net.sum())
            degradation = float(1-r_total/f_total) if f_total else float("nan")
            bn,bg,cn,cg,_ = align_paired_events(pinned,trades); seed=SEED_SB5_BASE+int(round(q*100))
            boot,sb5=paired_bootstrap(bn,bg,cn,cg,n_iter=N_BOOT,block_size=BLOCK_SIZE,seed=seed); boot.to_csv(OUT/f"SB5_q{q:.2f}_paired_moving_block_5000.csv",index=False)
            gates={"SB1_total":bool(m["total_R"]>=TOTAL_GATE),"SB2_gross_DD":bool(m["gross_MaxDD_R"]<=DD_GATE),"SB3_calendar":calendar_gate(m),
                   "SB4_reverse_chrono":bool(np.isfinite(degradation) and degradation<=.20),"SB5_paired_bootstrap":bool(sb5["PASS"])}
            b_candidate_results[str(q)]={"metrics":m,"risk_audit":b_audits[q],"reverse_metrics":metrics(reverse_trades),"reverse_common_months":common,
                                          "reverse_degradation":degradation,"gates":gates,"SB5":sb5,"PASS":bool(all(gates.values()))}
        passing=[(float(q),r) for q,r in b_candidate_results.items() if r["PASS"]]
        if passing: b_winner=max(passing,key=lambda x:x[1]["metrics"]["total_R"])[0]
    else:
        b_candidate_results["verdict"]={"status":"STOP_CONTROL_MISMATCH","reason":"Frozen trailing q0.96/90d did not reproduce PINNED; no candidate gates or composition."}
    b_summary={"control":b_control,"curve":b_rows,"candidates":b_candidate_results,"winner_q":b_winner,"PASS":b_winner is not None}
    (OUT/"B_summary.json").write_text(json.dumps(b_summary,indent=2))

    plt.figure(figsize=(8,5)); plt.plot(b_curve.top_pct,b_curve.total_R,marker="o"); plt.axhline(TOTAL_GATE,linestyle="--"); plt.xlabel("Selected top percentile (%)"); plt.ylabel("Net total (R)"); plt.title("Selection threshold curve — total"); plt.grid(True,alpha=.3); plt.tight_layout(); plt.savefig(OUT/"B_total_curve.png",dpi=160); plt.close()
    plt.figure(figsize=(8,5)); plt.plot(b_curve.top_pct,b_curve.gross_MaxDD_R,marker="o"); plt.axhline(DD_GATE,linestyle="--"); plt.xlabel("Selected top percentile (%)"); plt.ylabel("Gross MaxDD (R)"); plt.title("Selection threshold curve — gross DD"); plt.grid(True,alpha=.3); plt.tight_layout(); plt.savefig(OUT/"B_gross_DD_curve.png",dpi=160); plt.close()

    composition={"run":False,"reason":"Both A and B must pass."}
    if a_pass and b_winner is not None:
        comp=assign_trailing_terciles(b_trades[float(b_winner)]); comp.to_csv(OUT/f"trades_COMPOSITION_q{b_winner:.2f}_tiers.csv.gz",index=False,compression="gzip")
        cm=metrics(comp,"weighted_net","weighted_gross"); perm_c,c4=permutation_sizing(comp); perm_c.to_csv(OUT/"COMPOSITION_permutation200.csv",index=False)
        bn,bg,cn,cg,_=align_paired_events(pinned,comp,cand_net="weighted_net",cand_gross="weighted_gross")
        boot_c,c5=paired_bootstrap(bn,bg,cn,cg,n_iter=N_BOOT,block_size=BLOCK_SIZE,seed=2026072399); boot_c.to_csv(OUT/"COMPOSITION_paired_moving_block_5000.csv",index=False)
        gates={"SA1_total":bool(cm["total_R"]>=TOTAL_GATE),"SA2_gross_DD":bool(cm["gross_MaxDD_R"]<=DD_GATE),"SA3_calendar":calendar_gate(cm),"SA4_permutation":bool(c4["PASS"]),"SA5_paired_bootstrap":bool(c5["PASS"])}
        composition={"run":True,"threshold_q":b_winner,"metrics":cm,"gates":gates,"SA4":c4,"SA5":c5,"PASS":bool(all(gates.values()))}
    (OUT/"composition_summary.json").write_text(json.dumps(composition,indent=2))

    if composition.get("PASS"): verdict="COMPOSITION_PASS"
    elif a_pass and b_winner is None: verdict="A_SIZING_TIERS_PASS__B_NO_WINNER" if b_control["PASS"] else "A_VERDICT_VALID__B_STOP_CONTROL_MISMATCH"
    elif b_winner is not None and not a_pass: verdict=f"B_THRESHOLD_Q{b_winner:.2f}_PASS__A_FAIL"
    elif not a_pass and b_winner is None and b_control["PASS"]: verdict="ONE_BIT_SUFFICIENT"
    elif not b_control["PASS"]: verdict="A_VERDICT_VALID__B_STOP_CONTROL_MISMATCH"
    else: verdict="NO_WINNER"
    final={"session":"Selection & Sizing Lab v001","status":"COMPLETED" if b_control["PASS"] else "PARTIAL_STOP_B_CONTROL","verdict":verdict,
           "control":control,"part_A":a_summary,"part_B":b_summary,"composition":composition,
           "sampler":{"law":"paired non-circular moving-block, shared indices, chronological paired-event union","block_size":BLOCK_SIZE,"n_iter":N_BOOT,
                      "seeds":{"SA4":SEED_SA4,"SA5":SEED_SA5,"SB5_base":SEED_SB5_BASE},"absolute_formulation":"REJECTED"},
           "contprimary_touched":False,"exit_policy":"P0 TP2/TO120 unchanged"}
    (OUT/"FINAL_VERDICT.json").write_text(json.dumps(final,indent=2))

    tier_lines="\n".join(f"| {r.tier} | {int(r.N)} | {r.mean_p:.6f} | {r.EV_net:+.6f}R | {r.weighted_total_R:+.2f}R |" for r in tier_diag.itertuples())
    curve_lines="\n".join(f"| {r['top_pct']:.0f}% | {r['N']} | {r['total_R']:+.2f}R | {r['EV']:+.4f}R | {r['gross_MaxDD_R']:.3f}R | {r['negative_months']} | {r['day_cap_reject_share_raw']:.2%} |" for r in b_rows)
    report=f'''# FXArena Selection & Sizing Lab v001

## Verdict

**{verdict}**

P0 exits and ContPrimary were not modified. Gate metric is gross MaxDD. Bootstrap is paired moving-block, block {BLOCK_SIZE}, {N_BOOT} iterations, shared indices; absolute formulation is rejected.

## Control

- N: {control['N']}
- Total net: {control['total_R']:+.6f}R
- Gross MaxDD: {control['gross_MaxDD_R']:.6f}R
- p parity max abs diff: {control['p_parity_max']:.3g}
- **PASS: {control['PASS']}**

## Part A — sizing tiers

- Total weighted: {a_metrics['total_R']:+.2f}R
- EV weighted: {a_metrics['EV']:+.6f}R
- Gross MaxDD weighted: {a_metrics['gross_MaxDD_R']:.3f}R
- Realized mean weight: {tiered.weight.mean():.6f}
- EV monotonic by p tercile: **{monotonic}**

| Tier | N | Mean p | Flat EV | Weighted total |
|---|---:|---:|---:|---:|
{tier_lines}

Gates: `{json.dumps(a_gates)}`

SA4 real advantage {sa4['real_advantage_R']:+.2f}R; null p95 {sa4['null_total_p95']:+.2f}R; p={sa4['p_empirical']:.6f}.

SA5 P(total candidate > baseline)={sa5['p_total_candidate_gt_baseline']:.4%}; P(DD candidate > baseline+0.5)={sa5['p_gross_DD_candidate_gt_baseline_plus_0_5']:.4%}.

**Part A verdict: {'PASS' if a_pass else 'FAIL'}**

## Part B — threshold curve

| Top | N | Total | EV | Gross DD | Negative months | Day-cap rejected/raw |
|---:|---:|---:|---:|---:|---:|---:|
{curve_lines}

### Frozen 4% control

- Trailing q0.96 N: {b_control['N_trailing_q096']}
- PINNED N: {b_control['N_PINNED']}
- Ordered IDs equal: {b_control['ordered_episode_ids_equal']}
- Intersection: {b_control['intersection_N']}
- Trailing total: {b_control['trailing_total_R']:+.2f}R
- PINNED total: {b_control['PINNED_total_R']:+.2f}R
- **Control verdict: {'PASS' if b_control['PASS'] else 'STOP'}**

Source audit: original monthly-top-4% gives N={b_control['source_monthly_top4']['N']}, ordered parity={b_control['source_monthly_top4']['ordered_episode_ids_equal']}.

**Part B verdict: {'PASS, winner q='+str(b_winner) if b_winner is not None else ('STOP — control mismatch' if not b_control['PASS'] else 'NO WINNER')}**

## Composition

```json
{json.dumps(composition,ensure_ascii=False,indent=2)}
```

## Governance

No weights or threshold cells were tuned. If Part B control fails, its curve is diagnostic only and cannot be promoted. Sampler source, seeds, trades, bootstrap CSVs, plots and SHA256 manifest are included.
'''
    (OUT/"FXArena_SelectionSizing_v001_Report.md").write_text(report)
    shutil.copy2(HERE/"paired_moving_block_sampler.py",OUT/"paired_moving_block_sampler.py"); shutil.copy2(HERE/"run_selection_sizing_v001.py",OUT/"run_selection_sizing_v001.py")
    spec=ROOT/"Projects/FXArena/Specs/FXArena_SelectionSizing_TZ_v001_2026-07-23.md"
    if spec.exists(): shutil.copy2(spec,OUT/spec.name)
    write_manifest(); print(json.dumps(final,indent=2))

if __name__ == "__main__": main()
