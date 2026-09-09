#!/usr/bin/env python3
"""Technical parser hotfix only; research specification and router logic are unchanged."""
from pathlib import Path
p=Path(__file__).with_name('run_lab.py')
src=p.read_text().replace("df=pd.read_csv(path)", "df=pd.read_csv(path,sep=';')")
ns={'__name__':'__main__','__file__':str(p)}
exec(compile(src,str(p),'exec'),ns,ns)
