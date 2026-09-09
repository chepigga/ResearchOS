from pathlib import Path
import json
import math
import numpy as np
import pandas as pd

LAB = "BTC_FLOW_EVENT_CLOCK_PHASE_DRIFT_AND_CANONICAL_ANCHOR_RECOVERABILITY_LAB_059"
SRC = Path("labs/BTC_RETAIL_RATIO_REST_QUANTIZATION_ORIGIN_AND_CAUSAL_DECISION_RECOVERABILITY_LAB_058/output/evaluation_decision_recovery.csv")
OUT = Path(f"labs/{LAB}/output")
OUT.mkdir(parents=True, exist_ok=True)
COOLDOWN = pd.Timedelta(hours=12)
PREROLL = pd.Timedelta(hours=24)


def as_bool(s):
    if pd.api.types.is_bool_dtype(s):
        return s.fillna(False)
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def jnum(x):
    if x is None:
        return None
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.floating,)): return None if not np.isfinite(x) else float(x)
    if isinstance(x, pd.Timestamp): return x.isoformat()
    return x


def pctile(arr, p):
    arr = np.asarray(arr, dtype=float)
    arr = arr[np.isfinite(arr)]
    return None if len(arr) == 0 else float(np.quantile(arr, p))


def event_union_metrics(a, b, side=None):
    aa = a.copy(); bb = b.copy()
    if side is not None:
        aa = aa[aa.side == side]
        bb = bb[bb.side == side]
    aset = set(zip(aa.signal_time.astype(str), aa.side.astype(int)))
    bset = set(zip(bb.signal_time.astype(str), bb.side.astype(int)))
    inter = aset & bset; union = aset | bset
    return {
        "archive_n": len(aset), "other_n": len(bset),
        "intersection_n": len(inter), "union_n": len(union),
        "union_match": 1.0 if len(union) == 0 else len(inter) / len(union),
        "archive_only_n": len(aset - bset), "other_only_n": len(bset - aset),
    }


df = pd.read_csv(SRC, parse_dates=["time"])
df = df.sort_values("time").reset_index(drop=True)
for c in ["delta_lo", "delta_hi", "q20", "q80", "side_arc"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["side_arc"] = df["side_arc"].fillna(0).astype(int)
df["transport_fresh"] = as_bool(df["transport_fresh"])
formal_start = df.time.min() + PREROLL

# Build archive clock ground truth and naive LAB058 abstention clock.
archive_last = None
naive_last = None
archive_events = []
naive_events = []
archive_last_after = []
naive_last_after = []

if "recovered_side" in df.columns:
    rec = pd.to_numeric(df["recovered_side"], errors="coerce")
else:
    rec = pd.Series(np.nan, index=df.index)

for i, row in df.iterrows():
    t = row.time
    s = int(row.side_arc)
    if s != 0 and (archive_last is None or t - archive_last >= COOLDOWN):
        archive_last = t
        archive_events.append((t, s))
    archive_last_after.append(archive_last)

    ns = 0 if pd.isna(rec.iloc[i]) else int(rec.iloc[i])
    if ns != 0 and (naive_last is None or t - naive_last >= COOLDOWN):
        naive_last = t
        naive_events.append((t, ns))
    naive_last_after.append(naive_last)

# Set-valued clock.
states = {None}
trace = []
side_contains = []
path_contains = []
possible_side_sets = []

for i, row in df.iterrows():
    t = row.time
    if not bool(row.transport_fresh) or any(pd.isna(row[c]) for c in ["delta_lo", "delta_hi", "q20", "q80"]):
        possible = {-1, 0, 1}
    else:
        dlo, dhi, q20, q80 = float(row.delta_lo), float(row.delta_hi), float(row.q20), float(row.q80)
        possible = set()
        if dhi >= q80: possible.add(-1)
        if dlo <= q20: possible.add(1)
        if dhi > q20 and dlo < q80: possible.add(0)
        if not possible: possible = {-1, 0, 1}

    possible_side_sets.append(tuple(sorted(possible)))
    side_contains.append(int(row.side_arc) in possible)

    transition_outputs = []  # None or emitted side
    next_states = set()
    for last in states:
        for s in possible:
            if s != 0 and (last is None or t - last >= COOLDOWN):
                transition_outputs.append(int(s))
                next_states.add(t)
            else:
                transition_outputs.append(None)
                next_states.add(last)

    out_set = set(transition_outputs)
    if len(out_set) == 1:
        only = next(iter(out_set))
        event_label = "CERTAIN_NO_EVENT" if only is None else "CERTAIN_EVENT"
        certain_side = None if only is None else int(only)
    else:
        event_label = "AMBIGUOUS_EVENT_CLOCK"
        certain_side = None

    states = next_states
    true_last = archive_last_after[i]
    contained = true_last in states
    path_contains.append(contained)

    state_times = sorted([x for x in states if x is not None])
    trace.append({
        "time": t,
        "side_arc": int(row.side_arc),
        "transport_fresh": bool(row.transport_fresh),
        "possible_sides": ",".join(str(x) for x in sorted(possible)),
        "possible_side_count": len(possible),
        "state_count": len(states),
        "state_min_last_event": None if not state_times else state_times[0],
        "state_max_last_event": None if not state_times else state_times[-1],
        "archive_last_event": true_last,
        "archive_path_contained": contained,
        "archive_side_contained": int(row.side_arc) in possible,
        "event_label": event_label,
        "certain_event_side": certain_side,
    })

tr = pd.DataFrame(trace)
tr["time"] = pd.to_datetime(tr.time, utc=True)
for c in ["state_min_last_event", "state_max_last_event", "archive_last_event"]:
    tr[c] = pd.to_datetime(tr[c], utc=True)
tr.to_csv(OUT / "clock_state_trace.csv", index=False)

# Ground-truth event flag per row.
arc_event_map = {pd.Timestamp(t): int(s) for t, s in archive_events}
tr["archive_event_side"] = tr.time.map(arc_event_map)
tr["is_archive_event"] = tr.archive_event_side.notna()
tr["is_certain_event"] = tr.event_label.eq("CERTAIN_EVENT")
tr["certain_event_correct"] = (~tr.is_certain_event) | (tr.certain_event_side == tr.archive_event_side)

formal = tr[tr.time >= formal_start].copy()
formal_rows = len(formal)

# Divergence episodes on state count, starting formally only. Carry-in is reported separately.
episodes = []
in_ep = False
start_t = None
peak_states = 1
prev_count = None
carry_in = False
for _, r in tr.iterrows():
    if r.time < formal_start:
        prev_count = int(r.state_count)
        continue
    count = int(r.state_count)
    if prev_count is None:
        prev_count = count
    if r.time == formal_start and count > 1:
        carry_in = True
    if not in_ep and prev_count == 1 and count > 1:
        in_ep = True; start_t = r.time; peak_states = count
    elif in_ep:
        peak_states = max(peak_states, count)
        if count == 1:
            dur_h = (r.time - start_t).total_seconds() / 3600.0
            episodes.append({"start": start_t, "end": r.time, "duration_hours": dur_h, "recovered": True, "peak_states": peak_states})
            in_ep = False; start_t = None; peak_states = 1
    prev_count = count
if in_ep:
    end_t = tr.time.max()
    dur_h = (end_t - start_t).total_seconds() / 3600.0
    episodes.append({"start": start_t, "end": pd.NaT, "duration_hours_observed": dur_h, "recovered": False, "peak_states": peak_states})
epdf = pd.DataFrame(episodes)
epdf.to_csv(OUT / "divergence_episodes.csv", index=False)

recovered_eps = epdf[epdf.recovered == True] if len(epdf) else pd.DataFrame()
if len(epdf):
    recovered_48 = ((epdf.recovered == True) & (pd.to_numeric(epdf.get("duration_hours"), errors="coerce") <= 48)).sum()
    anchor_recovery_rate_48h = recovered_48 / len(epdf)
else:
    anchor_recovery_rate_48h = 1.0
resync_h = pd.to_numeric(recovered_eps.get("duration_hours", pd.Series(dtype=float)), errors="coerce").dropna().values

# Event precision/recall.
certain_events = formal[formal.is_certain_event].copy()
false_certain = certain_events[certain_events.certain_event_side != certain_events.archive_event_side].copy()
archive_event_rows = formal[formal.is_archive_event].copy()
correct_certain_archive = archive_event_rows[(archive_event_rows.is_certain_event) & (archive_event_rows.certain_event_side == archive_event_rows.archive_event_side)]

certain_event_precision = 1.0 if len(certain_events) == 0 else 1 - len(false_certain) / len(certain_events)
archive_event_certain_recall = 1.0 if len(archive_event_rows) == 0 else len(correct_certain_archive) / len(archive_event_rows)

certain_short = certain_events[certain_events.certain_event_side == -1]
false_certain_short = certain_short[certain_short.archive_event_side != -1]
archive_short_rows = archive_event_rows[archive_event_rows.archive_event_side == -1]
correct_certain_short = archive_short_rows[(archive_short_rows.is_certain_event) & (archive_short_rows.certain_event_side == -1)]
short_precision = 1.0 if len(certain_short) == 0 else 1 - len(false_certain_short) / len(certain_short)
short_recall = 1.0 if len(archive_short_rows) == 0 else len(correct_certain_short) / len(archive_short_rows)

# Save event tables.
archive_ev = pd.DataFrame(archive_events, columns=["signal_time", "side"])
naive_ev = pd.DataFrame(naive_events, columns=["signal_time", "side"])
if len(archive_ev): archive_ev = archive_ev[archive_ev.signal_time >= formal_start]
if len(naive_ev): naive_ev = naive_ev[naive_ev.signal_time >= formal_start]
archive_ev.to_csv(OUT / "archive_events_formal.csv", index=False)
naive_ev.to_csv(OUT / "naive_abstention_events_formal.csv", index=False)
certain_events[["time", "certain_event_side", "archive_event_side", "state_count"]].to_csv(OUT / "certain_events_formal.csv", index=False)
false_certain[["time", "certain_event_side", "archive_event_side", "state_count"]].to_csv(OUT / "false_certain_events.csv", index=False)
formal[formal.event_label.eq("AMBIGUOUS_EVENT_CLOCK")].to_csv(OUT / "ambiguous_clock_rows.csv", index=False)

naive_all = event_union_metrics(archive_ev, naive_ev)
naive_short = event_union_metrics(archive_ev, naive_ev, side=-1)

# Gates and verdict.
side_set_contains_archive = float(formal.archive_side_contained.mean()) if formal_rows else 0.0
archive_path_containment = float(formal.archive_path_contained.mean()) if formal_rows else 0.0
singleton_share = float((formal.state_count == 1).mean()) if formal_rows else 0.0
state_counts = formal.state_count.astype(float).values

gates = {
    "formal_rows_ge1000": formal_rows >= 1000,
    "side_set_contains_archive_eq100pct": side_set_contains_archive == 1.0,
    "archive_path_containment_eq100pct": archive_path_containment == 1.0,
    "certain_event_precision_eq100pct": certain_event_precision == 1.0,
    "false_certain_event_n_eq0": len(false_certain) == 0,
    "short_certain_event_precision_eq100pct": short_precision == 1.0,
    "anchor_recovery_rate_48h_ge90pct": anchor_recovery_rate_48h >= 0.90,
    "median_resync_hours_le24": (pctile(resync_h, .5) is not None and pctile(resync_h, .5) <= 24.0) if len(epdf) else True,
    "no_tuning": True,
}

safety_fail = not (gates["side_set_contains_archive_eq100pct"] and gates["archive_path_containment_eq100pct"] and gates["certain_event_precision_eq100pct"] and gates["false_certain_event_n_eq0"] and gates["short_certain_event_precision_eq100pct"])
if safety_fail:
    verdict = "FAIL_SET_CLOCK_EXCLUDES_CANONICAL"
elif all(gates.values()):
    verdict = "PASS_SET_CLOCK_RECOVERABLE"
else:
    verdict = "WATCH_SET_CLOCK_SAFE_BUT_LOW_RECOVERY"

metrics = {
    "lab": LAB,
    "source_lab": "LAB058",
    "cooldown_hours": 12,
    "formal_start": formal_start,
    "formal_end": formal.time.max() if formal_rows else None,
    "formal_rows": formal_rows,
    "carry_in_divergence_at_formal_start": carry_in,
    "side_set_contains_archive": side_set_contains_archive,
    "archive_path_containment": archive_path_containment,
    "clock_state_singleton_share": singleton_share,
    "state_count": {
        "p50": pctile(state_counts, .5), "p95": pctile(state_counts, .95), "max": int(formal.state_count.max()) if formal_rows else 0,
    },
    "divergence_episode_n": int(len(epdf)),
    "recovered_episode_n": int((epdf.recovered == True).sum()) if len(epdf) else 0,
    "anchor_recovery_rate_48h": anchor_recovery_rate_48h,
    "resynchronization_hours": {
        "p50": pctile(resync_h, .5), "p95": pctile(resync_h, .95), "max": None if len(resync_h)==0 else float(np.max(resync_h)),
    },
    "event_certainty": {
        "archive_event_n": int(len(archive_event_rows)),
        "certain_event_n": int(len(certain_events)),
        "ambiguous_clock_row_n": int((formal.event_label == "AMBIGUOUS_EVENT_CLOCK").sum()),
        "certain_event_precision": certain_event_precision,
        "archive_event_certain_recall": archive_event_certain_recall,
        "false_certain_event_n": int(len(false_certain)),
    },
    "short_event_certainty": {
        "archive_short_event_n": int(len(archive_short_rows)),
        "certain_short_event_n": int(len(certain_short)),
        "certain_short_precision": short_precision,
        "archive_short_certain_recall": short_recall,
        "false_certain_short_n": int(len(false_certain_short)),
    },
    "naive_abstention_clock_comparison": {"all": naive_all, "short": naive_short},
    "gates": gates,
    "verdict": verdict,
    "frozen_short_v1_changed": False,
    "live_allocation": 0,
}

with open(OUT / "metrics.json", "w") as f:
    json.dump(metrics, f, indent=2, default=jnum)

report = f"""# {LAB} — REPORT

## Verdict
**{verdict}**

## Canonical containment
- formal rows: {formal_rows}
- side-set contains archive side: {side_set_contains_archive:.6%}
- archive clock path containment: {archive_path_containment:.6%}
- singleton clock-state share: {singleton_share:.6%}
- state count p50 / p95 / max: {pctile(state_counts,.5)} / {pctile(state_counts,.95)} / {int(formal.state_count.max()) if formal_rows else 0}

## Divergence / resynchronization
- formal divergence episodes: {len(epdf)}
- recovered episodes: {int((epdf.recovered == True).sum()) if len(epdf) else 0}
- recover <=48h: {anchor_recovery_rate_48h:.6%}
- resync hours p50 / p95 / max: {pctile(resync_h,.5)} / {pctile(resync_h,.95)} / {None if len(resync_h)==0 else float(np.max(resync_h))}

## Event certainty
- archive events: {len(archive_event_rows)}
- CERTAIN_EVENT: {len(certain_events)}
- precision: {certain_event_precision:.6%}
- archive event certain recall: {archive_event_certain_recall:.6%}
- false certain events: {len(false_certain)}

## SHORT event certainty
- archive SHORT events: {len(archive_short_rows)}
- certain SHORT events: {len(certain_short)}
- precision: {short_precision:.6%}
- recall: {short_recall:.6%}

## Naive abstention clock (comparison only)
- all-event union parity: {naive_all['union_match']:.6%}
- SHORT-event union parity: {naive_short['union_match']:.6%}

No alpha, threshold, cooldown, execution, management, cost, sizing, or live-allocation change was made.
"""
(OUT / "REPORT.md").write_text(report)
print(json.dumps(metrics, indent=2, default=jnum))
