#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re
from pathlib import Path

ROOT=Path('research/gc/mt5')
SENSOR=ROOT/'AMP_GC_AEIF_SHADOW_SENSOR_001.mq5'
XAU=ROOT/'XAU_AEIF_SHADOW_EXECUTOR_001.mq5'
OUT=ROOT/'SHADOW_BUILD_MANIFEST_001.json'

FORBIDDEN=[
    r'\bOrderSend\s*\(', r'\bOrderSendAsync\s*\(', r'\bCTrade\b', r'\bMqlTradeRequest\b',
    r'\bPositionOpen\s*\(', r'\bPositionClose\s*\(', r'\bTRADE_ACTION_',
    r'\.Buy\s*\(', r'\.Sell\s*\('
]

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def executable_text(s:str)->str:
    # Static governance check only: ignore full-line // comments.
    return '\n'.join(line for line in s.splitlines() if not line.lstrip().startswith('//'))

def must(text:str, needles:list[str], label:str):
    missing=[x for x in needles if x not in text]
    if missing: raise SystemExit(f'{label} missing frozen invariants: {missing}')

def main():
    sensor=SENSOR.read_text(encoding='utf-8')
    xau=XAU.read_text(encoding='utf-8')
    exec_all=executable_text(sensor+'\n'+xau)
    hits=[pat for pat in FORBIDDEN if re.search(pat,exec_all)]
    if hits: raise SystemExit(f'FORBIDDEN TRADE API FOUND: {hits}')

    must(sensor,[
        'COPY_TICKS_TRADE','TICK_FLAG_BUY','TICK_FLAG_SELL','Quantile240(g_hist_delta,0.10',
        'Quantile240(g_hist_delta,0.90','Quantile240(g_hist_sell_loc,0.75',
        'Quantile240(g_hist_buy_loc,0.75','dn_eff<=0.15','up_eff<=0.15',
        'g_atr14=((13.0*g_atr14)+tr)/14.0','g_pending[i].offset=2','confirm_bar_msc+M5_MS'
    ],'sensor')
    must(xau,[
        'COPY_TICKS_ALL','InpMaxSignalAgeMs     = 5000','TP_R 3.0','HOLD_MS 14400000ULL',
        'BUSY_SINGLE_POSITION','q.ask','q.bid','ComputeATR20PrevClosed'
    ],'xau')

    result={
        'lab':'AMP_NATIVE_AEIF_FORWARD_SHADOW_001',
        'status':'STATIC_SAFETY_AND_FREEZE_AUDIT_PASS',
        'zero_order_api_calls':True,
        'sensor_sha256':sha(SENSOR),
        'xau_shadow_sha256':sha(XAU),
        'transport':'MT5 FILE_COMMON same-machine v001',
        'compile_status':'REQUIRES_METAEDITOR_COMPILE_ON_TARGET_WINDOWS_MT5',
        'note':'Static audit verifies frozen tokens and absence of order APIs; it is not an MQL5 compiler.'
    }
    OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
