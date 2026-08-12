#!/usr/bin/env python3
"""Fast historical v283 default stateless opportunity scanner.

This reproduces the existing U01 shadow logic with precomputed timeframe features and
adds the actual need_ai gate to pass_stateless. It intentionally remains a SHADOW,
not MT5 parity, because stateful position/cooldown/delivery memory is not replayed.
Default v283 facts used here:
- InpUseLiquidityFilter=false => SmartMock Priority A/D unreachable and liq-reversal false.
- InpUsePriorityE=false => Priority E unreachable.
- SmartMock reachable entry families: Priority B CHoCH+BOS and Priority C OB/FVG+micro-break.
"""
import argparse, zipfile, json
from pathlib import Path
import numpy as np, pandas as pd
SPREAD=27.5


def load_zip(p):
    fs=[]
    with zipfile.ZipFile(p) as z:
        for n in z.namelist():
            if n.lower().endswith('.csv'):
                with z.open(n) as f: fs.append(pd.read_csv(f))
    x=pd.concat(fs,ignore_index=True)
    if pd.api.types.is_numeric_dtype(x.time):
        v=pd.to_numeric(x.time,errors='coerce'); med=v.median(); unit='us' if med>1e14 else ('ms' if med>1e11 else 's')
        x['time']=pd.to_datetime(v,unit=unit,utc=True).dt.tz_localize(None)
    else:
        x['time']=pd.to_datetime(x.time,format='%Y.%m.%d %H:%M',errors='coerce',utc=True).dt.tz_localize(None)
    for c in ['open','high','low','close']: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.dropna(subset=['time','open','high','low','close']).sort_values('time').drop_duplicates('time').reset_index(drop=True)

def rs(x,rule):
    z=x.set_index('time').resample(rule,label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    z['close_time']=z.time+pd.Timedelta(rule); return z

def wilder(s,p): return s.ewm(alpha=1/p,adjust=False,min_periods=p).mean()
def atr(df,p=14):
    pc=df.close.shift(1); tr=pd.concat([df.high-df.low,(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1); return wilder(tr,p)
def ema(s,p): return s.ewm(span=p,adjust=False,min_periods=p).mean()

def pivots(df,strength=2):
    H=df.high.to_numpy(float); L=df.low.to_numpy(float); ph=np.zeros(len(df),bool); pl=np.zeros(len(df),bool)
    for j in range(strength,len(df)-strength):
        c=H[j]; ok=True
        for k in range(1,strength+1):
            if H[j+k]>=c or H[j-k]>c: ok=False; break
        ph[j]=ok
        c=L[j]; ok=True
        for k in range(1,strength+1):
            if L[j+k]<=c or L[j-k]<c: ok=False; break
        pl[j]=ok
    return ph,pl

def precompute_bos(df,lookback):
    H=df.high.to_numpy(float); L=df.low.to_numpy(float); C=df.close.to_numpy(float); ph,pl=pivots(df,2); out=np.zeros(len(df),np.int8)
    for n in range(10,len(df)):
        sh=sl=np.nan
        for shift in range(3,min(lookback,n-2)+1):
            j=n-(shift-1)
            if j<2: break
            if not np.isfinite(sh) and ph[j]: sh=H[j]
            if not np.isfinite(sl) and pl[j]: sl=L[j]
            if np.isfinite(sh) and np.isfinite(sl): break
        if np.isfinite(sh) and C[n]>sh: out[n]=1
        elif np.isfinite(sl) and C[n]<sl: out[n]=-1
    return out,ph,pl

def precompute_choch(df,atr_source):
    H=df.high.to_numpy(float);L=df.low.to_numpy(float);C=df.close.to_numpy(float);ph,pl=pivots(df,2);out=np.zeros(len(df),np.int8)
    for n in range(10,len(df)):
        av=float(atr_source[n]) if n<len(atr_source) else np.nan
        if not np.isfinite(av) or av<=0: continue
        sh=[];sl=[]
        for shift in range(3,min(20,n-2)+1):
            j=n-(shift-1)
            if ph[j] and len(sh)<2: sh.append(H[j])
            if pl[j] and len(sl)<2: sl.append(L[j])
            if len(sh)>=2 and len(sl)>=2: break
        buf=av*.05
        if len(sh)>=2 and len(sl)>=1 and sh[0]<sh[1] and C[n]<sl[0]-buf: out[n]=-1
        elif len(sl)>=2 and len(sh)>=1 and sl[0]>sl[1] and C[n]>sh[0]+buf: out[n]=1
    return out

def latest_fractals_m1(m1):
    H=m1.high.to_numpy(float);L=m1.low.to_numpy(float);n=len(m1);ph=np.zeros(n,bool);pl=np.zeros(n,bool)
    for j in range(1,n-1):
        ph[j]=H[j]>H[j-1] and H[j]>H[j+1]; pl[j]=L[j]<L[j-1] and L[j]<L[j+1]
    last_hi=np.full(n,np.nan);last_lo=np.full(n,np.nan);hi_idx=lo_idx=-10**9
    for i in range(n):
        j=i-1 # newest pivot confirmable at current closed index i
        if j>=1:
            if ph[j]: hi_idx=j
            if pl[j]: lo_idx=j
        if i-hi_idx<=18: last_hi[i]=H[hi_idx]
        if i-lo_idx<=18: last_lo[i]=L[lo_idx]
    return last_hi,last_lo

def fvgob_arrays(h1,atrh):
    O=h1.open.to_numpy(float);H=h1.high.to_numpy(float);L=h1.low.to_numpy(float);C=h1.close.to_numpy(float);n=len(h1)
    bf=np.zeros(n,np.int8);sf=np.zeros(n,np.int8);bo=np.zeros(n,np.int8);so=np.zeros(n,np.int8)
    for k in range(10,n):
        av=atrh[k]
        if not np.isfinite(av): continue
        mg=av*.18
        for right in range(1,19):
            jr=k-(right-1);jl=k-(right+1)
            if jl<0:break
            if not bf[k] and L[jr]-H[jl]>=mg:
                bf[k]=1;fL,fH=H[jl],L[jr]
                for q in range(jl,jl-7,-1):
                    if q<0:break
                    if C[q]<O[q]:
                        obL,obH=min(O[q],C[q]),max(O[q],C[q]);bo[k]=int(max(fL,obL)<=min(fH,obH));break
            if not sf[k] and L[jl]-H[jr]>=mg:
                sf[k]=1;fL,fH=H[jr],L[jl]
                for q in range(jl,jl-7,-1):
                    if q<0:break
                    if C[q]>O[q]:
                        obL,obH=min(O[q],C[q]),max(O[q],C[q]);so[k]=int(max(fL,obL)<=min(fH,obH));break
            if bf[k] and sf[k]:break
    return bf,sf,bo,so

def compression_arrays(m15,atr15):
    H=m15.high.to_numpy(float);L=m15.low.to_numpy(float);n=len(m15);cb=np.zeros(n,np.int8);cs=np.zeros(n,np.int8)
    for k in range(12,n):
        tol=max(10,min(150,atr15[k]*.15));hs=np.array([H[k-i] for i in range(12)]);ls=np.array([L[k-i] for i in range(12)]);ch=hs.max();cl=ls.min();eqh=(abs(hs-ch)<=tol).sum();eql=(abs(ls-cl)<=tol).sum();hl=lh=0
        for shift in range(12,2,-1):
            ja=k-(shift-1);jb=k-(shift-2)
            if L[jb]>L[ja]:hl+=1
            if H[jb]<H[ja]:lh+=1
        cb[k]=int(eqh>=3 and hl>=3);cs[k]=int(eql>=3 and lh>=3)
    return cb,cs

def extended_arrays(h1,h4,d1,atrh):
    H1=h1.high.to_numpy(float);L1=h1.low.to_numpy(float);C1=h1.close.to_numpy(float);O1=h1.open.to_numpy(float);H4=h4.high.to_numpy(float);L4=h4.low.to_numpy(float)
    h4ct=h4.close_time.to_numpy('datetime64[ns]');dct=d1.close_time.to_numpy('datetime64[ns]');t=h1.close_time.to_numpy('datetime64[ns]');n=len(h1)
    vals={k:np.zeros(n,np.int8) for k in ['bH4','sH4','bPDL','sPDH','bW','sW']}
    for i in range(8,n):
        n4=int(np.searchsorted(h4ct,t[i],'right')-1);nd=int(np.searchsorted(dct,t[i],'right')-1);av=atrh[i]
        if min(n4,nd)<3 or not np.isfinite(av):continue
        tol=av*.25;lows=[L4[n4-q] for q in range(3)];highs=[H4[n4-q] for q in range(3)]
        eql=abs(lows[0]-lows[1])<tol or abs(lows[1]-lows[2])<tol;lvl=min(lows[0],lows[1]);vals['bH4'][i]=int(eql and L1[i]<lvl and C1[i]>lvl)
        eqh=abs(highs[0]-highs[1])<tol or abs(highs[1]-highs[2])<tol;lvl=max(highs[0],highs[1]);vals['sH4'][i]=int(eqh and H1[i]>lvl and C1[i]<lvl)
        pdl=d1.low.iloc[nd];pdh=d1.high.iloc[nd];vals['bPDL'][i]=int(L1[i]<pdl and C1[i]>pdl);vals['sPDH'][i]=int(H1[i]>pdh and C1[i]<pdh)
        rlo=np.min(L1[i-7:i]);rhi=np.max(H1[i-7:i]);br=H1[i]-L1[i]
        if br>0:
            vals['bW'][i]=int(L1[i]<rlo and C1[i]>rlo and (min(C1[i],O1[i])-L1[i])/br>=.40)
            vals['sW'][i]=int(H1[i]>rhi and C1[i]<rhi and (H1[i]-max(C1[i],O1[i]))/br>=.40)
    return vals

def htf_bias_at(d,b4,b1,nd,n4,n1,h4ema,h4close):
    D=d[nd] if nd>=0 else 0;H=b4[n4] if n4>=0 else 0;one=b1[n1] if n1>=0 else 0
    if D==-1 and H==-1:return -1
    if D==1 and H==1:return 1
    if D==-1 and H==0:return -1
    if D==1 and H==0:return 1
    if D==0 and H==-1:return -1
    if D==0 and H==1:return 1
    if D==-1 and H==1:return -1 if one==-1 else 0
    if D==1 and H==-1:return 1 if one==1 else 0
    if D==0 and H==0 and one!=0:return int(one)
    if n4>=0 and np.isfinite(h4ema[n4]):return 1 if h4close[n4]>h4ema[n4] else -1
    return 0

def smartmock(pre,htf,b1,b15,dist,imp,c1,c15,panic,bullov,bearov,mup,mdn):
    if pre<40 or panic!=0 or abs(dist)>3 or imp>2 or htf==0:return ('WAIT',50,'WaitSetup')
    ps=8 if pre>=70 else 4 if pre>=50 else -10
    if htf==1 and c1==1 and b1==1:
        c=65+(8 if mup else 0)+(6 if bullov else 0)+(-8 if dist>2 else 0)+ps
        if c>=68:return ('BUY',min(c,95),'CHoCHBull')
    if htf==-1 and c1==-1 and b1==-1:
        c=65+(8 if mdn else 0)+(6 if bearov else 0)+(-8 if dist<-2 else 0)+ps
        if c>=68:return ('SELL',min(c,95),'CHoCHBear')
    if htf==1 and bullov and mup:
        c=62+ps+(5 if b1==1 else 0)+(5 if dist<-.5 else 0)
        if c>=80:return ('BUY',min(c,95),'OBFVGBull')
    if htf==-1 and bearov and mdn:
        c=62+ps+(5 if b1==-1 else 0)+(5 if dist>.5 else 0)
        if c>=80:return ('SELL',min(c,95),'OBFVGBear')
    return ('WAIT',50,'WaitSetup')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--btc-1m',required=True);ap.add_argument('--outdir',required=True);a=ap.parse_args();out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True)
    m1=load_zip(a.btc_1m);m1=m1[m1.time>=pd.Timestamp('2023-06-01')].reset_index(drop=True);m5=rs(m1,'5min');m15=rs(m1,'15min');h1=rs(m1,'1h');h4=rs(m1,'4h');d1=rs(m1,'1D')
    for df in [m15,h1,h4,d1]:df['atr14']=atr(df)
    h1['ema50']=ema(h1.close,50);h4['ema50']=ema(h4.close,50);d1['ema50']=ema(d1.close,50)
    b1,_,_=precompute_bos(h1,60);b15,_,_=precompute_bos(m15,60);b4,_,_=precompute_bos(h4,50);bd,_,_=precompute_bos(d1,30)
    c1=precompute_choch(h1,h1.atr14.to_numpy(float))
    # v283 DetectCHoCH_BTC(M15) uses H1 ATR buffer, not M15 ATR. Map current H1 ATR to each M15 bar close.
    h1ct=h1.close_time.to_numpy('datetime64[ns]');m15ct=m15.close_time.to_numpy('datetime64[ns]');h1av=h1.atr14.to_numpy(float);av15=np.full(len(m15),np.nan)
    for i,t in enumerate(m15ct):
        q=int(np.searchsorted(h1ct,t,'right')-1)
        if q>=0:av15[i]=h1av[q]
    c15=precompute_choch(m15,av15)
    bf,sf,bo,so=fvgob_arrays(h1,h1av);cb,cs=compression_arrays(m15,m15.atr14.to_numpy(float));ex=extended_arrays(h1,h4,d1,h1av);lfh,lfl=latest_fractals_m1(m1)
    # array aliases and causal index maps
    ct1=h1.close_time.to_numpy('datetime64[ns]');ct4=h4.close_time.to_numpy('datetime64[ns]');ctd=d1.close_time.to_numpy('datetime64[ns]');ct15=m15.close_time.to_numpy('datetime64[ns]');tm1=m1.time.to_numpy('datetime64[ns]');tm5=m5.time.to_numpy('datetime64[ns]')
    H5=m5.high.to_numpy(float);L5=m5.low.to_numpy(float);rollH=pd.Series(H5).rolling(5).max().to_numpy();rollL=pd.Series(L5).rolling(5).min().to_numpy()
    h1ema=h1.ema50.to_numpy(float);h4ema=h4.ema50.to_numpy(float);h4close=h4.close.to_numpy(float);h1close=h1.close.to_numpy(float);d1close=d1.close.to_numpy(float);d1ema=d1.ema50.to_numpy(float);d1atr=d1.atr14.to_numpy(float)
    m15O=m15.open.to_numpy(float);m15C=m15.close.to_numpy(float);m15H=m15.high.to_numpy(float);m15L=m15.low.to_numpy(float);atr15=m15.atr14.to_numpy(float)
    rows=[]
    for im,r in enumerate(m5.itertuples(index=False)):
        t=r.time
        if t<pd.Timestamp('2024-01-01'):continue
        nt=np.datetime64(t);n1=int(np.searchsorted(ct1,nt,'right')-1);n4=int(np.searchsorted(ct4,nt,'right')-1);nd=int(np.searchsorted(ctd,nt,'right')-1);n15=int(np.searchsorted(ct15,nt,'right')-1);nm1=int(np.searchsorted(tm1,nt,'left')-1)
        if min(n1,n4,nd,n15,nm1)<60:continue
        ah=h1av[n1];a15=atr15[n15]
        if not np.isfinite(ah) or ah<=0 or not np.isfinite(a15) or a15<=0:continue
        ht=htf_bias_at(bd,b4,b1,nd,n4,n1,h4ema,h4close);live=float(r.open);ask=live+SPREAD;bid=live;mup=np.isfinite(lfh[nm1]) and ask>lfh[nm1];mdn=np.isfinite(lfl[nm1]) and bid<lfl[nm1]
        e1=h1ema[n1];slope=(e1-h1ema[n1-1])/ah;dist=(bid-e1)/ah;imp=abs(h1close[n1]-h1close[n1-1])/ah
        o=m15O[n15];cc=m15C[n15];hi=m15H[n15];lo=m15L[n15];body=abs(cc-o);rng=hi-lo;panic=0
        if rng>0 and body/a15>=1.8:
            if cc<o and (cc-lo)/rng<=.20:panic=-1
            elif cc>o and (hi-cc)/rng<=.20:panic=1
        score=0
        if ht!=0:score+=15
        if (ht==1 and b1[n1]==1) or (ht==-1 and b1[n1]==-1):score+=30
        if (ht==1 and mup) or (ht==-1 and mdn):score+=25
        if ht==1 and ex['bH4'][n1]:score+=25
        if ht==-1 and ex['sH4'][n1]:score+=25
        if ht==1 and ex['bPDL'][n1]:score+=20
        if ht==-1 and ex['sPDH'][n1]:score+=20
        if ht==1 and ex['bW'][n1]:score+=15
        if ht==-1 and ex['sW'][n1]:score+=15
        if ht==-1 and (ex['sH4'][n1] or ex['sPDH'][n1] or ex['sW'][n1]):score+=5
        if (ht==1 and b15[n15]==1) or (ht==-1 and b15[n15]==-1):score+=15
        if ht==1 and bf[n1] and bo[n1]:score+=12
        if ht==-1 and sf[n1] and so[n1]:score+=12
        if (ht==1 and slope>.02) or (ht==-1 and slope<-.02):score+=8
        if (ht==1 and cb[n15] and mup) or (ht==-1 and cs[n15] and mdn):score+=10
        if (ht==1 and b1[n1]==-1) or (ht==-1 and b1[n1]==1):score-=20
        if panic!=0:score-=20
        if (ht==1 and mdn) or (ht==-1 and mup):score-=15
        if ht==1 and -.3>dist>-2.5:score+=15
        if ht==-1 and .3<dist<2.5:score+=15
        if ht==1 and dist>2:score-=20
        if ht==1 and dist>3.5:score-=20
        if ht==-1 and dist<-2:score-=20
        if ht==-1 and dist<-3.5:score-=20
        if ht==1 and c1[n1]==1:score+=12
        if ht==-1 and c1[n1]==-1:score+=12
        if ht==1 and c1[n1]==-1:score-=10
        if ht==-1 and c1[n1]==1:score-=10
        if c1[n1]==1 and c15[n15]==1:score+=8
        if c1[n1]==-1 and c15[n15]==-1:score+=8
        if c15[n15]!=0 and not mup and im>=1:
            # Existing shadow uses last five completed M5 bars ending at im-1.
            q=im-1
            if q>=4:
                hh=rollH[q];ll=rollL[q]
                if (ht==1 and ask>hh) or (ht==-1 and ask<ll):score+=20
        if ht==-1 and b1[n1]==1 and c1[n1]==1 and b15[n15]>=0 and dist<2.5:score+=30
        if ht==1 and b1[n1]==-1 and c1[n1]==-1 and b15[n15]<=0 and dist>-2.5:score+=30
        score=max(0,min(100,score));trend=(ht==1 and score>=35 and .3<dist<1.8 and panic==0) or (ht==-1 and score>=35 and -1.8<dist<-.3 and panic==0);brk=(ht==1 and score>=35 and mup and dist<2.2 and panic==0) or (ht==-1 and score>=35 and mdn and dist>-2.2 and panic==0);need=score>=60 or trend or brk
        action,conf,tag=smartmock(score,ht,b1[n1],b15[n15],dist,imp,c1[n1],c15[n15],panic,bo[n1],so[n1],mup,mdn);block=''
        if action!='WAIT':
            mom2=(d1close[nd]-d1close[nd-2])/d1atr[nd] if nd>=55 and np.isfinite(d1atr[nd]) else 0;eidx=(live-d1ema[nd])/d1atr[nd] if nd>=55 and np.isfinite(d1atr[nd]) else 0
            if action=='BUY' and mom2<-1.5 and eidx<-.5:block='BUY_BEAR_D1'
            if not block and b1[n1]!=0 and c1[n1]==0 and c15[n15]==0:block='BOS_ONLY_BLOCK'
            if not block and body>a15*1.5 and rng>0 and body/rng>.70:
                bull=cc>o
                if (action=='BUY' and not bull) or (action=='SELL' and bull):block='KNIFE_BTC'
            if not block and ((action=='BUY' and panic==-1) or (action=='SELL' and panic==1)):block='PANIC_DIRECTION'
            if not block:
                late=1.35 if brk else 1.5
                if (action=='BUY' and dist>late) or (action=='SELL' and dist<-late):block='LATE_ENTRY_BLOCK'
        passed=int(bool(need) and action!='WAIT' and not block)
        if action!='WAIT' or passed:
            rows.append(dict(time=t,year=t.year,pre=score,need_ai=int(need),action=action,conf=conf,tag=tag,block=block,pass_stateless=passed,htf=ht,bosH1=int(b1[n1]),bosM15=int(b15[n15]),chochH1=int(c1[n1]),chochM15=int(c15[n15]),dist=dist,slope=slope,impulse=imp,panic=panic,microUp=int(mup),microDn=int(mdn),bullOverlap=int(bo[n1]),bearOverlap=int(so[n1])))
    e=pd.DataFrame(rows);e.to_csv(out/'u01_v283_shadow_events.csv',index=False);sig=e[e.action!='WAIT'];passed=e[e.pass_stateless==1]
    sm={'mode':'FAST_V283_DEFAULT_STATELESS_SHADOW_NOT_MT5_PARITY','smartmock_signals':len(sig),'stateless_pass':len(passed),'tag_counts':sig.tag.value_counts().to_dict(),'block_counts':sig.block.value_counts().to_dict(),'yearly_pass':{str(k):int(v) for k,v in passed.groupby('year').size().to_dict().items()},'default_reachability_note':'InpUseLiquidityFilter=false and InpUsePriorityE=false make SmartMock A/D/E unreachable; B/C are reachable. Stateful delivery/cooldown/position memory excluded.'}
    (out/'u01_v283_shadow_summary.json').write_text(json.dumps(sm,indent=2));print(json.dumps(sm,indent=2))
if __name__=='__main__':main()
