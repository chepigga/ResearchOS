from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB124_ANTI_CROWD_QUALITY_SCORE_20261008/run_lab124.py"
spec=importlib.util.spec_from_file_location("lab124",SRC)
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)

OUT=Path("lab146_out");OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]
MAX_H=48
SEARCH_BARS=72
BT=A.BT;BO=A.BO;BH=A.BH;BL=A.BL;BC=A.BC;BA=A.BA
CTX=A.df[(A.df["split"]=="TRAIN") & (A.df.phase.isin(["CONT","REACCEL"]))].copy().reset_index(drop=True)

def first_swing3_close(i,side):
    for j in range(i+1,min(i+SEARCH_BARS,len(BT)-2)+1):
        lo=max(i,j-3)
        if side>0:
            ref=float(np.max(BH[lo:j]))
            if BC[j]>ref:return j,ref
        else:
            ref=float(np.min(BL[lo:j]))
            if BC[j]<ref:return j,ref
    return None,None

def extreme_reclaim(i,side):
    # First bar after the signal that makes/extends the capitulation extreme
    # and closes back across the previous bar's extreme.
    end=min(i+SEARCH_BARS,len(BT)-2)
    run_ext=float(BL[i] if side>0 else BH[i])
    for j in range(i+1,end+1):
        if side>0:
            new_ext=BL[j]<=run_ext
            if new_ext:
                run_ext=min(run_ext,float(BL[j]))
                if BC[j]>BL[j-1]:
                    return j
        else:
            new_ext=BH[j]>=run_ext
            if new_ext:
                run_ext=max(run_ext,float(BH[j]))
                if BC[j]<BH[j-1]:
                    return j
    return None

def failed_continuation(i,side):
    # New adverse extreme, but close fails to hold beyond prior bar extreme.
    end=min(i+SEARCH_BARS,len(BT)-2)
    run_ext=float(BL[i] if side>0 else BH[i])
    for j in range(i+1,end+1):
        if side>0:
            if BL[j]<run_ext:
                old=run_ext;run_ext=float(BL[j])
                if BC[j]>old:return j
        else:
            if BH[j]>run_ext:
                old=run_ext;run_ext=float(BH[j])
                if BC[j]<old:return j
    return None

def rejection_wick(i,side,min_wick_body=1.5):
    # Rejection candle after/at capitulation extreme:
    # long wick in reversal direction and close in favorable half.
    end=min(i+SEARCH_BARS,len(BT)-2)
    run_ext=float(BL[i] if side>0 else BH[i])
    for j in range(i+1,end+1):
        o=float(BO[j]);h=float(BH[j]);l=float(BL[j]);c=float(BC[j])
        body=max(abs(c-o),1e-9);rng=max(h-l,1e-9);mid=(h+l)/2
        if side>0:
            made=l<=run_ext
            run_ext=min(run_ext,l)
            lower=min(o,c)-l
            if made and lower/body>=min_wick_body and c>=mid:return j
        else:
            made=h>=run_ext
            run_ext=max(run_ext,h)
            upper=h-max(o,c)
            if made and upper/body>=min_wick_body and c<=mid:return j
    return None

def first_response_close(i,side):
    # Weakest causal confirmation: first favorable-color M5 close after signal
    # that also closes beyond previous close.
    end=min(i+SEARCH_BARS,len(BT)-2)
    for j in range(i+1,end+1):
        if side>0 and BC[j]>BO[j] and BC[j]>BC[j-1]:return j
        if side<0 and BC[j]<BO[j] and BC[j]<BC[j-1]:return j
    return None

def build(name):
    rows=[]
    for _,r in CTX.iterrows():
        i=int(r.signal_i);side=int(r.side);atr=float(r.atr)
        if name=="BASE_NEXT_OPEN":
            j,_=first_swing3_close(i,side)
            if j is None:continue
            ei=j+1;ep=float(BO[ei])
        elif name=="SWING3_CLOSE":
            j,_=first_swing3_close(i,side)
            if j is None:continue
            ei=j;ep=float(BC[j])
        elif name=="EXTREME_RECLAIM":
            j=extreme_reclaim(i,side)
            if j is None:continue
            ei=j;ep=float(BC[j])
        elif name=="FAILED_CONT":
            j=failed_continuation(i,side)
            if j is None:continue
            ei=j;ep=float(BC[j])
        elif name=="REJECTION_WICK":
            j=rejection_wick(i,side,1.5)
            if j is None:continue
            ei=j;ep=float(BC[j])
        elif name=="FIRST_RESPONSE":
            j=first_response_close(i,side)
            if j is None:continue
            ei=j;ep=float(BC[j])
        else: raise ValueError(name)
        if ei>=len(BT)-1:continue
        rows.append(dict(signal_i=i,trigger_i=j,entry_i=ei,signal_time=BT.iloc[i],
                         trigger_time=BT.iloc[j],entry_time=BT.iloc[ei],entry_price=ep,
                         side=side,atr=atr,delay_min=(BT.iloc[ei]-BT.iloc[i]).total_seconds()/60))
    return pd.DataFrame(rows)

def sim_one(r,cost):
    ei=int(r.entry_i);side=int(r.side);atr=float(r.atr);entry=float(r.entry_price)
    sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+MAX_H*12-1,len(BT)-1)
    gross=side*(BC[end]-entry)/atr;reason="TIME";xi=end;mfe=0.;mae=0.
    for j in range(ei,end+1):
        fav=((BH[j]-entry)*side/atr) if side>0 else ((entry-BL[j])/atr)
        adv=((entry-BL[j])/atr) if side>0 else ((BH[j]-entry)/atr)
        mfe=max(mfe,float(fav));mae=max(mae,float(adv))
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        # For same-bar close entries, do not allow pre-entry OHLC to stop/TP us on the trigger bar.
        # Start risk evaluation from next M5 bar when entry occurs at trigger close.
        if j==ei and pd.Timestamp(r.entry_time)==pd.Timestamp(r.trigger_time):
            continue
        if hs and ht:gross=-1;reason="BOTH_STOP_FIRST";xi=j;break
        if hs:gross=-1;reason="SL";xi=j;break
        if ht:gross=3;reason="TP";xi=j;break
    net=float(gross-(cost/10000.0)*entry/atr)
    return net,reason,xi,mfe,mae

def summarize(t):
    x=t.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
    ce=np.cumsum(x);dd=float(np.max(np.maximum.accumulate(ce)-ce))
    a=pd.Timestamp(t.entry_time.min());b=pd.Timestamp(t.exit_time.max());months=max((b.year-a.year)*12+b.month-a.month+1,1)
    losers=t[t.net_r<0]
    return dict(n=len(t),trades_month=len(t)/months,ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                wr=float((x>0).mean()),r_month=float(x.sum()/months),dd_r=dd,
                median_delay_min=float(t.delay_min.median()),stop_rate=float(t.reason.isin(["SL","BOTH_STOP_FIRST"]).mean()),
                loser_median_mfe=float(losers.mfe_r.median()) if len(losers) else np.nan,
                loser_reached_1r=float((losers.mfe_r>=1).mean()) if len(losers) else np.nan)

variants=["BASE_NEXT_OPEN","SWING3_CLOSE","EXTREME_RECLAIM","FAILED_CONT","REJECTION_WICK","FIRST_RESPONSE"]
summary=[];alltr=[]
for name in variants:
    v=build(name)
    for cost in COSTS:
        rows=[];open_until=pd.Timestamp.min.tz_localize("UTC")
        for _,r in v.sort_values("entry_time").iterrows():
            if r.entry_time<open_until:continue
            net,reason,xi,mfe,mae=sim_one(r,cost)
            open_until=BT.iloc[xi]
            q=r.to_dict();q.update(exit_time=BT.iloc[xi],net_r=net,reason=reason,mfe_r=mfe,mae_r=mae)
            rows.append(q)
        t=pd.DataFrame(rows)
        s=summarize(t);s.update(variant=name,cost_bps=cost,raw_signals=len(v),fill_rate=len(v)/len(CTX));summary.append(s)
        t["variant"]=name;t["cost_bps"]=cost;alltr.append(t)

S=pd.DataFrame(summary);S.to_csv(OUT/"LAB146_trigger_surface.csv",index=False)
pd.concat(alltr,ignore_index=True).to_csv(OUT/"LAB146_trades.csv",index=False)

b=S[(S.variant=="BASE_NEXT_OPEN")&(S.cost_bps==7.5)].iloc[0]
eligible=S[(S.cost_bps==7.5)&(S.pf>=b.pf)&(S.r_month>=b.r_month)&(S.dd_r<=1.25*b.dd_r)].sort_values(["r_month","pf"],ascending=False)
winner=str(eligible.iloc[0].variant) if len(eligible) else "BASE_NEXT_OPEN"

lines=["# LAB146 — A EARLY TRIGGER SURFACE","",
       "Engine A context is frozen. Only earlier/looser M5 entry triggers are tested.",
       f"Frozen context cohort: {len(CTX)} TRAIN CONT/REACCEL events.",
       "Exit stays SL=1 H1ATR / TP=3R / max48h / one-position chronology.",
       "Same-bar variants enter at trigger M5 close; stop/TP evaluation begins on the next bar to avoid impossible pre-entry OHLC fills.",
       ""]
for cost in COSTS:
    lines.append(f"## {cost:.2f}bps")
    for _,r in S[S.cost_bps==cost].sort_values("r_month",ascending=False).iterrows():
        lines.append(f"- {r.variant}: N={int(r.n)} ({r.trades_month:.2f}/mo), raw fill={r.fill_rate:.1%}, delay={r.median_delay_min:.0f}m, EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, DD={r.dd_r:.1f}R, stop={r.stop_rate:.1%}, loser MFE={r.loser_median_mfe:.2f}R, losers>=1R={r.loser_reached_1r:.1%}")
lines += ["",f"Frozen-rule winner: **{winner}**.",
          "Promotion rule requires stress PF and R/month both >= baseline, with DD <=125% of baseline.",
          "This is BTC TRAIN discovery only; no context thresholds changed."]
(OUT/"LAB146_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB146_meta.json").write_text(json.dumps(dict(winner=winner,variants=variants,
    decision_rule="stress PF>=baseline and R/month>=baseline and DD<=125% baseline",
    caveat="TRAIN discovery, same-bar close entries evaluated from next bar"),indent=2))
print("\n".join(lines))
