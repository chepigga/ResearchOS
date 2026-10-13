"""Create a full-period (2021-2026) copy of the canonical CrowdFade lab chain with thresholds FROZEN on TRAIN (<2025-01-01).
Usage: python patch_full_chain.py <src_repo_root_on_branch_lab157> <dst_root>
Verified: signals before 2025 == canonical 506 (+1 R48 at 2024-12-31 from data-edge)."""
import glob, shutil, sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
if (dst/"labs").exists(): shutil.rmtree(dst/"labs")
shutil.copytree(src/"labs", dst/"labs")
def patch(pat, pairs):
    p = glob.glob(str(dst/"labs"/pat))[0]; s = open(p).read()
    for a, b in pairs:
        assert a in s, (p, a[:60]); s = s.replace(a, b)
    open(p, "w").write(s)
patch("LAB132*/run_lab132.py", [("p=p[p.time<TRAIN_END].copy().reset_index(drop=True)\nf=f[f.time<TRAIN_END].copy().reset_index(drop=True)", "# FULL: no TRAIN cut")])
patch("LAB134*/run_lab134.py", [("A.df[(A.df['split']=='TRAIN') & (A.df.phase", "A.df[(A.df['split'].isin(['TRAIN','OOS'])) & (A.df.phase")])
patch("LAB136*/run_lab136.py", [
 ("b=b[b.time<TRAIN_END].copy().reset_index(drop=True)", "b=b.copy().reset_index(drop=True)"),
 ("f=f[f.time<TRAIN_END].sort_values('time')", "f=f.sort_values('time')"),
 ("oi120=pd.Series(BOI).pct_change(24)\nneg=(-oi120[oi120<0]).dropna()", "oi120=pd.Series(BOI).pct_change(24)\n_trm=(BT<TRAIN_END).to_numpy()\nneg=(-oi120[(oi120<0)&_trm]).dropna()")])
patch("LAB137*/run_lab137.py", [
 ("thr={\n    'break_depth_q60':float(df.breakout_depth", "_dfall=df\ndf=df[pd.to_datetime(df.signal_time,utc=True)<pd.Timestamp('2025-01-01',tz='UTC')]\nthr={\n    'break_depth_q60':float(df.breakout_depth"),
 ("(OUT/'LAB137_thresholds.json').write_text(json.dumps(thr,indent=2))", "(OUT/'LAB137_thresholds.json').write_text(json.dumps(thr,indent=2))\ndf=_dfall")])
patch("LAB148*/run_lab148.py", [
 ("while i<len(b)-MAX_H*12-2 and BT.iloc[i]<TRAIN_END:", "while i<len(b)-MAX_H*12-2:"),
 ("and BT.iloc[j]<TRAIN_END and abs(BZ[j])", "and abs(BZ[j])"),
 ('thr={\n    "age_q40":float(df.episode_age_min', '_dfall=df\ndf=df[pd.to_datetime(df.entry_time,utc=True)<TRAIN_END]\nthr={\n    "age_q40":float(df.episode_age_min'),
 ('(OUT/"LAB148_thresholds.json").write_text(json.dumps(thr,indent=2))', '(OUT/"LAB148_thresholds.json").write_text(json.dumps(thr,indent=2))\ndf=_dfall')])
patch("LAB149*/run_lab149.py", [("    if cost==2.81 and len(full)!=282:", "    if False:  # FULL period: TRAIN parity guard disabled")])
print("full chain ready at", dst/"labs")
