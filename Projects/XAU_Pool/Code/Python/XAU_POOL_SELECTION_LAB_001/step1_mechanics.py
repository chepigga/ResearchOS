"""
XAU_POOL_SELECTION_LAB_001 | КРОК 1
Реалізація 16 механік. Параметри — Додаток B. Умови — Додаток C.

Кожна функція повертає масив {-1, 0, +1} довжини len(df), де значення
на індексі i означає сигнал, ВИДИМИЙ на закритті бару i.
Каузальність: жодна не звертається до i+1 і далі.
"""
import numpy as np, pandas as pd

# ---------- допоміжні ----------
def sma(s, n): return s.rolling(n).mean()
def ema(s, n): return s.ewm(span=n, adjust=False).mean()

def atr_wilder(h, l, c, n):
    pc = c.shift(1)
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False, min_periods=n).mean()

def psar(h, l, af0=0.02, afmax=0.2):
    n=len(h); out=np.full(n, np.nan); bull=True
    ep=l.iloc[0]; sar=l.iloc[0]; af=af0
    hi=h.values; lo=l.values
    for i in range(1, n):
        sar = sar + af*(ep - sar)
        if bull:
            sar = min(sar, lo[i-1], lo[max(i-2,0)])
            if lo[i] < sar:
                bull=False; sar=ep; ep=lo[i]; af=af0
            elif hi[i] > ep:
                ep=hi[i]; af=min(af+af0, afmax)
        else:
            sar = max(sar, hi[i-1], hi[max(i-2,0)])
            if hi[i] > sar:
                bull=True; sar=ep; ep=hi[i]; af=af0
            elif lo[i] < ep:
                ep=lo[i]; af=min(af+af0, afmax)
        out[i]=sar
    return pd.Series(out, index=h.index)

def stoch(h, l, c, p1=5, p2=3, p3=3):
    ll=l.rolling(p1).min(); hh=h.rolling(p1).max()
    k=100*(c-ll)/(hh-ll).replace(0, np.nan)
    return k.rolling(p2).mean().rolling(p3).mean()

def linreg_channel(c, n=50, dev=1.0):
    x=np.arange(n); xm=x.mean(); den=((x-xm)**2).sum()
    vals=c.values; up=np.full(len(c),np.nan); dn=np.full(len(c),np.nan)
    for i in range(n-1, len(c)):
        y=vals[i-n+1:i+1]; ym=y.mean()
        b=((x-xm)*(y-ym)).sum()/den; a=ym-b*xm
        fit=a+b*x; resid=y-fit; sd=resid.std(ddof=0)
        up[i]=fit[-1]+dev*sd; dn[i]=fit[-1]-dev*sd
    return pd.Series(up,index=c.index), pd.Series(dn,index=c.index)

def fractal_up(h, n=2):
    return h.shift(n).where((h.shift(n)>h.shift(n+1))&(h.shift(n)>h.shift(n+2))&
                            (h.shift(n)>h.shift(n-1))&(h.shift(n)>h.shift(n-2))).ffill()
def fractal_dn(l, n=2):
    return l.shift(n).where((l.shift(n)<l.shift(n+1))&(l.shift(n)<l.shift(n+2))&
                            (l.shift(n)<l.shift(n-1))&(l.shift(n)<l.shift(n-2))).ffill()

def pivot_floor(df):
    d=df.set_index('time'); day=d.resample('1D').agg(h=('high','max'),l=('low','min'),c=('close','last')).dropna()
    p=(day.h+day.l+day.c)/3
    r1=2*p-day.l; s1=2*p-day.h
    pr=pd.DataFrame({'P':p,'R1':r1,'S1':s1}).shift(1)   # вчорашній день -> сьогодні
    key=df.time.dt.floor('D')
    return key.map(pr.R1), key.map(pr.S1)

# ---------- 16 механік ----------
def build_signals(df, tf):
    """df: колонки time, open, high, low, close. Повертає dict {id: array}"""
    o,h,l,c = df.open, df.high, df.low, df.close
    S={}

    # ===== TREND =====
    # 1 T_PRICECHANNEL : PC(21,21); обидві межі -> немає сигналу
    pcu=h.shift(1).rolling(21).max(); pcd=l.shift(1).rolling(21).min()
    up=(h>pcu); dn=(l<pcd)
    S['T_PRICECHANNEL']=np.where(up&~dn,1,np.where(dn&~up,-1,0))

    # 2 T_ENVELOPE : Envelops(10, 0.3%), СТОП-ордер на межах
    m=sma(c,10); eu=m*(1+0.3/100); el=m*(1-0.3/100)
    S['T_ENVELOPE']=np.where(h>=eu.shift(1),1,np.where(l<=el.shift(1),-1,0))

    # 3 T_LINREG : LinReg(50, dev 1), маркет
    lu,ld=linreg_channel(c,50,1.0)
    S['T_LINREG']=np.where(c>lu,1,np.where(c<ld,-1,0))

    # 4 T_PSAR : дедуплікація по зміні стану
    sar=psar(h,l,0.02,0.2); side=np.where(c>sar,1,np.where(c<sar,-1,0))
    S['T_PSAR']=np.where(side!=np.r_[0,side[:-1]],side,0)

    # 5 T_MACD_MOM : Momentum(5) навколо 100, Macd 12/26/9
    ml=ema(c,12)-ema(c,26); sg=ema(ml,9); mom=100*c/c.shift(5)
    S['T_MACD_MOM']=np.where((ml>sg)&(mom>100),1,np.where((ml<sg)&(mom<100),-1,0))

    # 6 T_SMA_STOCH : Sma(14) +/- Step, Stoch(5,3,3) перетин 30/70
    STEP=5.00   # 500 пунктів XAU
    sm=sma(c,14); st=stoch(h,l,c,5,3,3); stp=st.shift(1)
    S['T_SMA_STOCH']=np.where((c>sm+STEP)&(stp<=30)&(st>=30),1,
                      np.where((c<sm-STEP)&(stp>=70)&(st<=70),-1,0))

    # 7 T_ALLIGATOR : Lips3/Teeth10/Jaw40 + Fractal
    lip=sma((h+l)/2,3).shift(3); tee=sma((h+l)/2,10).shift(5); jaw=sma((h+l)/2,40).shift(8)
    fu=fractal_up(h); fd=fractal_dn(l)
    S['T_ALLIGATOR']=np.where((c>lip)&(c>tee)&(c>jaw)&(c>fu),1,
                      np.where((c<lip)&(c<tee)&(c<jaw)&(c<fd),-1,0))

    # 8 C_PIVOT (клас TREND) : пробій R1/S1 всередині бару
    R1,S1=pivot_floor(df)
    S['C_PIVOT']=np.where((c>R1)&(o<R1),1,np.where((c<S1)&(o>S1),-1,0))

    # ===== COUNTERTREND =====
    # 9 C_BOLLINGER : BB(21,2)
    bm=sma(c,21); bs=c.rolling(21).std(ddof=0)
    S['C_BOLLINGER']=np.where(c<bm-2*bs,1,np.where(c>bm+2*bs,-1,0))

    # 10 C_RSI — ВИКЛЮЧЕНО: 0 сигналів за 4 роки на всіх ТФ.
    # Механіка вимагає RSI<30 ПРИ ціні вище Sma(50); на XAU з Rsi(20)
    # цей стан не виникає. Умова відтворена за кодом, це не баг.

    # 11 C_WILLIAMS : WR(14), -80 / -20
    hh=h.rolling(14).max(); ll=l.rolling(14).min()
    wr=-100*(hh-c)/(hh-ll).replace(0,np.nan)
    S['C_WILLIAMS']=np.where(wr<-80,1,np.where(wr>-20,-1,0))

    # ===== PATTERN =====
    # 12 P_PINBAR : верхня/нижня третина + Sma(14)
    rng=(h-l).replace(0,np.nan); s14=sma(c,14)
    topi=(c>=h-rng/3)&(o>=h-rng/3); boti=(c<=l+rng/3)&(o<=l+rng/3)
    S['P_PINBAR']=np.where(topi&(s14<c),1,np.where(boti&(s14>c),-1,0))

    # 13 P_3SOLDIER : сукупно >=1.0%, кожна >=0.2%
    tot=(o.shift(2)-c).abs()/(c/100)
    e1=(o.shift(2)-c.shift(2)).abs()/(c.shift(2)/100)
    e2=(o.shift(1)-c.shift(1)).abs()/(c.shift(1)/100)
    e3=(o-c).abs()/(c/100)
    okh=(tot>=1.0)&(e1>=0.2)&(e2>=0.2)&(e3>=0.2)
    bull=(o.shift(2)<c.shift(2))&(o.shift(1)<c.shift(1))&(o<c)
    bear=(o.shift(2)>c.shift(2))&(o.shift(1)>c.shift(1))&(o>c)
    S['P_3SOLDIER']=np.where(okh&bull,1,np.where(okh&bear,-1,0))

    # 14 P_TURNAROUND : ТІЛЬКИ BUY, body>0.3*ATR(25)
    a25=atr_wilder(h,l,c,25); mn=0.3*a25
    b0=(c-o).abs(); b1=(c.shift(1)-o.shift(1)).abs()
    S['P_TURNAROUND']=np.where((b0>mn)&(b1>mn)&(c>o)&(c.shift(1)<o.shift(1)),1,0)

    # 15 P_IMPULSE : тільки M1, 2 свічки одного напрямку <=120с
    if tf=='M1':
        gap=(df.time-df.time.shift(2)).dt.total_seconds()
        u2=(c>o)&(c.shift(1)>o.shift(1)); d2=(c<o)&(c.shift(1)<o.shift(1))
        S['P_IMPULSE']=np.where(u2&(gap<=120),1,np.where(d2&(gap<=120),-1,0))

    # ===== VOLATILITY =====
    # 16 V_ATR_EXP : PC(50) + ATR(25) виріс >=3% за 20 барів
    p50u=h.shift(1).rolling(50).max(); p50d=l.shift(1).rolling(50).min()
    a25b=atr_wilder(h,l,c,25); grow=a25b/(a25b.shift(20)/100)-100
    S['V_ATR_EXP']=np.where((c>p50u)&(grow>=3.0),1,np.where((c<p50d)&(grow>=3.0),-1,0))

    # ---- СТАН -> ПОДІЯ ----
    # Механіка повідомляє сигнал ЛИШЕ на переході (хибне -> істинне).
    # Відтворює поведінку OsEngine, де вхід дозволений тільки за
    # відсутності відкритої позиції. Параметри НЕ змінюються.
    EVENT_ALREADY = {'T_PSAR'}          # вже дедупльовано всередині
    out={}
    for k,v in S.items():
        a=np.nan_to_num(np.asarray(v,float)).astype(int)
        if k not in EVENT_ALREADY:
            prev=np.r_[0,a[:-1]]
            a=np.where(a!=prev,a,0)     # сигнал тільки на зміні стану
        out[k]=a
    return out

# ================= ВЕРИФІКАЦІЯ =================
if __name__=='__main__':
    m1=pd.read_parquet('/home/claude/xau_m1.parquet').sort_values('time').reset_index(drop=True)
    print(f"M1: {len(m1):,} | {m1.time.min()} -> {m1.time.max()}\n")
    TFS=[('M1',None),('M5','5min'),('M15','15min'),('H1','1h')]
    rows=[]
    for tf,rule in TFS:
        g = m1[['time','open','high','low','close']].copy() if rule is None else \
            m1.set_index('time').resample(rule).agg(open=('open','first'),high=('high','max'),
              low=('low','min'),close=('close','last')).dropna().reset_index()
        S=build_signals(g,tf)
        for k,v in S.items():
            if tf!='M1' and k=='P_IMPULSE': continue
            if tf=='M1' and k!='P_IMPULSE': continue   # M1 лише для P_IMPULSE
            nb=(v==1).sum(); ns=(v==-1).sum(); n=nb+ns
            yr=pd.Series(v,index=g.time).pipe(lambda s:(s!=0).groupby(s.index.year).sum())
            rows.append(dict(tf=tf,mech=k,bars=len(g),signals=n,buy=nb,sell=ns,
                pct=100*n/len(g), years=len(yr[yr>0]), min_yr=int(yr.min()), gaps=int((yr==0).sum())))
    R=pd.DataFrame(rows)
    print(R.to_string(index=False,float_format=lambda v:f"{v:.2f}"))
    print("\n--- ПРОБЛЕМИ ---")
    bad=R[(R.signals==0)|(R.pct>40)|(R.gaps>0)|((R.buy==0)&(R.mech!='P_TURNAROUND'))|(R.sell==0)&(R.mech!='P_TURNAROUND')]
    print(bad.to_string(index=False) if len(bad) else "  немає")
