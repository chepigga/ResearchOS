import pickle, json, time, os
import numpy as np, pandas as pd
import lab251 as L

OUT = "/home/claude/lab251/out"; os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(251)
REPS = 1000
RAW = L.C["raw"]
TRAIN_END = pd.Timestamp(L.C["TRAIN_END"])


def tl_for(mode):
    p = f"/home/claude/lab251/tl_{mode}.pkl"
    if os.path.exists(p): return pickle.load(open(p, "rb"))
    tl = L.build_tl(mode); pickle.dump(tl, open(p, "wb")); return tl


def variant_inputs(name, tl, cost):
    raw = RAW[cost]
    lo, hi = int(raw.entry_i.min()), int(raw.entry_i.max())
    if name == "BASE": return dict(cfg={})
    if name == "R1_FILTER":
        veto = {rid for rid, r in enumerate(raw.itertuples(index=False))
                if r.source in ("B3_HIGH", "R48_HIGH") and int(r.side) == -int(tl["mtr"][int(r.entry_i)])}
        return dict(cfg={}, veto=veto)
    if name == "R2_TRAIL": return dict(cfg={"trail": True, "runner_h": 96})
    if name == "R2_CTRL96": return dict(cfg={"runner_h": 96})
    if name == "R3_ADDON":
        ev = tl["ev_add"].copy(); ev[:lo] = 0; ev[hi + 1:] = 0
        return dict(cfg={}, add_events=ev)
    if name == "R4_ENGINE_T":
        return dict(cfg={}, extra_sigs=[(i, s, "T") for i, s in tl["T"] if lo <= i <= hi])
    raise ValueError(name)


def run(name, tl, cost, **over):
    kw = variant_inputs(name, tl, cost); kw.update(over)
    t, e, sk, ad = L.replay(cost, kw.pop("cfg"), tl, **kw)
    return t, e, sk, ad


VARS = ["BASE", "R1_FILTER", "R2_TRAIL", "R2_CTRL96", "R3_ADDON", "R4_ENGINE_T"]


def main_block(mode):
    tl = tl_for(mode)
    rows, trades, yrs = [], [], []
    for cost in (2.81, 7.5):
        for v in VARS:
            t, e, sk, ad = run(v, tl, cost)
            s = L.stats(t, e); s.update(variant=v, cost_bps=cost, server=mode, skipped=sk, addons=ad)
            rows.append(s)
            tt = t.copy(); tt["variant"] = v; tt["cost_bps"] = cost; tt["server"] = mode; trades.append(tt)
            for y, g in t.groupby(t.exit_time.dt.year):
                yrs.append(dict(variant=v, cost_bps=cost, server=mode, year=int(y), n=len(g), net_r=g.net_r.sum()))
    return tl, pd.DataFrame(rows), pd.concat(trades), pd.DataFrame(yrs)


t0 = time.time()
tlS, S_srv, T_srv, Y_srv = main_block("SERVER")
tlU, S_utc, T_utc, Y_utc = main_block("UTC")
S = pd.concat([S_srv, S_utc]); T = pd.concat([T_srv, T_utc]); Y = pd.concat([Y_srv, Y_utc])
S.to_csv(f"{OUT}/SUMMARY.csv", index=False); T.to_csv(f"{OUT}/TRADES_ALL.csv", index=False); Y.to_csv(f"{OUT}/YEARLY.csv", index=False)
print("main done", f"{time.time()-t0:.0f}s", flush=True)

# ---------------- bootstrap (monthly diff vs BASE), stress, SERVER
cost = 7.5
months = pd.period_range("2021-01", "2024-12", freq="M").strftime("%Y-%m")
def mser(v, server="SERVER"):
    t = T[(T.variant == v) & (T.cost_bps == cost) & (T.server == server)]
    return L.monthly(t).reindex(months, fill_value=0.0)
base_m = mser("BASE")
boot = []
for v in VARS[1:]:
    d = (mser(v) - base_m).to_numpy()
    bs = np.array([rng.choice(d, len(d), replace=True).mean() for _ in range(5000)])
    boot.append(dict(variant=v, diff_r_month=d.mean(), ci_lo=np.percentile(bs, 2.5), ci_hi=np.percentile(bs, 97.5),
                     p_le0=float((bs <= 0).mean())))
B = pd.DataFrame(boot); B.to_csv(f"{OUT}/BOOTSTRAP.csv", index=False)

# ---------------- placebos (stress, SERVER)
tl = tlS; raw = RAW[cost]; lo, hi = int(raw.entry_i.min()), int(raw.entry_i.max())
def rmo(t, e): return L.stats(t, e)["r_month"]
plac = {}
# R1: random veto of same count among B3/R48
r1 = variant_inputs("R1_FILTER", tl, cost)["veto"]
pool = [rid for rid, r in enumerate(raw.itertuples(index=False)) if r.source in ("B3_HIGH", "R48_HIGH")]
vals = []
for _ in range(REPS):
    veto = set(rng.choice(pool, len(r1), replace=False).tolist())
    t, e, *_ = L.replay(cost, {}, tl, veto=veto); vals.append(rmo(t, e))
plac["R1_FILTER"] = np.array(vals)
# R3: random add-on events at H1 boundaries, same count per year, sides from TL events
ci = tl["ci"]; bound = np.where(np.r_[False, ci[1:] != ci[:-1]])[0]
ev = variant_inputs("R3_ADDON", tl, cost)["add_events"]
years = L.BT.year.to_numpy()
vals = []
for _ in range(REPS):
    pe = np.zeros(L.N, int)
    for y in np.unique(years[ev != 0]):
        idx_y = np.where((ev != 0) & (years == y))[0]
        cand = bound[(years[bound] == y) & (bound >= lo) & (bound <= hi)]
        pick = rng.choice(cand, len(idx_y), replace=False)
        pe[pick] = rng.choice(ev[idx_y], len(idx_y), replace=True)
    t, e, *_ = L.replay(cost, {}, tl, add_events=pe); vals.append(rmo(t, e))
plac["R3_ADDON"] = np.array(vals)
# R4: random T entries, same count per year, sides from T
Ts = [(i, s) for i, s in tl["T"] if lo <= i <= hi]
Ty = np.array([years[i] for i, _ in Ts]); Tside = np.array([s for _, s in Ts])
vals = []
for _ in range(REPS):
    ex = []
    for y in np.unique(Ty):
        nY = int((Ty == y).sum())
        cand = np.where(years == y)[0]; cand = cand[(cand >= lo) & (cand <= hi)]
        for i, s in zip(rng.choice(cand, nY, replace=False), rng.choice(Tside[Ty == y], nY, replace=True)):
            ex.append((int(i), int(s), "T"))
    t, e, *_ = L.replay(cost, {}, tl, extra_sigs=ex); vals.append(rmo(t, e))
plac["R4_ENGINE_T"] = np.array(vals)
P = []
for v, arr in plac.items():
    real = float(S_srv[(S_srv.variant == v) & (S_srv.cost_bps == cost)].r_month.iloc[0])
    P.append(dict(variant=v, real_r_month=real, plac_mean=arr.mean(), plac_p95=np.percentile(arr, 95),
                  pct_rank=float((arr < real).mean())))
P = pd.DataFrame(P); P.to_csv(f"{OUT}/PLACEBO.csv", index=False)
print("placebo done", f"{time.time()-t0:.0f}s", flush=True)
print(S.round(3).to_string()); print(B.round(3).to_string()); print(P.round(3).to_string())
