import importlib.util, pickle
from pathlib import Path
ROOT=Path("/home/claude/chepigga/full")
sp=importlib.util.spec_from_file_location("lab150",ROOT/"labs/LAB150_SELECTIVE_CONCURRENCY_OVERLAP_RISK_20261009/run_lab150.py")
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
L149=m.L149;L148=m.L148;L138=m.L138;A134=L138.A
out=dict(a_ev=A134.a_ev, a_all=A134.A.df, b_high=A134.b_high, b_bal=getattr(A134,"b_bal",None),
         r48_high=L138.r48_high, r48_bal=L138.r48_bal, r48_all=L138.R.df, r48_thr=L138.R.thr,
         res_all=L148.df, res_thr=L148.thr, BTi={str(t):i for i,t in enumerate(L148.BT)})
pickle.dump(out,open("extra.pkl","wb"))
for k,v in out.items():
    if hasattr(v,"columns"): print(k,len(v),list(v.columns)[:25])
print(out["r48_thr"],out["res_thr"])
