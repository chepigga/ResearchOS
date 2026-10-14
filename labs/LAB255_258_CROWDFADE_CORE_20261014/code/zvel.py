import io,contextlib,numpy as np,pandas as pd,statsmodels.api as sm
src=open("trendalt.py").read(); src2=src[:src.index("rows=[]")]
g={}
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src2,"ta","exec"),g)
BT,BO,BC,BA,N,TE,WV=[g[k] for k in "BT BO BC BA N TE WV".split()]
z6=g["z6"]; z24=g["z24"]; TR4=g["E"].TR4
r=np.load("ratio.npy").astype(float); rs=pd.Series(r)
sd72=rs.rolling(72).std(ddof=0).to_numpy()
def lag(a,k): return np.r_[np.full(k,np.nan),a[:-k]]
fut=(np.r_[BC[288:],np.full(288,np.nan)]-BC)/BA
F={}
for k in (6,12,24,36):
    F[f"dz{k}"]=z6-lag(z6,k)
    F[f"dr{k}"]=(r-lag(r,k))/sd72
for k in (12,72): F[f"pm{k}"]=(BC-lag(BC,k))/BA
F["z6"]=z6
D=pd.DataFrame(F); D["fut"]=fut; D["tr"]=BT<TE
S=D.iloc[::12].replace([np.inf,-np.inf],np.nan).dropna()
print("== регресія fut24 (ATR) — t-статистика (HAC), щогодинна вибірка")
for seg,x in S.groupby("tr"):
    nm="2021-24" if seg else "2025-26"
    for k in (6,12,24,36):
        for f in (f"dz{k}",f"dr{k}"):
            X=x[[f]].copy(); X=(X-X.mean())/X.std()
            m1=sm.OLS(x.fut,sm.add_constant(X)).fit(cov_type="HAC",cov_kwds={"maxlags":24})
            X2=x[[f,"z6",f"pm{12 if k<=12 else 72}","pm72"]].loc[:,lambda d:~d.columns.duplicated()]; X2=(X2-X2.mean())/X2.std()
            m2=sm.OLS(x.fut,sm.add_constant(X2)).fit(cov_type="HAC",cov_kwds={"maxlags":24})
            print(f"{nm} {f:5s} сам: t={m1.tvalues[f]:+.2f}  | з контролем z6+ціни: t={m2.tvalues[f]:+.2f} (z6 t={m2.tvalues['z6']:+.2f})")
S.to_pickle("zvel_S.pkl")
