"""Causal score-to-alert policy. Features and probabilities must be available at bar close."""
import numpy as np
from numba import njit
@njit
def emit(minutes,score,threshold,cooldown_minutes=60):
 out=[];last=-10**18
 for i in range(len(minutes)):
  if np.isfinite(score[i]) and score[i]>=threshold and minutes[i]-last>=cooldown_minutes:
   out.append(i);last=minutes[i]
 return np.asarray(out,dtype=np.int64)
def calibrate(minutes,score,days,rate):
 thresholds=np.unique(np.r_[np.quantile(score,np.linspace(0,.999,201)),1.000001]);records=[]
 for th in thresholds:
  n=len(emit(minutes,score,th));records.append((abs(n/days-rate),-th,float(th),n/days))
 _,_,threshold,actual=min(records);return threshold,actual
class AlertDetector:
 def __init__(self,threshold,cooldown_minutes=60):self.threshold=threshold;self.cooldown=cooldown_minutes;self.last=None
 def on_closed_bar(self,time_minutes,p_up,p_down):
  score=max(p_up,p_down)
  if not np.isfinite(score):return None
  if score<self.threshold or (self.last is not None and time_minutes-self.last<self.cooldown):return None
  self.last=time_minutes
  return dict(side=1 if p_up>=p_down else -1,score=float(score))
