#!/usr/bin/env python3
import argparse,re,json
from pathlib import Path
import pandas as pd

MARKERS=[
'D1_PARITY','EMA_PARITY','PRE_SCORE_BTC','SMART_MOCK','ORACLE_GATE_BLOCK',
'BOS_ONLY_BLOCK','KNIFE_BTC','LATE_ENTRY_BLOCK','EXEC_EVENT'
]

def ts(line):
    m=re.search(r'(20\d\d\.\d\d\.\d\d[ T]\d\d:\d\d:\d\d)',line)
    return m.group(1) if m else ''

def kvs(text):
    out={}
    for m in re.finditer(r'([A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]+\])?)\s*=\s*([^|\s,]+)',text):
        out[m.group(1)]=m.group(2)
    return out

def parse(path):
    rows=[]
    data=Path(path).read_text(errors='replace').splitlines()
    for ln in data:
        mk=next((m for m in MARKERS if m in ln),None)
        if not mk: continue
        row={'time':ts(ln),'marker':mk,'raw':ln.strip()}
        row.update(kvs(ln.split(mk,1)[1]))
        if mk=='PRE_SCORE_BTC':
            m=re.search(r'PRE_SCORE_BTC:\s*(-?\d+)',ln)
            if m: row['pre_score']=int(m.group(1))
        elif mk=='SMART_MOCK':
            for k,pat in [('action',r'action=([^\s|]+)'),('conf',r'conf=(\d+)'),('tag',r'tag=([^\s|]+)')]:
                m=re.search(pat,ln)
                if m: row[k]=m.group(1)
        elif mk=='ORACLE_GATE_BLOCK':
            m=re.search(r'action=([^\s]+)\s+reason=([^|]+)',ln)
            if m: row['action']=m.group(1); row['reason']=m.group(2).strip()
        rows.append(row)
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('log')
    ap.add_argument('--outdir',default='u01_parity_out')
    a=ap.parse_args(); out=Path(a.outdir); out.mkdir(parents=True,exist_ok=True)
    df=parse(a.log)
    df.to_csv(out/'v283_parity_rows.csv',index=False)
    counts=df.marker.value_counts().to_dict() if len(df) else {}
    summary={'rows':len(df),'marker_counts':counts,'required_markers':MARKERS,
             'missing_markers':[m for m in MARKERS if counts.get(m,0)==0]}
    (out/'v283_parity_log_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    if len(df): print('\n',df[['time','marker']].head(30).to_string(index=False))
if __name__=='__main__': main()
