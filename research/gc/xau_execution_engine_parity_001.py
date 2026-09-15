#!/usr/bin/env python3
from pathlib import Path
import json
import pandas as pd
from amp_native_aeif_xau_ev_001 import load_xau, simulate_one, single_position, summarize

ROOT=Path('research/gc')
RITH=ROOT/'RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CONFIRMED_EVENTS.csv'
OUT=ROOT/'XAU_EXECUTION_ENGINE_PARITY_001.json'
OUTMD=ROOT/'XAU_EXECUTION_ENGINE_PARITY_001.md'


def main():
    r=pd.read_csv(RITH)
    r['entry_eligible_utc']=pd.to_datetime(r.entry_eligible_utc,utc=True)
    r['xau_target_file_time']=r.entry_eligible_utc.dt.tz_convert(None)+pd.Timedelta(hours=2)
    x,m=load_xau(); times=set(x.t)
    r=r[r.xau_target_file_time.isin(times)].copy().sort_values('xau_target_file_time')
    gross=[]
    for e in r.itertuples(index=False):
        tr=simulate_one(e,x,m,False)
        if tr is not None: gross.append(tr)
    kept=single_position(gross)
    df=pd.DataFrame(kept)
    s=summarize(df.rename(columns={'r':'gross_r'}),'gross_r') if len(df) else {'n':0}
    result={'lab':'XAU_EXECUTION_ENGINE_PARITY_001','exact_timestamp_inputs':int(len(r)),'single_position':s,
            'expected_historical':{'n':46,'ev_r':0.666,'sum_r':30.63,'pf':2.33,'max_dd_r':3.32},
            'parity_count':s.get('n')==46,
            'parity_ev':(abs(s.get('ev_r',999)-0.666)<=0.02 if s.get('ev_r') is not None else False)}
    OUT.write_text(json.dumps(result,indent=2),encoding='utf-8')
    md=f"""# XAU_EXECUTION_ENGINE_PARITY_001\n\n- historical exact-timestamp Rithmic inputs: **{len(r)}**\n- reconstructed single-position N: **{s.get('n')}** vs expected **46**\n- EV: **{s.get('ev_r')}R** vs expected **+0.666R**\n- SumR: **{s.get('sum_r')}R** vs expected **+30.63R**\n- PF: **{s.get('pf')}** vs expected **2.33**\n- MaxDD: **{s.get('max_dd_r')}R** vs expected **3.32R**\n\nCount parity: **{result['parity_count']}**  \nEV parity: **{result['parity_ev']}**\n"""
    OUTMD.write_text(md,encoding='utf-8'); print(md); print(json.dumps(result,indent=2))

if __name__=='__main__': main()
