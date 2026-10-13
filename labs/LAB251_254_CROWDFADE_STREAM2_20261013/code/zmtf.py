import zwin as Wm
import numpy as np, pandas as pd
z6=Wm.Z["6 год (поточне)"]; z24=Wm.Z["24 год"]
rows=[]
for Tz,T24 in [(1.0,1.0),(2.0,1.0),(2.0,2.0)]:
    az=np.abs(z6)
    F=np.where((az>=Tz)&(np.r_[0,az[:-1]]<Tz)&np.isfinite(z6)&(np.sign(z24)==np.sign(z6))&(np.abs(z24)>=T24))[0]
    for sg in ["2021-24","2025-26"]:
        Fs=F[Wm.seg[F]==sg]; drift=np.nanmean(-np.sign(z6[Fs])*Wm.f24[Fs])
        early=first=sw=sa=nw=0
        for i0,i1,d_,s_ in Wm.WI:
            if s_!=sg: continue
            nw+=1; third=i0+(i1-i0)//3; f=F[(F>=i0)&(F<i1)]; sd=-np.sign(z6[f])
            early+=((f[sd==d_])<=third).any(); first+=(len(f)>0 and sd[0]==d_); sw+=(sd==d_).sum(); sa+=(sd==-d_).sum()
        rows.append(dict(rule=f"6г |z|≥{Tz} і 24г |z|≥{T24} той самий бік",seg=sg,signals_mo=len(Fs)/Wm.MO[sg],drift24_at_signal=drift,
                         in_first_third=early/nw,first_right=first/nw,precision=sw/max(sw+sa,1)))
print(pd.DataFrame(rows).pivot_table(index="rule",columns="seg",values=["signals_mo","drift24_at_signal","in_first_third","first_right","precision"],sort=False).round(2).to_string())
