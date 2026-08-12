#!/usr/bin/env python3
"""Source-faithful *shadow* scanner for v283 default entry logic.
Not accepted as MT5 parity: evaluates at M5 opens with a fixed research spread.
Purpose: reachability/count diagnostics before exact Strategy Tester parity.
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
    x['time']=pd.to_datetime(x.time,format='%Y.%m.%d %H:%M',errors='coerce')
    for c in ['open','high','low','close']: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.dropna(subset=['time','open','high','low','close']).sort_values('time').drop_duplicates('time').reset_index(drop=True)

def rs(x,rule):
    z=x.set_index('time').resample(rule,label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    z['close_time']=z.time+pd.Timedelta(rule); return z

def wilder(s,p):
    a=s.to_numpy(float); out=np.full(len(a),np.nan); valid=np.flatnonzero(np.isfinite(a))
    if len(valid)<p:return pd.Series(out,index=s.index)
    st=valid[0]
    if st+p>len(a):return pd.Series(out,index=s.index)
    out[st+p-1]=np.mean(a[st:st+p])
    for i in range(st+p,len(a)):
        if np.isfinite(a[i]): out[i]=(out[i-1]*(p-1)+a[i])/p
    return pd.Series(out,index=s.index)

def atr(df,p=14):
    pc=df.close.shift(1); tr=pd.concat([df.high-df.low,(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1); return wilder(tr,p)
def ema(s,p): return s.ewm(span=p,adjust=False,min_periods=p).mean()

def pivot_high(H,j,strength=2):
    if j-strength<0 or j+strength>=len(H):return False
    c=H[j]
    for k in range(1,strength+1):
        if H[j+k]>=c or H[j-k]>c:return False
    return True

def pivot_low(L,j,strength=2):
    if j-strength<0 or j+strength>=len(L):return False
    c=L[j]
    for k in range(1,strength+1):
        if L[j+k]<=c or L[j-k]<c:return False
    return True

def bos_at(df,n,lookback):
    if n<10:return 0
    H=df.high.to_numpy(float); L=df.low.to_numpy(float); C=df.close.to_numpy(float); sh=sl=None
    for shift in range(3,min(lookback,n-2)+1):
        j=n-(shift-1)
        if j<2:break
        if sh is None and pivot_high(H,j):sh=H[j]
        if sl is None and pivot_low(L,j):sl=L[j]
        if sh is not None and sl is not None:break
    if sh is not None and C[n]>sh:return 1
    if sl is not None and C[n]<sl:return -1
    return 0

def choch_at(df,n,atr_h1):
    if n<10 or not np.isfinite(atr_h1) or atr_h1<=0:return 0
    H=df.high.to_numpy(float); L=df.low.to_numpy(float); C=df.close.to_numpy(float); sh=[];sl=[]
    for shift in range(3,min(20,n-2)+1):
        j=n-(shift-1)
        if pivot_high(H,j) and len(sh)<2:sh.append(H[j])
        if pivot_low(L,j) and len(sl)<2:sl.append(L[j])
        if len(sh)>=2 and len(sl)>=2:break
    buf=atr_h1*.05
    if len(sh)>=2 and len(sl)>=1 and sh[0]<sh[1] and C[n]<sl[0]-buf:return -1
    if len(sl)>=2 and len(sh)>=1 and sl[0]>sl[1] and C[n]>sh[0]+buf:return 1
    return 0

def last_closed_idx(df,t):
    return int(np.searchsorted(df.close_time.to_numpy('datetime64[ns]'),np.datetime64(t),side='right')-1)

def htf_bias(d1,h4,h1,nd,nh4,nh1):
    d=bos_at(d1,nd,30) if nd>=0 else 0; h=bos_at(h4,nh4,50) if nh4>=0 else 0; one=bos_at(h1,nh1,60) if nh1>=0 else 0
    if d==-1 and h==-1:return -1
    if d==1 and h==1:return 1
    if d==-1 and h==0:return -1
    if d==1 and h==0:return 1
    if d==0 and h==-1:return -1
    if d==0 and h==1:return 1
    if d==-1 and h==1:return -1 if one==-1 else 0
    if d==1 and h==-1:return 1 if one==1 else 0
    if d==0 and h==0 and one!=0:return one
    if nh4>=0 and np.isfinite(h4.loc[nh4,'ema50']):return 1 if h4.loc[nh4,'close']>h4.loc[nh4,'ema50'] else -1
    return 0

def m1_fractal(m1,n):
    H=m1.high.to_numpy(float);L=m1.low.to_numpy(float);fh=fl=None
    for shift in range(2,20):
        j=n-(shift-1)
        if j-1<0 or j+1>=len(H):continue
        if fh is None and H[j]>H[j-1] and H[j]>H[j+1]:fh=H[j]
        if fl is None and L[j]<L[j-1] and L[j]<L[j+1]:fl=L[j]
        if fh is not None and fl is not None:break
    return fh,fl

def fvgob(h1,n,atrh):
    st={'bullFVG':0,'bearFVG':0,'bullOverlap':0,'bearOverlap':0}
    if n<10 or not np.isfinite(atrh):return st
    minGap=atrh*.18;O=h1.open.to_numpy(float);H=h1.high.to_numpy(float);L=h1.low.to_numpy(float);C=h1.close.to_numpy(float)
    for right in range(1,19):
        jr=n-(right-1);jl=n-(right+1)
        if jl<0:break
        if not st['bullFVG'] and L[jr]-H[jl]>=minGap:
            st['bullFVG']=1;fL,fH=H[jl],L[jr]
            for k in range(jl,jl-7,-1):
                if k<0:break
                if C[k]<O[k]:
                    obL,obH=min(O[k],C[k]),max(O[k],C[k]);st['bullOverlap']=int(max(fL,obL)<=min(fH,obH));break
        if not st['bearFVG'] and L[jl]-H[jr]>=minGap:
            st['bearFVG']=1;fL,fH=H[jr],L[jl]
            for k in range(jl,jl-7,-1):
                if k<0:break
                if C[k]>O[k]:
                    obL,obH=min(O[k],C[k]),max(O[k],C[k]);st['bearOverlap']=int(max(fL,obL)<=min(fH,obH));break
        if st['bullFVG'] and st['bearFVG']:break
    return st

def extended_liq(h1,h4,d1,nh1,nh4,nd,atrh):
    out=dict(bH4=0,sH4=0,bPDL=0,sPDH=0,bW=0,sW=0)
    if min(nh1,nh4,nd)<3:return out
    H4=h4.high.to_numpy(float);L4=h4.low.to_numpy(float);H1=h1.high.to_numpy(float);L1=h1.low.to_numpy(float);C1=h1.close.to_numpy(float);O1=h1.open.to_numpy(float);tol=atrh*.25
    lows=[L4[nh4-i] for i in range(3)];highs=[H4[nh4-i] for i in range(3)]
    eql=abs(lows[0]-lows[1])<tol or abs(lows[1]-lows[2])<tol;lvl=min(lows[0],lows[1]);out['bH4']=int(eql and L1[nh1]<lvl and C1[nh1]>lvl)
    eqh=abs(highs[0]-highs[1])<tol or abs(highs[1]-highs[2])<tol;lvl=max(highs[0],highs[1]);out['sH4']=int(eqh and H1[nh1]>lvl and C1[nh1]<lvl)
    pdl=d1.loc[nd,'low'];pdh=d1.loc[nd,'high'];out['bPDL']=int(L1[nh1]<pdl and C1[nh1]>pdl);out['sPDH']=int(H1[nh1]>pdh and C1[nh1]<pdh)
    recent_low=np.min(L1[max(0,nh1-7):nh1]);recent_high=np.max(H1[max(0,nh1-7):nh1]);br=H1[nh1]-L1[nh1]
    if br>0:
        out['bW']=int(L1[nh1]<recent_low and C1[nh1]>recent_low and (min(C1[nh1],O1[nh1])-L1[nh1])/br>=.40)
        out['sW']=int(H1[nh1]>recent_high and C1[nh1]<recent_high and (H1[nh1]-max(C1[nh1],O1[nh1]))/br>=.40)
    return out

def compression(m15,n,atr15):
    if n<12:return (0,0)
    H=m15.high.to_numpy(float);L=m15.low.to_numpy(float);tol=max(10,min(150,atr15*.15));hs=np.array([H[n-i] for i in range(12)]);ls=np.array([L[n-i] for i in range(12)]);ch=hs.max();cl=ls.min();eqh=(abs(hs-ch)<=tol).sum();eql=(abs(ls-cl)<=tol).sum();hl=lh=0
    for shift in range(12,2,-1):
        ja=n-(shift-1);jb=n-(shift-2)
        if L[jb]>L[ja]:hl+=1
        if H[jb]<H[ja]:lh+=1
    return int(eqh>=3 and hl>=3),int(eql>=3 and lh>=3)

def d1_state(d1,nd,live):
    if nd<55:return dict(mom2=0,eidx=0)
    av=d1.loc[nd,'atr14'];em=d1.loc[nd,'ema50'];return dict(mom2=(d1.loc[nd,'close']-d1.loc[nd-2,'close'])/av,eidx=(live-em)/av)

def smartmock(pre,htf,bos1,bos15,dist,imp,cho1,cho15,panic,ov,mup,mdn):
    if pre<40 or panic!=0 or abs(dist)>3 or imp>2 or htf==0:return ('WAIT',50,'WaitSetup')
    ps=8 if pre>=70 else 4 if pre>=50 else -10
    if htf==1 and cho1==1 and bos1==1:
        c=65+(8 if mup else 0)+(6 if ov['bullOverlap'] else 0)+(-8 if dist>2 else 0)+ps
        if c>=68:return ('BUY',min(c,95),'CHoCHBull')
    if htf==-1 and cho1==-1 and bos1==-1:
        c=65+(8 if mdn else 0)+(6 if ov['bearOverlap'] else 0)+(-8 if dist<-2 else 0)+ps
        if c>=68:return ('SELL',min(c,95),'CHoCHBear')
    if htf==1 and ov['bullOverlap'] and mup:
        c=62+ps+(5 if bos1==1 else 0)+(5 if dist<-.5 else 0)
        if c>=80:return ('BUY',min(c,95),'OBFVGBull')
    if htf==-1 and ov['bearOverlap'] and mdn:
        c=62+ps+(5 if bos1==-1 else 0)+(5 if dist>.5 else 0)
        if c>=80:return ('SELL',min(c,95),'OBFVGBear')
    return ('WAIT',50,'WaitSetup')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--btc-1m',required=True);ap.add_argument('--outdir',required=True);a=ap.parse_args();out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True)
    m1=load_zip(a.btc_1m);m1=m1[m1.time>=pd.Timestamp('2023-06-01')].reset_index(drop=True);m5=rs(m1,'5min');m15=rs(m1,'15min');h1=rs(m1,'1h');h4=rs(m1,'4h');d1=rs(m1,'1D')
    for df in [m15,h1,h4,d1]:df['atr14']=atr(df)
    h1['ema50']=ema(h1.close,50);h4['ema50']=ema(h4.close,50);d1['ema50']=ema(d1.close,50);rows=[]
    for r in m5.itertuples(index=False):
        t=r.time
        if t<pd.Timestamp('2024-01-01'):continue
        n1=last_closed_idx(h1,t);n4=last_closed_idx(h4,t);nd=last_closed_idx(d1,t);n15=last_closed_idx(m15,t);nm1=int(np.searchsorted(m1.time.to_numpy('datetime64[ns]'),np.datetime64(t),side='left')-1)
        if min(n1,n4,nd,n15,nm1)<60:continue
        atrh=h1.loc[n1,'atr14'];atr15=m15.loc[n15,'atr14']
        if not np.isfinite(atrh) or atrh<=0:continue
        bos1=bos_at(h1,n1,60);bos15=bos_at(m15,n15,60);htf=htf_bias(d1,h4,h1,nd,n4,n1);cho1=choch_at(h1,n1,atrh);cho15=choch_at(m15,n15,atrh);live=float(r.open);ask=live+SPREAD;bid=live;fh,fl=m1_fractal(m1,nm1);mup=fh is not None and ask>fh;mdn=fl is not None and bid<fl;ema1=h1.loc[n1,'ema50'];emap=h1.loc[n1-1,'ema50'];slope=(ema1-emap)/atrh;dist=(bid-ema1)/atrh;imp=abs(h1.loc[n1,'close']-h1.loc[n1-1,'close'])/atrh
        o,c,hi,lo=m15.loc[n15,['open','close','high','low']];body=abs(c-o);rng=hi-lo;bodyatr=body/atr15 if atr15>0 else 0;panic=0
        if rng>0 and bodyatr>=1.8:
            if c<o and (c-lo)/rng<=.20:panic=-1
            elif c>o and (hi-c)/rng<=.20:panic=1
        ov=fvgob(h1,n1,atrh);ex=extended_liq(h1,h4,d1,n1,n4,nd,atrh);cb,cs=compression(m15,n15,atr15);score=0
        if htf!=0:score+=15
        if (htf==1 and bos1==1) or (htf==-1 and bos1==-1):score+=30
        if (htf==1 and mup) or (htf==-1 and mdn):score+=25
        if htf==1 and ex['bH4']:score+=25
        if htf==-1 and ex['sH4']:score+=25
        if htf==1 and ex['bPDL']:score+=20
        if htf==-1 and ex['sPDH']:score+=20
        if htf==1 and ex['bW']:score+=15
        if htf==-1 and ex['sW']:score+=15
        if htf==-1 and (ex['sH4'] or ex['sPDH'] or ex['sW']):score+=5
        if (htf==1 and bos15==1) or (htf==-1 and bos15==-1):score+=15
        if htf==1 and ov['bullFVG'] and ov['bullOverlap']:score+=12
        if htf==-1 and ov['bearFVG'] and ov['bearOverlap']:score+=12
        if (htf==1 and slope>.02) or (htf==-1 and slope<-.02):score+=8
        if (htf==1 and cb and mup) or (htf==-1 and cs and mdn):score+=10
        if (htf==1 and bos1==-1) or (htf==-1 and bos1==1):score-=20
        if panic!=0:score-=20
        if (htf==1 and mdn) or (htf==-1 and mup):score-=15
        if htf==1 and -.3>dist>-2.5:score+=15
        if htf==-1 and .3<dist<2.5:score+=15
        if htf==1 and dist>2:score-=20
        if htf==1 and dist>3.5:score-=20
        if htf==-1 and dist<-2:score-=20
        if htf==-1 and dist<-3.5:score-=20
        if htf==1 and cho1==1:score+=12
        if htf==-1 and cho1==-1:score+=12
        if htf==1 and cho1==-1:score-=10
        if htf==-1 and cho1==1:score-=10
        if cho1==1 and cho15==1:score+=8
        if cho1==-1 and cho15==-1:score+=8
        if cho15!=0 and not mup:
            im5=int(np.searchsorted(m5.close_time.to_numpy('datetime64[ns]'),np.datetime64(t),side='right')-1)
            if im5>=4:
                hh=m5.high.iloc[im5-4:im5+1].max();ll=m5.low.iloc[im5-4:im5+1].min()
                if (htf==1 and ask>hh) or (htf==-1 and ask<ll):score+=20
        if htf==-1 and bos1==1 and cho1==1 and bos15>=0 and dist<2.5:score+=30
        if htf==1 and bos1==-1 and cho1==-1 and bos15<=0 and dist>-2.5:score+=30
        score=max(0,min(100,score));trend=(htf==1 and score>=35 and .3<dist<1.8 and panic==0) or (htf==-1 and score>=35 and -1.8<dist<-.3 and panic==0);brk=(htf==1 and score>=35 and mup and dist<2.2 and panic==0) or (htf==-1 and score>=35 and mdn and dist>-2.2 and panic==0);need=score>=60 or trend or brk;action,conf,tag=smartmock(score,htf,bos1,bos15,dist,imp,cho1,cho15,panic,ov,mup,mdn);block=''
        if action!='WAIT':
            st=d1_state(d1,nd,live)
            if action=='BUY' and st['mom2']<-1.5 and st['eidx']<-.5:block='BUY_BEAR_D1'
            if not block and bos1!=0 and cho1==0 and cho15==0:block='BOS_ONLY_BLOCK'
            if not block and body>atr15*1.5 and rng>0 and body/rng>.70:
                bull=c>o
                if (action=='BUY' and not bull) or (action=='SELL' and bull):block='KNIFE_BTC'
            if not block and ((action=='BUY' and panic==-1) or (action=='SELL' and panic==1)):block='PANIC_DIRECTION'
            if not block:
                late=1.35 if brk else 1.5
                if (action=='BUY' and dist>late) or (action=='SELL' and dist<-late):block='LATE_ENTRY_BLOCK'
        rows.append(dict(time=t,year=t.year,pre=score,need_ai=int(need),action=action,conf=conf,tag=tag,block=block,pass_stateless=int(action!='WAIT' and not block),htf=htf,bosH1=bos1,bosM15=bos15,chochH1=cho1,chochM15=cho15,dist=dist,slope=slope,impulse=imp,panic=panic,microUp=int(mup),microDn=int(mdn),bullOverlap=ov['bullOverlap'],bearOverlap=ov['bearOverlap']))
    e=pd.DataFrame(rows);e.to_csv(out/'u01_v283_shadow_events.csv',index=False);sig=e[e.action!='WAIT'];passed=e[e.pass_stateless==1];summary={'mode':'M5_OPEN_SHADOW_NOT_PARITY','rows':len(e),'smartmock_signals':len(sig),'stateless_pass':len(passed),'tag_counts':sig.tag.value_counts().to_dict(),'block_counts':sig.block.value_counts().to_dict(),'yearly_pass':{str(k):int(v) for k,v in passed.groupby('year').size().to_dict().items()}};(out/'u01_v283_shadow_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2));print('\nTAGS YEARLY\n',sig.groupby(['year','tag']).size().unstack(fill_value=0).to_string());print('\nPASS YEARLY SIDE\n',passed.groupby(['year','action']).size().unstack(fill_value=0).to_string())
if __name__=='__main__':main()
