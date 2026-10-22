import pandas as pd,numpy as np
src=open("/home/claude/bk/lrep.py").read().split("raw=b.sig.values")[0]
exec(src)
raw=b.sig.values
h1b=pd.read_pickle("/home/claude/bk/h1.pkl"); e30=h1b.close.ewm(span=30,adjust=False).mean()
belowH1=pd.Series(np.sign(h1b.close-e30).values,index=h1b.index+pd.Timedelta(hours=1)).reindex(t,method="ffill").values<0
m15b=pd.read_pickle("/home/claude/bk/m15.pkl")
day_open=m15b.open.groupby(m15b.index.normalize()).transform("first").values
# ціна закриття сигнального бару нижче відкриття дня
belowOpen=b.close.values<day_open
# нижче азійського мінімуму (01-09) поточного дня
hr=m15b.index.hour; asia=m15b.low.where((hr>=1)&(hr<9)).groupby(m15b.index.normalize()).transform("min").values
afterAsia=(m15b.index.hour>=9)
belowAsia=afterAsia&(b.close.values<asia)
hours=t.hour.values; night=(hours>=21)|(hours<1)
base_s=(raw<0)&~night
fullD1=(cc<ee50)&(ee50<ee50p)&(ee20<ee50)&(cc<ee200)
V={"тренд вниз D1 (як було)":base_s&fullD1&belowH1,
   "лише H1 нижче EMA30 (без D1)":base_s&belowH1,
   "D1 нижче EMA50 + H1":base_s&(cc<ee50)&belowH1,
   "день падає: нижче відкриття дня + H1":base_s&belowOpen&belowH1,
   "нижче азійського мінімуму + H1":base_s&belowAsia&belowH1,
   "нижче азійського мінімуму + D1<EMA50":base_s&belowAsia&(cc<ee50)}
out={}
for k,m in V.items():
    for tp,tps in (("1R",(1,1,1)),("1/2/3R",(1,2,3))):
        bs=b.copy(); bs["sig"]=np.where(m,-1,0); out[(k,tp)]=simulate(bs,tps=tps)
pd.to_pickle(out,"/home/claude/bk/lshort.pkl")
