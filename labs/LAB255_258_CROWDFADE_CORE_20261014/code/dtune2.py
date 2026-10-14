exec(open("dtune.py").read().split("rows=[]")[0])
src2=open("trendalt.py").read(); w0=src2.index("df=pd.DataFrame({\"c\":BC"); w1=src2.index("rows=[]",w0)
exec(src2[w0:w1],g); WV=g["WV"]
def info(name,SIG):
    t,e=simD(SIG); t["side"]=[dict(SIG)[i-1] for i in t.entry_i]; t["yr"]=pd.DatetimeIndex(BT[t.entry_i.to_numpy(int)]).year
    print("\n==",name,"| R по роках:",t.groupby("yr").net_r.sum().round(1).to_dict())
    for seg in (True,False):
        n=ft=mid=late=0; Rf=[];Rl=[]
        for i0,i1,d,tr in WV:
            if tr!=seg: continue
            x=t[(t.entry_i>=i0)&(t.entry_i<i1)&(t.side==d)]
            if len(x)==0: continue
            n+=1; f=(BO[int(x.entry_i.min())]-BC[i0])/(BC[i1]-BC[i0])
            if f<1/3: ft+=1
            elif f<2/3: mid+=1
            else: late+=1
        print("2021-24" if seg else "2025-26",f"рухів зі входом {n}: перша третина {ft/n:.0%}, середина {mid/n:.0%}, остання {late/n:.0%}; угод з рухом у першій третині (на всі ≥3ATR): {ft/sum(1 for w in WV if w[3]==seg):.0%}")
info("D зараз (2.0 / 1.0 / H4)",build(2.0,1.0,True,None,None))
info("D' (2.0 / 1.0 / без тренду)",build(2.0,1.0,False,None,None))
info("D2 (1.5 / 0.5 / H4)",build(1.5,0.5,True,None,None))
info("1.5 / 1.5 / H4 / запізнення≤1",build(1.5,1.5,True,1,None))
