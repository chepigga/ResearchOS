"""LAB269 (pre-registered): entry on crowd PEAK REVERSAL vs D2 (entry at threshold crossing).
Episode = run of |z6|>=1 with one sign; running peak |z6|. Trigger (once per episode): peak>=P and |z6|<=peak-Δ (checked also on the bar the episode ends).
Filters as D2: z24 same sign as episode with |z24|>=0.5, H4 EMA50 trend == side; side = -sign(episode). Grid P {1.5,2.0,2.5} x Δ {0.3,0.5,1.0};
variant 'без фільтрів' for reference. Exits identical to D2 (SL 3ATR, trail peak-3R after +2R, 48h, max 2). Select by 2021-24 portfolio ret/DD."""
import numpy as np,pandas as pd
exec(open("sw260.py").read().split("\nrows=[]")[0])
z6=g["z6"]; z24=g["z24"]
def peak_sigs(P,D,filt=True):
    out=[]; sg=0; pk=0.0; used=False
    for i in range(300,N-600):
        v=z6[i]
        if not np.isfinite(v): continue
        s=1 if v>0 else -1
        if sg!=0 and not used and pk>=P and (s!=sg or abs(v)<=pk-D):
            if s!=sg: cond=True
            else: cond=abs(v)<=pk-D
            if cond:
                sd=-sg; ok=True
                if filt: ok=np.isfinite(z24[i]) and np.sign(z24[i])==sg and abs(z24[i])>=0.5 and TR4[i]==sd
                if ok: out.append((i,sd)); used=True
        if abs(v)<1: sg=0; pk=0.0; used=False; continue
        if s!=sg: sg=s; pk=abs(v); used=False
        else: pk=max(pk,abs(v))
    return out
def to_EN(S): return [(i+1,sd,BO[i+1],3*BA[i+1],BA[i+1]) for i,sd in S]
wdir=np.zeros(N,int); wpos=np.full(N,np.nan)
WV=g["g"].get("WV")
if WV is None:
    src2=open("trendalt.py").read(); w0=src2.index("df=pd.DataFrame({\"c\":BC"); w1=src2.index("rows=[]",w0); gg=dict(g["g"]); exec(src2[w0:w1],gg); WV=gg["WV"]
for i0,i1,d,tr in WV: wdir[i0:i1]=d; wpos[i0:i1]=(np.arange(i0,i1)-i0)/(i1-i0)
fut=(np.r_[BC[288:],np.full(288,np.nan)]-BC)/BA
rows=[]
V=[("D2 (перетин 1.5, зараз)",SIG)]+[(f"розворот: пік≥{P}, відкат {D}",peak_sigs(P,D)) for P in (1.5,2.0,2.5) for D in (0.3,0.5,1.0)]+[("розворот пік≥2.0 відкат 0.5, без фільтрів",peak_sigs(2.0,0.5,False))]
for nm,S in V:
    t,e=sim(to_EN(S)); tot=AB+al(e)*0.10
    si=np.array([i for i,_ in S]); ss=np.array([s for _,s in S]); r=dict(v=nm)
    for seg,mk,mo in [("21-24",BT<TE,48),("25-26",BT>=TE,19.3)]:
        x=tot[mk]; x=x-x.iloc[0]; dd=float((x.cummax()-x).max()); tt=t[(BT[t.entry_i.to_numpy(int)]<TE)==(seg=="21-24")]
        sm=(BT[si]<TE)==(seg=="21-24"); ii=si[sm]; s_=ss[sm]
        r.update({f"сигн/міс {seg}":len(ii)/mo,f"рух24 {seg}":np.nanmean(s_*fut[ii]),f"бік {seg}":(wdir[ii][wdir[ii]!=0]==s_[wdir[ii]!=0]).mean(),
                  f"1/3 {seg}":((wdir[ii]==s_)&(wpos[ii]<1/3)).mean(),f"EV {seg}":tt.net_r.mean(),f"R/DD {seg}":x.iloc[-1]/dd,f"%м {seg}":x.iloc[-1]/mo,f"DD {seg}":dd})
    rows.append(r); print(nm,flush=True)
R=pd.DataFrame(rows).set_index("v"); k=7/R[["DD 21-24","DD 25-26"]].max(axis=1); R["$ 21-24"]=R["%м 21-24"]*k*1000; R["$ 25-26"]=R["%м 25-26"]*k*1000
R.to_csv("out_oos/LAB269_PEAK_REVERSAL.csv"); pd.set_option("display.width",320)
c=[x for x in R.columns if not x.startswith(("%м","DD"))]
print(R[c].round(2).to_string())
