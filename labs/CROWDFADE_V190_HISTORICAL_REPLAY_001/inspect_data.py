from pathlib import Path
import pandas as pd, zipfile, json, os
root=Path('labs/CROWDFADE_V190_HISTORICAL_REPLAY_001/data')
rows=[]
for zpath in sorted(root.glob('*.zip')):
    with zipfile.ZipFile(zpath) as z:
        names=z.namelist()
        rows.append({'zip':zpath.name,'members':names[:20],'n_members':len(names)})
        out=root/(zpath.stem+'_unz')
        z.extractall(out)
for f in sorted(root.rglob('*.csv')):
    try:
        d=pd.read_csv(f,nrows=5)
        rows.append({'file':str(f),'columns':list(d.columns),'sample':d.head(2).to_dict('records')})
    except Exception as e:
        rows.append({'file':str(f),'error':repr(e)})
Path('labs/CROWDFADE_V190_HISTORICAL_REPLAY_001/DATA_INSPECT.json').write_text(json.dumps(rows,indent=2,default=str))
print(json.dumps(rows,indent=2,default=str)[:20000])
