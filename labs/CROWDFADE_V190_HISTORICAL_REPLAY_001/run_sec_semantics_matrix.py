from pathlib import Path
import zipfile, json, math
import numpy as np
import pandas as pd

ROOT=Path('labs/CROWDFADE_V190_HISTORICAL_REPLAY_001'); DATA=ROOT/'secdata'; OUT=ROOT/'semantics_output'; OUT.mkdir(parents=True,exist_ok=True)
OFF=1.50; STOP=1.00; VALID_S=10800; PAUSE_S=10800; HOLD_S=21600
BE_AT=0.50; BE_LOCK=0.15; TRAIL_ARM=2.50; TRAIL_DIST=0.50; ZTH=1.0; COST=0.027

def extract(zname):
    zp=DATA/zname; out=DATA/(zp.stem+'_unz'); out.mkdir(parents=True,exist_ok=True)
    if not list(out.rglob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(out)
    return list(out.rglob('*.csv'))[0]

def stats(r,years):
    r=np.asarray(r,float)
    if not len(r): return {'N':0}
    eq=np.cumsum(r); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float((pk[1:]-eq).max())
    w=r[r>0]; l=r[r<0]; pf=float(w.sum()/abs(l.sum())) if len(l) else float('inf')
    se=r.std(ddof=1)/np.sqrt(len(r)) if len(r)>1 else np.nan
    return dict(N=int(len(r)),WR=float((r>0).mean()),EV=float(r.mean()),t=float(r.mean()/se) if se>0 else np.nan,PF=pf,SumR=float(r.sum()),Ryr=float(r.sum()/years),MaxDD_R=dd,R_DD=float((r.sum()/years)/dd) if dd>0 else np.nan)

def prepare():
    secf=extract('BTCUSDT_sec.csv.zip'); flowf=extract('BTCUSDT_flow_2021-01-2026-08.csv.zip')
    s=pd.read_csv(secf,usecols=['ts','o','h','l','c'],dtype={'ts':'int64','o':'float32','h':'float32','l':'float32','c':'float32'}).sort_values('ts').drop_duplicates('ts').reset_index(drop=True)
    ts=s.ts.to_numpy(np.int64); O=s.o.to_numpy(float); H=s.h.to_numpy(float); L=s.l.to_numpy(float); C=s.c.to_numpy(float)
    bucket=(ts//900)*900; starts=np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1]; ends=np.r_[starts[1:],len(ts)]
    bt=bucket[starts]; bh=np.maximum.reduceat(H,starts); bl=np.minimum.reduceat(L,starts); bc=C[ends-1]
    pc=np.r_[bc[0],bc[:-1]]; tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy(); atr_avail=bt+900
    f=pd.read_csv(flowf,usecols=['create_time','sum_open_interest','count_long_short_ratio']); f=f[f.sum_open_interest>0].copy()
    f['time']=pd.to_datetime(f.create_time,utc=True,errors='coerce'); f=f.dropna(subset=['time']).sort_values('time').drop_duplicates('time')
    ft=f.time.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64); r=f.count_long_short_ratio.to_numpy(float)
    rr=pd.Series(r); mm=rr.rolling(72,min_periods=72).mean(); sd=rr.rolling(72,min_periods=72).std(ddof=0); z=((rr-mm)/sd.replace(0,np.nan)).to_numpy()
    dts=np.arange(((ts[0]+299)//300)*300,ts[-1]+1,300,dtype=np.int64); di=np.searchsorted(ts,dts,'left'); ok=(di<len(ts))&(ts[np.minimum(di,len(ts)-1)]==dts); dts=dts[ok]; di=di[ok]
    fi=np.searchsorted(ft,dts,'left')-1; ai=np.searchsorted(atr_avail,dts,'right')-1; good=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    return ts,O,H,L,C,ft,z,dts[good],di[good],z[fi[good]],atr[ai[good]]

def run_position(ts,H,L,C,ft,z,fill_idx,entry,sl,side,a):
    fill_ts=int(ts[fill_idx]); mfe=0.; peak=entry; armed=False; exit_idx=fill_idx; exit_px=None; kind='time'
    if (H[fill_idx]>=sl) if side<0 else (L[fill_idx]<=sl):
        return fill_idx,sl,'stop',0.0
    cp=float(C[fill_idx]); peak=min(entry,cp) if side<0 else max(entry,cp); mfe=max(0.,((entry-peak) if side<0 else (peak-entry))/a)
    end=min(len(ts)-1,int(np.searchsorted(ts,fill_ts+HOLD_S,'left')))
    for j in range(fill_idx+1,end+1):
        if (H[j]>=sl) if side<0 else (L[j]<=sl):
            return j,sl,'trail' if armed else ('be' if ((side<0 and sl<entry) or (side>0 and sl>entry)) else 'stop'),mfe
        cp=float(C[j]); prof=(entry-cp) if side<0 else (cp-entry)
        if prof>=BE_AT*a:
            ns=entry+side*BE_LOCK*a
            if (ns<sl) if side<0 else (ns>sl): sl=ns
        peak=min(peak,cp) if side<0 else max(peak,cp); mfe=max(mfe,((entry-peak) if side<0 else (peak-entry))/a)
        if mfe>=TRAIL_ARM:
            armed=True; ns=peak+TRAIL_DIST*a if side<0 else peak-TRAIL_DIST*a
            if (ns<sl) if side<0 else (ns>sl): sl=ns
        if ts[j]%300==0:
            q=np.searchsorted(ft,ts[j],'left')-1
            if q>=0 and np.isfinite(z[q]) and ((z[q]<=-ZTH) if side<0 else (z[q]>=ZTH)):
                return j,cp,'signal',mfe
        if ts[j]>=fill_ts+HOLD_S: return j,cp,'time',mfe
    return end,float(C[end]),'time',mfe

def fill_search(ts,H,L,start_idx,order_ts,entry,side):
    end=min(len(ts),int(np.searchsorted(ts,order_ts+VALID_S,'left'))); st=min(start_idx+1,end)
    if st>=end: return None
    mask=(H[st:end]>=entry) if side<0 else (L[st:end]<=entry); hit=np.flatnonzero(mask)
    return st+int(hit[0]) if len(hit) else None

def simulate(mode,arr):
    ts,O,H,L,C,ft,z,dts,di,zdec,adec=arr; rows=[]; orders=0
    years=(ts[-1]-ts[0])/(365.25*86400)
    if mode=='live_send_anchor_single':
        next_t=int(dts[0]); k=0
        while k<len(dts):
            t=int(dts[k]);
            if t<next_t: k+=1; continue
            zz=float(zdec[k]); a=float(adec[k]); side=-1 if zz>=1 else (1 if zz<=-1 else 0)
            if side==0: k+=1; continue
            orders+=1; oi=int(di[k]); entry=float(O[oi]+OFF*a if side<0 else O[oi]-OFF*a); sl=entry-side*STOP*a
            fill=fill_search(ts,H,L,oi,t,entry,side)
            if fill is None:
                next_t=t+PAUSE_S; k=np.searchsorted(dts,next_t,'left'); continue
            ex,px,kind,mfe=run_position(ts,H,L,C,ft,z,fill,entry,sl,side,a); R=side*(px-entry)/a-COST
            rows.append((t,int(ts[fill]),int(ts[ex]),R,kind,mfe)); next_t=max(t+PAUSE_S,int(ts[ex])+1); k=np.searchsorted(dts,next_t,'left')
    elif mode in ('research_filled_signal_anchor_overlap','research_fill_anchor_overlap'):
        last=-10**18; k=0
        while k<len(dts):
            t=int(dts[k]);
            if t-last<PAUSE_S: k+=1; continue
            zz=float(zdec[k]); a=float(adec[k]); side=-1 if zz>=1 else (1 if zz<=-1 else 0)
            if side==0: k+=1; continue
            orders+=1; oi=int(di[k]); entry=float(O[oi]+OFF*a if side<0 else O[oi]-OFF*a); sl=entry-side*STOP*a
            fill=fill_search(ts,H,L,oi,t,entry,side)
            if fill is None: k+=1; continue
            ex,px,kind,mfe=run_position(ts,H,L,C,ft,z,fill,entry,sl,side,a); R=side*(px-entry)/a-COST
            rows.append((t,int(ts[fill]),int(ts[ex]),R,kind,mfe)); last=t if mode=='research_filled_signal_anchor_overlap' else int(ts[fill]); k+=1
    d=pd.DataFrame(rows,columns=['order_ts','fill_ts','exit_ts','R','kind','mfe']); d.to_csv(OUT/f'trades_{mode}.csv',index=False)
    s=stats(d.R.values,years); s.update({'orders':orders,'fills':len(d),'fill_rate':len(d)/orders if orders else np.nan,'toxic_rate':float((d.mfe<0.5).mean()) if len(d) else np.nan,'exit_kinds':d.kind.value_counts().to_dict() if len(d) else {}})
    return s

def main():
    arr=prepare(); out={}
    for mode in ['live_send_anchor_single','research_filled_signal_anchor_overlap','research_fill_anchor_overlap']:
        out[mode]=simulate(mode,arr); print(mode,json.dumps(out[mode],indent=2))
    (OUT/'summary_semantics_matrix.json').write_text(json.dumps(out,indent=2,default=float))
if __name__=='__main__': main()
