"""LAB283 (pre-registered): engine T (correction-line break with main trend + crowd against) moved one step down:
main TF H1 (was H4), correction line M15 (was H1), break on M5 close (same). TrendAssist v1.23 logic and params unchanged.
Crowd: none | z6 against >=0 | >=1 (as LAB259). Exits: X48 = as LAB259 (SL 3 ATR_H1, trail peak-3R after +2R, 48h);
X12 = scaled to M15 (SL 1 ATR_H1, trail peak-3R after +2R, 12h). Cost 7.5 bps. Compare with original T (H4/H1) and portfolio with D2.
Money as LAB259: $100k, worst DD of both periods = 7%."""
import io,contextlib,numpy as np,pandas as pd,time
SRC259=open("tl259.py").read().split("rows=[]; base_eq={}")[0]
exec(SRC259)
import lab251 as LL, trendlines as TLm
simsrc=SRC259[SRC259.index("def sim(SIG"):SRC259.index("def dsig(")]
exec(simsrc.replace("def sim(SIG,trail=\"3R\"):","def simP(SIG,RM,HOLD,trail=\"3R\"):").replace("R=3*BA[i]","R=RM*BA[i]").replace("min(i+575","min(i+HOLD"))
def build(main_rule,corr_rule):
    sidx=LL.server_index(LL.BT,"SERVER")
    m5=pd.DataFrame({"open":LL.BO,"high":LL.BH,"low":LL.BL,"close":LL.BC},index=sidx); m5=m5[~m5.index.duplicated(keep="first")]
    agg={"open":"first","high":"max","low":"min","close":"last"}
    cb=m5.resample(corr_rule,label="left",closed="left").agg(agg).dropna(); mb=m5.resample(main_rule,label="left",closed="left").agg(agg).dropna()
    t0=time.time(); main=TLm.compute_main(mb); corr=TLm.compute_corr(cb,main); print(main_rule,corr_rule,"tl",round(time.time()-t0),"s",flush=True)
    j=np.searchsorted(cb.index.values,sidx.values,side="right")-1; ci=j-1
    j4=np.searchsorted(main.index.values,sidx.values,side="right")-1
    mtr=np.where(j4-1>=0,main["trend_after_close"].to_numpy()[np.maximum(j4-1,0)],0)
    return LL.cl_break_fast(sidx,ci,corr,mtr)
T_new=build("1h","15min"); T_old=TL["T"]
print("сигналів T: H4/H1",len(T_old)," H1/M15",len(T_new))
def crowd(T,zc):
    return [(ei-1,sd) for ei,sd in T if zc is None or (np.isfinite(z6[ei-1]) and sd*z6[ei-1]<=-zc)]
D2eq=al(sim(dsig2(1.5,0.5,"EMA"))[1])*0.10
rows=[]
for nm,T in (("T H4/H1 (LAB259)",T_old),("T H1/M15",T_new)):
    for zc in (None,0.0,1.0):
        S=crowd(T,zc)
        for xn,(RM,HOLD) in (("X48",(3,575)),("X12",(1,143))):
            if nm.startswith("T H4") and xn=="X12": continue
            t,e=simP(S,RM,HOLD); eq=al(e)*0.10
            r=stats(f"{nm} натовп {'-' if zc is None else '≥'+str(zc)} {xn}",[eq],t); r2=stats("x",[D2eq,eq])
            r["$ з D2 21-24"]=r2["%/міс 21-24"]; r["$ з D2 25-26"]=r2["%/міс 25-26"]; r["R/DD з D2 21-24"]=r2["R/DD 21-24"]; r["R/DD з D2 25-26"]=r2["R/DD 25-26"]
            rows.append(r)
base=stats("D2",[D2eq]); base["$ з D2 21-24"]=base["%/міс 21-24"]; base["$ з D2 25-26"]=base["%/міс 25-26"]; base["R/DD з D2 21-24"]=base["R/DD 21-24"]; base["R/DD з D2 25-26"]=base["R/DD 25-26"]
R=pd.DataFrame([base]+rows).set_index("v")
pd.set_option("display.width",300)
print(R[["угод/міс 21-24","EV 21-24","угод/міс 25-26","EV 25-26","R/DD 21-24","R/DD 25-26","R/DD з D2 21-24","R/DD з D2 25-26"]].round(2).to_string())
R.to_csv("out_oos/LAB283_T_M15.csv")
