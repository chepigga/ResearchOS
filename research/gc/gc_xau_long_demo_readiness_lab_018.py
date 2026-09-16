#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path('research/gc')
P13=ROOT/'GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H.json'
P14=ROOT/'GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H.json'
P17=ROOT/'GC_XAU_PREFILL_APPROACH_SHAPE_ACCELERATION_LAB_017.json'
SPEC=ROOT/'GC_XAU_LONG_DEMO_EXECUTION_SPEC_001.json'
OUTJ=ROOT/'GC_XAU_LONG_DEMO_READINESS_LAB_018.json'
OUTM=ROOT/'GC_XAU_LONG_DEMO_READINESS_LAB_018.md'

def load(p): return json.loads(p.read_text(encoding='utf-8'))

def main():
    a=load(P13); b=load(P14); c=load(P17); spec=load(SPEC)
    amp=b['detail']['AMP_ALL']
    d13=a['one_active_semantic_diagnostic']['detail']['D1.00_E3M']['corrected_order_start_busy_clock']
    overlay_pass=c['status']=='HISTORICAL_CAUSAL_ACCELERATION_GATE_PASS_NOT_OOS' and all(c['gates'].values())
    chosen='D1.00_E3M_BARE_CORRECTED' if not overlay_pass else 'D1.00_E3M_PLUS_LAB017_ACCELERATION_GATE'
    # Readiness freeze says failed optional overlay is discarded; baseline metrics decide readiness.
    current_cost=0.05
    sumr=float(amp['observed_sum_r']); fills=int(amp['accepted_fills']); signals=int(amp['signals'])
    def stress(total_cost):
        extra=max(0.0,total_cost-current_cost)
        s=sumr-extra*fills
        return {'total_cost_r_per_fill':total_cost,'sum_r':s,'ev_r_per_signal':s/signals}
    s10=stress(0.10); s15=stress(0.15); s20=stress(0.20); s25=stress(0.25)
    break_even_total=current_cost+sumr/fills
    replay_exact=a['status']=='HISTORICAL_REPLAY_PASS' and all(a['gates'].values())
    no_lookahead=bool(spec['clock']['no_lookahead']) and not overlay_pass
    late_ev=float(d13['late_ev_r_per_original_signal'])
    gates={
      'historical_replay_exact': bool(replay_exact),
      'historical_ev_positive': float(amp['observed_ev_r_per_signal'])>0,
      'loo_week_min_positive': float(amp['leave_one_week_out_min_ev'])>0,
      'bootstrap_p_positive_ge95': float(amp['bootstrap_p_ev_gt_0'])>=0.95,
      'risk_p95_dd_025_le4pct': float(amp['bootstrap_dd_p95_pct_at_025risk'])<=4.0,
      'stress_cost_010_positive': s10['ev_r_per_signal']>0,
      'stress_cost_015_nonnegative': s15['ev_r_per_signal']>=0,
      'late_half_positive': late_ev>0,
      'execution_no_lookahead': no_lookahead,
      'implementation_spec_frozen': SPEC.exists() and spec.get('spec')=='GC_XAU_LONG_DEMO_EXECUTION_SPEC_001'
    }
    ready=all(gates.values())
    status='READY_FOR_FTMO_DEMO_SHADOW' if ready else 'NOT_READY_FOR_FTMO_DEMO_SHADOW'
    result={
      'lab':'GC_XAU_LONG_DEMO_READINESS_LAB_018',
      'status':status,
      'chosen_candidate':chosen,
      'optional_lab017_overlay_adopted':overlay_pass,
      'baseline':{
        'signals':signals,'accepted_signals':int(amp['accepted_signals']),'fills':fills,
        'ev_r_per_signal':float(amp['observed_ev_r_per_signal']),'sum_r':sumr,
        'observed_max_dd_r':float(amp['observed_max_dd_r']),
        'late_ev_r_per_signal':late_ev,
        'loo_week_min_ev':float(amp['leave_one_week_out_min_ev']),
        'bootstrap_p_ev_gt0':float(amp['bootstrap_p_ev_gt_0']),
        'bootstrap_dd_p95_pct_at_025risk':float(amp['bootstrap_dd_p95_pct_at_025risk'])
      },
      'cost_stress':{'0.10R':s10,'0.15R':s15,'0.20R_diagnostic':s20,'0.25R_diagnostic':s25,'break_even_total_cost_r_per_fill':break_even_total},
      'risk_for_demo_percent':0.25,
      'gates':gates,
      'governance':{
        'new_market_data':False,'independent_oos':False,'signal_retuned':False,
        'execution_depth_retuned':False,'lab017_rejected_if_failed':not overlay_pass,
        'demo_is_forward_oos_phase':True,'live_or_funded_authorized':False
      }
    }
    OUTJ.write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=[f"# GC_XAU_LONG_DEMO_READINESS_LAB_018\n\n**Status: {status}**\n",f"Chosen: **{chosen}**",f"LAB017 overlay adopted: **{overlay_pass}**\n","## Frozen baseline",f"- Signals / accepted / fills: **{signals} / {amp['accepted_signals']} / {fills}**",f"- EV/signal: **{amp['observed_ev_r_per_signal']:+.5f}R**",f"- SumR: **{sumr:+.2f}R**",f"- LOO-week minimum EV: **{amp['leave_one_week_out_min_ev']:+.5f}R**",f"- Bootstrap P(EV>0): **{amp['bootstrap_p_ev_gt_0']:.2%}**",f"- p95 DD @0.25% risk: **{amp['bootstrap_dd_p95_pct_at_025risk']:.3f}%**",f"- Corrected late-half EV: **{late_ev:+.5f}R/signal**\n","## Cost stress",f"- total 0.10R/fill: **EV {s10['ev_r_per_signal']:+.5f}R/signal**",f"- total 0.15R/fill: **EV {s15['ev_r_per_signal']:+.5f}R/signal**",f"- total 0.20R/fill diagnostic: **EV {s20['ev_r_per_signal']:+.5f}R/signal**",f"- total 0.25R/fill diagnostic: **EV {s25['ev_r_per_signal']:+.5f}R/signal**",f"- historical break-even total execution cost: **{break_even_total:.3f}R/fill**\n","## Readiness gates"]
    for k,v in gates.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    if ready:
        lines += ["\n## Decision","The frozen LONG system is ready to be transferred to **FTMO Demo / shadow execution at 0.25% risk per trade**.","This is not live/funded promotion. The demo phase is the independent forward/OOS and implementation/slippage test."]
    OUTM.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
