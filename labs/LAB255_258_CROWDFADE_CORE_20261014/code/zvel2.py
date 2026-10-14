exec(open("zvel.py").read().split('S=D.iloc')[0])
# wave lookup per bar
wdir=np.zeros(N,int); wpos=np.full(N,np.nan); wtr=np.zeros(N,bool)
for i0,i1,d,tr in WV: wdir[i0:i1]=d; wpos[i0:i1]=(np.arange(i0,i1)-i0)/(i1-i0)
def evaluate(name,ev):
    ev=np.array(ev,dtype=int) if len(ev) else np.zeros((0,2),int)
    for seg in (True,False):
        e=ev[(BT[ev[:,0]]<TE)==seg] if len(ev) else ev
        mo=48 if seg else 19.3
        i=e[:,0]; s=e[:,1]; inw=wdir[i]!=0
        prec=(wdir[i][inw]==s[inw]).mean()
        dr=np.nanmean(s*fut[i])
        early=((wdir[i]==s)&(wpos[i]<1/3))
        nw=sum(1 for w in WV if w[3]==seg)
        cov=len(set(np.searchsorted([w[0] for w in WV],i[early],side="right")))/nw
        print(f"{name:42s} {'2021-24' if seg else '2025-26'}: {len(e)/mo:5.1f}/міс  точність {prec:.0%}  дрейф24 {dr:+.2f} ATR  ранніх у правильний бік {early.mean():.0%}  рухів зі стартовим сигналом {cov:.0%}")
def cross(x,thr,rearm):
    out=[];armed=True
    for i in range(400,N-300):
        v=x[i]
        if not np.isfinite(v): continue
        if abs(v)<rearm: armed=True; continue
        if armed and abs(v)>=thr and abs(x[i-1])<thr: out.append((i,-int(np.sign(v)))); armed=False
    return out
evaluate("рівень z6 ≥2 (без фільтрів)",cross(z6,2,1))
evaluate("D (z6 2 + z24 1 + H4)",g["E"].SIG)
for k in (6,12,24):
    for thr in (2,3,4):
        evaluate(f"швидкість dr{k} ≥{thr}",cross(F[f"dr{k}"],thr,thr/3))
# D split by speed at signal (how z6 was built)
print("\n== угоди D за швидкістю набору натовпу (dr12 у момент сигналу)")
t,_=g["simD"](g["E"].SIG); t["i"]=t.entry_i-1; t["sp"]=np.abs(F["dr12"][t.i.to_numpy(int)]); t["seg"]=np.where(BT[t.i.to_numpy(int)]<TE,"2021-24","2025-26")
t["q"]=t.groupby("seg").sp.transform(lambda x:pd.qcut(x,3,labels=["повільно","середньо","швидко"]))
print(t.groupby(["seg","q"],observed=True).net_r.agg(["count","mean","sum"]).round(2).to_string())
