"""LAB271 (pre-registered): what starts the move? Triggers inside crowd-skew state.
State (per bar): crowd skewed = |z6|>=1 and z24 same sign with |z24|>=0.5; side = -sign(z6) (against crowd).
Episode = continuous state run with one side; ONE entry per episode (first trigger).
Triggers at M5 close i (data index <= i, causal):
 OI_k_q_m : coin OI change over k bars <= -q (positions being closed = liquidations/stop-outs) AND price moved >= m ATR in trade side over same k bars
 TK_k_p   : taker buy/sell volume ratio, mean log over k bars, in trade side beyond TRAIN p-quantile of |.| (aggressive flow joins our side)
 OI+TK    : both (k=6)
 FUND     : first bar of a funding window (00/08/16 UTC) inside state
 STATE    : first bar of state (control: 'just skewed')
 D2       : current D2 signal (control)
Exit identical to D2 (SL 3ATR, trail peak-3R after +2R, 48h, max 2). Report: signals/mo, EV, first-third share, drift 1h/4h/24h, portfolio money (A+B3 + engine at 0.10%)."""
import numpy as np,pandas as pd,zipfile
exec(open("sw260.py").read().split("\nrows=[]")[0])
z6=g["z6"]; z24=g["z24"]
with zipfile.ZipFile("/home/claude/data/BTCUSDT_flow_2021-01-2026-08.csv.zip") as zf:
    nm=[x for x in zf.namelist() if x.endswith(".csv")][0]; f=pd.read_csv(zf.open(nm))
f["time"]=pd.to_datetime(f.create_time,utc=True); f=f.sort_values("time").drop_duplicates("time").set_index("time")
OI=f.sum_open_interest.astype(float).where(lambda x:x>0).resample("5min").last().reindex(BT,method="ffill").ffill().to_numpy()
TK=np.log(f.sum_taker_long_short_vol_ratio.astype(float).clip(lower=1e-6)).resample("5min").last().reindex(BT,method="ffill").to_numpy()
T=pd.DatetimeIndex(BT)
# waves for timing
src2=open("trendalt.py").read(); w0=src2.index("df=pd.DataFrame({\"c\":BC"); w1=src2.index("rows=[]",w0); gg=dict(g["g"]); exec(src2[w0:w1],gg); WV=gg["WV"]
wdir=np.zeros(N,int); wpos=np.full(N,np.nan)
for i0,i1,d,tr in WV: wdir[i0:i1]=d; wpos[i0:i1]=(np.arange(i0,i1)-i0)/(i1-i0)
state=np.where((np.abs(z6)>=1)&np.isfinite(z24)&(np.sign(z24)==np.sign(z6))&(np.abs(z24)>=0.5),-np.sign(z6),0).astype(int)
def lagd(a,k): return np.r_[np.full(k,np.nan),a[k:]-a[:-k]]
oich={k:np.r_[np.full(k,np.nan),OI[k:]/OI[:-k]-1] for k in (3,6,12)}
pch={k:lagd(BC,k)/BA for k in (3,6,12)}
tkm={k:pd.Series(TK).rolling(k).mean().to_numpy() for k in (3,6,12)}
trm=T<TE
tkq={(k,p):np.nanquantile(np.abs(tkm[k][trm]),p) for k in (3,6,12) for p in (0.9,0.97)}
fundbar=np.asarray((T.hour%8==0)&(T.minute==0))
def episodes(trig):
    out=[]; cur=0; used=False
    for i in range(400,N-600):
        s=state[i]
        if s!=cur: cur=s; used=False
        if s==0 or used: continue
        if trig(i,s): out.append((i,s)); used=True
    return out
V={"STATE (перший бар перекосу)":lambda i,s:True,
   "FUND (вікно фандингу)":lambda i,s:fundbar[i]}
for k in (3,6,12):
    for q in (0.003,0.006,0.01):
        for m in (0.3,0.6):
            V[f"OI k{k} падіння≥{q*100:.1f}% ціна≥{m}ATR"]=(lambda k,q,m:lambda i,s:oich[k][i]<=-q and s*pch[k][i]>=m)(k,q,m)
    for p in (0.9,0.97):
        V[f"TK k{k} taker p{int(p*100)}"]=(lambda k,p:lambda i,s:np.isfinite(tkm[k][i]) and s*tkm[k][i]>=tkq[(k,p)])(k,p)
V["OI k6 ≥0.6% + TK k6 p90"]=lambda i,s:oich[6][i]<=-0.006 and s*tkm[6][i]>=tkq[(6,0.9)]
fut={h:np.r_[BC[h*12:],np.full(h*12,np.nan)]-BC for h in (1,4,24)}
rows=[]
allV=[("D2 (контроль)",SIG)]+[(k_,episodes(v)) for k_,v in V.items()]
for nm_,S in allV:
    if len(S)<20: continue
    t,e=sim(to_EN(S)) if False else sim([(i+1,sd,BO[i+1],3*BA[i+1],BA[i+1]) for i,sd in S])
    tot=AB+al(e)*0.10; si=np.array([i for i,_ in S]); ss=np.array([s for _,s in S]); r=dict(v=nm_)
    for seg,mk,mo in [("21-24",BT<TE,48),("25-26",BT>=TE,19.3)]:
        x=tot[mk]; x=x-x.iloc[0]; dd=float((x.cummax()-x).max()); tt=t[(BT[t.entry_i.to_numpy(int)]<TE)==(seg=="21-24")]
        sm=(BT[si]<TE)==(seg=="21-24"); ii=si[sm]; s_=ss[sm]
        r.update({f"сигн/міс {seg}":len(ii)/mo,f"1/3 {seg}":((wdir[ii]==s_)&(wpos[ii]<1/3)).mean(),
                  f"1г {seg}":np.nanmean(s_*fut[1][ii]/BA[ii]),f"4г {seg}":np.nanmean(s_*fut[4][ii]/BA[ii]),f"24г {seg}":np.nanmean(s_*fut[24][ii]/BA[ii]),
                  f"EV {seg}":tt.net_r.mean(),f"R/DD {seg}":x.iloc[-1]/dd,f"%м {seg}":x.iloc[-1]/mo,f"DD {seg}":dd})
    rows.append(r); print(nm_,flush=True)
R=pd.DataFrame(rows).set_index("v"); k_=7/R[["DD 21-24","DD 25-26"]].max(axis=1); R["$ 21-24"]=R["%м 21-24"]*k_*1000; R["$ 25-26"]=R["%м 25-26"]*k_*1000
R.to_csv("out_oos/LAB271_TRIGGERS.csv"); pd.set_option("display.width",360)
c=[x for x in R.columns if not x.startswith(("%м","DD"))]
print(R[c].round(2).to_string())
