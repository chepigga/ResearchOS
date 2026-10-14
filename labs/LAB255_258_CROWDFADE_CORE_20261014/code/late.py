import runpy,io,contextlib,numpy as np,pandas as pd
buf=io.StringIO()
with contextlib.redirect_stdout(buf): g=runpy.run_path("core_cov.py")
T=g["T"]; BT=g["BT"]; BC=g["BC"]; BA=g["BA"]; TE=g["TE"]
s=pd.Series(BC,index=BT); h1=s.resample("1h").last().dropna(); e20=h1.ewm(span=20,adjust=False).mean()
x=e20.copy(); x.index=x.index+pd.Timedelta("1h"); EMA=x.reindex(BT,method="ffill").to_numpy()
hi48=pd.Series(g["BH"]).shift(1).rolling(576).max().to_numpy(); lo48=pd.Series(g["BL"]).shift(1).rolling(576).min().to_numpy()
i=T.entry_i.to_numpy(int); sd=T.side.to_numpy()
T["ext"]=sd*(g["BO"][i]-EMA[i])/BA[i]
rngpos=(g["BO"][i]-lo48[i])/(hi48[i]-lo48[i]); T["pos48"]=np.where(sd>0,rngpos,1-rngpos)  # 1 = at the extreme in trade direction
T["seg"]=np.where(BT[i]<TE,"2021-24","2025-26")
pd.set_option("display.width",220)
for nm,col,bins in [("розтягнутість від EMA20 H1 у бік угоди (ATR)","ext",[-99,0,1,2,3,99]),("де в 48-год діапазоні (1 = на екстремумі в бік угоди)","pos48",[-9,0.5,0.8,0.95,9])]:
    T["b"]=pd.cut(T[col],bins)
    print("\n==",nm)
    print(T.groupby(["eng","b"],observed=True).apply(lambda x: pd.Series({"n":len(x),"R 21-24":x[x.seg=="2021-24"].net_r.mean(),"R 25-26":x[x.seg=="2025-26"].net_r.mean()})).round(2).to_string())
