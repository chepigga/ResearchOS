#!/usr/bin/env python3
"""LAB010 V2 compute engine.

Frozen research protocol is inherited from LAB010 v1. This file changes only
execution: vectorized/chunked stage-2 gate discovery and grouped exact-tick
replay per physical signal. Thresholds, grids, chronology, commission, entry
semantics, selection gates and 2026 OOS handling are unchanged.
"""
from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
V1_PATH = HERE / 'xau_price_time_double_trap_second_stage_response_lab010.py'
spec = importlib.util.spec_from_file_location('lab010_v1', V1_PATH)
v1 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(v1)


def find_stage2_signals_v2(x: pd.DataFrame, stage1: pd.DataFrame, chunk_size: int = 4096):
    """Same state machine as v1, vectorized across stage1 events."""
    mins = x.minute.to_numpy(np.int64)
    hi = x.mid_high.to_numpy(float)
    lo = x.mid_low.to_numpy(float)
    close = x.mid_close.to_numpy(float)
    first_t = x.first_time_msc.to_numpy(np.int64)
    first_bid = x.first_bid.to_numpy(float)
    first_ask = x.first_ask.to_numpy(float)
    atr_bar = x.atr14_causal.to_numpy(float)
    years = x.year.to_numpy()

    # V1 parity-fixed meaning: minute is integer minute index, not epoch-ms.
    hit_min = stage1.hit_time_msc.to_numpy(np.int64) // 60000
    j0_all = np.searchsorted(mins, hit_min, side='right').astype(np.int64)
    valid = (j0_all < len(x) - 1) & np.isfinite(stage1.atr_entry.to_numpy(float)) & (stage1.atr_entry.to_numpy(float) > 0) & np.isfinite(stage1.sl_price.to_numpy(float))
    src = stage1.reset_index(drop=True)
    out_parts = []
    offsets = np.arange(v1.MAX_STAGE2_WAIT_MIN, dtype=np.int64)

    valid_idx = np.flatnonzero(valid)
    for c0 in range(0, len(valid_idx), chunk_size):
        ridx = valid_idx[c0:c0 + chunk_size]
        r = src.iloc[ridx].reset_index(drop=True)
        j0 = j0_all[ridx]
        idx2 = j0[:, None] + offsets[None, :]
        in_bounds = idx2 <= (len(x) - 2)
        safe = np.minimum(idx2, len(x) - 1)
        H = hi[safe]; L = lo[safe]; C = close[safe]
        H = np.where(in_bounds, H, np.nan)
        L = np.where(in_bounds, L, np.nan)
        C = np.where(in_bounds, C, np.nan)
        side_buy = r.inverse_side.astype(str).eq('BUY').to_numpy()
        atr = r.atr_entry.to_numpy(float)
        slp = r.sl_price.to_numpy(float)
        n = len(r)

        for extra in v1.EXTRA_SWEEP_ATR:
            seen = np.full(n, extra <= 0.0, dtype=bool)
            worst = slp.copy()
            # Relative bar index of most recent significant extreme. V1 starts at j0-1.
            last_sig = np.full(n, -1, dtype=np.int16)
            first_hit = {(hold, reclaim): np.full(n, -1, dtype=np.int16)
                         for hold in v1.HOLD_MIN for reclaim in v1.RECLAIM_ATR}
            extra_thr = float(extra) * atr

            for k in range(v1.MAX_STAGE2_WAIT_MIN):
                ok = in_bounds[:, k]
                pext = np.where(side_buy, L[:, k], H[:, k])
                finite = ok & np.isfinite(pext)
                crosses = finite & (~seen) & np.where(side_buy, pext <= slp - extra_thr, pext >= slp + extra_thr)
                if crosses.any():
                    seen[crosses] = True
                    worst[crosses] = pext[crosses]
                    last_sig[crosses] = k

                active = finite & seen & (~crosses)
                sig = active & np.where(side_buy,
                                        pext < worst - v1.SIG_NEW_EXTREME_ATR * atr,
                                        pext > worst + v1.SIG_NEW_EXTREME_ATR * atr)
                if sig.any():
                    worst[sig] = pext[sig]
                    last_sig[sig] = k
                nonsig = active & (~sig)
                if nonsig.any():
                    worst[nonsig] = np.where(side_buy[nonsig],
                                             np.minimum(worst[nonsig], pext[nonsig]),
                                             np.maximum(worst[nonsig], pext[nonsig]))

                finite_c = ok & seen & np.isfinite(C[:, k])
                reclaim_dist = np.where(side_buy, C[:, k] - worst, worst - C[:, k])
                quiet = k - last_sig
                for hold in v1.HOLD_MIN:
                    hold_ok = finite_c & (quiet >= hold)
                    if not hold_ok.any():
                        continue
                    for reclaim in v1.RECLAIM_ATR:
                        a = first_hit[(hold, reclaim)]
                        q = hold_ok & (a < 0) & (reclaim_dist >= float(reclaim) * atr)
                        a[q] = k

            for hold in v1.HOLD_MIN:
                for reclaim in v1.RECLAIM_ATR:
                    karr = first_hit[(hold, reclaim)]
                    qidx = np.flatnonzero(karr >= 0)
                    if not len(qidx):
                        continue
                    kval = karr[qidx].astype(np.int64)
                    eidx = j0[qidx] + kval + 1
                    gid = v1.gate_id(extra, hold, reclaim)
                    # Reconstruct worst/reclaim at qualifying bar exactly with a tiny
                    # per-qualified-row replay over <=30 bars; gate discovery itself is vectorized.
                    recs = []
                    for qi, kk in zip(qidx, kval):
                        sb = bool(side_buy[qi]); w = float(slp[qi]); sn = (extra <= 0.0); ls = -1
                        for t in range(int(kk) + 1):
                            pe = float(L[qi, t] if sb else H[qi, t])
                            if not np.isfinite(pe):
                                continue
                            if not sn:
                                cross = pe <= slp[qi] - extra_thr[qi] if sb else pe >= slp[qi] + extra_thr[qi]
                                if cross:
                                    sn = True; w = pe; ls = t
                                else:
                                    continue
                            else:
                                significant = pe < w - v1.SIG_NEW_EXTREME_ATR * atr[qi] if sb else pe > w + v1.SIG_NEW_EXTREME_ATR * atr[qi]
                                if significant:
                                    w = pe; ls = t
                                else:
                                    w = min(w, pe) if sb else max(w, pe)
                        cc = float(C[qi, kk])
                        rd = (cc - w) if sb else (w - cc)
                        recs.append((w, rd / atr[qi]))
                    worst_q = np.array([z[0] for z in recs], float)
                    reclaim_q = np.array([z[1] for z in recs], float)
                    rr = r.iloc[qidx]
                    part = pd.DataFrame({
                        'stage1_uid': rr.stage1_uid.to_numpy(np.int64),
                        'event_idx': rr.event_idx.to_numpy(np.int64),
                        'source_cell_id': rr.cell_id.astype(str).to_numpy(),
                        'score_bucket': rr.score_bucket.astype(str).to_numpy(),
                        'wait_min': rr.wait_min.to_numpy(np.int64),
                        'transition': rr.transition.astype(str).to_numpy(),
                        'stage1_entry_mode': rr.entry_mode.astype(str).to_numpy(),
                        'inverse_side': rr.inverse_side.astype(str).to_numpy(),
                        'stage1_hit_time_msc': rr.hit_time_msc.to_numpy(np.int64),
                        'stage1_sl_price': slp[qidx],
                        'atr_stage1': atr[qidx],
                        'gate_id': gid,
                        'extra_sweep_atr': float(extra),
                        'hold_min': int(hold),
                        'reclaim_atr': float(reclaim),
                        'worst_price': worst_q,
                        'reclaim_dist_atr': reclaim_q,
                        'qualify_bar_idx': j0[qidx] + kval,
                        'entry_idx_stage2': eidx,
                        'entry_minute_stage2': mins[eidx],
                        'entry_time_msc_stage2': first_t[eidx],
                        'entry_bid_stage2': first_bid[eidx],
                        'entry_ask_stage2': first_ask[eidx],
                        'atr_stage2': np.where(np.isfinite(atr_bar[eidx]), atr_bar[eidx], atr[qidx]),
                        'entry_year_stage2': years[eidx].astype(int),
                    })
                    out_parts.append(part)
        print(f'[STAGE2-V2] {min(c0+chunk_size,len(valid_idx))}/{len(valid_idx)}', flush=True)

    if not out_parts:
        return pd.DataFrame()
    s = pd.concat(out_parts, ignore_index=True)
    return s.sort_values(['stage1_uid','gate_id','entry_minute_stage2']).drop_duplicates(['stage1_uid','gate_id'], keep='first').reset_index(drop=True)


def replay_exact_v2(raw_zip: Path, files, events: pd.DataFrame):
    """Exact Bid/Ask replay, grouped by physical signal instead of 18 duplicated scans."""
    e = events.reset_index(drop=True).copy()
    n = len(e)
    outcome = np.full(n, 'UNRESOLVED', object)
    rval = np.full(n, np.nan, float)
    hit_time = np.full(n, -1, np.int64)
    terminal_px = np.full(n, np.nan, float)

    start = e.entry_time_msc_stage2.to_numpy(np.int64)
    end = e.end_time_msc.to_numpy(np.int64)
    side_buy = e.inverse_side.eq('BUY').to_numpy()
    tp = e.tp_price.to_numpy(float); sl = e.sl_price.to_numpy(float)
    rr = e.rr.to_numpy(float); comm = e.commission_R.to_numpy(float)
    entry = e.entry_exec_price.to_numpy(float); atr = e.atr_stage2.to_numpy(float)
    stop_atr = e.stop_atr.to_numpy(float)

    groups = {int(sid): idx.to_numpy(np.int64) for sid, idx in e.groupby('signal_uid', sort=False).groups.items()}
    meta = e.drop_duplicates('signal_uid')[['signal_uid','entry_time_msc_stage2']].copy()
    meta['max_end'] = meta.signal_uid.map(e.groupby('signal_uid').end_time_msc.max())
    sig_ids = meta.signal_uid.to_numpy(np.int64)
    sig_start = meta.entry_time_msc_stage2.to_numpy(np.int64)
    sig_end = meta.max_end.to_numpy(np.int64)

    with zipfile.ZipFile(raw_zip, 'r') as z:
        names = set(z.namelist())
        for k, (member, ft, lt) in enumerate(files, 1):
            if member not in names:
                continue
            cand_pos = np.flatnonzero((sig_start <= lt) & (sig_end >= ft))
            if not len(cand_pos):
                continue
            with z.open(member) as fh:
                df = pd.read_csv(fh, usecols=['time_msc','bid','ask'])
            if df.empty:
                continue
            tt = df.time_msc.to_numpy(np.int64); bid = df.bid.to_numpy(float); ask = df.ask.to_numpy(float)
            for sp in cand_pos:
                sid = int(sig_ids[sp]); rows = groups[sid]
                active = rows[outcome[rows] == 'UNRESOLVED']
                if not len(active):
                    continue
                lo_i = int(np.searchsorted(tt, max(int(sig_start[sp]), int(ft)), side='left'))
                if lo_i >= len(tt):
                    continue
                sb = bool(side_buy[active[0]])
                px_all = bid if sb else ask
                for ei in active:
                    hi_i = int(np.searchsorted(tt, min(int(end[ei]), int(lt)), side='right'))
                    if hi_i <= lo_i:
                        continue
                    px = px_all[lo_i:hi_i]
                    terminal_px[ei] = float(px[-1])
                    hit = np.flatnonzero(((px >= tp[ei]) | (px <= sl[ei])) if sb else ((px <= tp[ei]) | (px >= sl[ei])))
                    if len(hit):
                        jj = lo_i + int(hit[0]); p = float(px_all[jj]); hit_time[ei] = int(tt[jj])
                        is_tp = (p >= tp[ei]) if sb else (p <= tp[ei])
                        if is_tp:
                            outcome[ei] = 'TP'; rval[ei] = rr[ei] - comm[ei]
                        else:
                            outcome[ei] = 'SL'; rval[ei] = -1.0 - comm[ei]
            if k % 100 == 0:
                print(f'[RAW-V2] {k}/{len(files)} resolved={(outcome != "UNRESOLVED").sum()}/{n}', flush=True)

    for ei in np.flatnonzero(outcome == 'UNRESOLVED'):
        if np.isfinite(terminal_px[ei]):
            pnl = (terminal_px[ei] - entry[ei]) if side_buy[ei] else (entry[ei] - terminal_px[ei])
            rval[ei] = pnl / (stop_atr[ei] * atr[ei]) - comm[ei]
            outcome[ei] = 'TIME'
        else:
            outcome[ei] = 'NO_TICKS'
    out = e.copy(); out['tick_outcome']=outcome; out['R_exact']=rval; out['hit_time_msc']=hit_time; out['terminal_exec_price']=terminal_px
    out['minutes_to_hit'] = np.where(hit_time >= 0, (hit_time-start)/60000.0, np.nan)
    return out


# Replace only compute engines; all frozen selection/report logic remains v1.
v1.find_stage2_signals = find_stage2_signals_v2
v1.replay_exact = replay_exact_v2

if __name__ == '__main__':
    v1.main()
