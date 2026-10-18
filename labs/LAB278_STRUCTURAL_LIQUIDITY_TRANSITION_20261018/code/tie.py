exec(open("lab280.py").read().split("# ---------- Part 1")[0])
P1=pd.read_pickle("p1.pkl"); dayidx=np.searchsorted(days.values,BT.floor("1D").values)
x=P1[(P1["mode"]=="OPEN")&(P1.K==2)&(P1.hor=="DAY")]
# recompute with ties split 50/50 and with ties -> target
res=[]
for rr in x.itertuples():
    i=rr.i; ei=i+1; e=BO[ei]; a=BA[i]; sd=rr.sd; dS=rr.dS*a; dT=rr.dT*a; T_=e+sd*dT; stp=e-sd*dS
    d_=dayidx[i]; end=dend[d_]
    hT=(BL[ei:end]<=T_) if sd<0 else (BH[ei:end]>=T_); hS=(BH[ei:end]>=stp) if sd<0 else (BL[ei:end]<=stp)
    kt=np.argmax(hT) if hT.any() else 10**9; ks=np.argmax(hS) if hS.any() else 10**9
    res.append(dict(tie=(kt==ks and kt<10**9),T_opt=(kt<=ks and kt<10**9),T_cons=(kt<ks),p0=rr.p0,tr=rr.tr))
R=pd.DataFrame(res)
for sg,m in (("2021-24",R.tr),("2025-26",~R.tr)):
    y=R[m]; print(sg,f"нічиїх (ціль і стоп в одному M5) {y.tie.mean():.1%}; відхилення: консерв. {(y.T_cons-y.p0).mean():+.3f}, нічия=ціль {(y.T_opt-y.p0).mean():+.3f}, z {(y.T_opt-y.p0).mean()/((y.T_opt-y.p0).std()/np.sqrt(len(y))):.1f}")
