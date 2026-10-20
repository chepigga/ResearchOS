#!/usr/bin/env python3
"""
CROWDFADE_LSR_SNAP_LAB_003 — big L/S swing + smooth turn -> price reversal? (vs price-only control)

User's pattern (2026-10-18/20): L/S Accounts rose from ~1.40 to ~1.83 (+30%) while price fell;
at the L/S peak it turned (smoothly) and price reversed up. Hypothesis: after a big L/S swing
and a turn at its extreme, a price reversal is more likely.

Definitions (per timeframe TF = 15m / 1h, bars labelled by close time):
  UP swing   : within the last W hours L/S min -> later max with max/min - 1 >= S,
               turn = first bar with L/S <= max * (1 - D)
  DOWN swing : L/S max -> later min with max/min - 1 >= S, turn = first bar with L/S >= min * (1 + D)
  Swing move : price change from the bar of the L/S swing start to the turn bar.
  Directions : REVERSAL = against the swing price move; CROWD = with the crowd's side
               (UP swing -> long); FADE = against the crowd.
Outcome: first touch +-1 ATR / +-2 ATR (ATR(24) on TF) within H hours; trade R (stop 1.5 ATR,
  target 2R, hold H, 4 bps cost). Stop first on ambiguous bars.
CONTROL (key): for every event, bars anywhere in history with a price move of the same sign and
  similar size (|move_ATR| within +-25%) over the same number of bars -> their reversal rate.
  Lift = event reversal rate - control reversal rate. L/S adds information only if lift > 0.
Grid: TF {15m,1h} x W {12h,24h} x S {15,20,25%} x D {2,3%}. IS < 2025-01-01 <= OOS.
"""
import argparse, importlib.util, os
from datetime import date
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "lab001", os.path.join(HERE, "..", "CROWDFADE_LSR_SNAP_LAB_001", "run_lab.py"))
L1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(L1)

COST_BPS = 4.0
OOS = pd.Timestamp("2025-01-01", tz="UTC")
H_HOURS = 12
ATR_N = 24
CTRL_N = 300


def resample(d5, rule):
    agg = dict(open="first", high="max", low="min", close="last", ls="last", oi="last",
               top_pos="last", taker="last", premium="last", spot_delta="sum")
    agg = {k: v for k, v in agg.items() if k in d5.columns}
    d = d5.resample(rule, label="right", closed="right").agg(agg).dropna(subset=["close", "ls"])
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(),
                    (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(ATR_N).mean()
    return d


def first_touch_all(d, mult, H):
    """Vectorised first touch for every bar: +1 up first, -1 down first, 0 none, 2 = both same bar."""
    C, Hh, Ll, A = d.close.values, d.high.values, d.low.values, d.atr.values
    n = len(C)
    up, dn = C + mult * A, C - mult * A
    out = np.zeros(n, int); done = np.zeros(n, bool)
    for h in range(1, H + 1):
        hi = np.full(n, np.nan); lo = np.full(n, np.nan)
        hi[:n - h] = Hh[h:]; lo[:n - h] = Ll[h:]
        hu = (hi >= up) & ~done; hd = (lo <= dn) & ~done
        both = hu & hd
        out[both] = 2; out[hu & ~hd] = 1; out[hd & ~hu] = -1
        done |= hu | hd
    return out


def win_for_side(ft, side):
    """1 win / 0 loss / nan unresolved, ambiguous bar = loss."""
    if ft == 0:
        return np.nan
    if ft == 2:
        return 0.0
    return 1.0 if ft == side else 0.0


def trade_r(d, i, side, H):
    C, Hh, Ll, A = d.close.values, d.high.values, d.low.values, d.atr.values
    e, a = C[i], A[i]; risk = 1.5 * a
    stop, tgt = e - side * risk, e + side * 2 * risk
    cost = COST_BPS / 1e4 * e / risk
    end = min(i + 1 + H, len(C))
    for j in range(i + 1, end):
        if (side == 1 and Ll[j] <= stop) or (side == -1 and Hh[j] >= stop):
            return -1 - cost
        if (side == 1 and Hh[j] >= tgt) or (side == -1 and Ll[j] <= tgt):
            return 2 - cost
    return side * (C[end - 1] - e) / risk - cost


def find_swings(d, Wb, S, D):
    ls = d.ls.values
    n = len(ls)
    from numpy.lib.stride_tricks import sliding_window_view as swv
    v = swv(ls, Wb)                      # row k = ls[k : k+Wb], ends at bar k+Wb-1
    imin = v.argmin(1); imax = v.argmax(1)
    mn = v.min(1); mx = v.max(1)
    pad = Wb - 1
    imin = np.r_[np.full(pad, -1), imin + np.arange(len(imin))]
    imax = np.r_[np.full(pad, -1), imax + np.arange(len(imax))]
    mn = np.r_[np.full(pad, np.nan), mn]; mx = np.r_[np.full(pad, np.nan), mx]
    swing = mx / mn - 1
    up_turn = (swing >= S) & (imax > imin) & (ls <= mx * (1 - D)) & (imax < np.arange(n))
    dn_turn = (swing >= S) & (imin > imax) & (ls >= mn * (1 + D)) & (imin < np.arange(n))
    ev, last = [], -10**9
    cool = Wb // 2
    for i in range(Wb, n):
        kind = 1 if up_turn[i] else (-1 if dn_turn[i] else 0)
        if kind == 0 or i - last < cool or not np.isfinite(d.atr.values[i]):
            continue
        prev_ok = up_turn[i - 1] if kind == 1 else dn_turn[i - 1]
        if prev_ok:
            continue                      # only the first bar of the turn
        start = imin[i] if kind == 1 else imax[i]
        last = i
        ev.append((i, kind, start, swing[i]))
    return ev


def boot(x, n=2000, seed=1):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 10:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    b = rng.choice(x, (n, len(x))).mean(1)
    return x.mean(), np.percentile(b, 2.5), np.percentile(b, 97.5)


def f3(m, lo, hi, pct=True):
    if not np.isfinite(m):
        return "—"
    k = 100 if pct else 1
    return f"{m*k:+.1f} [{lo*k:+.1f}…{hi*k:+.1f}]" if pct else f"{m:+.3f} [{lo:+.3f}…{hi:+.3f}]"


def fr(m, lo, hi):
    return "—" if not np.isfinite(m) else f"{m*100:.1f}% [{lo*100:.1f}–{hi*100:.1f}]"


def run_tf(d, tfname, bars_per_hour, rng):
    H = H_HOURS * bars_per_hour
    ft1 = first_touch_all(d, 1.0, H)
    ft2 = first_touch_all(d, 2.0, H)
    C, A = d.close.values, d.atr.values
    n = len(C)
    rows, ev_rows = [], []
    for Wh in [12, 24]:
        Wb = Wh * bars_per_hour
        for S in [0.15, 0.20, 0.25]:
            for D in [0.02, 0.03]:
                evs = find_swings(d, Wb, S, D)
                recs = []
                for i, kind, start, sw in evs:
                    if i + H >= n:
                        continue
                    move = (C[i] - C[start]) / A[i]
                    if move == 0 or not np.isfinite(move):
                        continue
                    rev = -int(np.sign(move))
                    L = i - start
                    # control: same lag, same-sign similar move size
                    mv = np.full(n, np.nan); mv[L:] = (C[L:] - C[:-L]) / A[L:]
                    ok = (np.sign(mv) == np.sign(move)) & (np.abs(mv - move) <= 0.25 * abs(move))
                    ok[max(0, i - H):i + H + 1] = False
                    ok[n - H:] = False
                    cand = np.where(ok)[0]
                    if len(cand) > CTRL_N:
                        cand = rng.choice(cand, CTRL_N, replace=False)
                    cw = [win_for_side(ft1[j], rev) for j in cand]
                    ctrl = np.nanmean(cw) if len(cw) and not np.all(np.isnan(cw)) else np.nan
                    w1 = win_for_side(ft1[i], rev)
                    w2 = win_for_side(ft2[i], rev)
                    recs.append(dict(t=d.index[i], kind=kind, swing=sw, move_atr=move, bars=L,
                                     rev=rev, crowd=kind, win1=w1, win2=w2, ctrl=ctrl,
                                     lift=(w1 - ctrl) if np.isfinite(w1) and np.isfinite(ctrl) else np.nan,
                                     crowd_win1=win_for_side(ft1[i], kind),
                                     R_rev=trade_r(d, i, rev, H), R_crowd=trade_r(d, i, kind, H)))
                r = pd.DataFrame(recs)
                if r.empty:
                    continue
                r["split"] = np.where(r.t >= OOS, "OOS", "IS")
                r["tf"], r["W"], r["S"], r["D"] = tfname, Wh, S, D
                ev_rows.append(r)
                out = dict(tf=tfname, W=Wh, S=S, D=D, n=len(r),
                           agree=(r.rev == r.crowd).mean() * 100)
                for sp in ["IS", "OOS"]:
                    s = r[r.split == sp]
                    out[f"{sp}_n"] = len(s)
                    out[f"{sp}_rev"] = boot(s.win1)
                    out[f"{sp}_ctrl"] = s.ctrl.mean()
                    out[f"{sp}_lift"] = boot(s.lift)
                    out[f"{sp}_R"] = boot(s.R_rev)
                    out[f"{sp}_crowd"] = boot(s.crowd_win1)
                rows.append(out)
    return rows, (pd.concat(ev_rows) if ev_rows else pd.DataFrame())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2022-01-01")
    ap.add_argument("--end", default="2026-10-19")
    ap.add_argument("--cache", default="./binance_cache")
    ap.add_argument("--out", default=os.path.join(HERE, "output"))
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    global OOS
    if a.synthetic:
        d5 = L1.synthetic(n=120000); OOS = pd.Timestamp("2024-01-01", tz="UTC")
    else:
        d5 = L1.build_dataset(date.fromisoformat(a.start), date.fromisoformat(a.end), a.cache)
    d5 = d5.dropna(subset=["close", "ls"])
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(11)

    rows, evs = [], []
    for tf, rule, bph in [("15m", "15min", 4), ("1h", "60min", 1)]:
        d = resample(d5, rule)
        r, e = run_tf(d, tf, bph, rng)
        rows += r; evs.append(e)
        if tf == "15m" and not a.synthetic:
            diag = d.loc["2026-10-18 12:00":"2026-10-19 06:00", ["close", "ls"]]
    E = pd.concat(evs)
    E.to_csv(os.path.join(a.out, "events.csv"), index=False)

    Lr = []; w = Lr.append
    w("# CROWDFADE_LSR_SNAP_LAB_003 — big L/S swing + turn → price reversal?\n")
    w(f"Data {d5.index[0]:%Y-%m-%d} → {d5.index[-1]:%Y-%m-%d}. IS < {OOS:%Y-%m-%d} ≤ OOS. "
      f"Horizon {H_HOURS}h, ATR({ATR_N}) on TF, cost {COST_BPS} bps.\n")
    w("**rev%** = P(price reverses first, ±1 ATR). **ctrl%** = same for bars with a similar price "
      "move but no L/S condition. **lift** = rev − ctrl in pp (paired, bootstrap CI). "
      "**R** = reversal trade, stop 1.5 ATR, target 2R. **crowd%** = P(win) trading WITH the crowd.\n")
    w("L/S adds information only if lift CI > 0 in BOTH IS and OOS.\n")
    w("| TF | W h | S | D | IS n | IS rev% | IS ctrl% | IS lift pp | IS R | OOS n | OOS rev% | OOS ctrl% | OOS lift pp | OOS R | OOS crowd% | rev=crowd% |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for o in rows:
        w(f"| {o['tf']} | {o['W']} | {o['S']:.0%} | {o['D']:.0%} | {o['IS_n']} | {fr(*o['IS_rev'])} | "
          f"{o['IS_ctrl']*100:.1f}% | {f3(*o['IS_lift'])} | {f3(*o['IS_R'], pct=False)} | "
          f"{o['OOS_n']} | {fr(*o['OOS_rev'])} | {o['OOS_ctrl']*100:.1f}% | {f3(*o['OOS_lift'])} | "
          f"{f3(*o['OOS_R'], pct=False)} | {fr(*o['OOS_crowd'])} | {o['agree']:.0f}% |")
    passed = [o for o in rows if o["IS_lift"][1] > 0 and o["OOS_lift"][1] > 0]
    w(f"\n**Configs with lift CI > 0 in IS and OOS: {len(passed)} of {len(rows)}**\n")
    if not a.synthetic:
        w("## Diagnostic — 15m L/S and price, 2026-10-18 12:00 → 10-19 06:00 UTC (Kyiv = UTC+3)\n")
        w("| UTC | close | L/S |")
        w("|---|---|---|")
        for t, row in diag.iterrows():
            w(f"| {t:%m-%d %H:%M} | {row.close:,.0f} | {row.ls:.3f} |")
        recent = E[E.t >= pd.Timestamp("2026-10-15", tz="UTC")]
        w("\n### Events detected since 2026-10-15\n")
        if len(recent):
            w("| UTC | TF | W | S | D | swing | kind | price move ATR | reversal side | win ±1ATR |")
            w("|---|---|---|---|---|---|---|---|---|---|")
            for r_ in recent.drop_duplicates(["t", "tf"]).itertuples():
                w(f"| {r_.t:%m-%d %H:%M} | {r_.tf} | {r_.W} | {r_.S:.0%} | {r_.D:.0%} | "
                  f"{r_.swing:.0%} | {'UP' if r_.kind == 1 else 'DOWN'} | {r_.move_atr:+.1f} | "
                  f"{'long' if r_.rev == 1 else 'short'} | {r_.win1} |")
        else:
            w("none")
    rep = "\n".join(Lr)
    open(os.path.join(a.out, "report.md"), "w").write(rep)
    print(rep)


if __name__ == "__main__":
    main()
