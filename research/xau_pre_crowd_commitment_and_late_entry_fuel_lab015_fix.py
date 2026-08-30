#!/usr/bin/env python3
"""Technical-only fix for LAB015.

The frozen LAB015 protocol is unchanged. This wrapper fixes only the precursor
score aggregation bug: numpy.bool_ additions collapsed to a boolean-like 0/1
instead of the intended integer count 0..5.
"""
import numpy as np
import pandas as pd
import xau_pre_crowd_commitment_and_late_entry_fuel_lab015 as m


def build_precursors_fixed(x):
    hi=x.mid_high.to_numpy(float);lo=x.mid_low.to_numpy(float);cl=x.mid_close.to_numpy(float);atr=x.atr14_causal.to_numpy(float)
    mins=x.minute.to_numpy(np.int64);ft=x.first_time_msc.to_numpy(np.int64);fb=x.first_bid.to_numpy(float);fa=x.first_ask.to_numpy(float);yr=x.year.to_numpy(int)
    prior_hi=pd.Series(hi).shift(1).rolling(60,min_periods=60).max().to_numpy();prior_lo=pd.Series(lo).shift(1).rolling(60,min_periods=60).min().to_numpy()
    rows=[];base_rows=[];n=len(x)
    for i in range(60,n-max(m.HORIZONS)-2):
        a=float(atr[i])
        if not np.isfinite(a) or a<=0:continue
        for side in ('BUY','SELL'):
            level=float(prior_hi[i] if side=='BUY' else prior_lo[i])
            if not np.isfinite(level):continue
            if side=='BUY':
                dist=(level-cl[i])/a
                if dist<0 or dist>m.MAX_PROX:continue
            else:
                dist=(cl[i]-level)/a
                if dist<0 or dist>m.MAX_PROX:continue
            h20=hi[i-19:i+1];l20=lo[i-19:i+1];c10=cl[i-9:i+1];h10=hi[i-9:i+1];l10=lo[i-9:i+1]
            if side=='BUY':
                attacks=int(np.sum(h20>=level-m.ATTACK_ATR*a));resilience=(level-np.nanmin(l10))/a;dwell=int(np.sum((level-c10)<=m.DWELL_ATR*a));pressure=(cl[i]-cl[i-5])/a;local_extreme=float(np.nanmin(l10))
            else:
                attacks=int(np.sum(l20<=level+m.ATTACK_ATR*a));resilience=(np.nanmax(h10)-level)/a;dwell=int(np.sum((c10-level)<=m.DWELL_ATR*a));pressure=(cl[i-5]-cl[i])/a;local_extreme=float(np.nanmax(h10))
            compression=(np.nanmax(h10)-np.nanmin(l10))/a
            # Technical fix only: force every condition to int before summing.
            score=sum(int(v) for v in (
                attacks>=m.ATTACK_MIN,
                compression<=m.COMP_MAX_ATR,
                resilience<=m.RESILIENCE_MAX_ATR,
                dwell>=m.DWELL_MIN,
                pressure>=m.PRESSURE_MIN_ATR,
            ))
            prox='P0_0.10' if dist<=m.PROX_CUT else 'P0.10_0.20'
            crowd={};lat=None
            for h in m.CROWD_HORIZONS:
                fut=cl[i+1:i+h+1];hit=np.flatnonzero(fut>=level+m.CROWD_COMMIT_ATR*a) if side=='BUY' else np.flatnonzero(fut<=level-m.CROWD_COMMIT_ATR*a)
                crowd[f'crowd_commit_{h}']=bool(len(hit))
                if h==max(m.CROWD_HORIZONS) and len(hit):lat=int(hit[0]+1)
            base_rows.append(dict(idx=i,minute=int(mins[i]),side=side,year=int(yr[i]),dist_atr=float(dist),score=score,**crowd))
            if score not in m.SCORES:continue
            en=i+1;state=f'{side}|{prox}|S{score}'
            rows.append(dict(signal_idx=i,minute=int(mins[i]),signal_time_msc=int(ft[i]),side=side,state=state,prox_bucket=prox,score=score,level=level,dist_atr=float(dist),attacks=attacks,compression_atr=float(compression),resilience_atr=float(resilience),dwell=dwell,pressure_atr=float(pressure),local_extreme=local_extreme,atr_signal=a,entry_idx=en,entry_minute=int(mins[en]),entry_time_msc=int(ft[en]),entry_bid=float(fb[en]),entry_ask=float(fa[en]),atr_entry=float(atr[en]),year=int(yr[en]),crowd_latency_20=lat,**crowd))
    base=pd.DataFrame(base_rows);s=pd.DataFrame(rows)
    if s.empty:return base,s
    s=m.physical_cooldown(s);s['signal_id']=np.arange(len(s),dtype=np.int64);return base,s


m.build_precursors=build_precursors_fixed

if __name__=='__main__':
    m.main()
