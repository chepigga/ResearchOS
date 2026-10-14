"""LAB262 (pre-registered): D2 exit management. Entry = D2 at next M5 open. 1R = stop distance (3 H1ATR unless noted).
Variants (all max 2 D positions, 2nd same side & MTM>=0, cost 7.5bps, risk 0.10%/R):
 X0  current: SL3, trail stop=peak-3R after peak>=2R, 48h
 NS  'no stop': catastrophic SL 10 ATR (R still = 3 ATR for sizing), trail as X0, 48h
 NSt no stop, no trail, 48h
 CH3/CH45/CH6 chandelier: stop = max(initial SL3, highest-high since entry - m*ATR_now), active from entry, 48h
 P2/P3  partial: close 50% at +2R / +3R, runner stop -> entry (BE), trail as X0, 48h
 RE  re-entry: X0 + after a position closes in profit, if crowd still against (side*z6<=-1) and H4 EMA with side -> new D trade (max 2 re-entries per signal)
 P2RE  P2 + re-entry
 EXT winners extension: X0, but at 48h close only if MTM<+1R; others keep trailing up to 96h
 EXTRE EXT + re-entry
Select by 2021-24 portfolio (A+B3+D) ret/DD; 2025-26 shown; money $100k at worst DD 7%."""
import numpy as np,pandas as pd
exec(open("sw260.py").read().split("\nrows=[]")[0])
z6=g["z6"]
EN=entries("NOW",0,"ATR3")
def sim(cfg):
    stopm=cfg.get("stop",3.0); R_atr=3.0; trail=cfg.get("trail","3R"); ch=cfg.get("ch"); H=cfg.get("H",48)
    part=cfg.get("part"); ext=cfg.get("ext"); re=cfg.get("re",0)
    sig={}
    for ei,sd,e,d,a in EN: sig.setdefault(ei,[]).append((sd,0))
    act=[]; done=[]; eq=np.zeros(N); real=0.0
    mt=lambda q,px:q["w"]*(q["s"]*(px-q["e"])-q["c"])/q["R"]+q["bank"]
    first=min(sig)
    for i in range(first,N):
        for sd,gen in sig.get(i,[]):
            if len(act)==0 or (len(act)==1 and act[0]["s"]==sd and mt(act[0],BO[i])>=0):
                a=BA[i]; e=BO[i]; R=R_atr*a
                act.append(dict(s=sd,e=e,R=R,a0=a,c=COST/1e4*e,stp=e-sd*stopm*a,pk=0.0,hh=e,i0=i,end=i+H*12-1,w=1.0,bank=0.0,half=False,gen=gen))
        keep=[]
        for q in act:
            s_,e,R=q["s"],q["e"],q["R"]; res=None
            hit=(BL[i]<=q["stp"]) if s_>0 else (BH[i]>=q["stp"])
            if hit: res=s_*(q["stp"]-e)
            else:
                fav=(BH[i]-e) if s_>0 else (e-BL[i]); q["pk"]=max(q["pk"],fav/R)
                if part and not q["half"] and q["pk"]>=part:
                    q["bank"]=0.5*(part-q["c"]/R); q["w"]=0.5; q["half"]=True
                    q["stp"]=max(q["stp"],e) if s_>0 else min(q["stp"],e)
                if trail=="3R" and q["pk"]>=2:
                    ns=e+s_*(q["pk"]-3)*R; q["stp"]=max(q["stp"],ns) if s_>0 else min(q["stp"],ns)
                if ch:
                    ext_px=e+s_*q["pk"]*R; ns=ext_px-s_*ch*BA[i]; q["stp"]=max(q["stp"],ns) if s_>0 else min(q["stp"],ns)
                if i>=q["end"]:
                    m=(s_*(BC[i]-e)-q["c"])/R
                    if ext and m>=1.0 and i<q["i0"]+96*12-1: pass
                    else: res=s_*(BC[i]-e)
            if res is None: keep.append(q); continue
            r=q["w"]*(res-q["c"])/R+q["bank"]; real+=r
            done.append(dict(entry_i=q["i0"],net_r=r,gen=q["gen"],h=(i-q["i0"])/12))
            if re and r>0 and q["gen"]<re and np.isfinite(z6[i]) and s_*z6[i]<=-1 and TR4[i]==s_ and i+1<N:
                sig.setdefault(i+1,[]).append((s_,q["gen"]+1))
        act=keep; eq[i]=real+sum(mt(q,BC[i]) for q in act)
    eq[:first]=0
    return pd.DataFrame(done),pd.Series(eq,index=pd.DatetimeIndex(BT))
V={"X0 зараз":{},"NS без стопа (аварійний 10 ATR) + трейл":{"stop":10},"NSt без стопа, без трейлу":{"stop":10,"trail":None},
   "CH3 динамічний трейл 3 ATR":{"trail":None,"ch":3},"CH45 динамічний трейл 4.5 ATR":{"trail":None,"ch":4.5},"CH6 динамічний трейл 6 ATR":{"trail":None,"ch":6},
   "P2 50% на +2R, раннер БУ":{"part":2},"P3 50% на +3R, раннер БУ":{"part":3},
   "RE повторний вхід":{"re":2},"P2RE 50% на +2R + повторний вхід":{"part":2,"re":2},
   "EXT прибуткові до 96 год":{"ext":True},"EXTRE прибуткові до 96 год + повторний вхід":{"ext":True,"re":2}}
rows=[]
for nm,cfg in V.items():
    t,e=sim(cfg); tot=AB+e*0.10; r=dict(v=nm)
    for seg,mk,mo in [("21-24",BT<TE,48),("25-26",BT>=TE,19.3)]:
        x=tot[mk]; x=x-x.iloc[0]; dd=float((x.cummax()-x).max()); tt=t[(BT[t.entry_i.to_numpy(int)]<TE)==(seg=="21-24")]
        r.update({f"угод {seg}":len(tt)/mo,f"повт. {seg}":(tt.gen>0).sum()/mo,f"EV {seg}":tt.net_r.mean(),f"утрим {seg}":tt.h.mean(),f"R/DD {seg}":x.iloc[-1]/dd,f"%м {seg}":x.iloc[-1]/mo,f"DD {seg}":dd})
    rows.append(r); print(nm,flush=True)
R=pd.DataFrame(rows).set_index("v"); k=7/R[["DD 21-24","DD 25-26"]].max(axis=1); R["$ 21-24"]=R["%м 21-24"]*k*1000; R["$ 25-26"]=R["%м 25-26"]*k*1000
R.to_csv("out_oos/LAB262_EXITS.csv")
pd.set_option("display.width",320)
print(R[["угод 21-24","повт. 21-24","EV 21-24","утрим 21-24","R/DD 21-24","EV 25-26","R/DD 25-26","DD 21-24","DD 25-26","$ 21-24","$ 25-26"]].round(2).to_string())
