import runpy,io,contextlib,numpy as np,pandas as pd
src=open("trendalt.py").read(); src=src[:src.index("df=pd.DataFrame({\"c\":BC")]
g={}; 
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src,"ta","exec"),g)
BT,TE,TR4=g["BT"],g["TE"],g["E"].TR4
SIG=g["signals"](g["TR"]["2 без тренду"],False)
side_at={i+1:(sd,TR4[i]) for i,sd in SIG}
t,e=g["simD"](SIG)
t["side"]=[side_at[i][0] for i in t.entry_i]; t["tr4"]=[side_at[i][1] for i in t.entry_i]
t["grp"]=np.where(t.tr4==t.side,"H4 у бік угоди",np.where(t.tr4==0,"H4 без тренду","H4 проти угоди"))
t["seg"]=np.where(BT[t.entry_i.to_numpy(int)]<TE,"2021-24","2025-26")
mo={"2021-24":48,"2025-26":19.3}
out=t.groupby(["grp","seg"]).net_r.agg(n="count",ev="mean",tot="sum").reset_index()
out["угод/міс"]=out.apply(lambda r:r.n/mo[r.seg],axis=1); out["R/міс"]=out.apply(lambda r:r.tot/mo[r.seg],axis=1)
out["WR"]=t.groupby(["grp","seg"]).net_r.apply(lambda x:(x>0).mean()).values
print(out.round(2).to_string(index=False))
# displacement: H4-aligned signals that were taken in D(H4) but not in D' because slots busy
SIGh=g["signals"](g["TR"]["1 H4 EMA50 (зараз)"],False)
th,_=g["simD"](SIGh)
lost=set(th.entry_i)-set(t.entry_i)
th["seg"]=np.where(BT[th.entry_i.to_numpy(int)]<TE,"2021-24","2025-26")
L_=th[th.entry_i.isin(lost)]
print("\nугоди старого D, які D' не взяв (слоти зайняті іншими):",L_.groupby("seg").net_r.agg(["count","mean","sum"]).round(2).to_dict("index"))
# monthly correlation of extra trades with H4-aligned trades and with A+B3
