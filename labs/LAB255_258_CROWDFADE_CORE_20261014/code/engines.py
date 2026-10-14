import os, itertools
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L, engD3 as D3
TLD=dict(mtr=np.zeros(L.N,int),ci=np.zeros(L.N,int),swl=None,swh=None,catr=None)
RAW=L.C["raw"][7.5]; idx=L.BT
months=pd.Index(sorted(set(idx.tz_convert("UTC").strftime("%Y-%m"))))[:-1]
def al(s):
    s=s[~s.index.duplicated(keep="last")]; return s.reindex(s.index.union(idx)).ffill().reindex(idx).ffill().fillna(0.0)
def monthly(eq): 
    m=al(eq).groupby(idx.tz_convert("UTC").strftime("%Y-%m")).last(); return m.diff().fillna(m.iloc[0]).reindex(months)
def v157(srcs):
    raw=RAW[RAW.source.isin(srcs)].reset_index(drop=True)
    if raw.empty: return None
    t,e,_,_=L.replay(7.5,{},TLD,raw=raw)
    return al(pd.Series(e.equity_r.to_numpy(),index=pd.DatetimeIndex(e.time)))
td,eqD=D3.sim(48,3); D_eq=al(eqD)*0.10
V4=["A","B3_HIGH","R48_HIGH","EARLY_EPISODE"]
# standalone monthly per engine
solo={}
for s in V4: solo[s]=monthly(v157([s]))*0.25
solo["D"]=monthly(eqD)*0.10
S=pd.DataFrame(solo)
seg=np.where(S.index<"2025-01","2021-24","2025-26")
pd.set_option("display.width",250)
for sg in ["2021-24","2025-26"]:
    x=S[seg==sg]
    print(f"\n=== {sg}: кожен двигун окремо (ризик як у портфелі)")
    print(pd.DataFrame({"%/міс":x.mean(),"Шарп":x.mean()/x.std()*np.sqrt(12),"збитк. міс.":(x<0).mean()}).round(2).T.to_string())
    print("кореляція по місяцях:"); print(x.corr().round(2).to_string())
# all subsets
rows=[]
ENG=V4+["D"]
for r in range(1,6):
    for sub in itertools.combinations(ENG,r):
        vs=[s for s in sub if s!="D"]
        E=(v157(vs)*0.25 if vs else pd.Series(0.0,index=idx))+(D_eq if "D" in sub else 0.0)
        m=E.groupby(idx.tz_convert("UTC").strftime("%Y-%m")).last(); m=m.diff().fillna(m.iloc[0]).reindex(months)
        for sg,(a,b) in {"2021-24":(None,"2025-01"),"2025-26":("2025-01",None)}.items():
            mm=m[(m.index<b) if a is None else (m.index>=a)]
            em=E[(idx<pd.Timestamp("2025-01-01",tz="UTC")) if a is None else (idx>=pd.Timestamp("2025-01-01",tz="UTC"))]; em=em-em.iloc[0]
            dd=float((em.cummax()-em).max())
            rows.append(dict(engines="+".join(x.replace("_HIGH","").replace("EARLY_EPISODE","EARLY") for x in sub),n=r,seg=sg,pct_mo=mm.mean(),dd=dd,ret_dd=mm.sum()/dd if dd>0 else np.nan,sharpe=mm.mean()/mm.std()*np.sqrt(12),losing=(mm<0).mean()))
R=pd.DataFrame(rows)
P=R.pivot_table(index=["n","engines"],columns="seg",values=["pct_mo","dd","sharpe","losing"],sort=False).round(2)
print("\n=== комбінації (v157-двигуни 0.25%, D 0.10%)"); print(P.to_string())
R.to_csv("out_oos/ENGINE_SUBSETS.csv",index=False); S.to_csv("out_oos/ENGINE_MONTHLY.csv")
