import pandas as pd,numpy as np
src=open("/home/claude/xau/algo2.py").read()
src=src.replace('pd.read_pickle("m15.pkl")','pd.read_pickle("/home/claude/bk/m15.pkl")').replace('pd.read_pickle("h1.pkl")','pd.read_pickle("/home/claude/bk/h1.pkl")').replace('pd.read_pickle("m1b.pkl")','pd.read_pickle("/home/claude/bk/m1.pkl")')
exec(src)
d1=pd.read_pickle("/home/claude/bk/d1.pkl"); h4=pd.read_pickle("/home/claude/bk/h4.pkl"); c=d1.close
e20=c.ewm(span=20,adjust=False).mean(); e50=c.ewm(span=50,adjust=False).mean(); e200=c.ewm(span=200,adjust=False).mean()
# D1 shift(1) = попередній D1 бар (включно з недільними барами, як у MT5)
D=pd.DataFrame({"c":c,"e20":e20,"e50":e50,"e50p":e50.shift(5),"e200":e200}).shift(1)
fh=(h4.high>h4.high.shift(1))&(h4.high>h4.high.shift(-1)); fl=(h4.low<h4.low.shift(1))&(h4.low<h4.low.shift(-1))
H=h4.high.where(fh).shift(1); Lw=h4.low.where(fl).shift(1)
lh1=H.ffill(); lh2=H.dropna().shift(1).reindex(h4.index).ffill(); ll1=Lw.ffill(); ll2=Lw.dropna().shift(1).reindex(h4.index).ffill()
st=pd.Series(np.where((lh1>lh2)&(ll1>ll2),1,np.where((lh1<lh2)&(ll1<ll2),-1,0)),index=h4.index+pd.Timedelta(hours=4))
b=build(1.5); t=b.index+pd.Timedelta(minutes=15)   # момент рішення = відкриття наступного бару
day=b.index.normalize()
# D1 значення на день бару: shift(1) по барах D1 -> беремо рядок D1 з датою <= день бару
Dd=D.reindex(day,method="ffill").values
cc,ee20,ee50,ee50p,ee200=[Dd[:,k] for k in range(5)]
s4=st.reindex(t,method="ffill").values
raw=b.sig.values
longok=(raw>0)&(cc>ee50)&(s4!=-1)
shortok=(raw<0)&(cc<ee50)&(ee50<ee50p)&(ee20<ee50)&(cc<ee200)&(s4!=1)
b["sig"]=np.where(longok,1,np.where(shortok,-1,0))
T=simulate(b,tps=(1,2,3))
# шорти: повний вихід 1R — пересимулювати окремо
bs=b.copy(); bs["sig"]=np.where(shortok,-1,0); TS=simulate(bs,tps=(1,1,1))
bl=b.copy(); bl["sig"]=np.where(longok,1,0); TL=simulate(bl,tps=(1,2,3))
pd.to_pickle(dict(T=T,TL=TL,TS=TS),"/home/claude/bk/lrep.pkl")
