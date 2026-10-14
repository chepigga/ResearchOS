"""LAB256 engine P (pre-registered before run).
Signal at M5 close i: close breaks the high (long) / low (short) of the previous L hours of M5 bars (excl. bar i).
Crowd filter: sd*z6[i] <= -zc (crowd stands against the breakout); zc=None -> pure breakout control.
Optional z24 same rule (z24c). Cooldown: no new same-side signal for 12h after a signal.
Exit = D: SL 3*H1ATR, trail 3R from peak after +2R, 48h. Max 2 pos (2nd same side, MTM>=0). Cost 7.5bps. Risk 0.10%.
Selection: portfolio A+B3+D(current)+P ret/DD on 2021-24. OOS 2025-26 reported only."""
import io,contextlib,itertools,numpy as np,pandas as pd
src=open("trendalt.py").read(); src2=src[:src.index("rows=[]")]
g={}
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src2,"ta","exec"),g)
BT,BO,BH,BL,BC,BA,N,TE,AB,al,simD,WV=[g[k] for k in "BT BO BH BL BC BA N TE AB al simD WV".split()]
z6,z24=g["z6"],g["z24"]; E=g["E"]
tD,eD=simD(E.SIG); DCUR=al(eD)*0.10
wdir=np.zeros(N,int); wpos=np.full(N,np.nan)
for i0,i1,d,tr in WV: wdir[i0:i1]=d; wpos[i0:i1]=(np.arange(i0,i1)-i0)/(i1-i0)
HI={L:pd.Series(BH).rolling(L*12).max().shift(1).to_numpy() for L in (12,24,48)}
LO={L:pd.Series(BL).rolling(L*12).min().shift(1).to_numpy() for L in (12,24,48)}
def build(L,zc,z24c):
    up=np.where(BC>HI[L])[0]; dn=np.where(BC<LO[L])[0]
    c=sorted([(i,1) for i in up]+[(i,-1) for i in dn]); out=[]; last={1:-10**9,-1:-10**9}
    for i,sd in c:
        if i<400 or i>N-1000 or i-last[sd]<144: continue
        if zc is not None and not(np.isfinite(z6[i]) and sd*z6[i]<=-zc): continue
        if z24c is not None and not(np.isfinite(z24[i]) and sd*z24[i]<=-z24c): continue
        out.append((i,sd)); last[sd]=i
    return out
rows=[]
for L,zc,z24c in itertools.product((12,24,48),(None,0.0,0.5,1.0,1.5),(None,0.0,0.5)):
    if zc is None and z24c is not None: continue
    SIG=build(L,zc,z24c); t,e=simD(SIG); P=al(e)*0.10
    si=np.array([i for i,_ in SIG]); ss=np.array([s for _,s in SIG])
    r=dict(L=L,zc="-" if zc is None else zc,z24c="-" if z24c is None else z24c)
    for seg,mask,mo in [("TR",BT<TE,48),("OOS",BT>=TE,19.3)]:
        tt=t[(BT[t.entry_i.to_numpy(int)]<TE)==(seg=="TR")]
        Pm=P[mask]; Pm=Pm-Pm.iloc[0]; ddP=float((Pm.cummax()-Pm).max())
        tot=(AB+DCUR+P)[mask]; tot=tot-tot.iloc[0]; dd=float((tot.cummax()-tot).max())
        sm=(BT[si]<TE)==(seg=="TR"); ii=si[sm]; s=ss[sm]
        mP=Pm.groupby(Pm.index.strftime("%Y-%m")).last().diff(); dm=(DCUR[mask]-DCUR[mask].iloc[0]); mD=dm.groupby(dm.index.strftime("%Y-%m")).last().diff()
        r.update({f"n_{seg}":len(tt)/mo,f"ev_{seg}":tt.net_r.mean(),f"Rmo_{seg}":tt.net_r.sum()/mo,f"Rdd_{seg}":Pm.iloc[-1]/ddP if ddP>0 else np.nan,
                  f"early_{seg}":((wdir[ii]==s)&(wpos[ii]<1/3)).mean(),f"prec_{seg}":(wdir[ii][wdir[ii]!=0]==s[wdir[ii]!=0]).mean(),
                  f"corrD_{seg}":mP.corr(mD),f"port_pct_{seg}":tot.iloc[-1]/mo,f"port_dd_{seg}":dd,f"port_rdd_{seg}":tot.iloc[-1]/dd})
    rows.append(r)
R=pd.DataFrame(rows); R.to_csv("out_oos/ENGINE_P_GRID.csv",index=False)
pd.set_option("display.width",320)
c=["L","zc","z24c","n_TR","ev_TR","Rmo_TR","Rdd_TR","early_TR","prec_TR","n_OOS","ev_OOS","Rmo_OOS","Rdd_OOS","early_OOS","corrD_TR","corrD_OOS","port_rdd_TR","port_rdd_OOS"]
print(R[c].round(2).to_string(index=False))
