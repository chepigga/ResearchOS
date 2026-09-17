from pathlib import Path
import zipfile, json, math
import numpy as np
import pandas as pd

ROOT=Path('labs/CROWDFADE_CONFIRMATION_ENTRY_REFINEMENT_LAB_004'); DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
ZTH=2.50; CONF=0.50; STOP=1.50; EXITZ=0.75; TTL=3*3600; HOLD=6*3600
BE_AT=0.50; BE_LOCK=0.15; TRAIL_ARM=2.50; TRAIL_DIST=0.50
PAUSE_ATR=1.0; MAX_DAY=3
MODES=['A0_TOUCH','A1_CONFIRM_M5_CLOSE','A2_NEXT_M5_CLOSE']
VETO_LOOK=[2,3,4]; VETO_THR=[0.75,1.00,1.25]
T0=int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()); T1=int(pd.Timestamp('2026-09-01',tz='UTC').timestamp())

def extract(name):
    z=DATA/name; d=DATA/(z.stem+'_unz'); d.mkdir(parents=True,exist_ok=True)
    if not list(d.rglob('*.csv')):
        with zipfile.ZipFile(z) as q:q.extractall(d)
    return list(d.rglob('*.csv'))[0]

def stats(r):
    r=np.asarray(r,float)
    if len(r)==0:return {'N':0}
    eq=np.cumsum(r); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float((pk[1:]-eq).max())
    pos=r[r>0].sum(); neg=abs(r[r<0].sum()); pf=float(pos/neg) if neg>0 else float('inf')
    se=r.std(ddof=1)/math.sqrt(len(r)) if len(r)>1 else np.nan
    return {'N':len(r),'WR':float((r>0).mean()),'EV':float(r.mean()),'PF':pf,'SumR':float(r.sum()),'MaxDD_R':dd,'t':float(r.mean()/se) if se>0 else np.nan}

def prep():
    sf=extract('BTCUSDT_sec.csv.zip'); ff=extract('BTCUSDT_flow_2021-01-2026-08.csv.zip')
    s=pd.read_csv(sf,usecols=['ts','o','h','l','c'],dtype={'ts':'int64','o':'float32','h':'float32','l':'float32','c':'float32'}).sort_values('ts').drop_duplicates('ts')
    s=s[(s.ts>=T0-86400)&(s.ts<T1+86400)].reset_index(drop=True)
    ts=s.ts.to_numpy(np.int64); O=s.o.to_numpy(float); H=s.h.to_numpy(float); L=s.l.to_numpy(float); C=s.c.to_numpy(float)
    # M15 ATR
    b15=(ts//900)*900; st15=np.r_[0,np.flatnonzero(b15[1:]!=b15[:-1])+1]; en15=np.r_[st15[1:],len(ts)]
    bt15=b15[st15]; hi=np.maximum.reduceat(H,st15); lo=np.minimum.reduceat(L,st15); cl=C[en15-1]; prev=np.r_[cl[0],cl[:-1]]
    tr=np.maximum(hi-lo,np.maximum(abs(hi-prev),abs(lo-prev))); atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy(); atr_av=bt15+900
    # M5 closes for timing/impulse
    b5=(ts//300)*300; st5=np.r_[0,np.flatnonzero(b5[1:]!=b5[:-1])+1]; en5=np.r_[st5[1:],len(ts)]
    bt5=b5[st5]; c5=C[en5-1]
    # flow z
    f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio']); f=f[f.sum_open_interest>0].copy()
    f['time']=pd.to_datetime(f.create_time,utc=True,errors='coerce'); f=f.dropna(subset=['time']).sort_values('time').drop_duplicates('time')
    ft=f.time.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64); rr=pd.Series(f.count_long_short_ratio.to_numpy(float))
    z=((rr-rr.rolling(72,min_periods=72).mean())/rr.rolling(72,min_periods=72).std(ddof=0).replace(0,np.nan)).to_numpy()
    # decision times exact M5 opens
    dts=np.arange(((max(ts[0],T0)+299)//300)*300,T1,300,dtype=np.int64); di=np.searchsorted(ts,dts,'left'); ok=(di<len(ts))&(ts[np.minimum(di,len(ts)-1)]==dts); dts=dts[ok]; di=di[ok]
    fi=np.searchsorted(ft,dts,'left')-1; ai=np.searchsorted(atr_av,dts,'right')-1; good=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    return ts,O,H,L,C,ft,z,bt5,c5,dts[good],di[good],z[fi[good]],atr[ai[good]]

def flowz(ft,z,t):
    q=np.searchsorted(ft,t,'left')-1
    return float(z[q]) if q>=0 and np.isfinite(z[q]) else np.nan

def manage(arr, ei, entry, side, a):
    ts,O,H,L,C,ft,z,bt5,c5,*_=arr; sl=entry-side*STOP*a; peak=entry; armed=False; mfe=0.; mae=0.; end=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD,'left'))
    for j in range(ei+1,end+1):
        # path diagnostics before exit
        fav=((entry-L[j]) if side<0 else (H[j]-entry))/a; adv=((H[j]-entry) if side<0 else (entry-L[j]))/a
        mfe=max(mfe,fav); mae=max(mae,adv)
        if (H[j]>=sl if side<0 else L[j]<=sl):
            return j,float(sl),'stop' if not armed else 'trail',mfe,mae
        cp=float(C[j]); prof=((entry-cp) if side<0 else (cp-entry))/a
        if prof>=BE_AT:
            ns=entry+side*BE_LOCK*a
            if (ns<sl if side<0 else ns>sl): sl=ns
        peak=min(peak,cp) if side<0 else max(peak,cp)
        if mfe>=TRAIL_ARM:
            armed=True; ns=peak+TRAIL_DIST*a if side<0 else peak-TRAIL_DIST*a
            if (ns<sl if side<0 else ns>sl): sl=ns
        if ts[j]%300==0:
            zz=flowz(ft,z,int(ts[j]))
            if np.isfinite(zz) and ((zz<=-EXITZ) if side<0 else (zz>=EXITZ)):
                return j,cp,'exitz',mfe,mae
        if ts[j]>=ts[ei]+HOLD:return j,cp,'time',mfe,mae
    return end,float(C[end]),'time',mfe,mae

def entry_index(arr, ci, level, side, mode):
    ts,O,H,L,C,ft,z,bt5,c5,*_=arr; t=int(ts[ci]); b=(t//300)*300
    if mode=='A0_TOUCH': return ci
    target=(b+300-1) if mode=='A1_CONFIRM_M5_CLOSE' else (b+600-1)
    ei=np.searchsorted(ts,target,'right')-1
    if ei<=ci or ei>=len(ts): return None
    px=float(C[ei]); held=(px<=level) if side<0 else (px>=level)
    return int(ei) if held else None

def impulse_at(arr, ei, side, a, look):
    ts,O,H,L,C,ft,z,bt5,c5,*_=arr; t=int(ts[ei]); last=np.searchsorted(bt5,(t//300)*300,'left')-1
    if last-look<0:return np.nan
    ret=(c5[last]-c5[last-look])/a
    # adverse/crowd direction: up for SHORT, down for LONG
    return float(-side*ret)

def simulate(arr, mode, veto=None):
    ts,O,H,L,C,ft,z,bt5,c5,dts,di,zdec,adec=arr; rows=[]; k=0; last_entry=None; last_a=None; day=None; dayn=0; cap_skip=0; pause_skip=0
    while k<len(dts):
        t=int(dts[k]); zz=float(zdec[k]); a=float(adec[k]); side=-1 if zz>=ZTH else (1 if zz<=-ZTH else 0)
        if side==0:k+=1;continue
        thisday=t//86400
        if day!=thisday: day=thisday; dayn=0
        if dayn>=MAX_DAY: cap_skip+=1;k+=1;continue
        sigi=int(di[k]); sig=float(O[sigi])
        if last_entry is not None and abs(sig-last_entry)<PAUSE_ATR*last_a: pause_skip+=1;k+=1;continue
        level=sig+side*CONF*a; end=min(len(ts),np.searchsorted(ts,t+TTL,'left')); st=sigi+1
        if st>=end:k+=1;continue
        mask=(L[st:end]<=level) if side<0 else (H[st:end]>=level); h=np.flatnonzero(mask)
        if not len(h):k+=1;continue
        ci=st+int(h[0]); ei=entry_index(arr,ci,level,side,mode)
        if ei is None:k+=1;continue
        imps={n:impulse_at(arr,ei,side,a,n) for n in [2,3,4]}
        if veto is not None:
            look,thr=veto
            if np.isfinite(imps[look]) and imps[look]>thr:k+=1;continue
        entry=float(C[ei]); ex,px,kind,mfe,mae=manage(arr,ei,entry,side,a); R=side*(px-entry)/(STOP*a)
        rows.append({'signal_ts':t,'confirm_ts':int(ts[ci]),'entry_ts':int(ts[ei]),'exit_ts':int(ts[ex]),'side':side,'z':zz,'atr':a,'entry':entry,'exit':px,'R':R,'reason':kind,'mfe_atr':mfe,'mae_atr':mae,'imp2':imps[2],'imp3':imps[3],'imp4':imps[4],'delay_s':int(ts[ei])-int(ts[ci])})
        dayn+=1; last_entry=entry; last_a=a; k=np.searchsorted(dts,int(ts[ex])+1,'left')
    return pd.DataFrame(rows),{'cap_skips':cap_skip,'atr_pause_skips':pause_skip}

def summarize(d):
    out={'all':stats(d.R.values),'stop_rate':float((d.reason=='stop').mean()) if len(d) else np.nan,'median_delay_s':float(d.delay_s.median()) if len(d) else np.nan,'months':{}}
    for m in range(3,9):
        a=int(pd.Timestamp(f'2026-{m:02d}-01',tz='UTC').timestamp()); b=int((pd.Timestamp(f'2026-{m:02d}-01',tz='UTC')+pd.offsets.MonthBegin()).timestamp())
        q=d[(d.signal_ts>=a)&(d.signal_ts<b)]; out['months'][f'2026-{m:02d}']=stats(q.R.values)
    return out

def main():
    arr=prep(); res={'defaults':{'Z':ZTH,'ConfirmATR':CONF,'StopATR':STOP,'ExitZ':EXITZ,'PauseMode':'ATR','PauseATR':PAUSE_ATR,'MaxTradesPerDay':MAX_DAY}}
    timing={}; dfs={}
    for mode in MODES:
        d,diag=simulate(arr,mode); dfs[mode]=d; d.to_csv(OUT/f'trades_{mode}.csv',index=False); timing[mode]={'summary':summarize(d),'diagnostics':diag}
    res['timing']=timing
    # choose timing by simple preregistered ordering: must beat A0 EV, DD, stop-rate relative -10%, retain >=60%; otherwise A0
    base=timing['A0_TOUCH']['summary']; best='A0_TOUCH'; candidates=[]
    for mode in MODES[1:]:
        s=timing[mode]['summary']; pos=sum(1 for x in s['months'].values() if x.get('EV',-9)>0); retain=s['all']['N']/max(1,base['all']['N'])
        ok=s['all']['EV']>=base['all']['EV'] and s['all']['MaxDD_R']<=base['all']['MaxDD_R'] and s['stop_rate']<=0.9*base['stop_rate'] and retain>=0.60 and pos>=4
        candidates.append((ok,s['all']['EV'],mode))
    good=[x for x in candidates if x[0]]
    if good: best=max(good)[2]
    res['selected_timing']=best
    veto={}
    for look in VETO_LOOK:
        for thr in VETO_THR:
            d,diag=simulate(arr,best,(look,thr)); key=f'{best}_veto_{look}bar_{thr:.2f}'; d.to_csv(OUT/f'trades_{key}.csv',index=False); veto[key]={'summary':summarize(d),'diagnostics':diag}
    res['veto']=veto
    (OUT/'summary.json').write_text(json.dumps(res,indent=2,default=float))
    print(json.dumps(res,indent=2,default=float))
if __name__=='__main__':main()
