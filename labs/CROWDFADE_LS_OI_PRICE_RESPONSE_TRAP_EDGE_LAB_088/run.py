from pathlib import Path
import json, importlib.util, numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p54=ROOT.parent/'CROWDFADE_CF191G_CAUSAL_REGIME_IMPULSE_MODEL_LAB_054'/'run.py'
sp=importlib.util.spec_from_file_location('l54',p54)
l54=importlib.util.module_from_spec(sp); sp.loader.exec_module(l54)
l43=l54.lab43
l54.DATA=DATA; l54.lab53.DATA=DATA; l43.DATA=DATA

LOOKBACKS=[1,3,5,10]
OUTCOME_H=[15,30,60,120]
OI_FLAT=0.0002
PRICE_FLAT_ATR=0.10
MIN_ABS_Z=1.0

def asof(a,q): return np.searchsorted(a,q,'right')-1

def load():
    flow=l54.load_flow_meta().copy()
    ft,fz=l43.load_flow()
    hist=l43.prep(l43.load_hist(),ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=l43.prep(l43.load_sec(),ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    return flow,{'historical':hist,'forward_2026':fwd}

def level(z):
    a=abs(z)
    if a>=2.5:return 'EXTREME'
    if a>=1.5:return 'ELEVATED'
    return 'NORMAL_1_1P5'

def oi_state(x):
    if not np.isfinite(x):return 'NA'
    if x>OI_FLAT:return 'UP'
    if x<-OI_FLAT:return 'DOWN'
    return 'FLAT'

def price_state(x):
    if not np.isfinite(x):return 'NA'
    if x>PRICE_FLAT_ATR:return 'WITH_CROWD'
    if x<-PRICE_FLAT_ATR:return 'AGAINST_CROWD'
    return 'FLAT'

def crossed_tp(H,L,ep,rd,side,target,end_idx,start_idx):
    if side>0:return bool(np.nanmax(H[start_idx:end_idx])>=ep+target*rd)
    return bool(np.nanmin(L[start_idx:end_idx])<=ep-target*rd)

def event_frame(label,p,flow):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    start,end=int(ts[0]),int(ts[-1])
    f=flow[(flow.ts>=start)&(flow.ts<=end)&(flow.z.abs()>=MIN_ABS_Z)].copy()
    # one observation per unique flow timestamp; source cadence is frozen archive cadence.
    f=f.drop_duplicates('ts').reset_index(drop=True)
    fts=flow.ts.to_numpy(np.int64); ratio=flow.ratio.to_numpy(float); oi=flow.oi.to_numpy(float)
    rows=[]
    for _,r in f.iterrows():
        t=int(r.ts); z=float(r.z); crowd=1 if z>0 else -1; side=-crowd
        j=asof(ts,t); k=asof(dt5,t)
        if j<10 or k<2:continue
        atr=float(A5[k]); ep=float(C[j])
        if not np.isfinite(atr) or atr<=0:continue
        rec={'dataset':label,'ts':t,'z':z,'abs_z':abs(z),'ls_level':level(z),
             'crowd_dir':crowd,'side':side,'ratio':float(r.ratio),'oi':float(r.oi),'atr':atr,'entry':ep}
        fi=asof(fts,t)
        ok=True
        for w in LOOKBACKS:
            fp=asof(fts,t-w*60); jp=asof(ts,t-w*60)
            if fi<0 or fp<0 or jp<0 or oi[fp]<=0:
                ok=False; break
            dls=crowd*(ratio[fi]-ratio[fp])
            doi=oi[fi]/oi[fp]-1.0
            pr=crowd*(ep-float(C[jp]))/atr
            rec[f'dls_{w}m']=dls
            rec[f'doi_{w}m']=doi
            rec[f'price_crowd_{w}m_R']=pr
            rec[f'oi_state_{w}m']=oi_state(doi)
            rec[f'price_state_{w}m']=price_state(pr)
            rec[f'trap_{w}m']=bool(dls>0 and doi>OI_FLAT and pr<=PRICE_FLAT_ATR)
            rec[f'continuation_{w}m']=bool(dls>0 and doi>OI_FLAT and pr>PRICE_FLAT_ATR)
        if not ok:continue
        for h in OUTCOME_H:
            e=np.searchsorted(ts,t+h*60,'right')
            s=j+1
            if e<=s:
                rec[f'mfe_{h}m']=np.nan;rec[f'mae_{h}m']=np.nan
                continue
            if side>0:
                fav=(np.nanmax(H[s:e])-ep)/atr; adv=(ep-np.nanmin(L[s:e]))/atr
            else:
                fav=(ep-np.nanmin(L[s:e]))/atr; adv=(np.nanmax(H[s:e])-ep)/atr
            rec[f'mfe_{h}m']=float(max(0,fav));rec[f'mae_{h}m']=float(max(0,adv))
        # TP success over 120m with SL 1R tie conservatively counted loss if both same minute cannot resolve.
        e=np.searchsorted(ts,t+120*60,'right'); s=j+1
        for target in [1.0,1.5,2.0]:
            hit=False; sl=False
            for q in range(s,e):
                tp=(H[q]>=ep+target*atr) if side>0 else (L[q]<=ep-target*atr)
                st=(L[q]<=ep-atr) if side>0 else (H[q]>=ep+atr)
                if tp or st:
                    hit=bool(tp and not st); sl=bool(st); break
            rec[f'tp{str(target).replace(".","p")}R_120m']=int(hit)
        rows.append(rec)
    return pd.DataFrame(rows)

def summarize_cells(d,w):
    rows=[]
    keys=['dataset','side','ls_level',f'oi_state_{w}m',f'price_state_{w}m']
    for k,g in d.groupby(keys):
        if len(g)<5:continue
        rows.append({'window_min':w,'dataset':k[0],'side':'BUY' if k[1]>0 else 'SELL',
          'ls_level':k[2],'oi_state':k[3],'price_state':k[4],'N':len(g),
          'dls_mean':float(g[f'dls_{w}m'].mean()),'doi_mean':float(g[f'doi_{w}m'].mean()),
          'price_crowd_R_mean':float(g[f'price_crowd_{w}m_R'].mean()),
          'MFE30':float(g.mfe_30m.mean()),'MAE30':float(g.mae_30m.mean()),
          'MFE60':float(g.mfe_60m.mean()),'MAE60':float(g.mae_60m.mean()),
          'MFE120':float(g.mfe_120m.mean()),'MAE120':float(g.mae_120m.mean()),
          'TP1R':float(g.tp1p0R_120m.mean()),'TP1p5R':float(g.tp1p5R_120m.mean()),'TP2R':float(g.tp2p0R_120m.mean())})
    return pd.DataFrame(rows)

def compare_trap(d,w):
    rows=[]
    for ds,g0 in d.groupby('dataset'):
      for sd,g in g0.groupby('side'):
        for name,mask in [('TRAP',g[f'trap_{w}m']),('CONTINUATION',g[f'continuation_{w}m']),('OTHER',~g[f'trap_{w}m']&~g[f'continuation_{w}m'])]:
            h=g[mask]
            if len(h)<5:continue
            rows.append({'dataset':ds,'side':'BUY' if sd>0 else 'SELL','window_min':w,'state':name,'N':len(h),
                         'abs_z_mean':float(h.abs_z.mean()),'MFE60':float(h.mfe_60m.mean()),'MAE60':float(h.mae_60m.mean()),
                         'MFE120':float(h.mfe_120m.mean()),'MAE120':float(h.mae_120m.mean()),
                         'TP1R':float(h.tp1p0R_120m.mean()),'TP1p5R':float(h.tp1p5R_120m.mean()),'TP2R':float(h.tp2p0R_120m.mean())})
    return pd.DataFrame(rows)

def main():
    flow,periods=load()
    parts=[event_frame(label,p,flow) for label,p in periods.items()]
    d=pd.concat(parts,ignore_index=True)
    d.to_csv(OUT/'lab088_events.csv',index=False)

    cells=pd.concat([summarize_cells(d,w) for w in LOOKBACKS],ignore_index=True)
    cmp=pd.concat([compare_trap(d,w) for w in LOOKBACKS],ignore_index=True)
    cells.to_csv(OUT/'matrix_cells.csv',index=False); cmp.to_csv(OUT/'trap_vs_continuation.csv',index=False)

    # Rank horizons by TRAIN trap edge: TP2 improvement vs continuation plus MFE/MAE separation.
    rank=[]
    h=cmp[cmp.dataset=='historical']
    for sd in ['BUY','SELL']:
      for w in LOOKBACKS:
        a=h[(h.side==sd)&(h.window_min==w)&(h.state=='TRAP')]
        b=h[(h.side==sd)&(h.window_min==w)&(h.state=='CONTINUATION')]
        if len(a) and len(b):
            A=a.iloc[0];B=b.iloc[0]
            rank.append({'side':sd,'window_min':w,'N_trap':int(A.N),'N_cont':int(B.N),
                         'delta_MFE60':float(A.MFE60-B.MFE60),'delta_MAE60':float(A.MAE60-B.MAE60),
                         'delta_TP1R':float(A.TP1R-B.TP1R),'delta_TP1p5R':float(A.TP1p5R-B.TP1p5R),
                         'delta_TP2R':float(A.TP2R-B.TP2R)})
    rank=pd.DataFrame(rank)
    rank.to_csv(OUT/'horizon_ranking.csv',index=False)

    summary={'lab':'LAB088_LS_OI_PRICE_RESPONSE_TRAP_EDGE',
      'decision_features':'all LS/dLS/dOI/price-response features are trailing and known at decision timestamp',
      'ls_levels':{'NORMAL_1_1P5':'1.0<=|Z|<1.5','ELEVATED':'1.5<=|Z|<2.5','EXTREME':'|Z|>=2.5'},
      'trap_definition':'directional dLS>0 AND dOI>+0.02% AND crowd-direction price response <= +0.10 ATR',
      'continuation_control':'directional dLS>0 AND dOI>+0.02% AND crowd-direction price response > +0.10 ATR',
      'windows_min':LOOKBACKS,'outcome_horizons_min':OUTCOME_H,'fixed_outcome':'TP 1R/1.5R/2R before -1R within 120m; same-minute ambiguity counted conservatively against TP',
      'N':int(len(d)),'period_counts':d.dataset.value_counts().to_dict(),
      'horizon_ranking_train':rank.to_dict('records'),
      'limitations':['Overlapping flow observations are not independent trades.','2026 Mar-Aug has been reused in prior LABs and is diagnostic, not pristine OOS.','No taker or burst feature included by design.','No production rule promoted from LAB088 alone.']}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB088 — LS × ΔLS × ΔOI × PRICE RESPONSE TRAP EDGE\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## Trap vs continuation\n\n'+cmp.to_markdown(index=False)+'\n\n## Horizon ranking\n\n'+rank.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
