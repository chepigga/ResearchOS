import json
from pathlib import Path
import run_2026_stress as s

OUT=Path(__file__).resolve().parent/'output'

def main():
    arr=s.prep(); out={}
    for cfg in s.CANDS:
        rows={}
        for bps in [0,1,2,3,4,5]:
            s.COST_BPS=float(bps)
            d=s.sim(arr,cfg)
            rows[str(bps)]=s.stats(d.R.values)
        out[cfg['id']]={'config':cfg,'cost_bps':rows}
        print(cfg['id'],rows)
    (OUT/'stress_2026_cost_sensitivity.json').write_text(json.dumps(out,indent=2))
if __name__=='__main__':main()
