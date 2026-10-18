"""LAB274: HINDSIGHT diagnostic (not tradable). Each engine's entries moved EARLIER by s hours (s=1,2,4,6), same side, same exit rules.
Measures the 'cost of lag' = upper bound of what an earlier trigger could add."""
import numpy as np,pandas as pd
exec(open("ct268.py").read().split("\nrows=[]; EQ={}")[0])
L_,TLD,RAW=g["g"]["L"],g["g"]["TLD"],g["g"]["RAW"]
cols=["source","entry_time","entry_i","side","atr","pri"]
MO={"2021-24":48,"2025-26":19.3}
def summ(name,sh,r,ii,risk):
    d=pd.DataFrame({"r":r,"seg":np.where(BT[ii]<TE,"2021-24","2025-26")})
    out=[]
    for seg,x in d.groupby("seg"): out.append(dict(engine=name,shift_h=sh,seg=seg,n_mo=len(x)/MO[seg],EV=x.r.mean(),usd_mo=x.r.sum()*risk*1000/MO[seg]))
    return out
rows=[]
for sh in (0,1,2,4,6):
    b=sh*12
    # A, B3 (72h runner), shifted raw entry
    raw=RAW[RAW.source.isin(["A","B3_HIGH"])][cols].copy(); raw["entry_i"]=raw.entry_i-b
    raw["atr"]=[BA[i] for i in raw.entry_i]; raw["entry_time"]=BT[raw.entry_i.to_numpy(int)]
    t,_,_,_=L_.replay(7.5,{"runner_h":72},TLD,raw=raw.reset_index(drop=True))
    for src,nm in [("A","A"),("B3_HIGH","B3")]:
        x=t[t.source==src]; rows+=summ(nm,sh,x.net_r.to_numpy(),x.entry_i.to_numpy(int),0.25)
    # D2 (SL3, trail, 48h, crowd exit) via shifted EN
    global EN
    EN0=entries("NOW",0,"ATR3")
    EN=[(ei-b,sd,BO[ei-b],3*BA[ei-b],BA[ei-b]) for ei,sd,e,d,a in EN0]
    tD=run_D(CMP,"PROFIT"); rows+=summ("D2",sh,tD.r.to_numpy(),tD.i.to_numpy(int),0.10)
    # S shifted
    S0=list(S2)
    S2=[(si-b,ei-b,sd,dist) for si,ei,sd,dist in S0]
    tS=run_S(EMAX,"ALWAYS"); rows+=summ("S",sh,tS.r.to_numpy(),tS.i.to_numpy(int),0.10)
    S2=S0
    print("shift",sh,flush=True)
R=pd.DataFrame(rows); R.to_csv("out_oos/LAB274_SHIFT.csv",index=False)
pd.set_option("display.width",250)
P=R.pivot_table(index=["engine","seg"],columns="shift_h",values=["EV","usd_mo"],sort=False).round(2)
print(P.to_string())
tot=R.groupby(["shift_h","seg"]).usd_mo.sum().unstack().round(0); print("\nРАЗОМ $/міс:"); print(tot.to_string())
# how much price moved in trade side during the 6h BEFORE actual D2 entries
EN0=entries("NOW",0,"ATR3"); pre=np.array([sd*(BO[ei]-BO[ei-72])/BA[ei] for ei,sd,e,d,a in EN0]); seg=np.array([BT[ei]<TE for ei,*_ in EN0])
print(f"\nрух ціни в бік угоди D2 за 6 год ДО входу: 2021-24 {pre[seg].mean():+.2f} ATR (медіана {np.median(pre[seg]):+.2f}), 2025-26 {pre[~seg].mean():+.2f} ATR (медіана {np.median(pre[~seg]):+.2f})")
