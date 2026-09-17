from pathlib import Path
import zipfile, json, math
import numpy as np
import pandas as pd

ROOT=Path('labs/CROWDFADE_V190_HISTORICAL_REPLAY_001'); DATA=ROOT/'secdata'; OUT=ROOT/'sec_output'; OUT.mkdir(parents=True,exist_ok=True)
OFF=1.50; STOP=1.00; VALID_S=3*3600; PAUSE_S=3*3600; HOLD_S=6*3600
BE_AT=0.50; BE_LOCK=0.15; TRAIL_ARM=2.50; TRAIL_DIST=0.50; ZTH=1.0; HALF_SPREAD_R=0.027


def extract(zname):
    zp=DATA/zname; out=DATA/(zp.stem+'_unz'); out.mkdir(parents=True,exist_ok=True)
    if not list(out.rglob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(out)
    return list(out.rglob('*.csv'))[0]

def stats(r,years):
    r=np.asarray(r,float); eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0.,eq]); dd=(peak[1:]-eq).max() if len(r) else np.nan
    pos=r[r>0]; neg=r[r<0]; pf=pos.sum()/abs(neg.sum()) if len(neg) else np.inf
    se=r.std(ddof=1)/np.sqrt(len(r)) if len(r)>1 else np.nan
    run=best=0
    for x in r: run=run+1 if x<0 else 0; best=max(best,run)
    return dict(N=len(r),WR=float((r>0).mean()),EV=float(r.mean()),t=float(r.mean()/se) if se>0 else np.nan,PF=float(pf),SumR=float(r.sum()),Ryr=float(r.sum()/years),MaxDD_R=float(dd),R_DD=float((r.sum()/years)/dd),MaxLossStreak=best)

def main():
    secf=extract('BTCUSDT_sec.csv.zip'); flowf=extract('BTCUSDT_flow_2021-01-2026-08.csv.zip')
    # Seconds: only fields needed for execution parity. float32 materially reduces RAM.
    s=pd.read_csv(secf,usecols=['ts','o','h','l','c'],dtype={'ts':'int64','o':'float32','h':'float32','l':'float32','c':'float32'})
    s=s.sort_values('ts').drop_duplicates('ts',keep='last').reset_index(drop=True)
    ts=s.ts.to_numpy(np.int64); O=s.o.to_numpy(float); H=s.h.to_numpy(float); L=s.l.to_numpy(float); C=s.c.to_numpy(float)
    # Build M15 ATR from second OHLC. MT5 iATR = SMA; only CLOSED M15 value may be used.
    bucket=(ts//900)*900
    starts=np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1]; ends=np.r_[starts[1:],len(ts)]
    bt=bucket[starts]; bh=np.maximum.reduceat(H,starts); bl=np.minimum.reduceat(L,starts); bc=C[ends-1]
    pc=np.r_[bc[0],bc[:-1]]; tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    atr_available=bt+900
    # Flow z exactly as live code: 72 x 5m, population variance, strict causal availability.
    f=pd.read_csv(flowf,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    f=f[f.sum_open_interest>0].copy(); f['time']=pd.to_datetime(f.create_time,utc=True,errors='coerce'); f=f.dropna(subset=['time']).sort_values('time').drop_duplicates('time',keep='last')
    ft=(f.time.astype('int64')//10**9).to_numpy(np.int64); r=f.count_long_short_ratio.to_numpy(float)
    rr=pd.Series(r); m=rr.rolling(72,min_periods=72).mean(); sd=rr.rolling(72,min_periods=72).std(ddof=0); fz=((rr-m)/sd.replace(0,np.nan)).to_numpy()
    # Decision clock = each exact M5 boundary that exists in seconds data.
    dts=np.arange(((ts[0]+299)//300)*300, ts[-1]+1,300,dtype=np.int64)
    di=np.searchsorted(ts,dts,'left'); ok=(di<len(ts)) & (ts[np.minimum(di,len(ts)-1)]==dts); dts=dts[ok]; di=di[ok]
    # strict causal flow point (< decision timestamp), matching frozen sim causality convention
    fi=np.searchsorted(ft,dts,'left')-1
    ai=np.searchsorted(atr_available,dts,'right')-1
    good=(fi>=0)&(ai>=0)&np.isfinite(fz[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    dts=dts[good]; di=di[good]; fi=fi[good]; ai=ai[good]
    zdec=fz[fi]; adec=atr[ai]
    # Map timestamp -> position in decision arrays for fast next eligible decision.
    rows=[]; n_orders=0; next_allowed_ts=int(dts[0]); k=0
    while k<len(dts):
        t=int(dts[k])
        if t<next_allowed_ts: k+=1; continue
        z=float(zdec[k]); a=float(adec[k]); side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0 or not np.isfinite(a) or a<=0: k+=1; continue
        order_ts=t; order_idx=int(di[k]); n_orders+=1
        entry=float(O[order_idx] + OFF*a if side<0 else O[order_idx]-OFF*a); sl=float(entry+STOP*a if side<0 else entry-STOP*a)
        exp_idx=int(np.searchsorted(ts,order_ts+VALID_S,'left')); exp_idx=min(exp_idx,len(ts))
        segH=H[order_idx:exp_idx]; segL=L[order_idx:exp_idx]
        mask=(segH>=entry) if side<0 else (segL<=entry)
        hits=np.flatnonzero(mask)
        if len(hits)==0:
            next_allowed_ts=order_ts+PAUSE_S; k=np.searchsorted(dts,next_allowed_ts,'left'); continue
        fill_idx=order_idx+int(hits[0]); fill_ts=int(ts[fill_idx])
        mfe=0.; peak=entry; armed=False; kind='time'; exit_idx=fill_idx; exit_px=None
        # Fill second: conservative same-second initial stop priority.
        if (H[fill_idx]>=sl) if side<0 else (L[fill_idx]<=sl):
            exit_px=sl; kind='stop'
        else:
            # timer sees approximately the end-of-second quote; server stop sees whole second H/L
            cp=float(C[fill_idx]); peak=min(entry,cp) if side<0 else max(entry,cp); mfe=max(0.,((entry-peak) if side<0 else (peak-entry))/a)
            hold_end=min(len(ts)-1,int(np.searchsorted(ts,fill_ts+HOLD_S,'left')))
            j=fill_idx+1
            while j<=hold_end:
                if (H[j]>=sl) if side<0 else (L[j]<=sl):
                    exit_px=sl; exit_idx=j; kind='trail' if armed else ('be' if ((side<0 and sl<entry) or (side>0 and sl>entry)) else 'stop'); break
                cp=float(C[j]); prof=(entry-cp) if side<0 else (cp-entry)
                if prof>=BE_AT*a:
                    ns=entry+side*BE_LOCK*a
                    if (ns<sl) if side<0 else (ns>sl): sl=ns
                peak=min(peak,cp) if side<0 else max(peak,cp); mfe=max(mfe,((entry-peak) if side<0 else (peak-entry))/a)
                if mfe>=TRAIL_ARM:
                    armed=True; ns=peak+TRAIL_DIST*a if side<0 else peak-TRAIL_DIST*a
                    if (ns<sl) if side<0 else (ns>sl): sl=ns
                # Signal source can only change on 5m points; evaluate at exact 5m clock.
                if ts[j]%300==0:
                    q=np.searchsorted(ft,ts[j],'left')-1
                    if q>=0 and np.isfinite(fz[q]) and ((fz[q]<=-ZTH) if side<0 else (fz[q]>=ZTH)):
                        exit_px=cp; exit_idx=j; kind='signal'; break
                if ts[j]>=fill_ts+HOLD_S:
                    exit_px=cp; exit_idx=j; kind='time'; break
                j+=1
            if exit_px is None:
                exit_idx=min(hold_end,len(ts)-1); exit_px=float(C[exit_idx]); kind='time'
        gross=side*(exit_px-entry)/a; net=gross-HALF_SPREAD_R
        rows.append(dict(order_ts=order_ts,fill_ts=fill_ts,exit_ts=int(ts[exit_idx]),side='SELL' if side<0 else 'BUY',z=z,atr=a,entry=entry,exit=exit_px,gross_R=gross,R=net,kind=kind,mfe=mfe,fill_lag_s=fill_ts-order_ts,hold_s=int(ts[exit_idx])-fill_ts,toxic=mfe<0.5))
        next_allowed_ts=max(order_ts+PAUSE_S,int(ts[exit_idx])+1)
        k=np.searchsorted(dts,next_allowed_ts,'left')
    tr=pd.DataFrame(rows); tr.to_csv(OUT/'trades_sec_live_parity.csv',index=False)
    years=(ts[-1]-ts[0])/(365.25*86400)
    summ=stats(tr.R.values,years); summ.update(dict(orders=n_orders,fills=len(tr),fill_rate=len(tr)/n_orders,toxic_rate=float(tr.toxic.mean()),median_fill_lag_min=float(tr.fill_lag_s.median()/60),years=years,exit_kinds=tr.kind.value_counts().to_dict(),gross=stats(tr.gross_R.values,years),full_spread_cost=stats((tr.gross_R-0.054).values,years)))
    (OUT/'summary_sec_live_parity.json').write_text(json.dumps(summ,indent=2,default=float))
    print(json.dumps(summ,indent=2,default=float))
if __name__=='__main__':main()
