import importlib.util, pickle, sys
from pathlib import Path
ROOT=Path("/home/claude/chepigga/full")
sp=importlib.util.spec_from_file_location("lab150",ROOT/"labs/LAB150_SELECTIVE_CONCURRENCY_OVERLAP_RISK_20261009/run_lab150.py")
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
L148=m.L148
out=dict(BT=m.BT.reset_index(drop=True),BO=m.BO,BH=m.BH,BL=m.BL,BC=m.BC,BA=L148.BA,BZ=L148.BZ,
         raw={c:m.raw_events(c) for c in (2.81,7.5)},TRAIN_END=L148.TRAIN_END)
pickle.dump(out,open("cache_full.pkl","wb"))
print(len(out["BT"]),out["BT"].iloc[0],out["BT"].iloc[-1],{c:len(v) for c,v in out["raw"].items()})
print(out["raw"][7.5].groupby("source").size())
print(out["raw"][7.5].entry_time.min(),out["raw"][7.5].entry_time.max())
