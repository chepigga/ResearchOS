"""
XAU_POOL_SELECTION_LAB_001 | КРОК 3 — базова лінія

Випадковий вхід тією самою моделлю угоди, окремо на
(місяць x напрямок x ТФ). Мінімум 1500 семплів на комбінацію.

Обґрунтування (§7 спеки): золото зросло 1745 -> 4622 (+165%).
Виміряно раніше: випадковий лонг дає +0.200R на OOS-1 і +0.172R на OOS-2
без жодного еджу. Без віднімання дрейфу будь-який лонговий ухил
пройшов би поріг +0.10R.
"""
import pandas as pd, numpy as np, time
import os
DATA=os.environ.get("XAU_DATA", os.path.dirname(os.path.abspath(__file__)))


t0=time.time()
m1=pd.read_parquet(f'{DATA}/xau_m1.parquet').sort_values('time').reset_index(drop=True)
T=m1.time.values
BH,BL,BC=m1.high.values,m1.low.values,m1.close.values
AH,AL,AC=m1.ask_high.values,m1.ask_low.values,m1.ask_close.values
SL_M,TP_M,TO_BARS=1.5,3.0,120
NSAMP=1500

def tf_frame(rule):
    g=m1.set_index('time').resample(rule).agg(
        open=('open','first'),high=('high','max'),low=('low','min'),
        close=('close','last'),ask_close=('ask_close','last')).dropna().reset_index()
    pc=g.close.shift(1)
    tr=pd.concat([g.high-g.low,(g.high-pc).abs(),(g.low-pc).abs()],axis=1).max(axis=1)
    g['atr']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    return g[g.atr.notna()].reset_index(drop=True)

def sim(HT,ATR,ACL,CL,i,d,to_min):
    atr=ATR[i]
    if not np.isfinite(atr) or atr<=0: return None
    e=ACL[i] if d>0 else CL[i]
    sl=e-SL_M*atr if d>0 else e+SL_M*atr
    tp=e+TP_M*atr if d>0 else e-TP_M*atr
    risk=SL_M*atr
    a=np.searchsorted(T,HT[i],side='right')
    b=np.searchsorted(T,HT[i]+np.timedelta64(to_min,'m'),side='right')
    if b<=a: return None
    if d>0: ftp=np.flatnonzero(BH[a:b]>=tp); fsl=np.flatnonzero(BL[a:b]<=sl)
    else:   ftp=np.flatnonzero(AL[a:b]<=tp); fsl=np.flatnonzero(AH[a:b]>=sl)
    p=ftp[0] if len(ftp) else np.inf; q=fsl[0] if len(fsl) else np.inf
    if p==np.inf and q==np.inf:
        xp=BC[b-1] if d>0 else AC[b-1]
        return (xp-e)/risk if d>0 else (e-xp)/risk
    if p==q: return None
    return TP_M/SL_M if p<q else -1.0

rng=np.random.default_rng(2026)
rows=[]
for tf,rule,mins in [('M5','5min',5),('M15','15min',15),('H1','1h',60)]:
    g=tf_frame(rule)
    HT=g.time.values; ATR=g.atr.values; ACL=g.ask_close.values; CL=g.close.values
    ym=g.time.dt.to_period('M')
    for m,idx in g.groupby(ym).groups.items():
        idx=np.asarray(idx); idx=idx[idx<len(g)-1]
        if len(idx)<30: continue
        for d in (1,-1):
            pick=rng.choice(idx,size=min(NSAMP,len(idx)*4),replace=True)
            v=[sim(HT,ATR,ACL,CL,int(i),d,TO_BARS*mins) for i in pick]
            v=[x for x in v if x is not None]
            if len(v)<100: continue
            rows.append(dict(tf=tf,month=str(m),dir=d,base=float(np.mean(v)),
                             n=len(v),sd=float(np.std(v,ddof=1))))
    print(f"{tf}: готово  [{time.time()-t0:.0f}s]")

B=pd.DataFrame(rows)
B.to_parquet(f'{DATA}/baseline.parquet',index=False)
print("\n"+"="*70); print("БАЗОВА ЛІНІЯ"); print("="*70)
print(f"комбінацій (місяць x напрямок x ТФ): {len(B)}")
print(f"семплів на комбінацію: медіана {B.n.median():.0f}, мін {B.n.min()}")

print("\n--- середній дрейф по ТФ і напрямку ---")
print(B.pivot_table(index='tf',columns='dir',values='base',aggfunc='mean').round(4).to_string())

print("\n--- по роках (усі ТФ разом) ---")
B['year']=B.month.str[:4]
print(B.pivot_table(index='year',columns='dir',values='base',aggfunc='mean').round(4).to_string())

print("\n--- по розбиттях специфікації ---")
def split(m):
    if m<='2024-03': return 'IS'
    if m<='2025-01': return 'OOS-1'
    if m<='2025-12': return 'OOS-2'
    return 'CONTROL'
B['split']=B.month.map(split)
print(B.pivot_table(index='split',columns='dir',values='base',aggfunc='mean')
       .reindex(['IS','OOS-1','OOS-2','CONTROL']).round(4).to_string())

# застосування до пулу
P=pd.read_parquet(f'{DATA}/pool.parquet')
P['month']=P.time.dt.to_period('M').astype(str)
P=P.merge(B[['tf','month','dir','base']],on=['tf','month','dir'],how='left')
miss=P.base.isna().sum()
print(f"\nкандидатів без базової лінії: {miss} ({100*miss/len(P):.2f}%)")
P=P[P.base.notna()].reset_index(drop=True)
P['excess']=P.R-P.base
P.to_parquet(f'{DATA}/pool_excess.parquet',index=False)

print("\n"+"="*70); print("ПУЛ ПІСЛЯ ВІДНІМАННЯ ДРЕЙФУ"); print("="*70)
print(f"N={len(P):,}")
print(f"сира EV      {P.R.mean():+.4f}R")
print(f"дрейф        {P.base.mean():+.4f}R")
print(f"НАДЛИШОК     {P.excess.mean():+.4f}R   <- це те, що має піднімати відбір")
print(f"\nнадлишок BUY  {P[P.dir==1].excess.mean():+.4f}R")
print(f"надлишок SELL {P[P.dir==-1].excess.mean():+.4f}R")
print("\nнадлишок по ТФ:")
print(P.groupby('tf').excess.agg(['size','mean']).round(4).to_string())
print("\nнадлишок по механіках (де прапорець=1):")
MECHS=[c for c in P.columns if c.startswith('f_')]
res=[(m[2:],int(P[P[m]==1].shape[0]),float(P[P[m]==1].excess.mean())) for m in MECHS]
print(pd.DataFrame(res,columns=['механіка','N','excess']).sort_values('excess',ascending=False)
        .to_string(index=False,float_format=lambda v:f"{v:.4f}"))
print(f"\n[OK] pool_excess.parquet  [{time.time()-t0:.0f}s]")
