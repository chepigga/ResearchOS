import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L, engD3 as D3
TE=pd.Timestamp("2025-01-01",tz="UTC")
tv,ev,_,_=L.replay(7.5,{},dict(mtr=np.zeros(L.N,int),ci=np.zeros(L.N,int),swl=None,swh=None,catr=None))
eqV=pd.Series(ev.equity_r.to_numpy(),index=pd.DatetimeIndex(ev.time)); eqV=eqV[~eqV.index.duplicated(keep="last")]
td,eqD=D3.sim(48,3); eqD=eqD[~eqD.index.duplicated(keep="last")]
def realized(t):
    s=t.groupby("exit_time").net_r.sum().sort_index().cumsum(); s.index=pd.DatetimeIndex(s.index); return s
rV=realized(tv); rD=realized(td)
def run(rv,rd,label):
    out=[]
    for seg,(a,b) in {"2021-24":(None,TE),"2025-26":(TE,None)}.items():
        idx=L.BT[(L.BT>=a) if a is not None else (L.BT<b)] if a is not None else L.BT[L.BT<b]
        def al(s): 
            x=s.reindex(s.index.union(idx)).ffill().reindex(idx)
            x=x.ffill().fillna(0.0); return x-x.iloc[0]
        E=al(eqV)*rv+al(eqD)*rd                     # equity in % of initial balance
        Bal=al(rV)*rv+al(rD)*rd                      # realized balance %
        cet=E.index.tz_convert("Europe/Prague").floor("D")
        df=pd.DataFrame({"E":E.to_numpy(),"B":Bal.to_numpy(),"d":cet})
        g=df.groupby("d")
        start_eq=g.E.first(); start_bal=g.B.first(); mn=g.E.min()
        loss_vs_eq=(start_eq-mn); loss_vs_bal=(start_bal-mn)
        peak=E.cummax(); dd=(peak-E).max(); worst_from_start=-E.min()
        months=(E.index[-1]-E.index[0]).days/30.44
        out.append(dict(book=label,seg=seg,pct_mo=E.iloc[-1]/months,max_dd_pct=dd,lowest_vs_initial=-worst_from_start,
            worst_day_vs_start_equity=loss_vs_eq.max(),worst_day_vs_start_balance=loss_vs_bal.max(),
            days_over_3pct=int((loss_vs_bal>3).sum()),days_over_4pct=int((loss_vs_bal>4).sum()),days_over_5pct=int((loss_vs_bal>5).sum())))
    return out
rows=[]
for rv,rd,lab in [(0.25,0.10,"зараз: v157 0.25% + D 0.10%"),(0.45,0.18,"масштаб: v157 0.45% + D 0.18%"),(0.60,0.24,"агресивно: v157 0.60% + D 0.24%")]:
    rows+=run(rv,rd,lab)
R=pd.DataFrame(rows); pd.set_option("display.width",260)
print(R.round(2).to_string(index=False))
