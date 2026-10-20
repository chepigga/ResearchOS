#!/usr/bin/env python3
"""
CROWDFADE_ENGINE_A_ABLATION_LAB_004 — does the crowd (L/S z) condition add anything to Engine A?

Engine A (frozen 2026-10-08, LAB122 CORE_CONT + REACCEL):
  fresh |z6h| >= 1 crossing (count_long_short_ratio, crowd WITH the H4 trend)
  + H4 trend phase CONT / REACCEL + price extension >= EXT80 in trend direction + OI4h >= OI70
  -> trade AGAINST the trend/crowd after M5 SWING3 break, SL 1 H1 ATR, TP 3R, 48h, one position.

Data prep and execution are copied verbatim from LAB122 (_lab122_data.py + sim_one below).

Variants (same context thresholds EXT80 / OI70 frozen on TRAIN, same execution):
  FULL          original Engine A trigger (z crossing)            -> must reproduce LAB122
  CTX_ONSET     NO crowd condition: trigger on the first bar the context becomes true
  CTX_ONSET by crowd state at onset (z * h4_trend): >=1 | 0..1 | <0
  Z_AGAINST     z crossing with the crowd AGAINST the trend (crowd already on our side)
  FULL_NO_OI    Engine A without the OI condition
  FULL_NO_EXT   Engine A without the extension condition
Run inside a folder containing BTCUSDT_flow_2021-01-2026-08.csv.zip and btc_5m.zip
(ResearchOS release 'btc').
"""
import os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
NS = {}
exec(open(os.path.join(HERE, "_lab122_data.py")).read(), NS)
b, BT, BO, BH, BL, BC, BA, BZ = (NS[k] for k in ["b", "BT", "BO", "BH", "BL", "BC", "BA", "BZ"])
EXT80, OI70, TRAIN_END, MAX_H = NS["EXT80"], NS["OI70"], NS["TRAIN_END"], NS["MAX_H"]
swing3_entry = NS["swing3_entry"]
COST = 2.81
OUT = os.path.join(HERE, "output"); os.makedirs(OUT, exist_ok=True)


def phase(age, imp_age):            # verbatim from LAB122
    if age <= 3: return 'BIRTH'
    if imp_age <= 2: return 'REACCEL'
    if age <= 12: return 'CONT'
    return 'OTHER'


def sim_one(ei, side, atr, costbps):  # verbatim from LAB122
    entry = float(BO[ei]); dist = atr; sl = entry - side * dist; tp = entry + side * 3.0 * dist
    end = min(ei + MAX_H * 12 - 1, len(b) - 1)
    gross = side * (BC[end] - entry) / dist; xi = end
    for j in range(ei, end + 1):
        hs = (BL[j] <= sl) if side > 0 else (BH[j] >= sl)
        ht = (BH[j] >= tp) if side > 0 else (BL[j] <= tp)
        if hs and ht: gross = -1; xi = j; break
        if hs: gross = -1; xi = j; break
        if ht: gross = 3.0; xi = j; break
    return gross - (costbps / 10000.0) * entry / dist, xi


h4t = b.trend_h4.to_numpy(int); age = b.trend_age.to_numpy(int); imp = b.impulse_age.to_numpy(int)
ext = b.extension.to_numpy(float); oi = b.oi4h.to_numpy(float)
ph = np.array([phase(a, m) for a, m in zip(age, imp)])
phase_ok = np.isin(ph, ["CONT", "REACCEL"])
ext_ok = (h4t != 0) & (np.sign(ext) == h4t) & (np.abs(ext) >= EXT80)
oi_ok = oi >= OI70
ctx = (h4t != 0) & phase_ok & ext_ok & oi_ok
zcross = (np.abs(BZ) >= 1) & (np.abs(np.r_[0, BZ[:-1]]) < 1)
crowd_with = np.sign(BZ) == h4t             # crowd positioned with the old trend
last = len(b) - 1 - MAX_H * 12 - 1


def signals(mask, side_arr):
    out = []
    for i in np.where(mask[:last])[0]:
        if i < 1: continue
        side = int(side_arr[i])
        if side == 0: continue
        ei, _ = swing3_entry(i, side)
        if ei is None: continue
        out.append((i, ei, side))
    return out


def run(sigs, one_pos=True):
    rows, open_until = [], -1
    for i, ei, side in sorted(sigs, key=lambda x: x[1]):
        if one_pos and ei < open_until: continue
        net, xi = sim_one(ei, side, float(BA[i]), COST)
        open_until = xi
        rows.append(dict(t=BT.iloc[i], split="TRAIN" if BT.iloc[i] < TRAIN_END else "OOS",
                         side=side, z=BZ[i], zt=BZ[i] * h4t[i], net=net))
    return pd.DataFrame(rows)


def stats(t):
    if t.empty: return dict(n=0)
    x = t.net.to_numpy()
    rng = np.random.default_rng(5)
    bs = rng.choice(x, (3000, len(x))).mean(1) if len(x) >= 5 else np.array([np.nan])
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    return dict(n=len(x), ev=x.mean(), lo=np.nanpercentile(bs, 2.5), hi=np.nanpercentile(bs, 97.5),
                pf=pos / neg if neg > 0 else np.inf, wr=(x > 0).mean() * 100)


side_against_trend = -h4t
V = {}
V["FULL (Engine A)"] = signals(zcross & crowd_with & ctx, side_against_trend)
onset = ctx & ~np.r_[False, ctx[:-1]]
V["CTX_ONSET (no crowd)"] = signals(onset, side_against_trend)
zt_now = BZ * h4t
V["CTX_ONSET, crowd z≥1 with trend"] = signals(onset & (zt_now >= 1), side_against_trend)
V["CTX_ONSET, crowd z 0..1"] = signals(onset & (zt_now >= 0) & (zt_now < 1), side_against_trend)
V["CTX_ONSET, crowd against trend (z<0)"] = signals(onset & (zt_now < 0), side_against_trend)
V["Z_AGAINST (crowd on our side)"] = signals(zcross & ~crowd_with & ctx, side_against_trend)
V["FULL_NO_OI"] = signals(zcross & crowd_with & (h4t != 0) & phase_ok & ext_ok, side_against_trend)
V["FULL_NO_EXT"] = signals(zcross & crowd_with & (h4t != 0) & phase_ok & oi_ok, side_against_trend)
ctx_any = (h4t != 0) & phase_ok & ext_ok & oi_ok
# all bars in context (overlapping, no one-position) to see raw base edge of context
V["CTX_EVERY_6h (no crowd, sampled)"] = signals(ctx_any & (np.arange(len(b)) % 72 == 0), side_against_trend)

L = []; w = L.append
w("# CROWDFADE_ENGINE_A_ABLATION_LAB_004 — does the crowd condition add to Engine A?\n")
w(f"Frozen thresholds (TRAIN): EXT80 = {EXT80:.2f} H1 ATR, OI70 = {OI70:+.3%}. Cost {COST} bps. "
  f"Execution = LAB122 (SWING3 → next M5 open, SL 1 H1 ATR, TP 3R, 48h, one position). "
  f"TRAIN < {TRAIN_END:%Y-%m-%d} ≤ OOS. Data {BT.iloc[0]:%Y-%m-%d} → {BT.iloc[-1]:%Y-%m-%d}.\n")
w("| variant | split | N | EV R [95% CI] | PF | win% |")
w("|---|---|---|---|---|---|")
res = {}
for name, sg in V.items():
    t = run(sg)
    res[name] = t
    t.to_csv(os.path.join(OUT, "trades_" + "".join(c if c.isalnum() else "_" for c in name)[:40] + ".csv"), index=False)
    for sp in ["ALL", "TRAIN", "OOS"]:
        q = t if sp == "ALL" else t[t.split == sp]
        s = stats(q)
        if s["n"] == 0:
            w(f"| {name} | {sp} | 0 | — | — | — |"); continue
        w(f"| {name} | {sp} | {s['n']} | {s['ev']:+.3f} [{s['lo']:+.3f}…{s['hi']:+.3f}] | {s['pf']:.2f} | {s['wr']:.1f} |")

# overlap: how many Engine A trades would exist anyway in the no-crowd version
full_t = set(res["FULL (Engine A)"].t.dt.floor("D"))
ons_t = set(res["CTX_ONSET (no crowd)"].t.dt.floor("D"))
w(f"\nEngine A trade days also present in CTX_ONSET: {len(full_t & ons_t)} of {len(full_t)}.")
w("\n**Reading:** if CTX_ONSET (no crowd) ≈ FULL, the crowd condition adds little beyond the "
  "price/OI context. If FULL > CTX_ONSET and the crowd-split rows rank z≥1 > 0..1 > z<0, "
  "the crowd extreme carries real information.")
rep = "\n".join(L)
open(os.path.join(OUT, "report.md"), "w").write(rep)
print(rep)
