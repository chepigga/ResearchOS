"""
XAU_POOL_SELECTION_LAB_001 | КРОК 2 — побудова пулу

ЗАФІКСОВАНО перед прогоном:
  D1 структура      рядок = (бар, ТФ, напрямок); механіки = 15 прапорців
  D2 прогрів        спільний старт для всіх ТФ: перший бар, де ВСІ механіки
                    мають валідні значення (найдовший = LinReg 50 + Alligator 48)
  D3 збіг між ТФ    сигнал M5/M15 відноситься до H1-бару, у який потрапляє
                    його час закриття. n_timeframes = скільки ТФ дали той
                    самий напрямок у межах цього H1-бару
  D4 перекриття     ДОЗВОЛЕНЕ. Кожен кандидат оцінюється незалежно.
                    Обґрунтування: у PINNED GEO* 1454 дублікати entry_t
                    з 3535 — перекриття є нормою в еталоні
  D5 модель угоди   SL 1.5xATR(14), TP 3.0xATR(14), тайм-аут 120 барів ТФ
                    вхід BUY по ask_close, SELL по close(bid)
                    вихід BUY по bid, SELL по ask
  D6 AMBIGUOUS      SL і TP в одному M1-барі -> позначка, виключення з EV
"""
import pandas as pd, numpy as np, importlib.util, time
import os
DATA=os.environ.get("XAU_DATA", os.path.dirname(os.path.abspath(__file__)))

spec=importlib.util.spec_from_file_location("m",f"{DATA}/step1_mechanics.py")
MECH=importlib.util.module_from_spec(spec); spec.loader.exec_module(MECH)

t0=time.time()
m1=pd.read_parquet(f'{DATA}/xau_m1.parquet').sort_values('time').reset_index(drop=True)
T=m1.time.values
BH,BL,BC=m1.high.values,m1.low.values,m1.close.values
AH,AL,AC=m1.ask_high.values,m1.ask_low.values,m1.ask_close.values
SPRM=m1.spread_mean.values
print(f"M1 {len(m1):,}  [{time.time()-t0:.0f}s]")

SL_M,TP_M,TO_BARS=1.5,3.0,120
TFS=[('M5','5min',5),('M15','15min',15),('H1','1h',60)]

def tf_frame(rule):
    g=m1.set_index('time').resample(rule).agg(
        open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),
        ask_close=('ask_close','last'),spr=('spread_mean','mean')).dropna().reset_index()
    pc=g.close.shift(1)
    tr=pd.concat([g.high-g.low,(g.high-pc).abs(),(g.low-pc).abs()],axis=1).max(axis=1)
    g['atr']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    # режимні фічі
    g['atr100']=tr.ewm(alpha=1/100,adjust=False,min_periods=100).mean()
    g['atr_ratio']=g.atr/g.atr100
    dirn=(g.close-g.close.shift(20)).abs(); vol=g.close.diff().abs().rolling(20).sum()
    g['kaufman_er']=dirn/vol.replace(0,np.nan)
    s=g.close.rolling(1200,min_periods=1200).mean()
    g['slope']=s-s.shift(240)
    af=tr.ewm(alpha=1/480,adjust=False,min_periods=480).mean()
    asw=tr.ewm(alpha=1/4800,adjust=False,min_periods=4800).mean()
    g['vr']=af/asw
    return g

def simulate(HT,ATR,ACL,CL,i,d,to_min):
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
        return ((xp-e)/risk if d>0 else (e-xp)/risk),'TO',T[b-1]
    if p==q: return None,'AMB',T[a+int(p)]
    if p<q: return TP_M/SL_M,'TP',T[a+int(p)]
    return -1.0,'SL',T[a+int(q)]

MECHS=None; frames={}; sigs={}
for tf,rule,mins in TFS:
    g=tf_frame(rule); S=MECH.build_signals(g,tf)
    S={k:v for k,v in S.items() if k!='P_IMPULSE'}
    if MECHS is None: MECHS=sorted(S)
    frames[tf]=g; sigs[tf]=S
    print(f"{tf}: {len(g):,} барів  [{time.time()-t0:.0f}s]")

# D2 спільний прогрів: перший індекс, де є ATR100, slope, vr і всі механіки
rows=[]
for tf,rule,mins in TFS:
    g=frames[tf]; S=sigs[tf]
    A=np.vstack([S[k] for k in MECHS])
    ready=g[['atr','atr_ratio','kaufman_er','slope','vr']].notna().all(axis=1).values
    HT=g.time.values; ATR=g.atr.values; ACL=g.ask_close.values; CL=g.close.values
    for d in (1,-1):
        cand=np.flatnonzero(((A==d).any(0))&ready)
        for i in cand:
            r=simulate(HT,ATR,ACL,CL,int(i),d,TO_BARS*mins)
            if r is None: continue
            R,why,xt=r
            flags=(A[:,i]==d).astype(np.int8)
            rows.append((g.time.iloc[i],tf,d,R if R is not None else np.nan,why,
                         g.atr_ratio.iloc[i],g.kaufman_er.iloc[i],g.slope.iloc[i],g.vr.iloc[i],
                         g.spr.iloc[i]/100/g.atr.iloc[i],g.time.iloc[i].hour,*flags))
    print(f"{tf}: кандидатів накопичено {len(rows):,}  [{time.time()-t0:.0f}s]")

cols=['time','tf','dir','R','why','atr_ratio','kaufman_er','slope','vr','spread_atr','hour']+['f_'+m for m in MECHS]
P=pd.DataFrame(rows,columns=cols)
P['n_bots']=P[['f_'+m for m in MECHS]].sum(axis=1)

# D3 n_timeframes: збіг напрямку в межах H1-бару
P['h1key']=P.time.dt.floor('h')
tfset=P.groupby(['h1key','dir']).tf.nunique().rename('n_timeframes')
P=P.merge(tfset,on=['h1key','dir'],how='left')
# протилежний напрямок у тому ж H1-барі
opp=P.groupby(['h1key','dir']).size().rename('cnt').reset_index()
opp['dir']=-opp['dir']
P=P.merge(opp.rename(columns={'cnt':'n_opposite'}),on=['h1key','dir'],how='left')
P['n_opposite']=P.n_opposite.fillna(0).astype(int)
P['session']=pd.cut(P.hour,[-1,7,12,17,23],labels=['ASIA','LONDON','NY','LATE'])

print("\n"+"="*70); print("ПУЛ ПОБУДОВАНО"); print("="*70)
print(f"кандидатів: {len(P):,}")
print(f"AMBIGUOUS: {(P.why=='AMB').sum():,} ({100*(P.why=='AMB').mean():.2f}%)")
P=P[P.why!='AMB'].reset_index(drop=True)
print(f"після виключення AMB: {len(P):,}")
print(f"період: {P.time.min()} -> {P.time.max()}")
print(f"\nпо ТФ: {P.tf.value_counts().to_dict()}")
print(f"напрямок: BUY {(P.dir==1).sum():,} | SELL {(P.dir==-1).sum():,}")
print(f"виходи: {P.why.value_counts().to_dict()}")
print(f"\nСИРА EV пулу: {P.R.mean():+.4f}R | WR {100*(P.R>0).mean():.1f}%")
print(f"  BUY  {P[P.dir==1].R.mean():+.4f}R (N={(P.dir==1).sum():,})")
print(f"  SELL {P[P.dir==-1].R.mean():+.4f}R (N={(P.dir==-1).sum():,})")
print(f"\nEV по ТФ:"); print(P.groupby('tf').R.agg(['size','mean']).round(4).to_string())
print(f"\nn_bots: {P.n_bots.value_counts().sort_index().head(10).to_dict()}")
P.to_parquet(f'{DATA}/pool.parquet',index=False)
print(f"\n[OK] pool.parquet  [{time.time()-t0:.0f}s]")
