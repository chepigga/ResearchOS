import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L
BT,BO,BH,BL,BC,BA,N=L.BT,L.BO,L.BH,L.BL,L.BC,L.BA,L.N; BZ=np.asarray(L.C["BZ"],float); az=np.abs(BZ)
oi=np.load("oi.npy"); TE=pd.Timestamp("2025-01-01",tz="UTC")
# --- context features at M5 (closed-bar, causal) ---
s=pd.Series(BC,index=BT)
h1=s.resample("1h").last().dropna(); e20=h1.ewm(span=20,adjust=False).mean()
h4=s.resample("4h").last().dropna(); e50=h4.ewm(span=50,adjust=False).mean()
tr4=np.where((h4>e50)&(e50>e50.shift(6)),1,np.where((h4<e50)&(e50<e50.shift(6)),-1,0))
tr4=pd.Series(tr4,index=h4.index)
def asof(ser,shift):  # value of last CLOSED bar
    x=ser.copy(); x.index=x.index+shift; return x.reindex(BT,method="ffill").to_numpy()
EXT=(BC-asof(e20,pd.Timedelta("1h")))/BA
TR4=asof(tr4,pd.Timedelta("4h"))
OI4=oi/np.r_[np.full(48,np.nan),oi[:-48]]-1
hi48=pd.Series(BH).shift(1).rolling(576).max().to_numpy(); lo48=pd.Series(BL).shift(1).rolling(576).min().to_numpy()
# --- 3 ATR waves (H1 zigzag) ---
df=pd.DataFrame({"c":BC,"a":BA},index=BT); hh=df.resample("1h").agg({"c":"last","a":"last"}).dropna()
C=hh.c.to_numpy(); A=hh.a.to_numpy(); T=hh.index
piv=[0]; d=0; ei=0
for i in range(1,len(C)):
    if d>=0:
        if C[i]>C[ei]: ei=i
        elif C[ei]-C[i]>=3*A[ei]: piv.append(ei); d=-1; ei=i; continue
    if d<=0:
        if C[i]<C[ei]: ei=i
        elif C[i]-C[ei]>=3*A[ei]: piv.append(ei); d=1; ei=i
piv.append(ei)
W=[(T[a],T[b],C[a],C[b],int(np.sign(C[b]-C[a])),abs(C[b]-C[a])/A[a]) for a,b in zip(piv[:-1],piv[1:]) if b>a]
W=pd.DataFrame(W,columns=["t0","t1","p0","p1","dir","size"]); W=W[W["size"]>=3].reset_index(drop=True)
pos=lambda t:int(np.searchsorted(BT.values,np.datetime64(t.tz_convert("UTC").tz_localize(None))))
Tr=pd.read_csv("out_oos/TRADES.csv",parse_dates=["entry_time"]); Tr=Tr[(Tr.variant=="BASE")&(Tr.cost_bps==7.5)]
raw=L.C["raw"][7.5]
EXT_T,OI_T=1.529,0.00867
rows=[]
for w in W.itertuples():
    i0,i1=pos(w.t0),pos(w.t1); d=w.dir; third=i0+(i1-i0)//3
    tk=Tr[(Tr.entry_time>=w.t0)&(Tr.entry_time<w.t1)]
    taken=(tk.side==d).any()
    rw=raw[(raw.entry_time>=w.t0)&(raw.entry_time<w.t1)&(raw.side==d)]
    win=np.arange(i0,max(third,i0+1)+1)
    zal=win[(az[win]>=1)&(-np.sign(BZ[win])==d)]
    r=dict(seg="2021-24" if w.t0<TE else "2025-26",dir=d,size=w.size,taken=taken)
    if taken: r["why"]="0 взяв"
    elif len(rw): r["why"]="1 сигнал двигуна був, але не відкрили (позиція/пізно)"
    elif len(zal)==0: r["why"]="2 у першій третині натовп не був проти руху (|z|<1 або з рухом)"
    else:
        # check A-like context at aligned z bars: ext against side >= thr, OI4h >= thr, H4 trend opposite
        ext_ok=( (-d*EXT[zal])>=EXT_T ).any()   # price stretched AGAINST side (fade into stretch)
        ext_with=( (d*EXT[zal])>=EXT_T ).any()   # stretched in move direction
        oi_ok=(OI4[zal]>=OI_T).any()
        trend_with=(TR4[zal]==d).any(); trend_opp=(TR4[zal]==-d).any()
        brk=((d>0)&(BC[zal]>hi48[zal])|(d<0)&(BC[zal]<lo48[zal])).any()
        r.update(ext_ok=ext_ok,ext_with=ext_with,oi_ok=oi_ok,trend_with=trend_with,trend_opp=trend_opp,brk48=brk)
        r["why"]="3 натовп проти руху, але умови двигунів не зійшлись"
    rows.append(r)
D=pd.DataFrame(rows)
D["band"]=pd.cut(D["size"],[3,4.5,6,10,1e9],labels=["3–4.5","4.5–6","6–10","10+"],right=False)
pd.set_option("display.width",250)
print("рухів:",D.groupby("seg").size().to_dict(),"на місяць:",(D.groupby("seg").size()/pd.Series({"2021-24":48,"2025-26":19.3})).round(1).to_dict())
print(pd.crosstab(D.why,D.seg,normalize="columns").round(2))
print("\nчастка взятих за розміром руху і напрямом:")
print(pd.crosstab([D.band,D.dir],D.seg,values=D.taken,aggfunc="mean").round(2))
m=D[D.why.str.startswith("3")]
print("\nсеред 'умови не зійшлись' (n=%d): частка рухів, де в першій третині хоча б раз:"%len(m))
print(m[["ext_ok","ext_with","oi_ok","trend_with","trend_opp","brk48"]].mean().round(2).rename({
 "ext_ok":"ціна розтягнута ПРОТИ нашого боку ≥1.53 ATR (умова A)","ext_with":"розтягнута В бік руху ≥1.53 ATR",
 "oi_ok":"OI за 4 год ≥ +0.87% (умова A)","trend_with":"H4-тренд у бік руху","trend_opp":"H4-тренд проти руху (умова A)","brk48":"пробій 48-год діапазону (R48)"}))
# combos for A full
a_full=(m.ext_ok&m.oi_ok&m.trend_opp).mean(); print("усі три умови A хоча б по разу:",round(a_full,2))
D.to_csv("out_oos/MISS3.csv",index=False)
