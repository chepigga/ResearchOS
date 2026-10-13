import zwin as Wm
import numpy as np, pandas as pd
BT,BC,BA=Wm.BT,Wm.BC,Wm.BA
z6=Wm.Z["6 год (поточне)"]; z24=Wm.Z["24 год"]; z3d=Wm.Z["3 дні"]
s=pd.Series(BC,index=BT)
h1=s.resample("1h").last().dropna(); e20=h1.ewm(span=20,adjust=False).mean()
h4=s.resample("4h").last().dropna(); e50=h4.ewm(span=50,adjust=False).mean()
tr4=pd.Series(np.where((h4>e50)&(e50>e50.shift(6)),1,np.where((h4<e50)&(e50<e50.shift(6)),-1,0)),index=h4.index)
def asof(ser,sh): x=ser.copy(); x.index=x.index+sh; return x.reindex(BT,method="ffill").to_numpy()
EXT=(BC-asof(e20,pd.Timedelta("1h")))/BA; TR4=asof(tr4,pd.Timedelta("4h"))
side=-np.sign(z6)
base=(np.abs(z6)>=2)&(np.r_[0,np.abs(z6)[:-1]]<2)&np.isfinite(z6)&(np.sign(z24)==np.sign(z6))&(np.abs(z24)>=1)
rules={
 "A: 6г≥2 + 24г≥1 (база)":base,
 "B: A + 3 дні той самий бік (|z3д|≥0.5)":base&(np.sign(z3d)==np.sign(z6))&(np.abs(z3d)>=0.5),
 "C: A + 3 дні протилежний бік":base&(np.sign(z3d)==-np.sign(z6))&(np.abs(z3d)>=0.5),
 "D: A + H4-тренд за угодою":base&(TR4==side),
 "E: A + H4-тренд проти угоди":base&(TR4==-side),
 "F: A + H4 без тренду":base&(TR4==0),
 "G: A + ціна вже йде в бік угоди (H1 ≥1 ATR від EMA20)":base&(side*EXT>=1),
 "H: A + ціна розтягнута проти угоди (≥1 ATR)":base&(side*EXT<=-1),
}
rows=[]
for nm,m in rules.items():
    F=np.where(m)[0]
    for sg in ["2021-24","2025-26"]:
        Fs=F[Wm.seg[F]==sg]; drift=np.nanmean(side[Fs]*Wm.f24[Fs])
        early=first=sw=sa=nw=0
        for i0,i1,d_,s_ in Wm.WI:
            if s_!=sg: continue
            nw+=1; third=i0+(i1-i0)//3; f=F[(F>=i0)&(F<i1)]; sd=side[f]
            early+=((f[sd==d_])<=third).any(); first+=(len(f)>0 and sd[0]==d_); sw+=(sd==d_).sum(); sa+=(sd==-d_).sum()
        rows.append(dict(rule=nm,seg=sg,signals_mo=len(Fs)/Wm.MO[sg],drift24=drift,first_third=early/nw,precision=sw/max(sw+sa,1)))
pd.set_option("display.width",260)
print(pd.DataFrame(rows).pivot_table(index="rule",columns="seg",values=["signals_mo","drift24","first_third","precision"],sort=False).round(2).to_string())
