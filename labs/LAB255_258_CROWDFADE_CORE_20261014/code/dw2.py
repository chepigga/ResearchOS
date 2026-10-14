exec(open("dweight.py").read().split("V={")[0])
for name,(S,w,sep) in {"0":(SIGH,1,0),"1":(SIG,1,0),"4 sep1":(SIG,1,1),"6 sep2":(SIG,1,2)}.items():
    t,_=sim(S,w,sep); t["seg"]=np.where(BT[t.entry_i.to_numpy(int)]<TE,"TRAIN","OOS")
    print(name, t.groupby(["seg","al"]).net_r.agg(["count","mean","sum"]).round(2).to_dict("index"))
