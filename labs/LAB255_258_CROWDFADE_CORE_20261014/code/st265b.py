import io,contextlib,numpy as np,pandas as pd
st=pd.read_pickle("st265_store.pkl")
src=open("dtune.py").read().split("rows=[]")[0]; g={}
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src,"dt","exec"),g)
BT,TE,AB,al,build,simD=[g[k] for k in "BT TE AB al build simD".split()]
t,e=simD(build(1.5,0.5,True,None,None)); CORE=AB+al(e)*0.10
idx=pd.DatetimeIndex(BT)
def eq(A):
    ex=idx[A.si.to_numpy(int)+1]+pd.to_timedelta(A.h,unit="h")
    s=pd.Series(A.r.to_numpy(),index=ex).sort_index().cumsum(); s=s[~s.index.duplicated(keep="last")]
    return s.reindex(s.index.union(idx)).ffill().reindex(idx).fillna(0)
def stat(s,mo):
    x=s-s.iloc[0]; dd=float((x.cummax()-x).max()); return x.iloc[-1]/mo,dd
cells=[("1h",1.3,True),("1h",1.8,True),("2h",1.3,True),("2h",1.8,True)]
cm=CORE.groupby(idx.strftime("%Y-%m")).last().diff()
print("ядро A+B3+D2: ",[tuple(round(v,2) for v in stat(CORE[m],mo)) for m,mo in [(idx<TE,48),(idx>=TE,19.3)]])
for tf,sens,htf in cells:
    A=st[(tf,sens,htf,"RIDE")]
    for fn,mask in [("усі",np.ones(len(A),bool)),("без проти",~((A.cz==-A.side)&(A.az>=1)).to_numpy())]:
        E=eq(A[mask]); sm=E.groupby(idx.strftime("%Y-%m")).last().diff()
        line=f"ST {tf} sens{sens} HTF {fn:9s}:"
        for m,mo,lab in [(idx<TE,48,"21-24"),(idx>=TE,19.3,"25-26")]:
            Rmo,dd=stat(E[m],mo); line+=f" {lab} R/міс {Rmo:+.2f} DD {dd:.1f}R R/DD(рік) {Rmo*12/dd:.2f} |"
        line+=f" кор. з ядром {sm.corr(cm):+.2f}"
        print(line)
        if fn=="без проти":
            for w in (0.10,0.20,0.30):
                P=CORE+E*w; out=[]
                for m,mo in [(idx<TE,48),(idx>=TE,19.3)]: out+=list(stat(P[m],mo))
                k=7/max(out[1],out[3]); print(f"     ядро + ST ризик {w:.2f}%: %/міс {out[0]:.2f}/{out[2]:.2f} DD {out[1]:.2f}/{out[3]:.2f} -> $ {out[0]*k*1000:.0f} / {out[2]*k*1000:.0f}")
b=[stat(CORE[m],mo) for m,mo in [(idx<TE,48),(idx>=TE,19.3)]]; k=7/max(b[0][1],b[1][1]); print("ядро окремо $:",round(b[0][0]*k*1000),"/",round(b[1][0]*k*1000))
