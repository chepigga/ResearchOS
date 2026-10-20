#!/usr/bin/env python3
"""
CROWDFADE_LSR_SNAP_LAB_002 — L/S snap as CONFIRMATION (follow-up to LAB001).

LAB001: entering in the price direction right at the L/S snap loses (45.5% vs 49.1% base),
but OOS MFE > MAE hints the move often continues after a pullback.

Tests:
  A) Snap-follow trades (direction = price move during the snap), grid:
       entry  : IMM (close of signal bar) | PB0.5 / PB1.0 (limit pullback of x ATR, wait 24 bars)
       stop   : 1.0 / 1.5 / 2.0 ATR       target: 2R  or  TRAIL (trailing stop = stop distance)
       hold   : 48 / 144 bars (4h / 12h)  subset: all | level-break only
  B) Snap as HOLD FILTER on a plain breakout strategy (prior-24h high/low break, stop 1.5 ATR,
     target 2R, hold 144): ALWAYS vs EXIT@12 bars unless a confirming snap appeared
     (breakout up + crowd-long unwinding, or breakout down + crowd-short unwinding)
     vs EXIT@12 if an opposite snap appeared.

Reuses data/feature code from LAB001. Same no-look-ahead rules, cost 4 bps,
stop-first on ambiguous bars (including the fill bar of a limit entry).
"""
import argparse, importlib.util, os, sys
from datetime import date
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "lab001", os.path.join(HERE, "..", "CROWDFADE_LSR_SNAP_LAB_001", "run_lab.py"))
L1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(L1)
P = L1.P

PB_WAIT = 24
CONFIRM_BARS = 12


def trade(arr, i_sig, side, entry, pb_x, sl_mult, hold, exit_mode, cost_bps):
    O, H, Lw, C, A = arr["open"], arr["high"], arr["low"], arr["close"], arr["atr"]
    n = len(C)
    a = A[i_sig]
    if not np.isfinite(a) or a <= 0:
        return None
    if entry == "IMM":
        ie, e = i_sig, C[i_sig]
        first = ie + 1
    else:
        lim = C[i_sig] - side * pb_x * a
        ie = None
        for j in range(i_sig + 1, min(i_sig + 1 + PB_WAIT, n)):
            if side == 1 and Lw[j] <= lim:
                ie, e = j, min(O[j], lim); break
            if side == -1 and H[j] >= lim:
                ie, e = j, max(O[j], lim); break
        if ie is None:
            return "nofill"
        first = ie            # fill bar: check stop only (conservative)
    risk = sl_mult * a
    stop = e - side * risk
    tgt = e + side * 2 * risk
    best = e
    end = min(ie + 1 + hold, n)
    cost_r = cost_bps / 1e4 * e / risk
    for j in range(first, end):
        if (side == 1 and Lw[j] <= stop) or (side == -1 and H[j] >= stop):
            return side * (stop - e) / risk - cost_r
        if j == ie:
            continue
        if exit_mode == "T2R":
            if (side == 1 and H[j] >= tgt) or (side == -1 and Lw[j] <= tgt):
                return 2.0 - cost_r
        else:  # TRAIL on closes
            best = max(best, C[j]) if side == 1 else min(best, C[j])
            stop = max(stop, best - risk) if side == 1 else min(stop, best + risk)
    return side * (C[end - 1] - e) / risk - cost_r


def summarize(r):
    r = np.asarray([x for x in r if x is not None and x != "nofill"], float)
    m, lo, hi = L1.boot_mean(r)
    return len(r), m, lo, hi, (r > 0).mean() * 100 if len(r) else np.nan


def part_a(d, ev, oos, cost):
    arr = {k: d[k].values for k in ["open", "high", "low", "close", "atr"]}
    ev = ev[np.sign(ev["ret_k"]) != 0].copy()
    ev["side"] = np.sign(ev["ret_k"]).astype(int)
    ev["split"] = np.where(ev["t"] >= oos, "OOS", "IS")
    rows = []
    for entry, pbx in [("IMM", 0), ("PB0.5", 0.5), ("PB1.0", 1.0)]:
        for sl in [1.0, 1.5, 2.0]:
            for hold in [48, 144]:
                for ex in ["T2R", "TRAIL"]:
                    res = [trade(arr, int(r.i), int(r.side), entry, pbx, sl, hold, ex, cost)
                           for r in ev.itertuples()]
                    ev["_r"] = res
                    for subset in ["all", "level"]:
                        s = ev if subset == "all" else ev[ev["level"]]
                        fill = np.mean([x != "nofill" for x in s["_r"]]) * 100
                        out = dict(entry=entry, sl=sl, hold=hold, exit=ex, subset=subset,
                                   fill=fill)
                        for sp in ["IS", "OOS"]:
                            n, m, lo, hi, wr = summarize(s.loc[s.split == sp, "_r"])
                            out.update({f"{sp}_n": n, f"{sp}_R": m, f"{sp}_lo": lo,
                                        f"{sp}_hi": hi, f"{sp}_win": wr})
                        rows.append(out)
    return pd.DataFrame(rows)


def part_b(d, oos, cost):
    """Breakout strategy with snap as hold filter."""
    zp, sm = P["Z_PEAK"], P["SNAP_MIN"]
    long_snap = ((d["zmax"] >= zp) & (d["dz_k"] <= -sm)).values    # crowd long unwinding
    short_snap = ((d["zmin"] <= -zp) & (d["dz_k"] >= sm)).values   # crowd short unwinding
    hi = d["high"].shift(1).rolling(P["LEVEL_LOOK"]).max().values
    lo = d["low"].shift(1).rolling(P["LEVEL_LOOK"]).min().values
    C, H, Lw, A = d["close"].values, d["high"].values, d["low"].values, d["atr"].values
    n = len(C)
    events, last = [], -10**9
    for i in range(P["LEVEL_LOOK"] + 2, n - 2):
        side = 1 if C[i] > hi[i] and C[i - 1] <= hi[i - 1] else (
            -1 if C[i] < lo[i] and C[i - 1] >= lo[i - 1] else 0)
        if side == 0 or not np.isfinite(A[i]) or i - last < P["COOLDOWN"]:
            continue
        last = i
        events.append((i, side))
    rows = []
    for i, side in events:
        e, a = C[i], A[i]
        risk = 1.5 * a
        stop, tgt = e - side * risk, e + side * 2 * risk
        cost_r = cost / 1e4 * e / risk
        end = min(i + 1 + 144, n)
        res = {"ALWAYS": None, "KEEP_IF_CONFIRM": None, "EXIT_IF_OPPOSITE": None}
        confirm = opposite = False
        for j in range(i + 1, end):
            k = j - i
            if k <= CONFIRM_BARS:
                cs = long_snap[j] if side == 1 else short_snap[j]
                os_ = short_snap[j] if side == 1 else long_snap[j]
                confirm |= bool(cs); opposite |= bool(os_)
            hit_stop = (side == 1 and Lw[j] <= stop) or (side == -1 and H[j] >= stop)
            hit_tgt = (side == 1 and H[j] >= tgt) or (side == -1 and Lw[j] <= tgt)
            r_bar = -1.0 if hit_stop else (2.0 if hit_tgt else None)
            for key in res:
                if res[key] is not None:
                    continue
                if r_bar is not None:
                    res[key] = r_bar - cost_r
                elif k == CONFIRM_BARS and (
                        (key == "KEEP_IF_CONFIRM" and not confirm) or
                        (key == "EXIT_IF_OPPOSITE" and opposite)):
                    res[key] = side * (C[j] - e) / risk - cost_r
            if all(v is not None for v in res.values()):
                break
        for key in res:
            if res[key] is None:
                res[key] = side * (C[end - 1] - e) / risk - cost_r
        rows.append(dict(t=d.index[i], side=side, confirm=confirm, opposite=opposite, **res))
    b = pd.DataFrame(rows)
    b["split"] = np.where(b["t"] >= oos, "OOS", "IS")
    return b


def fm(m, lo, hi):
    return "—" if not np.isfinite(m) else f"{m:+.3f} [{lo:+.3f}…{hi:+.3f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2022-01-01")
    ap.add_argument("--end", default="2026-10-18")
    ap.add_argument("--cache", default="./binance_cache")
    ap.add_argument("--out", default=os.path.join(HERE, "output"))
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    if a.synthetic:
        d = L1.synthetic(); P["OOS_FROM"] = "2023-05-01"
    else:
        d = L1.build_dataset(date.fromisoformat(a.start), date.fromisoformat(a.end), a.cache)
    d = d.dropna(subset=["close", "ls"])
    d = L1.features(d)
    ev = L1.find_events(d)
    oos = pd.Timestamp(P["OOS_FROM"], tz="UTC")
    cost = P["COST_BPS"]
    os.makedirs(a.out, exist_ok=True)

    A = part_a(d, ev, oos, cost)
    A.to_csv(os.path.join(a.out, "part_a_grid.csv"), index=False)
    B = part_b(d, oos, cost)
    B.to_csv(os.path.join(a.out, "part_b_breakouts.csv"), index=False)

    Lr = []; w = Lr.append
    w("# CROWDFADE_LSR_SNAP_LAB_002 — L/S snap as confirmation\n")
    w(f"Data {d.index[0]:%Y-%m-%d} → {d.index[-1]:%Y-%m-%d}; snap events {len(ev)}; "
      f"OOS from {P['OOS_FROM']}; cost {cost} bps; R = multiples of the stop distance.\n")
    w("## A — Snap-follow grid (direction = price move during snap)\n")
    w("Sorted by IS mean R. 72 combos → expect ~3–4 false positives at 95%: "
      "a combo counts only if BOTH IS and OOS CI are above 0.\n")
    w("| entry | SL ATR | hold | exit | subset | fill% | IS n | IS R [CI] | OOS n | OOS R [CI] | OOS win% |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in A.sort_values("IS_R", ascending=False).itertuples():
        w(f"| {r.entry} | {r.sl} | {r.hold} | {r.exit} | {r.subset} | {r.fill:.0f} | {r.IS_n} | "
          f"{fm(r.IS_R, r.IS_lo, r.IS_hi)} | {r.OOS_n} | {fm(r.OOS_R, r.OOS_lo, r.OOS_hi)} | "
          f"{r.OOS_win:.1f} |")
    passed = A[(A.IS_lo > 0) & (A.OOS_lo > 0)]
    w(f"\n**Combos with IS and OOS CI > 0: {len(passed)}**\n")

    w("## B — Breakout (24h high/low) with L/S snap as hold filter\n")
    w(f"Breakouts: {len(B)}; confirming snap within {CONFIRM_BARS} bars: "
      f"{B.confirm.mean()*100:.1f}%; opposite snap: {B.opposite.mean()*100:.1f}%\n")
    w("| rule | IS n | IS R [CI] | OOS n | OOS R [CI] |")
    w("|---|---|---|---|---|")
    for key in ["ALWAYS", "KEEP_IF_CONFIRM", "EXIT_IF_OPPOSITE"]:
        i_ = L1.boot_mean(B.loc[B.split == "IS", key]); o_ = L1.boot_mean(B.loc[B.split == "OOS", key])
        w(f"| {key} | {(B.split=='IS').sum()} | {fm(*i_)} | {(B.split=='OOS').sum()} | {fm(*o_)} |")
    w("\nConditional (ALWAYS rule) by snap seen in first 12 bars:\n")
    w("| group | IS n | IS R [CI] | OOS n | OOS R [CI] |")
    w("|---|---|---|---|---|")
    for lab, m in [("confirm", B.confirm), ("no confirm", ~B.confirm),
                   ("opposite", B.opposite), ("no opposite", ~B.opposite)]:
        s = B[m]
        i_ = L1.boot_mean(s.loc[s.split == "IS", "ALWAYS"]); o_ = L1.boot_mean(s.loc[s.split == "OOS", "ALWAYS"])
        w(f"| {lab} | {(s.split=='IS').sum()} | {fm(*i_)} | {(s.split=='OOS').sum()} | {fm(*o_)} |")
    w("\nNote: the conditional table uses information from the first 12 bars of the trade; "
      "it describes the filter's value, the rules above are the tradable versions.")
    rep = "\n".join(Lr)
    open(os.path.join(a.out, "report.md"), "w").write(rep)
    print(rep)


if __name__ == "__main__":
    main()
