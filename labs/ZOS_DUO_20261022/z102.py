import pandas as pd,numpy as np
m15=pd.read_pickle("/home/claude/xau/m15.pkl")
def atr_mt5(b,n=14):
    c=b.close; tr=pd.concat([b.high-b.low,(b.high-c.shift()).abs(),(b.low-c.shift()).abs()],axis=1).max(axis=1); return tr.rolling(n).mean()
def run(dev_arr=None,dev=0.008,depth=8,body=0.30,life=200,maxord=2,struct=True,extbars=10,buf=0.10,minr=0.15,maxr=4.0,spr_atr=0.20,dev_mode="pct",dev_k=None,dev_atr=None,onepos=True,tout=32):
    b=m15; o,h,l,c=[b[x].values for x in ("open","high","low","close")]; A=atr_mt5(b).values; sp=b.spread.values/100
    t=b.index; N=len(b)
    piv=[]; lv=[]; zt=0; zi=0; zp=0.0; ev=[]; busy=-1
    for i in range(N):
        a=A[i]
        D=(dev if dev_mode=="pct" else None)
        # ---- ProcessBar
        if not np.isnan(a) and a>0 and abs(c[i]-o[i])>=body*a:
            for L in lv:
                if L["dead"] or i<L["av"]: continue
                if i>L["av"]+life: L["dead"]=True; continue
                side=L["side"]; beyond=(c[i]<L["p"]) if side>0 else (c[i]>L["p"])
                if not beyond: continue
                L["o"]+=1; od=L["o"]
                if od>=maxord: L["dead"]=True
                if od>maxord: continue
                d=-side
                hs=[p for p in piv if p[3]<i]
                H=[p[1] for p in reversed(hs) if p[2]>0][:2]; Lo=[p[1] for p in reversed(hs) if p[2]<0][:2]
                stt=0
                if len(H)==2 and len(Lo)==2:
                    stt=1 if (H[0]>H[1] and Lo[0]>Lo[1]) else (-1 if (H[0]<H[1] and Lo[0]<Lo[1]) else 0)
                wt=0 if stt==0 else (1 if d==stt else -1)
                if struct and wt<0: ev.append((t[i],"struct",d)); continue
                lo_=max(i-extbars,L["av"])
                ext=(l[lo_:i+1].min() if d>0 else h[lo_:i+1].max())
                if i+1>=N: continue
                e=o[i+1]+(sp[i] if d>0 else 0)   # вхід на відкритті наступного бару
                risk=(e-ext+buf*a) if d>0 else (ext-e+buf*a)
                if risk<=minr*a: ev.append((t[i],"risk_small",d)); continue
                if risk>maxr*a: ev.append((t[i],"risk_big",d)); continue
                if sp[i]/a>spr_atr: ev.append((t[i],"spread",d)); continue
                if onepos and i<busy: ev.append((t[i],"busy",d)); continue
                sl=e-d*risk; tp=e+d*3*risk; j=i+1; res=None
                while j<N and j<=i+tout:
                    if (d>0 and l[j]<=sl) or (d<0 and h[j]>=sl): res=-1.0; break
                    if (d>0 and h[j]>=tp) or (d<0 and l[j]<=tp): res=3.0; break
                    j+=1
                if res is None: j=min(j,N-1); res=d*(c[j]-e)/risk
                busy=j if onepos else busy
                ev.append((t[i],"ENTRY",d,e,risk,a,res)); break
        # ---- ZigZag
        dv=dev if dev_arr is None else dev_arr[i]
        if np.isnan(dv): continue
        thr_up=lambda p:p*(1+dv)
        thr_dn=lambda p:p*(1-dv)
        if zt==0:
            if zp<=0: zp=c[i]; zi=i; continue
            if h[i]>=thr_up(zp): zt=1; zi=i; zp=h[i]
            elif l[i]<=thr_dn(zp): zt=-1; zi=i; zp=l[i]
        elif zt>0:
            if h[i]>zp: zi=i; zp=h[i]
            elif l[i]<=thr_dn(zp) and i-zi>=depth:
                piv.append((zi,zp,1,i)); lv.append(dict(p=zp,side=-1,av=i+1,o=0,dead=False)); zt=-1; zi=i; zp=l[i]
        else:
            if l[i]<zp: zi=i; zp=l[i]
            elif h[i]>=thr_up(zp) and i-zi>=depth:
                piv.append((zi,zp,-1,i)); lv.append(dict(p=zp,side=1,av=i+1,o=0,dead=False)); zt=1; zi=i; zp=h[i]
        lv=[L for L in lv if not L["dead"] and i<=L["av"]+life]
    return ev,piv
