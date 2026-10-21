"""LAB_ZOS_REG_001 (pre-registered): can the 'October regime' be detected BEFORE entry and is cutting risk in it profitable?
Trades: MT5 tester ZOS_Multi v2.09 A+D+F 2022.01-2026.10.20 (FIFO leg attribution). Features from D1 closed bars up to the day before entry.
Regimes (all defined before seeing their P/L):
 FLAT90   : |close/close_90cal_days_ago - 1| < 2%        (A's 90-day trend filter is meaningless)
 ER20     : 20-day efficiency ratio < 0.20               (no direction)
 BOX20    : (20-day high-low) / ATR_D14 < 4.0            (narrow box)
 POSTSHOCK: max daily range% in last 30 days >= 3.5% AND ATR14% now < 0.75 x ATR14% 20 days ago (calm after a shock)
 LOWVOL   : ATR14% < 0.8 x 120-day median
 FLAT90&ER20, POSTSHOCK&ER20
Action: risk x0.5 (and x0) for trades entered in regime. Report P/L inside/outside per half, and portfolio sum / monthly DD / neg months / Oct-2026."""
import pandas as pd,numpy as np
T=pd.read_pickle("/tmp/claude-0/-home-claude/879a62a8-009b-5e46-ab07-25d07c2b7f01/scratchpad/zos2/r1.xlsx.pkl")
T=T[(T.et!=T.xt)].copy(); T["et"]=pd.to_datetime(T.et)
d=pd.read_pickle("d1.pkl"); d=d[d.index.dayofweek<5].copy()
d["rp"]=(d.high-d.low)/d.close*100; d["atrp"]=d.rp.rolling(14).mean()
c=d.close
f=pd.DataFrame(index=d.index)
c90=c.copy(); c90.index=c90.index+pd.Timedelta(days=90); c90=c90.reindex(d.index,method="ffill")
f["FLAT90"]=(c/c90-1).abs()<0.02
f["ER20"]=((c-c.shift(20)).abs()/c.diff().abs().rolling(20).sum())<0.20
f["BOX20"]=((d.high.rolling(20).max()-d.low.rolling(20).min())/((d.high-d.low).rolling(14).mean()))<4.0
f["POSTSHOCK"]=(d.rp.rolling(30).max()>=3.5)&(d.atrp<0.75*d.atrp.shift(20))
f["LOWVOL"]=d.atrp<0.8*d.atrp.rolling(120).median()
f["FLAT90&ER20"]=f.FLAT90&f.ER20; f["POSTSHOCK&ER20"]=f.POSTSHOCK&f.ER20
f=f.shift(1)   # known before the day
T["day"]=T.et.dt.normalize(); T=T.merge(f,left_on="day",right_index=True,how="left").fillna(False)
T["h"]=np.where(T.et<"2024-07-01","H1","H2")
months=pd.period_range("2022-01","2026-10",freq="M")
def port(net):
    m=net.groupby(T.xt.dt.to_period("M")).sum().reindex(months).fillna(0); eq=m.cumsum()
    return round(m.sum()),round((eq.cummax()-eq).max()),int((m<0).sum()),round(m[pd.Period("2026-10","M")])
rows=[dict(режим="(немає — як зараз)",частка_угод=np.nan,**dict(zip(["сума","DD_міс","мінус_міс","жовтень"],port(T.net))))]
for r in ["FLAT90","ER20","BOX20","POSTSHOCK","LOWVOL","FLAT90&ER20","POSTSHOCK&ER20"]:
    m=T[r].astype(bool)
    x=dict(режим=r,частка_угод=round(m.mean(),2),
           в_режимі_H1=round(T.net[m&(T.h=="H1")].sum()),в_режимі_H2=round(T.net[m&(T.h=="H2")].sum()),
           R_на_угоду_в=round(T.net[m].mean()/270,2),R_на_угоду_поза=round(T.net[~m].mean()/270,2),
           жовт26_в_режимі=f"{int(m[T.et>='2026-10-01'].sum())}/{int((T.et>='2026-10-01').sum())}")
    for k,lab in ((0.5,"x0.5"),(0.0,"x0")):
        s=port(T.net*np.where(m,k,1.0)); x.update({f"{lab}_сума":s[0],f"{lab}_DD":s[1],f"{lab}_мінус":s[2],f"{lab}_жовт":s[3]})
    rows.append(x)
pd.set_option("display.width",320); print(pd.DataFrame(rows).to_string(index=False))
print("\nЖовтень 2026 по днях (режими):"); print(f.loc["2026-10-01":].astype(int).to_string())
