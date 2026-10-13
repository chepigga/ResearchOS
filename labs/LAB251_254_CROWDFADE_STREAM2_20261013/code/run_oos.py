import os, pickle
os.environ["LAB_CACHE"] = "/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L

OUT = "/home/claude/lab251/out_oos"; os.makedirs(OUT, exist_ok=True)
X = pickle.load(open("/home/claude/lab251/extra.pkl", "rb"))
TE = pd.Timestamp("2025-01-01", tz="UTC")
IDX = {t: i for i, t in enumerate(L.BT)}
TLD = dict(mtr=np.zeros(L.N, int), ci=np.zeros(L.N, int), swl=None, swh=None, catr=None)
BASE_RAW = L.C["raw"]


def rows(df, src, pri):
    out = []
    for r in df.itertuples(index=False):
        t = pd.Timestamp(r.entry_time)
        t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
        if t not in IDX: continue
        out.append(dict(source=src, entry_time=t, entry_i=IDX[t], side=int(r.side), atr=float(r.atr), pri=pri))
    return pd.DataFrame(out)


def key(d): return set(zip(d.entry_i, d.side))


def extra_pool(name, cost):
    base = BASE_RAW[cost][["source", "entry_time", "entry_i", "side", "atr", "pri"]]
    if name == "BASE": return base
    if name == "F1_A_ALLPHASE":
        add = rows(X["a_all"][~X["a_all"].phase.isin(["CONT", "REACCEL"])], "A_X", 5)
    elif name == "F2_B3_BAL":
        add = rows(X["b_bal"], "B3_X", 5)
    elif name == "F3_R48_BAL":
        add = rows(X["r48_bal"], "R48_X", 5)
    elif name == "F4_RESCUE_ALL":
        add = rows(X["res_all"], "EARLY_X", 5)
    else:
        return base
    add = add[~add.set_index(["entry_i", "side"]).index.isin(list(key(base)))]
    return pd.concat([base, add], ignore_index=True).sort_values(["entry_i", "pri"]).reset_index(drop=True)


VARS = {"BASE": 2, "F1_A_ALLPHASE": 2, "F2_B3_BAL": 2, "F3_R48_BAL": 2, "F4_RESCUE_ALL": 2, "F5_MAX3": 3}
res, trades = [], []
for cost in (2.81, 7.5):
    for v, mp in VARS.items():
        pool = extra_pool(v, cost)
        for seg, m in [("TRAIN_2021_24", pool.entry_time < TE), ("OOS_2025_26", pool.entry_time >= TE), ("ALL", pool.entry_time.notna())]:
            raw = pool[m].reset_index(drop=True)
            t, e, sk, ad = L.replay(cost, {}, TLD, raw=raw, max_pos=mp)
            s = L.stats(t, e); s.update(variant=v, cost_bps=cost, segment=seg, addons=ad, pool=len(raw))
            res.append(s)
            if seg == "ALL":
                tt = t.copy(); tt["variant"] = v; tt["cost_bps"] = cost; trades.append(tt)
R = pd.DataFrame(res); T = pd.concat(trades)
R.to_csv(f"{OUT}/SUMMARY.csv", index=False); T.to_csv(f"{OUT}/TRADES.csv", index=False)
cols = ["variant", "segment", "pool", "n", "trades_month", "ev", "pf", "r_month", "mtm_dd_pct", "r_per_dd", "months"]
print(R[R.cost_bps == 7.5][cols].round(3).to_string())
b = T[(T.variant == "BASE") & (T.cost_bps == 7.5)]
print(b.groupby([b.entry_time.dt.year, "source"]).net_r.agg(["count", "mean", "sum"]).round(2).to_string())
print(b.groupby(b.entry_time.dt.year).net_r.agg(["count", "mean", "sum"]).round(2))
