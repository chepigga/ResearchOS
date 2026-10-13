"""LAB253x — execution grid on frozen v157 signals. Choose on TRAIN (2021-24), report OOS (2025-26).
Same portfolio rules as v157: priority A>B3>R48>EARLY, max 2 positions, 2nd only same side & first MTM>=0 at open.
1R = stop distance = k * H1ATR. Stop-first intrabar. Cost 7.5 bps round trip."""
import os
os.environ["LAB_CACHE"] = "/home/claude/lab251/cache_full.pkl"
import itertools, numpy as np, pandas as pd
import lab251 as L

BO, BH, BL, BC, N, BT = L.BO, L.BH, L.BL, L.BC, L.N, L.BT
TE = pd.Timestamp("2025-01-01", tz="UTC")
COST = 7.5


def sim(raw, k, H, tp, half_lock=False):
    sigs = {}
    for r in raw.itertuples(index=False):
        sigs.setdefault(int(r.entry_i), []).append((int(r.pri), int(r.side), float(r.atr), r.source))
    idx = sorted(sigs); act = []; done = []; eq = []; real = 0.0
    if not idx: return pd.DataFrame(), np.array([0.0])
    i = idx[0]; p_i = 0; last = idx[-1]
    def mtm(p, px):
        r = p["s"] * (px - p["e"]) / p["R"]
        return (p["bank"] + p["w"] * r if p["half"] else r) - p["c"]
    while i < N:
        for pri, s, a, src in sorted(sigs.get(i, [])):
            ok = len(act) == 0 or (len(act) == 1 and act[0]["s"] == s and mtm(act[0], BO[i]) >= 0)
            if ok:
                e = BO[i]; R = k * a
                act.append(dict(s=s, e=e, R=R, c=COST / 1e4 * e / R, st=-1.0, end=min(i + H * 12 - 1, N - 1),
                                i0=i, src=src, half=False, bank=0.0, w=1.0))
        keep = []
        for p in act:
            s, e, R = p["s"], p["e"], p["R"]
            sp = e + s * p["st"] * R
            hs = (BL[i] <= sp) if s > 0 else (BH[i] >= sp)
            res = None
            if hs:
                res = p["bank"] + p["w"] * p["st"]
            elif tp is not None and not p["half"]:
                tpp = e + s * tp * R
                ht = (BH[i] >= tpp) if s > 0 else (BL[i] <= tpp)
                if ht:
                    if half_lock:
                        p["half"] = True; p["bank"] = 0.5 * tp; p["w"] = 0.5; p["st"] = max(p["st"], tp - 1.0)
                    else:
                        res = tp
            if res is None and i >= p["end"]:
                res = p["bank"] + p["w"] * s * (BC[i] - e) / R
            if res is None: keep.append(p)
            else:
                net = res - p["c"]; real += net
                done.append(dict(entry_time=BT[p["i0"]], exit_time=BT[i], net_r=net, source=p["src"], side=s))
        act = keep
        eq.append(real + sum(mtm(p, BC[i]) for p in act))
        if act: i += 1
        else:
            while p_i < len(idx) and idx[p_i] <= i: p_i += 1
            if p_i >= len(idx): break
            i = idx[p_i]
    return pd.DataFrame(done), np.array(eq)


def st(t, eq, months):
    if t.empty: return dict(n=0, ev=np.nan, r_month=0, dd=np.nan, r_dd=np.nan, wr=np.nan)
    dd = float(np.max(np.maximum.accumulate(eq) - eq))
    return dict(n=len(t), ev=t.net_r.mean(), wr=(t.net_r > 0).mean(), r_month=t.net_r.sum() / months, dd=dd,
                r_dd=t.net_r.sum() / dd if dd > 0 else np.inf)


if __name__ == '__main__':
    raw = L.C["raw"][COST].copy()
    segs = {"TRAIN": (raw[raw.entry_time < TE], 48), "OOS": (raw[raw.entry_time >= TE], 19)}
    rows = []
    grid = list(itertools.product([1.0, 1.5, 2.0, 3.0], [24, 48, 72], [None, 3.0, "H3"]))
    for k, H, tp in grid:
        for seg, (rw, m) in segs.items():
            if tp == "H3": t, eq = sim(rw, k, H, 3.0, half_lock=True)
            else: t, eq = sim(rw, k, H, tp)
            d = st(t, eq, m); d.update(stop_atr=k, hold_h=H, exit={None: "TIME", 3.0: "TP3", "H3": "HALF_TP3_LOCK2"}[tp], seg=seg)
            rows.append(d)
    G = pd.DataFrame(rows)
    P = G.pivot_table(index=["stop_atr", "hold_h", "exit"], columns="seg", values=["r_month", "r_dd", "ev", "wr", "dd", "n"])
    P.columns = [f"{a}_{b}" for a, b in P.columns]
    P = P.sort_values("r_dd_TRAIN", ascending=False)
    pd.set_option("display.width", 250)
    print(P[["n_TRAIN", "ev_TRAIN", "r_month_TRAIN", "dd_TRAIN", "r_dd_TRAIN", "n_OOS", "ev_OOS", "r_month_OOS", "dd_OOS", "r_dd_OOS"]].round(2).to_string())
    os.makedirs("out_exec", exist_ok=True); P.to_csv("out_exec/EXEC_GRID.csv")
