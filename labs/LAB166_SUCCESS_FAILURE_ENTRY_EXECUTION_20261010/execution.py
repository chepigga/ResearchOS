from prepare import R,O
import json,numpy as np,pandas as pd
ENTRIES=['MARKET','DELAY30','LIMIT025'];COSTS=[5.,7.5,10.]

def simulate(bars,i,side,atr,mode):
 n=len(bars);end=min(i+288,n-1);entry_i=-1;entry=np.nan;atopen=True;limit=bars[i,3]-side*.25*atr
 if mode in ['MARKET','DELAY30']:
  entry_i=i+(1 if mode=='MARKET' else 7)
  if entry_i>end:return dict(filled=False,reservation_end=end)
  entry=bars[entry_i,0]
 else:
  for j in range(i+1,min(i+12,end)+1):
   op,h,l,_=bars[j]
   if (side==1 and l<=limit) or(side==-1 and h>=limit):
    entry_i=j;atopen=side*(op-limit)<=0;entry=op if atopen else limit;break
  if entry_i<0:return dict(filled=False,reservation_end=min(i+12,end))
 risk=1.5*atr;stop=entry-side*risk;target=entry+side*3*atr;exit_i=end;exit_price=bars[end,3];reason='TIMEOUT';ambiguous=False
 for j in range(entry_i,end+1):
  op,h,l,c=bars[j];bad= (l<=stop) if side==1 else(h>=stop);good=(h>=target) if side==1 else(l<=target)
  if (j>entry_i or atopen) and side*(op-stop)<=0:
   exit_i=j;exit_price=op;reason='STOP_GAP';break
  if bad:
   exit_i=j;exit_price=stop;reason='STOP';ambiguous=bool(good);break
  if good and (j>entry_i or atopen):
   exit_i=j;exit_price=target;reason='TARGET';break
 gross=side*(exit_price-entry)/risk
 return dict(filled=True,entry_i=entry_i,entry=entry,exit_i=exit_i,exit_price=exit_price,stop=stop,target=target,risk_price=risk,gross_R=gross,cost_unit_R=1e-4*(entry+exit_price)/2/risk,reason=reason,ambiguous=ambiguous,reservation_end=exit_i,fill_at_open=atopen,entry_delay_minutes=(entry_i-i-1)*5 if mode in ['MARKET','DELAY30'] else (entry_i-i)*5)

def fixture():
 # both barriers in one candle -> adverse first
 b=np.tile([100.,101.,99.,100.],(5,1));b[1]=[100,107,96,100];r=simulate(b,0,1,2,'MARKET');assert r['gross_R']==-1 and r['ambiguous']
 # gap across stop -> gap price, not ideal stop
 b=np.tile([100.,101.,99.,100.],(5,1));b[2]=[95,96,94,95];r=simulate(b,0,1,2,'MARKET');assert np.isclose(r['gross_R'],-5/3) and r['reason']=='STOP_GAP'
 # intrabar limit fill cannot credit an earlier same-bar target
 b=np.tile([100.,101.,99.7,100.],(5,1));b[1]=[100,107,99.4,100];r=simulate(b,0,1,2,'LIMIT025');assert r['entry']==99.5 and r['reason']=='TIMEOUT'
 # favorable opening gap improves limit fill mechanically
 b=np.tile([100.,101.,99.7,100.],(5,1));b[1]=[99,100,98,99];r=simulate(b,0,1,2,'LIMIT025');assert r['entry']==99 and r['fill_at_open']
 # no touch -> unfilled
 b=np.tile([100.,101.,99.7,100.],(5,1));assert not simulate(b,0,1,2,'LIMIT025')['filled']
 return True

def stats(t,netcol='net_R'):
 if not len(t):return dict(n=0,EV=np.nan,PF=np.nan,sum_R=0,win_pct=np.nan)
 r=t[netcol].to_numpy();wins=r[r>0].sum();loss=-r[r<0].sum();return dict(n=len(r),EV=r.mean(),PF=wins/loss if loss>0 else np.inf,sum_R=r.sum(),win_pct=100*(r>0).mean())

def portfolio(q,alltrades,d,cost):
 active=[];filled=[];unfilled=blocked=0;maxocc=0
 for r in q.sort_values('i').itertuples():
  active=[t for t in active if t['reservation_end']>r.i]
  if len(active)>=2:blocked+=1;continue
  t=alltrades[int(r.i)];active.append(t);maxocc=max(maxocc,len(active))
  if t['filled']:filled.append(t|dict(signal_i=int(r.i),side=int(r.side)))
  else:unfilled+=1
 assert maxocc<=2
 t=pd.DataFrame(filled)
 if t.empty:return t,dict(blocked=blocked,unfilled=unfilled,max_occupied=maxocc,mtm_dd_pct=np.nan)
 t['net_R']=t.gross_R-cost*t.cost_unit_R
 # Fixed initial equity risk; mark at each closed candle. No compounding or future trade sizing.
 lo=int(q.i.min());hi=int(t.exit_i.max());curve=np.zeros(hi-lo+1);price=d.close.to_numpy();realized=np.zeros(len(curve))
 for r in t.itertuples():
  realized[int(r.exit_i)-lo]+=r.net_R
  a=int(r.entry_i)-lo;z=int(r.exit_i)-lo
  if z>a:curve[a:z]+=r.side*(price[int(r.entry_i):int(r.exit_i)]-r.entry)/r.risk_price-cost*r.cost_unit_R/2
 curve+=np.cumsum(realized);equity=np.r_[100.,100.+.25*curve];peak=np.maximum.accumulate(equity);dd=100*np.max((peak-equity)/peak)
 return t,dict(blocked=blocked,unfilled=unfilled,max_occupied=maxocc,mtm_dd_pct=float(dd))

def main():
 assert fixture();d=pd.read_pickle(O/'price_runtime.pkl');bars=d[['open','high','low','close']].to_numpy();x=pd.read_csv(O/'scored_signals.csv.gz',parse_dates=['time']);x=x[x.split.isin(['VALIDATION','CHECK'])].copy();rows=[]
 for r in x.itertuples():
  for mode in ENTRIES:rows.append(dict(signal_i=r.i,signal_time=r.time,side=r.side,mode=mode,year=r.year,split=r.split,**simulate(bars,int(r.i),int(r.side),r.atr,mode)))
 t=pd.DataFrame(rows);t.to_csv(O/'entry_events.csv.gz',index=False,compression='gzip');selections={'ALL':np.ones(len(x),bool)}
 for level in ['PRICE_TREND','CROWD','OI','PROFILE','OBSTACLES']:selections[level+'_50']=x['pass_'+level+'_50'].to_numpy(bool)
 for retention in [25,75]:selections['OBSTACLES_'+str(retention)]=x['pass_OBSTACLES_'+str(retention)].to_numpy(bool)
 periods={'VALIDATION_2024':(x.year==2024,365.),'CHECK_2025':(x.year==2025,364.),'CHECK_2026':(x.year==2026,220.89583333333334),'CHECK_2025_26':(x.year>=2025,584.8958333333334),'ALL_2024_26':(x.year>=2024,949.8958333333334)};result=[];accepted=[]
 for selection,mask in selections.items():
  for period,(pm,days) in periods.items():
   q=x[mask&pm];ids=set(q.i)
   for mode in ENTRIES:
    et=t[(t['mode']==mode)&t.signal_i.isin(ids)];f=et[et.filled].copy();lookup={int(r.signal_i):r._asdict() for r in et.itertuples(index=False)}
    for cost in COSTS:
     f['net_R']=f.gross_R-cost*f.cost_unit_R;pt,extra=portfolio(q,lookup,d,cost)
     for replay,tr,meta in [('INDEPENDENT',f,dict(blocked=0,unfilled=int((~et.filled).sum()),max_occupied=np.nan,mtm_dd_pct=np.nan)),('PORTFOLIO2',pt,extra)]:
      st=stats(tr);result.append(dict(selection=selection,period=period,mode=mode,cost_bps=cost,replay=replay,candidates=len(q),days=days,months=days/30.4375,trades_month=st['n']/(days/30.4375),R_month=st['sum_R']/(days/30.4375),**st,**meta))
     if cost==7.5 and period=='CHECK_2025_26' and selection in ['ALL','OBSTACLES_50'] and len(pt):
      pt=pt.copy();pt['selection']=selection;pt['mode']=mode;pt['period']=period;pt['cost_bps']=cost;accepted.append(pt)
 pd.DataFrame(result).to_csv(O/'execution_summary.csv',index=False)
 if accepted:pd.concat(accepted,ignore_index=True).to_csv(O/'portfolio_trades.csv.gz',index=False,compression='gzip')
 # Check raw returns and chronological horizon; entry pricing parity at next opens.
 ff=t[t.filled];assert (ff.entry_i>ff.signal_i).all();assert (ff.exit_i<=ff.signal_i+288).all();assert (ff.exit_i>=ff.entry_i).all();assert np.allclose(ff.gross_R,ff.side*(ff.exit_price-ff.entry)/ff.risk_price)
 market=ff[ff['mode']=='MARKET'];assert np.allclose(market.entry,d.open.iloc[market.entry_i.astype(int)].to_numpy());assert (market.entry_i==market.signal_i+1).all()
 (O/'execution_validation.json').write_text(json.dumps(dict(gap_and_double_touch_fixtures=True,limit_samebar_no_optimistic_target=True,next_open_fill_verified=True,max_positions_including_pending_verified=True,horizon_verified=True,gross_returns_recomputed=True,fixed_initial_risk_pct=.25,cost_bps=COSTS,entry_events=len(t),filled_events=len(ff),ambiguous_stop_first_events=int(ff.ambiguous.sum())),indent=2));res=pd.DataFrame(result);print(res[(res.period=='CHECK_2025_26')&(res.cost_bps==7.5)&(res.replay=='PORTFOLIO2')].to_string(index=False),flush=True)
if __name__=='__main__':main()
