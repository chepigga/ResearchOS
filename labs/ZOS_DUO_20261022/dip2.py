import pandas as pd,numpy as np,itertools
exec(open("dip.py").read().split("E={")[0])
d1=pd.read_pickle("d1.pkl"); d1=d1[d1.index.dayofweek<5]; cd=d1.close
trd=pd.concat([d1.high-d1.low,(d1.high-cd.shift()).abs(),(d1.low-cd.shift()).abs()],axis=1).max(axis=1); atrd=trd.rolling(14).mean()
e20=cd.ewm(span=20,adjust=False).mean()
dEMA=((cd-e20)/atrd).shift(1); m60=(cd/cd.shift(60)-1).shift(1)*100
day=h1.index.normalize(); DE=dEMA.reindex(day,method="ffill").values; M60=m60.reindex(day,method="ffill").values
trh=pd.concat([h1.high-h1.low,(h1.high-h1.close.shift()).abs(),(h1.low-h1.close.shift()).abs()],axis=1).max(axis=1); ah=trh.rolling(14).mean().values
bear2=bear&np.r_[False,bear[:-1]]
drop3=(c-np.r_[np.nan,np.nan,np.nan,c[:-3]])/ah     # рух за 3 години в ATR H1
ENT={"1 ведмежа свічка":bear,"2 ведмежі поспіль":bear2,"падіння за 3 год ≥1 ATR H1":drop3<=-1.0,"падіння за 3 год ≥2 ATR H1":drop3<=-2.0}
rows=[]
for k in (0.3,0.7,1.0,1.5):
    reg=(DE<-k)&(M60>0)
    for (en,ent),(tp,sl),eb in itertools.product(ENT.items(),((0.5,0.5),(0.75,0.75),(1.0,1.0),(1.0,0.5)),(True,False)):
        T=run(ent&reg,tp,sl,24,eb)
        if len(T)<50: continue
        f=T[(T.t>="2023-02-01")&(T.t<"2023-03-01")]
        rows.append((k,en,tp,sl,eb,len(T),T.R.mean(),T.R[T.t<"2024-06-01"].mean(),T.R[T.t>="2024-06-01"].mean(),f.R.sum(),T.R.sum()))
O=pd.DataFrame(rows,columns=["EMA20 нижче на k ATR","вхід","TP%","SL%","швидкий вихід","угод","R/уг","1-а пол","2-а пол","лют23","ΣR"])
O.to_pickle("dip2.pkl"); pd.set_option("display.width",230)
O["мін.пол"]=O[["1-а пол","2-а пол"]].min(axis=1)
print(O.sort_values("мін.пол",ascending=False).head(20).round(3).to_string(index=False))
