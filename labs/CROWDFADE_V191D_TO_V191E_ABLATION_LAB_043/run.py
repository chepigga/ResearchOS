from pathlib import Path
import json, zipfile
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Frozen v191d/e common shell
ZTH=1.00
CONF_ATR=0.30
CONF_TTL=3*3600
SL_ATR=1.50
BE_ATR=0.50
BE_LOCK_ATR=0.15
TRAIL_ARM_ATR=2.50
TRAIL_GAP_ATR=0.50
HOLD=6*3600
PAUSE_ATR=1.00
MAXDAY=3
COST_BPS=0.50

# Ablation variants:
# D = v191d: confirm contradiction only beyond opposite ExitZ threshold; ExitZ=0.75 active
# D_EXIT_OFF = only disable ExitZ
# D_SAMESIDE = only tighten confirmation to original crowd side
# E = both changes (v191e)
V_D=0; V_EXIT_OFF=1; V_SAMESIDE=2; V_E=3
NAMES={0:'V191D_CONTROL',1:'EXITZ_OFF_ONLY',2:'SAMESIDE_CONFIRM_ONLY',3:'V191E_BOTH'}

def load_flow():
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    with zipfile.ZipFile(zp) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:r=pd.read_csv(f,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy()
    r['t']=pd.to_datetime(r.create_time,utc=True,errors='coerce')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['t','ratio']).sort_values('t').drop_duplicates('t')
    mu=r.ratio.rolling(72,min_periods=72).mean(); sd=r.ratio.rolling(72,min_periods=72).std(ddof=0)
    r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
    ft=r.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    return ft,r.z.to_numpy(float)

def read_zip(path):
    with zipfile.ZipFile(path) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:r=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
    ts=pd.to_numeric(r.iloc[:,0],errors='coerce'); med=np.nanmedian(ts.to_numpy(float))
    if med>1e15: ts=(ts//1_000_000).astype('Int64')
    elif med>1e12: ts=(ts//1000).astype('Int64')
    else: ts=ts.astype('Int64')
    q=pd.DataFrame({'ts':ts,'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),'c':pd.to_numeric(r.iloc[:,4],errors='coerce')})
    return q.dropna()

def load_hist():
    parts=[read_zip(zp) for zp in sorted((DATA/'hist_1m').glob('BTCUSDT-1m-*.zip'))]
    p=pd.concat(parts,ignore_index=True).drop_duplicates('ts').sort_values('ts')
    return tuple(p[x].to_numpy(np.int64 if x=='ts' else np.float64) for x in ['ts','o','h','l','c'])

def load_sec():
    with zipfile.ZipFile(DATA/'BTCUSDT_sec.csv.zip') as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:s=pd.read_csv(f,usecols=['ts','o','h','l','c'])
    s=s.sort_values('ts').drop_duplicates('ts')
    return tuple(s[x].to_numpy(np.int64 if x=='ts' else np.float64) for x in ['ts','o','h','l','c'])

def prep(raw,ft,fz,start,end):
    ts,O,H,L,C=raw
    order=np.argsort(ts);ts=ts[order];O=O[order];H=H[order];L=L[order];C=C[order]
    keep=np.r_[True,ts[1:]!=ts[:-1]];ts=ts[keep];O=O[keep];H=H[keep];L=L[keep];C=C[keep]

    b15=(ts//900)*900; st15=np.r_[0,np.flatnonzero(b15[1:]!=b15[:-1])+1]; en15=np.r_[st15[1:],len(ts)]
    bt15=b15[st15]; bh15=np.maximum.reduceat(H,st15); bl15=np.minimum.reduceat(L,st15); bc15=C[en15-1]
    pc=np.r_[bc15[0],bc15[:-1]]; tr=np.maximum(bh15-bl15,np.maximum(np.abs(bh15-pc),np.abs(bl15-pc)))
    atr15=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy(); av15=bt15+900

    b5=(ts//300)*300; st5=np.r_[0,np.flatnonzero(b5[1:]!=b5[:-1])+1]; en5=np.r_[st5[1:],len(ts)]
    bt5=b5[st5]; c5=C[en5-1]; av5=bt5+300

    fi=np.searchsorted(ft,av5,'left')-1; ai=np.searchsorted(av15,av5,'right')-1
    fi0=np.maximum(fi,0); ai0=np.maximum(ai,0)
    good=(av5>=start)&(av5<end)&(fi>=0)&(ai>=0)&np.isfinite(fz[fi0])&np.isfinite(atr15[ai0])
    good &= ((av5-ft[fi0])>=0)&((av5-ft[fi0])<=600)

    # raw causal flow state used for confirm/ExitZ
    ri=np.searchsorted(ft,ts,'right')-1; ri0=np.maximum(ri,0)
    rz=np.full(len(ts),np.nan)
    rg=(ri>=0)&((ts-ft[ri0])>=0)&((ts-ft[ri0])<=600)
    rz[rg]=fz[ri[rg]]
    return ts,O,H,L,C,rz,av5[good],c5[good],fz[fi[good]],atr15[ai[good]]

@njit(cache=True)
def confirm_ok(side,current_z,sameside):
    if not np.isfinite(current_z): return False
    if sameside:
        return current_z<0.0 if side>0 else current_z>0.0
    # v191d consistency: cancel only once crowd reached opposite ExitZ side
    return current_z<0.75 if side>0 else current_z>-0.75

@njit(cache=True)
def simulate(ts,O,H,L,C,RZ,dt5,C5,Z5,A5,variant):
    sameside=(variant==V_SAMESIDE or variant==V_E)
    exitz_on=(variant==V_D or variant==V_SAMESIDE)
    cap=len(dt5)
    R=np.zeros(cap); ST=np.zeros(cap,np.int64); ET=np.zeros(cap,np.int64); XT=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8); REASON=np.zeros(cap,np.int8); AGE=np.zeros(cap); OZ=np.zeros(cap); CZ=np.zeros(cap)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    while k<len(dt5)-2:
        t=dt5[k]
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z=Z5[k]; side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        sig=C5[k];a=A5[k]
        if has and abs(sig-last)<PAUSE_ATR*la:k+=1;continue

        target=sig+side*CONF_ATR*a
        ps=np.searchsorted(ts,t+1);pe=np.searchsorted(ts,t+CONF_TTL,'right')
        ci=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and C[q]>=target) or (side<0 and C[q]<=target):
                if confirm_ok(side,RZ[q],sameside):
                    ci=q
                else:
                    ci=-2
                break
        if ci<0:
            k+=1;continue

        entry=C[ci]; stop=entry-side*SL_ATR*a; peak=entry
        lastbar=min(len(ts)-1,np.searchsorted(ts,ts[ci]+HOLD,'left'))
        xp=C[lastbar];ex=lastbar;reason=3
        pending_stop=stop
        for q in range(ci+1,lastbar+1):
            stop=pending_stop
            sh=(side>0 and L[q]<=stop) or (side<0 and H[q]>=stop)
            if sh:
                xp=stop;ex=q;reason=-1;break
            if side>0:
                if H[q]>peak:peak=H[q]
                mfe=(peak-entry)/a
            else:
                if L[q]<peak:peak=L[q]
                mfe=(entry-peak)/a
            ns=stop
            if mfe>=BE_ATR:
                lvl=entry+side*BE_LOCK_ATR*a
                if (side>0 and lvl>ns) or (side<0 and lvl<ns):ns=lvl
            if mfe>=TRAIL_ARM_ATR:
                lvl=peak-side*TRAIL_GAP_ATR*a
                if (side>0 and lvl>ns) or (side<0 and lvl<ns):ns=lvl
            pending_stop=ns
            if exitz_on and np.isfinite(RZ[q]):
                hit=(side>0 and RZ[q]>=0.75) or (side<0 and RZ[q]<=-0.75)
                if hit:
                    xp=C[q];ex=q;reason=2;break
        rr=side*(xp-entry)/(SL_ATR*a)-(COST_BPS/10000.)*entry/(SL_ATR*a)
        R[n]=rr;ST[n]=t;ET[n]=ts[ci];XT[n]=ts[ex];SIDE[n]=side;REASON[n]=reason;AGE[n]=(ts[ci]-t)/60.;OZ[n]=z;CZ[n]=RZ[ci];n+=1
        dc+=1;last=entry;la=a;has=True
        nextts=ts[ex]+1;k=np.searchsorted(dt5,nextts)
    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n],REASON[:n],AGE[:n],OZ[:n],CZ[:n]

def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:return {'N':0}
    eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max())
    pos=a[a>0].sum();neg=abs(a[a<0].sum());mcl=cur=0
    for x in a:
        if x<0:cur+=1;mcl=max(mcl,cur)
        else:cur=0
    return {'N':int(len(a)),'WR':float((a>0).mean()),'EV':float(a.mean()),'PF':float(pos/neg) if neg else 99.,'SumR':float(a.sum()),'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.,'MaxConsecutiveLosses':int(mcl)}

def make_df(z):
    R,st,et,xt,side,rs,age,oz,cz=z
    reason=np.where(rs==-1,'STOP',np.where(rs==2,'EXIT_Z','TIME'))
    return pd.DataFrame({'R':R,'signal_ts':st,'entry_ts':et,'exit_ts':xt,'side':side,'exit_reason':reason,'confirm_age_min':age,'orig_z':oz,'confirm_z':cz})

def summarize(df,kind):
    out={'all':metrics(df.R)}
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True)
    key=t.dt.year.astype(str) if kind=='year' else t.dt.strftime('%Y-%m')
    out['periods']={str(k):metrics(g.R) for k,g in df.groupby(key)}
    out['exit_reasons']={str(k):int(v) for k,v in df.exit_reason.value_counts().items()}
    out['median_confirm_age_min']=float(df.confirm_age_min.median()) if len(df) else 0.
    return out

def run_period(raw,ft,fz,start,end,label):
    p=prep(raw,ft,fz,start,end);res={}
    for v in [V_D,V_EXIT_OFF,V_SAMESIDE,V_E]:
        df=make_df(simulate(*p,v));df.to_csv(OUT/f'{label}_{NAMES[v]}.csv',index=False)
        res[NAMES[v]]=summarize(df,'year' if label=='historical' else 'month')
    return res

def fmt(m):
    return f"N={m['N']} WR={m['WR']:.1%} EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f} MCL={m['MaxConsecutiveLosses']}"

def main():
    ft,fz=load_flow();hist=load_hist();sec=load_sec()
    H=run_period(hist,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),'historical')
    F=run_period(sec,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),'forward')
    result={'lab':'CROWDFADE_V191D_TO_V191E_ABLATION_LAB_043','variants':{
      'V191D_CONTROL':'ExitZ=0.75 active; confirm allows original side until opposite ExitZ threshold.',
      'EXITZ_OFF_ONLY':'Only ExitZ disabled; v191d confirm consistency unchanged.',
      'SAMESIDE_CONFIRM_ONLY':'ExitZ=0.75 retained; confirm must remain on original crowd side (BUY z<0, SELL z>0).',
      'V191E_BOTH':'ExitZ disabled + same-side confirm.'},
      'historical':H,'forward_2026_shadow':F,
      'limitations':['BTCUSDT only.','Historical path is 1m OHLC; 2026 Mar-Aug uses second OHLC.','2026 is reused forward-shadow, not pristine OOS.','MT5 v191d/e is tick/timer based; replay approximates market confirmation with raw close crossing 0.30 ATR.','Stop modifications are conservatively effective from the next raw bar; exact tick ordering differs.','Flat 0.5bps cost proxy; broker-specific IC/GetLeveraged spreads/slippage are not reproduced.']}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    rows=[]
    for period,d in [('historical',H),('2026',F)]:
        for name,v in d.items():rows.append({'period':period,'variant':name,**v['all']})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
    lines=['# LAB043 — v191d → v191e ABLATION','','Four-way causal ablation: control, ExitZ-off only, same-side-confirm only, both.','','## Full sample']
    for period,d in [('Historical 2021-2025',H),('2026 Mar-Aug shadow',F)]:
        lines+=['',f'### {period}']
        for name,v in d.items(): lines.append(f"- {name}: {fmt(v['all'])}; exits={v['exit_reasons']}; medianConfirm={v['median_confirm_age_min']:.1f}m")
    lines+=['','## Period consistency']
    for period,d in [('Historical',H),('2026',F)]:
        lines+=['',f'### {period}']
        for name,v in d.items():lines.append(f"- {name}: {json.dumps(v['periods'])}")
    lines+=['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())
if __name__=='__main__':main()
