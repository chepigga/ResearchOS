"""LAB277 (pre-registered): Tori Trades 'Trendline Bounce' as an independent engine on BTC (causal, no repainting).
Lines (H1): pivot lows/highs p=3|5 bars each side, confirmed at close of H1 bar k+p. Support = last two confirmed pivot lows with
  L2>L1 and no H1 close below the line between them (and up to confirmation). Active until an H1 close below it (or 10 days). Mirror for resistance.
Context: H4 structure up = last two confirmed H4 pivot highs ascending AND last two pivot lows ascending (p=2) [STRUCT] | + HTF EMA150>250 H1 [STRUCT+HTF].
Touch: M5 low within zone*ATR_H1 of the line (zone 0.1|0.25), close stays above line.
Confirm: UP = M5 close>open and close>line on touch bar or within next 3 bars | NONE = enter on touch bar close. Entry next M5 open.
Stop: lowest low since touch - 0.05 ATR_H1, distance clamped [0.25,2] ATR_H1.
Exit: stop | M15 close below the ENTRY line -> next open | trail: each new confirmed H1 pivot low above stop -> stop = pivot-0.05ATR | max 7 days.
Re-entry: new touch only after price moved >=1 ATR_H1 away from the line. One position at a time. Cost 7.5 bps.
Crowd: ANY | NOT_AGAINST (compass z24 not against) | WITH (compass with).
Select on 2021-24; 2025-26 shown. Report EV, R/mo, PF, MTM DD(R), hit +1R before stop."""
import numpy as np,pandas as pd
exec(open("ct268.py").read().split("\nrows=[]; EQ={}")[0])
h1=df.resample("1h").agg({"o":"first","h":"max","l":"min","c":"last"}).dropna()
H,Lo,C=h1.h.to_numpy(),h1.l.to_numpy(),h1.c.to_numpy(); TH=h1.index; NH=len(C)
tH=(TH-TH[0])/pd.Timedelta("1h"); tH=np.asarray(tH,float)            # bar open, hours
tM=np.asarray((T+pd.Timedelta("5min")-TH[0])/pd.Timedelta("1h"),float)  # M5 close, hours
hpos=np.searchsorted(TH.values,T.values,side="right")-1                  # H1 bar containing M5 bar
hend=np.asarray((T+pd.Timedelta("5min")).minute==0)                      # M5 bar closes an H1 bar
m15end=np.asarray((T+pd.Timedelta("5min")).minute%15==0)
# H4 structure
h4=df.resample("4h").agg({"h":"max","l":"min"}).dropna(); H4h,H4l=h4.h.to_numpy(),h4.l.to_numpy()
st4=np.zeros(len(H4h),int); ph=[];pl=[]
for k in range(4,len(H4h)):
    j=k-2
    if H4h[j]==H4h[j-2:j+3].max(): ph.append(H4h[j])
    if H4l[j]==H4l[j-2:j+3].min(): pl.append(H4l[j])
    if len(ph)>=2 and len(pl)>=2:
        st4[k]=1 if (ph[-1]>ph[-2] and pl[-1]>pl[-2]) else (-1 if (ph[-1]<ph[-2] and pl[-1]<pl[-2]) else 0)
S4=tfser("4h",h4.index,st4).astype(int)
def lines(p):
    """per M5 bar: active support/resistance line id (state known at last closed H1). table: (t1,v1,slope,side)"""
    tab=[]; act={1:-1,-1:-1}; pivs={1:[],-1:[]}; born={1:0,-1:0}
    stateH={1:np.full(NH,-1),-1:np.full(NH,-1)}
    val=lambda lid,t: tab[lid][1]+tab[lid][2]*(t-tab[lid][0])
    for m in range(NH):
        # breaks at close of m
        for sd in (1,-1):
            lid=act[sd]
            if lid>=0:
                v=val(lid,tH[m]+1)
                if (C[m]<v if sd>0 else C[m]>v) or tH[m]-tab[lid][0]>240: act[sd]=-1
        k=m-p
        if k>=p:
            if Lo[k]==Lo[k-p:k+p+1].min(): pivs[1].append(k)
            if H[k]==H[k-p:k+p+1].max(): pivs[-1].append(k)
            for sd,arr in ((1,Lo),(-1,H)):
                pv=pivs[sd]
                if len(pv)>=2 and pv[-1]==k:
                    k1,k2=pv[-2],pv[-1]
                    if (arr[k2]>arr[k1]) if sd>0 else (arr[k2]<arr[k1]):
                        sl=(arr[k2]-arr[k1])/(tH[k2]-tH[k1]); t1=tH[k1]; v1=arr[k1]
                        js=np.arange(k1+1,m+1); lv=v1+sl*(tH[js]+1-t1)
                        ok=(C[js]>=lv).all() if sd>0 else (C[js]<=lv).all()
                        if ok: tab.append((t1,v1,sl,sd)); act[sd]=len(tab)-1
        stateH[1][m]=act[1]; stateH[-1][m]=act[-1]
    # M5 bar i uses state at close of previous H1 bar
    prevH=hpos-1
    LS={sd:np.where(prevH>=0,stateH[sd][np.maximum(prevH,0)],-1) for sd in (1,-1)}
    TAB=np.array(tab) if tab else np.zeros((0,4))
    LV={sd:np.where(LS[sd]>=0,TAB[np.maximum(LS[sd],0),1]+TAB[np.maximum(LS[sd],0),2]*(tM-TAB[np.maximum(LS[sd],0),0]),np.nan) for sd in (1,-1)}
    pivconf={sd:sorted(k+p for k in pivs[sd]) for sd in (1,-1)}
    return LS,LV,TAB,pivs
def run(p,ctx,zone,conf,crowd,LS,LV,TAB,pivs):
    # pivot lows/highs confirmation times (M5 index of close of H1 bar k+p)
    hstart=np.searchsorted(T.values,TH.values)
    pl_conf=[(hstart[k+p+1] if k+p+1<NH else N-1,Lo[k]) for k in pivs[1]]
    ph_conf=[(hstart[k+p+1] if k+p+1<NH else N-1,H[k]) for k in pivs[-1]]
    out=[]; busy=-1; rearm={1:True,-1:True}
    i=400
    while i<N-3:
        if i<=busy: i=busy+1; continue
        took=False
        for sd in (1,-1):
            lv=LV[sd][i]
            if not np.isfinite(lv): rearm[sd]=True; continue
            a=BA[i]
            if not rearm[sd]:
                if sd*(BC[i]-lv)>=a: rearm[sd]=True
                continue
            if S4[i]!=sd: continue
            if ctx=="STRUCT+HTF" and HTF[i]!=sd: continue
            if crowd=="NOT_AGAINST" and CMP[i]==-sd: continue
            if crowd=="WITH" and CMP[i]!=sd: continue
            touch=(BL[i]<=lv+zone*a) if sd>0 else (BH[i]>=lv-zone*a)
            if not touch or sd*(BC[i]-lv)<=0: continue
            lid=LS[sd][i]; trig=None
            if conf=="NONE": trig=i
            else:
                for j in range(i,min(i+4,N-2)):
                    lvj=TAB[lid,1]+TAB[lid,2]*(tM[j]-TAB[lid,0])
                    if sd*(BC[j]-lvj)<=0: break
                    if sd*(BC[j]-BO[j])>0: trig=j; break
            rearm[sd]=False
            if trig is None: continue
            ei=trig+1; e=BO[ei]
            ext=BL[i:trig+1].min() if sd>0 else BH[i:trig+1].max()
            dist=sd*(e-ext)+0.05*a; dist=min(max(dist,0.25*a),2*a); stp=e-sd*dist
            # walk
            pk=0.0; hit1=False; x=None; r=None
            pc=[(t,v) for t,v in (pl_conf if sd>0 else ph_conf) if t>ei]; pci=0
            for k in range(ei,min(ei+2016,N-2)):
                while pci<len(pc) and pc[pci][0]<=k:
                    v=pc[pci][1]-sd*0.05*a
                    if sd*(v-stp)>0 and sd*(BC[k-1]-v)>0: stp=v
                    pci+=1
                if (BL[k]<=stp) if sd>0 else (BH[k]>=stp): r=sd*(stp-e)/dist; x=k; break
                if sd*((BH[k] if sd>0 else BL[k])-e)>=dist: hit1=True
                if m15end[k]:
                    lvk=TAB[lid,1]+TAB[lid,2]*(tM[k]-TAB[lid,0])
                    if sd*(BC[k]-lvk)<0: x=k+1; r=sd*(BO[x]-e)/dist; break
            if x is None: x=min(ei+2015,N-2); r=sd*(BC[x]-e)/dist
            out.append(dict(i=ei,x=x,r=r-COST/1e4*e/dist,tr=BT[ei]<TE,sd=sd,e=e,R=dist,hit1=hit1))
            busy=x; took=True; break
        i+=1
    return pd.DataFrame(out)
rows=[]
for p in (3,5):
    LS,LV,TAB,pivs=lines(p); print("lines",p,len(TAB),flush=True)
    for ctx in ("STRUCT","STRUCT+HTF"):
        for zone in (0.1,0.25):
            for conf in ("UP","NONE"):
                for crowd in ("ANY","NOT_AGAINST","WITH"):
                    t=run(p,ctx,zone,conf,crowd,LS,LV,TAB,pivs)
                    if len(t)==0: continue
                    E=mtm_eq(t); o=st_(t,E); r_=dict(p=p,ctx=ctx,zone=zone,conf=conf,crowd=crowd)
                    for sg,m in (("21",t.tr),("25",~t.tr)):
                        x=t[m]; pf=x.r[x.r>0].sum()/max(1e-9,-x.r[x.r<0].sum())
                        r_.update({f"n{sg}":o[f"n{sg}"],f"ev{sg}":o[f"ev{sg}"],f"pf{sg}":pf,f"Rmo{sg}":o[f"Rmo{sg}"],f"rdd{sg}":o[f"rdd{sg}"],f"hit{sg}":x.hit1.mean(),f"hold{sg}":o[f"hold{sg}"]})
                    rows.append(r_); print(p,ctx,zone,conf,crowd,round(r_["ev21"],3),round(r_["ev25"],3),flush=True)
X=pd.DataFrame(rows); X.to_csv("out_oos/LAB277_TLBOUNCE.csv",index=False)
pd.set_option("display.width",300); print(X.round(2).to_string(index=False))
