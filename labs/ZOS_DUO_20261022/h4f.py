import pandas as pd,numpy as np
h1=pd.read_pickle("h1.pkl"); h4=h1.resample("4h").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
h4["e20"]=h4.close.ewm(span=20,adjust=False).mean(); h4["e50"]=h4.close.ewm(span=50,adjust=False).mean()
# fractals confirmed one bar later
fh=(h4.high>h4.high.shift(1))&(h4.high>h4.high.shift(-1)); fl=(h4.low<h4.low.shift(1))&(h4.low<h4.low.shift(-1))
H=h4.high.where(fh); Lw=h4.low.where(fl)
H=H.shift(1); Lw=Lw.shift(1)   # стає відомим після закриття наступного бару
lh1=H.ffill(); lh2=H.dropna().shift(1).reindex(h4.index).ffill()
ll1=Lw.ffill(); ll2=Lw.dropna().shift(1).reindex(h4.index).ffill()
st=np.where((lh1>lh2)&(ll1>ll2),1,np.where((lh1<lh2)&(ll1<ll2),-1,0))
f=pd.DataFrame({"c>e20":np.sign(h4.close-h4.e20),"e20>e50":np.sign(h4.e20-h4.e50),"struct":st},index=h4.index)
f.index=f.index+pd.Timedelta(hours=4)   # лише закриті H4 бари
f.to_pickle("h4feat.pkl")
