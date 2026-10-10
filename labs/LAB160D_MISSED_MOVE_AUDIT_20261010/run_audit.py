from pathlib import Path
import types,ast,json
from collections import Counter
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/LAB160D_20261010';OUT.mkdir(exist_ok=True)
cp=ROOT/'labs/LAB160C_GATE_RELAXATION_PROFILE_REPLAY_20261010/run_lab160c.py';g={'__file__':str(cp)}
exec(compile(cp.read_text().split('for cost in [7.5,2.81]:')[0],str(cp),'exec'),g)
A=g['A'];fn=g['fn'];raw=g['sets']['OLD'];eligible=g['sets']['OLD_PROFILE'];cut=pd.Timestamp('2025-01-01',tz='UTC');five=pd.Timedelta(minutes=5)
# Capture exact portfolio decisions, partial execution timestamps and full completed trades.
by={}
for _,r in eligible.sort_values(['entry_i','pri']).iterrows():by.setdefault(int(r.entry_i),[]).append(r)
active=[];closed=[];decisions=[]
for i in range(int(raw.entry_i.min()),int(raw.entry_i.max())+577):
 for r in by.get(i,[]):
  block='';allow=len(active)==0;addon=False
  if len(active)==1:
   if int(active[0]['side'])!=int(r.side):block='OPPOSITE_POSITION'
   elif fn.total_mtm_at_open(active[0],i)<0:block='FIRST_POSITION_MTM_NEGATIVE'
   else:allow=True;addon=True
  elif len(active)>=2:block='MAX_TWO_POSITIONS'
  decisions.append(dict(event_id=r.event_id,key=r.key,source=r.source,entry_time=r.entry_time,side=r.side,decision='ACCEPT' if allow else block,active_ids='|'.join(p['event_id'] for p in active)))
  if allow:
   if addon:fn.transfer_first_stop(active[0],'LOCK2_LOCK025')
   p=fn.init_pos(r,7.5,'LOCK2');p.update(event_id=r.event_id,key=r.key,partial_time=pd.NaT,partial_i=-1,profile_shape=r.profile_shape);active.append(p)
 alive=[]
 for p in active:
  was=p['partial'];done=fn.evaluate_bar(p,i)
  if p['partial'] and not was:p['partial_time']=A.BT.iloc[i]+five;p['partial_i']=i
  if done is None:alive.append(p)
  else:done['exit_bar_open']=A.BT.iloc[i];done['exit_observed_time']=A.BT.iloc[i]+five;closed.append(done)
 active=alive
 if i>int(raw.entry_i.max()) and not active:break
tr=pd.DataFrame(closed);dec=pd.DataFrame(decisions)
ref=pd.read_csv(ROOT/'results/LAB160C_20261010/LAB160C_trades.csv');ref=ref[(ref.variant=='OLD_PROFILE')&(ref.cost_bps==7.5)].set_index('event_id')
assert len(tr)==251 and set(tr.event_id)==set(ref.index)
assert np.max(np.abs(tr.set_index('event_id').net_r-ref.net_r))<1e-9
tr.to_csv(OUT/'LAB160D_execution_trades.csv',index=False);dec.to_csv(OUT/'LAB160D_portfolio_decisions.csv',index=False)
print('PORTFOLIO PARITY',len(tr),flush=True)
# Gate assessments are descriptive journals, not hypothetical fills.
journal=[]
def log(engine,start,assessed,side,stage,fail='',entry=pd.NaT,**kw):
 journal.append(dict(engine=engine,signal_time=start,assessment_time=assessed,side=int(side),stage=stage,failed_gates=fail,entry_time=entry,**kw))
# A full fresh-Z universe with all contemporaneous gate failures retained, plus SWING3 timing.
ix=np.flatnonzero((np.abs(A.BZ[1:])>=1)&(np.abs(A.BZ[:-1])<1))+1
for i in ix:
 if i>=len(A.b)-578 or A.BT.iloc[i]>=cut:continue
 r=A.b.iloc[i];side=-1 if A.BZ[i]>0 else 1;ts=A.BT.iloc[i]+five;fail=[]
 if int(r.trend)==0 or int(r.trend)==side:fail.append('H4_TREND')
 if not((side>0 and r.extension<0)or(side<0 and r.extension>0)) or abs(r.extension)<A.EXT80:fail.append('EXTENSION')
 if r.oi4h<A.OI70:fail.append('OI')
 if A.phase(int(r.trend_age),int(r.impulse_age)) not in ['CONT','REACCEL']:fail.append('PHASE')
 if fail:log('A',ts,ts,side,'GATED','|'.join(fail));continue
 ei,ti,_=A.swing3_entry(i,side)
 if ei is None:log('A',ts,A.BT.iloc[min(i+72,len(A.b)-2)]+five,side,'NO_CONFIRMATION','SWING3')
 else:log('A',ts,A.BT.iloc[ei],side,'PASS',entry=A.BT.iloc[ei])
# R48 complete breakout ladder. Cooldown is updated only after accepted4/6, exactly as LAB136.
b=g['b'];bc=b.close.to_numpy();bh=b.high.to_numpy();bl=b.low.to_numpy();ba=b.atr.to_numpy();oi=b.oi.to_numpy();bt=b.time;hi=g['hi'];lo=g['lo'];last=-9999
for i in range(577,len(b)-576-7):
 up=bc[i]>hi[i];down=bc[i]<lo[i]
 if up==down:continue
 side=1 if up else -1;ts=bt.iloc[i]+five
 if i-last<24:log('R48_HIGH',ts,ts,side,'GATED','COOLDOWN');continue
 boundary=hi[i] if up else lo[i];cl=bc[i+1:i+7];outside=cl>boundary if up else cl<boundary;assessed=bt.iloc[i+6]+five
 if outside.sum()<4:log('R48_HIGH',ts,assessed,side,'GATED','ACCEPT_4_OF_6');continue
 last=i;ei=i+7;mm=np.mean((cl-boundary)*side/ba[i]);oich=oi[ei]/oi[i]-1;retest=np.any(bl[i+1:i+7]<=boundary) if up else np.any(bh[i+1:i+7]>=boundary);fail=[]
 if mm<g['margin']:fail.append('ACCEPT_MARGIN')
 if retest:fail.append('RETEST')
 if oich<g['oit']:fail.append('OI')
 log('R48_HIGH',ts,bt.iloc[ei],side,'GATED' if fail else 'PASS','|'.join(fail),entry=bt.iloc[ei] if not fail else pd.NaT)
# B3 uses its own historical tape, not A's compressed flow alignment.
bp=ROOT/'labs/LAB132_B3_COUNTERTREND_ATTACK_EXHAUSTION_20261008/run_lab132.py';B=types.ModuleType('b3');B.__file__=str(bp)
exec(compile(bp.read_text().split('events=[]')[0],str(bp),'exec'),B.__dict__)
ix=np.flatnonzero((np.abs(B.BZ[1:])>=1)&(np.abs(B.BZ[:-1])<1))+1
for i in ix:
 if i>=len(B.b)-578:continue
 r=B.b.iloc[i];side=-1 if B.BZ[i]>0 else 1;ts=B.BT.iloc[i]+five
 if int(r.trend)==0 or int(r.trend_age)<4 or int(r.trend)!=side:log('B3_HIGH',ts,ts,side,'GATED','H4_TREND_OR_AGE');continue
 hits,levels=B.first_milestones(i,side,B.BA[i],.5)
 if hits is None:log('B3_HIGH',ts,B.BT.iloc[min(i+72,len(B.b)-2)]+five,side,'GATED','ATTACK_DEPTH');continue
 hit=hits[-1];crowd=-side;strength=abs(B.BZ[hit])-abs(B.BZ[i]) if np.sign(B.BZ[hit])==crowd else -abs(B.BZ[i]);oich=B.BOI[hit]/B.BOI[i]-1;fail=[]
 if strength<.25:fail.append('Z_STRENGTH')
 if not(np.isfinite(oich) and oich>0):fail.append('OI')
 intervals=np.diff(np.array([i]+list(hits)))
 if not(intervals[3]>intervals[2] and intervals[4]>intervals[3]):fail.append('TERMINAL_TWO_STEP')
 if fail:log('B3_HIGH',ts,B.BT.iloc[hit]+five,side,'GATED','|'.join(fail));continue
 reclaim=None
 for j in range(hit,min(hit+72,len(B.b)-2)+1):
  if B.BC[j]>levels[-2] if side>0 else B.BC[j]<levels[-2]:reclaim=j;break
 if reclaim is None:log('B3_HIGH',ts,B.BT.iloc[min(hit+72,len(B.b)-2)]+five,side,'NO_CONFIRMATION','RECLAIM')
 else:log('B3_HIGH',ts,B.BT.iloc[reclaim+1],side,'PASS',entry=B.BT.iloc[reclaim+1])
# EARLY_EPISODE original active-Z loop. Record contemporaneous blockers and the final age gate.
i=1;rescue_pass=[]
while i<len(A.b)-578 and A.BT.iloc[i]<cut:
 if abs(A.BZ[i])>=1 and abs(A.BZ[i-1])<1:
  sign=1 if A.BZ[i]>0 else -1;side=-sign;start=i;j=i+1
  while j<len(A.b)-578 and A.BT.iloc[j]<cut and abs(A.BZ[j])>=1 and (1 if A.BZ[j]>0 else -1)==sign and j-start<=144:
   r=A.b.iloc[j];fail=[];ts=A.BT.iloc[start]+five;now=A.BT.iloc[j]+five
   if int(r.trend)==0 or int(r.trend)==side:fail.append('H4_TREND')
   if A.phase(int(r.trend_age),int(r.impulse_age)) not in ['CONT','REACCEL']:fail.append('PHASE')
   if not((side>0 and r.extension<0)or(side<0 and r.extension>0)) or abs(r.extension)<A.EXT80:fail.append('EXTENSION')
   if r.oi4h<A.OI70:fail.append('OI')
   if fail:log('EARLY_EPISODE',ts,now,side,'GATED','|'.join(fail));j+=1;continue
   ei,ti,_=A.swing3_entry(j,side)
   if ei is None:log('EARLY_EPISODE',ts,A.BT.iloc[min(j+72,len(A.b)-2)]+five,side,'NO_CONFIRMATION','SWING3');j+=1;continue
   age=(A.BT.iloc[j]-A.BT.iloc[start]).total_seconds()/60;rescue_pass.append(age)
   log('EARLY_EPISODE',ts,A.BT.iloc[ei],side,'PASS' if age<=5 else 'GATED','' if age<=5 else 'EPISODE_AGE',entry=A.BT.iloc[ei] if age<=5 else pd.NaT,episode_age_minutes=age);break
  i=max(i+1,j)
 else:i+=1
assert float(np.quantile(rescue_pass,.4))==5
J=pd.DataFrame(journal);J['key']=J.engine+'|'+J.entry_time.astype(str)+'|'+J.side.astype(str)
parity={}
for engine in ['A','B3_HIGH','R48_HIGH','EARLY_EPISODE']:
 actual=Counter(raw.loc[raw.source==engine,'key']);recovered=Counter(J.loc[(J.engine==engine)&(J.stage=='PASS'),'key']);assert actual==recovered,(engine,len(actual),len(recovered),actual-recovered,recovered-actual);parity[engine]=sum(recovered.values())
J.to_csv(OUT/'LAB160D_gate_journal.csv',index=False);print('ALL GATE PARITY',parity,flush=True)
# Regular price-only grid and closed H1 ATR exactly following LAB160; no flow-based row deletion.
p=g['ps']['p'].set_index('time');p=p.loc['2020-12-28':].reindex(pd.date_range(pd.Timestamp('2020-12-28',tz='UTC'),p.index.max(),freq='5min'))
hour=p.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'});counts=p.close.resample('1h').count();hour.loc[counts!=12,:]=np.nan;prev=hour.close.shift();trange=pd.concat([hour.high-hour.low,(hour.high-prev).abs(),(hour.low-prev).abs()],axis=1).max(axis=1);trange[(counts!=12)|prev.isna()]=np.nan
atr=trange.rolling(14,min_periods=14).mean();atr.index+=pd.Timedelta(hours=1);p.index+=five;p['atr']=atr.reindex(p.index,method='ffill');p=p[(p.index>=pd.Timestamp('2021-01-01',tz='UTC'))&(p.index<cut)]
# Only fixed anchors are needed, no storage of overlapping all-M5 path arrays.
moves=[]
for h in [6,24,48]:
 for i in np.flatnonzero((p.index.asi8//(60*10**9))%(h*60)==0):
  if i+h*12>=len(p):continue
  v=p.iloc[i+1:i+h*12+1];refprice=p.close.iloc[i];scale=p.atr.iloc[i]
  if not np.isfinite(scale) or v.close.isna().any():continue
  u=(v.high.max()-refprice)/scale;d=(refprice-v.low.min())/scale;end=(v.close.iloc[-1]-refprice)/scale;side=1 if u>d or(u==d and end>=0) else -1;m=max(u,d)
  if m<3 or side*end<.5*m:continue
  peak=v.high.idxmax() if side>0 else v.low.idxmin();peakprice=v.high.max() if side>0 else v.low.min();peakopen=peak-five
  pre=p.loc[p.index[i]+five:peak-five];adverse=max(0,(refprice-pre.low.min())/scale) if side>0 else max(0,(pre.high.max()-refprice)/scale)
  moves.append(dict(definition=f'CLOCK_{h}H',start=p.index[i],peak=peak,cutoff=peakopen,end=v.index[-1],side=side,start_price=refprice,peak_price=peakprice,amplitude_atr=m,pre_adverse_atr=adverse,duration_h=(peak-p.index[i]).total_seconds()/3600))
# Alternating close pivots; confirmation after fixed ATR reversal, no future pivot as trading signal.
def legs(frame,reversal):
 c=frame.close.to_numpy();at=frame.atr.to_numpy();rows=[];valid=np.flatnonzero(np.isfinite(c+at));start=int(valid[0]);ext=start;direction=0
 for i in range(start+1,len(frame)):
  if not np.isfinite(c[i]+at[i]):start=i+1;ext=start;direction=0;continue
  if start>=len(frame) or not np.isfinite(c[start]+at[start]):start=i;ext=i;continue
  if direction==0:
   if abs(c[i]-c[start])>=reversal*at[start]:direction=1 if c[i]>c[start] else -1;ext=i
   continue
  if direction*(c[i]-c[ext])>0:ext=i
  elif direction*(c[ext]-c[i])>=reversal*at[ext]:
   amp=direction*(c[ext]-c[start])/at[start]
   if amp>=3:
    rows.append(dict(definition=f'LEG_REV{reversal:g}ATR',start=frame.index[start],peak=frame.index[ext],cutoff=frame.index[ext],end=frame.index[i],side=direction,start_price=c[start],peak_price=c[ext],amplitude_atr=amp,pre_adverse_atr=0.,duration_h=(frame.index[ext]-frame.index[start]).total_seconds()/3600))
   start=ext;direction=-direction;ext=i
 return rows
for rev in [1.,2.]:moves+=legs(p,rev)
M=pd.DataFrame(moves).sort_values(['definition','start']).reset_index(drop=True);M['move_id']=[f'M{i:05d}' for i in range(len(M))]
M.to_csv(OUT/'LAB160D_price_moves.csv',index=False)
# Trade mark-to-market curve at arbitrary closed-grid timestamp, including partial cash flows.
def value(row,t,price,net=True):
 if t<row.entry_time:return 0.
 cost=row.cost_r if net else 0.
 if t>=row.exit_observed_time:return row.net_r+row.cost_r-cost
 rr=int(row.side)*(price-row.entry)/row.atr
 if pd.notna(row.partial_time) and t>=row.partial_time:return 1.5+.5*rr-cost
 return rr-cost

def mark(t,is_clock=False):
 if is_clock:return float(p.loc[t+five,'open'])
 return float(p.loc[t,'close'])
rawtimes=raw.entry_time;eltimes=eligible.entry_time
records=[];relations=[]
for row in M.itertuples():
 start=row.start;end=row.cutoff;side=row.side;clock=row.definition.startswith('CLOCK');price_start=row.start_price;price_end=mark(end,clock)
 # Decisions at start belong to the forward window; a carried position is marked immediately before those entries.
 same=tr[tr.side==side];over=same[((same.entry_time<=end) if clock else (same.entry_time<end))&(same.exit_observed_time>start)].copy()
 old=over[over.entry_time<start];nowraw=raw[(raw.side==side)&(raw.entry_time>=start)&((raw.entry_time<=end) if clock else (raw.entry_time<end))];nowelig=eligible[(eligible.side==side)&(eligible.entry_time>=start)&((eligible.entry_time<=end) if clock else (eligible.entry_time<end))]
 if clock:
  atpeak=over[(over.entry_time<=end)&(over.exit_bar_open>end)];amb=over[over.exit_bar_open==end]
 else:
  atpeak=over[(over.entry_time<end)&(over.exit_observed_time>end)];amb=over[over.exit_observed_time==end]
 nearby=J[(J.side==side)&(J.signal_time>=start-pd.Timedelta(hours=12))&(J.signal_time<=end)]
 late=nearby[(nearby.stage=='PASS')&((nearby.entry_time>end) if clock else (nearby.entry_time>=end))&(nearby.entry_time<=row.end+pd.Timedelta(hours=12))]
 # Also distinguish a genuine earlier filled signal that finished before this movement began.
 prior=tr[(tr.side==side)&(tr.entry_time>=start-pd.Timedelta(hours=12))&(tr.entry_time<start)&(tr.exit_observed_time<=start)]
 if len(atpeak):category='POSITION_THROUGH_PEAK'
 elif len(amb):category='EXIT_ON_PEAK_BAR'
 elif len(over):category='POSITION_EXITED_EARLY'
 elif len(nowelig):category='PORTFOLIO_BLOCKED'
 elif len(nowraw):category='PROFILE_FILTERED'
 elif len(late):category='LATE_CONFIRMATION'
 else:category='NO_TIMELY_RAW_SIGNAL'
 flags=set()
 for rr in nearby[(nearby.assessment_time<=end)&(nearby.stage!='PASS')].itertuples():
  for f in str(rr.failed_gates).split('|'):
   if f and f!='nan':flags.add(rr.engine+':'+f)
 unfinished=nearby[(nearby.signal_time<=end)&(nearby.assessment_time>end)]
 netr=0.;best=None;captured=0.
 for rr in over.itertuples():
  v0=value(rr,start,price_start) if rr.entry_time<start else 0.;v1=value(rr,end,price_end);nr=v1-v0;netr+=nr
  z0=value(rr,start,price_start,False) if rr.entry_time<start else 0.;z1=value(rr,end,price_end,False);points=(z1-z0)*rr.atr;ratio=points/abs(row.peak_price-row.start_price)*100
  if best is None or ratio>best:best=ratio
  relations.append(dict(move_id=row.move_id,definition=row.definition,event_id=rr.event_id,source=rr.source,entry_time=rr.entry_time,exit_time=rr.exit_observed_time,carried=rr.entry_time<start,net_r_during_move=nr,gross_price_capture_pct=ratio))
 if category=='PORTFOLIO_BLOCKED':
  decisions_now=dec[dec.event_id.isin(nowelig.event_id)];assert not (decisions_now.decision=='ACCEPT').any()
 else:decisions_now=dec.iloc[:0]
 records.append(dict(**row._asdict(),category=category,raw_before_peak=len(nowraw),eligible_before_peak=len(nowelig),positions_overlap=len(over),carried_positions=len(old),held_at_peak=len(atpeak),peak_bar_ambiguous=len(amb),prior_finished_positions=len(prior),late_confirmations=len(late),net_r_during_move=netr,best_single_trade_gross_capture_pct=best if best is not None else 0.,positive_directional_contribution=netr>0,gate_flags='|'.join(sorted(flags)),candidate_engines='|'.join(sorted(nearby.engine.unique())),unfinished_candidates=len(unfinished),portfolio_block_reasons='|'.join(sorted(decisions_now.decision.unique()))))
audit=pd.DataFrame(records).drop(columns=['Index']);audit.to_csv(OUT/'LAB160D_move_audit.csv',index=False);pd.DataFrame(relations).to_csv(OUT/'LAB160D_move_trade_links.csv',index=False)
# Exact reproduction of previously published raw coverage numbers.
for h,n,cov in [(6,877,61),(24,539,67),(48,345,70)]:
 q=audit[audit.definition==f'CLOCK_{h}H'];assert len(q)==n,(h,len(q));assert int((q.eligible_before_peak>0).sum())==cov,(h,(q.eligible_before_peak>0).sum())
summary=[];cats=[];gatecounts=[]
for name,q in audit.groupby('definition'):
 summary.append(dict(definition=name,n=len(q),raw_coverage_pct=(q.eligible_before_peak>0).mean()*100,position_overlap_pct=(q.positions_overlap>0).mean()*100,carried_position_pct=(q.carried_positions>0).mean()*100,positive_contribution_pct=q.positive_directional_contribution.mean()*100,held_through_peak_pct=(q.held_at_peak>0).mean()*100,no_position_pct=(q.positions_overlap==0).mean()*100,median_best_capture_pct=q.best_single_trade_gross_capture_pct.median(),median_capture_when_overlap=q.loc[q.positions_overlap>0,'best_single_trade_gross_capture_pct'].median(),median_amplitude_atr=q.amplitude_atr.median(),median_duration_h=q.duration_h.median()))
 for cat,qq in q.groupby('category'):cats.append(dict(definition=name,category=cat,n=len(qq),pct=len(qq)/len(q)*100))
 absent=q[q.positions_overlap==0]
 for flag in sorted({f for v in absent.gate_flags for f in str(v).split('|') if f}):gatecounts.append(dict(definition=name,gate=flag,moves=int(absent.gate_flags.str.split('|').map(lambda x:flag in x).sum()),denominator_without_position=len(absent)))
pd.DataFrame(summary).to_csv(OUT/'LAB160D_summary.csv',index=False);pd.DataFrame(cats).to_csv(OUT/'LAB160D_categories.csv',index=False);pd.DataFrame(gatecounts).to_csv(OUT/'LAB160D_gate_flags.csv',index=False)
# Deterministic representative examples: closest duration/amplitude to class median, not best profit.
examples=[]
for cat,q in audit[audit.definition=='LEG_REV1ATR'].groupby('category'):
 score=(np.log1p(q.duration_h)-np.log1p(q.duration_h.median())).abs()+(q.amplitude_atr-q.amplitude_atr.median()).abs()
 examples.append(q.loc[score.idxmin()].to_dict())
pd.DataFrame(examples).to_csv(OUT/'LAB160D_examples.csv',index=False)
# Small regular close tape enables figure reproduction without reloading historical inputs.
p[['open','high','low','close','atr']].to_pickle(OUT/'LAB160D_price_tape.pkl')
(OUT/'LAB160D_validation.json').write_text(json.dumps(dict(portfolio_trades=251,portfolio_net_r_parity=True,gate_pass_counts=parity,old_clock_coverage_parity=True,period='2021-2024',baseline='OLD_PROFILE',cost_bps=7.5,unconfirmed_final_leg_excluded=True),indent=2))
print(pd.DataFrame(summary).round(3).to_string(index=False),flush=True);print('COMPLETE',flush=True)
