#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB = 'XAU_H1_CONTEXT_ALIGNED_MAE_FIRST_PASSAGE_STOP_PATH_LAB_005'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LAB002_PATH = ROOT / 'labs' / 'CROSS_MARKET_CAUSAL_CONTEXT_CONTINUOUS_SCORE_INTERACTION_LAB_002' / 'run_lab.py'
THRESH = 0.55
BOOT_N = 5000
SEED = 2026091005
YEARS = ['2023','2024','2025','2026']
HORIZONS = [10,30,120]
FP_LEVELS = [0.5,1.0,1.5]
STOP_ATR = [1.0,1.5,2.0]


def load_lab002():
    spec = importlib.util.spec_from_file_location('lab002_lab005', LAB002_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def h1_signal_features(m1: pd.DataFrame) -> pd.DataFrame:
    g = m1.set_index('time').resample('1h', origin='epoch', label='left', closed='left').agg(
        open=('open','first'), high=('high','max'), low=('low','min'), close=('close','last')
    ).dropna().reset_index()
    pc = g.close.shift(1)
    tr = pd.concat([g.high-g.low, (g.high-pc).abs(), (g.low-pc).abs()], axis=1).max(axis=1)
    g['signal_atr'] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    g['signal_close'] = g.close
    return g[['time','signal_close','signal_atr']].rename(columns={'time':'signal_time'})


def prepare_subset(x: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    sig_col = 'time' if 'time' in x.columns else ('time_x' if 'time_x' in x.columns else None)
    if sig_col is None:
        raise KeyError(f'No signal-time column in XAU join: {list(x.columns)}')
    z = x.rename(columns={sig_col:'signal_time'}).copy()
    z['signal_time'] = pd.to_datetime(z.signal_time, errors='coerce')
    z['available_event_time'] = pd.to_datetime(z.available_event_time, errors='coerce')
    z = z.merge(h1_signal_features(m1), on='signal_time', how='left', validate='many_to_one')
    z['is_high'] = pd.to_numeric(z.context_score, errors='coerce') > THRESH
    z = z[
        z.tf.eq('H1') & z.is_high & z.bias_compat_label.isin(['ALIGNED','OPPOSED'])
    ].copy()
    z['signal_atr'] = pd.to_numeric(z.signal_atr, errors='coerce')
    z['signal_close'] = pd.to_numeric(z.signal_close, errors='coerce')
    z['dir'] = pd.to_numeric(z.dir, errors='coerce')
    z['excess'] = pd.to_numeric(z.excess, errors='coerce')
    z['R'] = pd.to_numeric(z.R, errors='coerce')
    z = z.dropna(subset=['available_event_time','signal_atr','signal_close','dir','excess'])
    z = z[(z.signal_atr > 0) & z.dir.isin([-1,1])].copy()
    z['risk_unit'] = 1.5 * z.signal_atr
    z['year'] = z.available_event_time.dt.year.astype(str)
    return z.reset_index(drop=True)


def first_idx(mask: np.ndarray):
    q = np.flatnonzero(mask)
    return int(q[0]) if len(q) else None


def event_path(row, T, H, L, C):
    start = np.datetime64(pd.Timestamp(row.available_event_time).to_datetime64())
    end = start + np.timedelta64(120, 'h')
    i0 = int(np.searchsorted(T, start, side='left'))
    i1 = int(np.searchsorted(T, end, side='right'))
    if i0 >= len(T) or i1 <= i0:
        return None
    t = T[i0:i1]; hi = H[i0:i1]; lo = L[i0:i1]; cl = C[i0:i1]
    entry = float(row.signal_close); ru = float(row.risk_unit); atr = float(row.signal_atr); d = int(row.dir)
    if not np.isfinite(entry) or not np.isfinite(ru) or ru <= 0:
        return None
    if d == 1:
        fav = (hi-entry)/ru
        worst = (lo-entry)/ru
    else:
        fav = (entry-lo)/ru
        worst = (entry-hi)/ru
    close_r = d*(cl-entry)/ru
    elapsed_h = (t-start) / np.timedelta64(1,'h')

    rec = {}
    # MAE/MFE + terminal close on common clocks.
    for h in HORIZONS:
        m = elapsed_h <= h
        if not np.any(m):
            rec[f'mfe_{h}h'] = np.nan; rec[f'mae_{h}h'] = np.nan; rec[f'term_{h}h_r'] = np.nan
        else:
            rec[f'mfe_{h}h'] = float(np.nanmax(fav[m]))
            rec[f'mae_{h}h'] = float(np.nanmin(worst[m]))
            rec[f'term_{h}h_r'] = float(close_r[np.flatnonzero(m)[-1]])

    # Symmetric first-passage diagnostics.
    for h in HORIZONS:
        mh = elapsed_h <= h
        f = fav[mh]; w = worst[mh]
        for k in FP_LEVELS:
            ip = first_idx(f >= k); im = first_idx(w <= -k)
            if ip is None and im is None:
                state = 'NONE'
            elif ip is not None and im is None:
                state = 'PLUS_FIRST'
            elif ip is None and im is not None:
                state = 'MINUS_FIRST'
            elif ip == im:
                state = 'AMBIGUOUS'
            elif ip < im:
                state = 'PLUS_FIRST'
            else:
                state = 'MINUS_FIRST'
            rec[f'fp_{k:g}_{h}h'] = state

    # Current 1R (=1.5ATR) stop first, then late recovery by 120h.
    ip1 = first_idx(fav >= 1.0); im1 = first_idx(worst <= -1.0)
    ambiguous = ip1 is not None and im1 is not None and ip1 == im1
    stop_first = (im1 is not None) and (ip1 is None or im1 < ip1)
    rec['current_fp_ambiguous'] = bool(ambiguous)
    rec['current_stop_first'] = bool(stop_first)
    rec['stop_first_recover_plus1_120h'] = bool(stop_first and ip1 is not None and ip1 > im1)
    rec['stop_first_recover_zero_120h'] = False
    rec['hours_stop_to_zero'] = np.nan
    rec['hours_stop_to_plus1'] = np.nan
    if stop_first:
        # Subsequent bars only, avoiding same-minute path ambiguity.
        after = np.arange(len(fav)) > im1
        iz_rel = first_idx(after & (fav >= 0.0))
        if iz_rel is not None:
            rec['stop_first_recover_zero_120h'] = True
            rec['hours_stop_to_zero'] = float((t[iz_rel]-t[im1]) / np.timedelta64(1,'h'))
        if ip1 is not None and ip1 > im1:
            rec['hours_stop_to_plus1'] = float((t[ip1]-t[im1]) / np.timedelta64(1,'h'))

    # Fixed-R:R stop-width ablation. Same-bar ambiguity is STOP first.
    for sm in STOP_ATR:
        stop_dist = sm * atr
        tp_dist = 1.5 * stop_dist
        if d == 1:
            stop_hit = lo <= entry-stop_dist
            tp_hit = hi >= entry+tp_dist
        else:
            stop_hit = hi >= entry+stop_dist
            tp_hit = lo <= entry-tp_dist
        isx = first_idx(stop_hit); itp = first_idx(tp_hit)
        same = isx is not None and itp is not None and isx == itp
        if isx is not None and (itp is None or isx <= itp):
            pnl = -1.0; state = 'SL'; exit_idx = isx
        elif itp is not None:
            pnl = 1.5; state = 'TP'; exit_idx = itp
        else:
            pnl = float(d*(cl[-1]-entry)/stop_dist); state = 'TIME'; exit_idx = len(cl)-1
        rec[f'sl_{sm:g}atr_state'] = state
        rec[f'sl_{sm:g}atr_pnl_r'] = pnl
        rec[f'sl_{sm:g}atr_samebar'] = bool(same)
        rec[f'sl_{sm:g}atr_hours'] = float(elapsed_h[exit_idx])
    return rec


def build_paths(z: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    T = m1.time.to_numpy(dtype='datetime64[ns]')
    H = m1.high.to_numpy(float); L = m1.low.to_numpy(float); C = m1.close.to_numpy(float)
    rows=[]
    for _, r in z.iterrows():
        q = event_path(r, T, H, L, C)
        if q is None:
            continue
        base = {
            'available_event_time': r.available_event_time,
            'signal_time': r.signal_time,
            'year': r.year,
            'compat': r.bias_compat_label,
            'dir': int(r.dir),
            'excess': float(r.excess),
            'R': float(r.R),
            'signal_close': float(r.signal_close),
            'signal_atr': float(r.signal_atr),
        }
        base.update(q); rows.append(base)
    return pd.DataFrame(rows)


def mean_by_compat(d: pd.DataFrame, col: str):
    out={}
    for c in ['ALIGNED','OPPOSED']:
        v=pd.to_numeric(d.loc[d.compat.eq(c),col],errors='coerce').dropna()
        out[c]={'n':int(len(v)),'mean':float(v.mean()) if len(v) else np.nan,'median':float(v.median()) if len(v) else np.nan}
    a=out['ALIGNED']['mean']; o=out['OPPOSED']['mean']
    out['premium']=float(a-o) if np.isfinite(a) and np.isfinite(o) else np.nan
    return out


def recovery_stats(d: pd.DataFrame):
    q=d[~d.current_fp_ambiguous].copy()
    rows=[]
    for c in ['ALIGNED','OPPOSED']:
        g=q[q.compat.eq(c)]
        sf=g.current_stop_first.astype(bool)
        r0=g.stop_first_recover_zero_120h.astype(bool)
        rp=g.stop_first_recover_plus1_120h.astype(bool)
        sf_n=int(sf.sum())
        rows.append({
            'compat':c,'n':int(len(g)),'stop_first_n':sf_n,'stop_first_rate':float(sf.mean()) if len(g) else np.nan,
            'recover_zero_n':int(r0.sum()),'recover_zero_unconditional':float(r0.mean()) if len(g) else np.nan,
            'recover_zero_given_stop':float(r0.sum()/sf_n) if sf_n else np.nan,
            'recover_plus1_n':int(rp.sum()),'recover_plus1_unconditional':float(rp.mean()) if len(g) else np.nan,
            'recover_plus1_given_stop':float(rp.sum()/sf_n) if sf_n else np.nan,
            'median_hours_stop_to_zero':float(pd.to_numeric(g.hours_stop_to_zero,errors='coerce').median()),
            'median_hours_stop_to_plus1':float(pd.to_numeric(g.hours_stop_to_plus1,errors='coerce').median()),
        })
    return pd.DataFrame(rows)


def recovery_delta(d: pd.DataFrame):
    q=d[~d.current_fp_ambiguous].copy()
    vals={}
    for c in ['ALIGNED','OPPOSED']:
        g=q[q.compat.eq(c)]
        vals[c]=float(g.stop_first_recover_plus1_120h.astype(float).mean()) if len(g) else np.nan
    return vals['ALIGNED']-vals['OPPOSED'], vals


def weekly_bootstrap_recovery(d: pd.DataFrame):
    q=d[~d.current_fp_ambiguous].copy()
    t=pd.to_datetime(q.available_event_time,errors='coerce',utc=True)
    q=q.loc[t.notna()].copy(); t=t.loc[t.notna()]
    q['_week']=t.dt.to_period('W-SUN').astype(str).values
    rows=[]
    for _,g in q.groupby('_week',sort=True):
        rec=[]
        for c in ['ALIGNED','OPPOSED']:
            h=g[g.compat.eq(c)]; rec.extend([len(h),int(h.stop_first_recover_plus1_120h.sum())])
        rows.append(rec)
    a=np.asarray(rows,float); rng=np.random.default_rng(SEED); vals=np.full(BOOT_N,np.nan)
    for k in range(BOOT_N):
        s=a[rng.integers(0,len(a),size=len(a))].sum(axis=0)
        an,asuc,on,osuc=s
        if an>0 and on>0: vals[k]=asuc/an-osuc/on
    vals=vals[np.isfinite(vals)]
    return {'weeks':int(len(a)),'draws':BOOT_N,
            'ci_lo':float(np.quantile(vals,.025)),'ci_hi':float(np.quantile(vals,.975)),
            'p_positive':float(np.mean(vals>0))}


def year_recovery(d: pd.DataFrame):
    rows=[]
    for y in YEARS:
        g=d[d.year.eq(y) & ~d.current_fp_ambiguous]
        a=g[g.compat.eq('ALIGNED')]; o=g[g.compat.eq('OPPOSED')]
        ar=float(a.stop_first_recover_plus1_120h.mean()) if len(a) else np.nan
        orr=float(o.stop_first_recover_plus1_120h.mean()) if len(o) else np.nan
        eligible=len(a)>=100 and len(o)>=100
        delta=ar-orr if np.isfinite(ar) and np.isfinite(orr) else np.nan
        rows.append({'year':y,'aligned_n':len(a),'opposed_n':len(o),'aligned_rate':ar,'opposed_rate':orr,
                     'delta_recovery':delta,'eligible':eligible,'positive':bool(eligible and delta>0)})
    return pd.DataFrame(rows)


def loyo_recovery(d: pd.DataFrame, eligible_years):
    rows=[]
    for y in eligible_years:
        g=d[~d.year.eq(y)]
        delta, rates=recovery_delta(g)
        rows.append({'left_out':y,'delta_recovery':delta,'aligned_rate':rates['ALIGNED'],'opposed_rate':rates['OPPOSED'],
                     'positive':bool(np.isfinite(delta) and delta>0)})
    return pd.DataFrame(rows)


def first_passage_table(d: pd.DataFrame):
    rows=[]
    for h in HORIZONS:
        for k in FP_LEVELS:
            col=f'fp_{k:g}_{h}h'
            for c in ['ALIGNED','OPPOSED']:
                g=d[d.compat.eq(c)]; vc=g[col].value_counts()
                n=len(g); ordered=n-int(vc.get('AMBIGUOUS',0))
                rows.append({'horizon_h':h,'level_r':k,'compat':c,'n':n,'ordered_n':ordered,
                             'plus_first_rate':float(vc.get('PLUS_FIRST',0)/ordered) if ordered else np.nan,
                             'minus_first_rate':float(vc.get('MINUS_FIRST',0)/ordered) if ordered else np.nan,
                             'none_rate':float(vc.get('NONE',0)/ordered) if ordered else np.nan,
                             'ambiguous_n':int(vc.get('AMBIGUOUS',0))})
    return pd.DataFrame(rows)


def path_summary(d: pd.DataFrame):
    rows=[]
    for h in HORIZONS:
        for c in ['ALIGNED','OPPOSED']:
            g=d[d.compat.eq(c)]
            rows.append({'horizon_h':h,'compat':c,'n':len(g),
                         'mfe_mean':float(g[f'mfe_{h}h'].mean()),'mfe_median':float(g[f'mfe_{h}h'].median()),
                         'mae_mean':float(g[f'mae_{h}h'].mean()),'mae_median':float(g[f'mae_{h}h'].median()),
                         'terminal_mean_r':float(g[f'term_{h}h_r'].mean()),'terminal_median_r':float(g[f'term_{h}h_r'].median())})
    return pd.DataFrame(rows)


def stop_ablation(d: pd.DataFrame):
    rows=[]
    for sm in STOP_ATR:
        col=f'sl_{sm:g}atr_pnl_r'; state=f'sl_{sm:g}atr_state'; same=f'sl_{sm:g}atr_samebar'
        means={}
        for c in ['ALIGNED','OPPOSED']:
            g=d[d.compat.eq(c)]; v=pd.to_numeric(g[col],errors='coerce').dropna(); means[c]=float(v.mean())
            rows.append({'sl_atr':sm,'compat':c,'n':len(v),'mean_pnl_r':means[c],
                         'tp_rate':float((g[state]=='TP').mean()),'sl_rate':float((g[state]=='SL').mean()),
                         'time_rate':float((g[state]=='TIME').mean()),'samebar_n':int(g[same].sum())})
        rows.append({'sl_atr':sm,'compat':'PREMIUM','n':np.nan,'mean_pnl_r':means['ALIGNED']-means['OPPOSED'],
                     'tp_rate':np.nan,'sl_rate':np.nan,'time_rate':np.nan,'samebar_n':np.nan})
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--xau-pool',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    lab002=load_lab002(); router=lab002.load_router_module()
    x,meta=lab002.build_xau_join(Path(a.xau_m1),Path(a.xau_pool),router)
    if len(x)!=263405: raise RuntimeError(f'Frozen XAU parity failed: {len(x)} != 263405')
    m1=lab002.read_xau_native(Path(a.xau_m1))
    z=prepare_subset(x,m1)
    if not ((z.compat.eq('ALIGNED').sum()==1195) and (z.compat.eq('OPPOSED').sum()==966)):
        raise RuntimeError(f'Frozen H1 HIGH parity failed A={z.compat.eq("ALIGNED").sum()} O={z.compat.eq("OPPOSED").sum()} expected 1195/966')
    p=build_paths(z,m1)
    if len(p)!=len(z): raise RuntimeError(f'Path coverage failure {len(p)} != {len(z)}')

    ps=path_summary(p); ps.to_csv(out/'path_summary.csv',index=False)
    fp=first_passage_table(p); fp.to_csv(out/'first_passage.csv',index=False)
    rs=recovery_stats(p); rs.to_csv(out/'recovery_summary.csv',index=False)
    yd=year_recovery(p); yd.to_csv(out/'year_recovery.csv',index=False)
    eligible=yd.loc[yd.eligible,'year'].astype(str).tolist()
    lo=loyo_recovery(p,eligible); lo.to_csv(out/'leave_one_year_out.csv',index=False)
    sa=stop_ablation(p); sa.to_csv(out/'stop_ablation.csv',index=False)

    delta,rates=recovery_delta(p); boot=weekly_bootstrap_recovery(p)
    terminal=mean_by_compat(p,'term_120h_r')
    realized=mean_by_compat(p,'excess')
    sy=yd[yd.eligible]
    gates={
        'S1_delta_recovery_gt_zero':bool(np.isfinite(delta) and delta>0),
        'S2_boot_ci_lo_gt_zero':bool(np.isfinite(boot['ci_lo']) and boot['ci_lo']>0),
        'S3_terminal_120h_premium_gt_zero':bool(np.isfinite(terminal['premium']) and terminal['premium']>0),
        'S4_realized_frozen_premium_lt_zero':bool(np.isfinite(realized['premium']) and realized['premium']<0),
        'S5_year_3of4_positive':bool(len(sy)==4 and int(sy.positive.sum())>=3),
        'S6_loyo_3of4_positive':bool(len(lo)==4 and int(lo.positive.sum())>=3),
    }
    if all(gates.values()): verdict='H1_STOP_PATH_MISMATCH_SUPPORTED_DISCOVERY_ONLY'
    elif gates['S1_delta_recovery_gt_zero'] and gates['S3_terminal_120h_premium_gt_zero'] and gates['S4_realized_frozen_premium_lt_zero']:
        verdict='MIXED_H1_STOP_PATH_MISMATCH_EVIDENCE'
    else: verdict='H1_STOP_PATH_MISMATCH_NOT_SUPPORTED'

    summary={'lab':LAB,'status':'REUSED_HISTORY_PREREGISTERED_PATH_DIAGNOSTIC','verdict':verdict,
             'n_h1_high':int(len(p)),'aligned_n':int((p.compat=='ALIGNED').sum()),'opposed_n':int((p.compat=='OPPOSED').sum()),
             'primary_delta_recovery':float(delta),'recovery_rates':rates,'bootstrap':boot,
             'terminal_120h':terminal,'realized_frozen_excess':realized,'gates':gates,
             'eligible_years':int(len(sy)),'positive_years':int(sy.positive.sum()),
             'loyo_runs':int(len(lo)),'loyo_positive':int(lo.positive.sum()),'xau_meta':meta,'promotion_authorized':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    rr=rs.set_index('compat')
    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','',
           '> Reused-history causal path diagnostic. No stop change, filter, sizing, or production promotion is authorized.','',
           '## Frozen H1 HIGH subset','',f'- ALIGNED: {summary["aligned_n"]}',f'- OPPOSED: {summary["opposed_n"]}',
           f'- Frozen realized excess premium A-O: **{realized["premium"]:+.5f}R**',
           f'- 120h terminal directional premium A-O: **{terminal["premium"]:+.5f}R**','',
           '## Primary STOP-FIRST -> late +1R recovery','',
           f'- ALIGNED rate: **{rates["ALIGNED"]:.4%}**',f'- OPPOSED rate: **{rates["OPPOSED"]:.4%}**',
           f'- Delta recovery: **{delta:+.4%}**',f'- Weekly bootstrap 95% CI: **[{boot["ci_lo"]:+.4%}, {boot["ci_hi"]:+.4%}]**, P>0={boot["p_positive"]:.3f}',
           f'- Years positive: {int(sy.positive.sum())}/{len(sy)}; LOYO positive: {int(lo.positive.sum())}/{len(lo)}','',
           '## Recovery conditional on current stop-first','',
           f'- ALIGNED stop-first rate: {rr.loc["ALIGNED","stop_first_rate"]:.3%}; recover-to-zero given stop: {rr.loc["ALIGNED","recover_zero_given_stop"]:.3%}; recover-to-+1R given stop: {rr.loc["ALIGNED","recover_plus1_given_stop"]:.3%}',
           f'- OPPOSED stop-first rate: {rr.loc["OPPOSED","stop_first_rate"]:.3%}; recover-to-zero given stop: {rr.loc["OPPOSED","recover_zero_given_stop"]:.3%}; recover-to-+1R given stop: {rr.loc["OPPOSED","recover_plus1_given_stop"]:.3%}','',
           '## Gates']
    for k,v in gates.items(): lines.append(f'- {"PASS" if v else "FAIL"} — `{k}`')
    lines += ['', 'See CSV outputs for MAE/MFE, symmetric first-passage, year/LOYO transfer, recovery timing, and fixed 1:1.5 stop-width ablations.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print((out/'REPORT.md').read_text()); print(json.dumps(summary,indent=2,default=str))


if __name__=='__main__': main()
