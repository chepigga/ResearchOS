import importlib.util,os,sys,numpy as np,pandas as pd
D=[d for d in os.listdir("/home/claude/chepigga/full/labs") if d.startswith("LAB124")][0]
os.chdir("/home/claude/data")
sp=importlib.util.spec_from_file_location("l124",f"/home/claude/chepigga/full/labs/{D}/run_lab124.py")
m=importlib.util.module_from_spec(sp)
src=open(sp.origin).read(); src=src[:src.index("# Broader anti-crowd")]
exec(compile(src,"l124","exec"),m.__dict__)
b,BZ,BT=m.b,m.BZ,m.BT
print("thresholds EXT80",round(m.EXT80,2),"OI70",round(m.OI70,4))
rows=[]
for i in range(1,len(b)-600):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1; trend=int(b.trend.iloc[i]); ext=float(b.extension.iloc[i]); oi=float(b.oi4h.iloc[i])
    r=dict(t=BT.iloc[i],stage=0)
    if trend!=0 and trend!=side:
        r["stage"]=1
        ext_against=(side>0 and ext<0) or (side<0 and ext>0)
        if ext_against and abs(ext)>=m.EXT80:
            r["stage"]=2
            if oi>=m.OI70:
                r["stage"]=3
                ei,ti,br=m.swing3_entry(i,side)
                if ei is not None:
                    r["stage"]=4
                    ph=m.phase(int(b.trend_age.iloc[i]),int(b.impulse_age.iloc[i]))
                    if ph in("CONT","REACCEL"): r["stage"]=5
    rows.append(r)
F=pd.DataFrame(rows); F["yr"]=F.t.dt.year
mo=F.groupby("yr").t.agg(lambda x:(x.max()-x.min()).days/30.44)
names=["перетин |z|≥1","H4-тренд з натовпом","розтяг ≥EXT80 проти","OI 4h ≥ OI70","злам свінгу","фаза CONT/REACCEL"]
out=pd.DataFrame({n:F[F.stage>=k].groupby("yr").size()/mo for k,n in enumerate(names)}).round(1)
print("подій на місяць:"); print(out.to_string())
# drivers per year
b["yr"]=b.time.dt.year
print("\nчастка часу: |ext|>=EXT80",b.groupby("yr").extension.apply(lambda x:(x.abs()>=m.EXT80).mean()).round(3).to_dict())
print("частка часу: OI4h>=OI70",b.groupby("yr").oi4h.apply(lambda x:(x>=m.OI70).mean()).round(3).to_dict())
print("частка часу: H4 trend!=0",b.groupby("yr").trend.apply(lambda x:(x!=0).mean()).round(3).to_dict())
print("медіана OI4h %",(b.groupby("yr").oi4h.median()*100).round(3).to_dict(), " p70:",(b.groupby("yr").oi4h.quantile(.7)*100).round(3).to_dict())
