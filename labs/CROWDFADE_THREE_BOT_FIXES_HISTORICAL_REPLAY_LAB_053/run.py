from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

# Reuse frozen, previously validated loaders / common research conventions.
p43=ROOT.parent/'CROWDFADE_V191D_TO_V191F_ABLATION_LAB_043'/'run.py'
sp43=importlib.util.spec_from_file_location('lab43',p43)
lab43=importlib.util.module_from_spec(sp43); sp43.loader.exec_module(lab43)
lab43.DATA=DATA

p51=ROOT.parent/'CROWDFADE_V200_FIXED_ENTRY_TRAILING_LAB_051'/'run.py'
sp51=importlib.util.spec_from_file_location('lab51',p51)
lab51=importlib.util.module_from_spec(sp51); sp51.loader.exec_module(lab51)
lab51.DATA=DATA

COST_BPS=0.50
ZTH=1.00
CONF_ATR=0.30
CONF_TTL=2700
SL_ATR=1.50
HOLD_S=6*3600
PAUSE_ATR=1.00
MAXDAY=3

# CF191s v1.96 additions.
S_MIN_ABS_Z=0.75
S_MAX_ADV=0.75
S_MIN_RESPONSE=0.50

# CF191g current positive-skew management + v1.95 episode guard.
G_MIN_ABS_Z=0.75
G_MAX_ADV=0.75
G_MIN_RESPONSE=0.50
G_BE_ARM=3.00
G_BE_LOCK=2.25
G_TRAIL_ARM=3.50
G_TRAIL_GAP=0.50
G_EP_MAX=2
G_EP_RESET_Z=0.50

def metrics(a):
    return lab43.metrics(np.asarray(a,float))

def period_count(st,r,kind):
    if len(r)==0:return {'positive':0,'total':0,'details':{}}
    t=pd.to_datetime(st,unit='s',utc=True)
    keys=(t.year.astype(str).to_numpy() if kind=='year' else t.to_period('M').astype(str).to_numpy())
    d={}
    for k in sorted(set(keys)):
        m=metrics(r[keys==k]); d[str(k)]=m
    return {'positive':sum(1 for v in d.values() if v.get('SumR',0)>0),'total':len(d),'details':d}

@njit(cache=True)
def sim_cf191s(ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5,guarded):
    cap=len(dt5)
    R=np.zeros(cap); ST=np.zeros(cap,np.int64); SIDE=np.zeros(cap,np.int8)
    n=0;k=0;day=-1;dc=0;nextts=0;last=0.;la=0.;has=False
    skips=np.zeros(6,np.int64) # no_confirm/adverse/side/minz/noise/contradict
    while k<len(dt5)-3:
        t=dt5[k]
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z0=Z5[k]
        side=-1 if z0>=ZTH else (1 if z0<=-ZTH else 0)
        if side==0:k+=1;continue
        sig=C5[k];atr=A5[k]
        if has and abs(sig-last)<PAUSE_ATR*la:k+=1;continue

        target=sig+side*CONF_ATR*atr
        ps=np.searchsorted(ts,t+1);pe=np.searchsorted(ts,t+CONF_TTL,'right')
        ci=-1;maxadv=0.;maxfav=0.
        for q in range(ps,min(len(ts),pe)):
            adv=((H[q]-sig) if side<0 else (sig-L[q]))/atr
            fav=((sig-L[q]) if side<0 else (H[q]-sig))/atr
            if adv>maxadv:maxadv=adv
            if fav>maxfav:maxfav=fav
            if maxadv>S_MAX_ADV:
                ci=-2;break
            if (side>0 and C[q]>=target) or (side<0 and C[q]<=target):
                ci=q;break
        if ci==-2:
            skips[1]+=1;k+=1;continue
        if ci<0:
            skips[0]+=1;k+=1;continue

        zi=np.searchsorted(dt5,ts[ci],'right')-1
        if zi<0:k+=1;continue
        cz=Z5[zi]
        response=maxfav/(maxadv+1e-9)

        if guarded:
            same=(cz<0.0) if side>0 else (cz>0.0)
            if not same:
                skips[2]+=1;k=np.searchsorted(dt5,ts[ci])+1;continue
            if abs(cz)<S_MIN_ABS_Z:
                skips[3]+=1;k=np.searchsorted(dt5,ts[ci])+1;continue
            if response<S_MIN_RESPONSE:
                skips[4]+=1;k=np.searchsorted(dt5,ts[ci])+1;continue

        # Existing STRICT contradiction / ExitZ condition retained.
        if (side>0 and cz>=0.75) or (side<0 and cz<=-0.75):
            skips[5]+=1;k=np.searchsorted(dt5,ts[ci])+1;continue

        entry=C[ci]
        rr,ex,reason=lab43.manage_v191(ts,H,L,C,dt5,Z5,ci,side,entry,atr,0.75)
        R[n]=rr;ST[n]=t;SIDE[n]=side;n+=1
        dc+=1;last=entry;la=atr;has=True;nextts=ts[ex]+1
        k=np.searchsorted(dt5,nextts)
    return R[:n],ST[:n],SIDE[:n],skips

@njit(cache=True)
def manage_cf191g(dt5,H5,L5,C5,ei,side,entry,atr):
    stop0=entry-side*SL_ATR*atr
    pending=stop0; peak=entry
    xe=min(len(dt5)-1,np.searchsorted(dt5,dt5[ei]+HOLD_S,'left'))
    xp=C5[xe];ex=xe;reason=4
    for q in range(ei+1,xe+1):
        stop=pending
        if (side>0 and L5[q]<=stop) or (side<0 and H5[q]>=stop):
            xp=stop;ex=q;reason=2 if ((side>0 and stop>entry) or (side<0 and stop<entry)) else 1
            break
        if side>0:
            if H5[q]>peak:peak=H5[q]
            mfe=(peak-entry)/atr
        else:
            if L5[q]<peak:peak=L5[q]
            mfe=(entry-peak)/atr
        ns=stop
        if mfe>=G_BE_ARM:
            lvl=entry+side*G_BE_LOCK*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns):ns=lvl
        if mfe>=G_TRAIL_ARM:
            lvl=peak-side*G_TRAIL_GAP*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns):ns=lvl
        pending=ns
    rr=side*(xp-entry)/(SL_ATR*atr)-(COST_BPS/10000.)*entry/(SL_ATR*atr)
    return rr,ex,reason

@njit(cache=True)
def sim_cf191g(ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5,episode_guard):
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);SIDE=np.zeros(cap,np.int8)
    n=0;k=0;day=-1;dc=0;nextts=0;last=0.;la=0.;has=False

    conf=False;cs=0;cp=0.;ca=0.;ct=0;cb=0;mf=0.;ma=0.
    ep_side=0;ep_count=0
    skips=np.zeros(7,np.int64) # episode_arm/episode_confirm/timeout/adverse/side/minz/noise

    while k<len(dt5)-3:
        t=dt5[k];z=Z5[k]

        # Exact v1.95 episode refresh runs on every canonical M5 clock, even while occupied.
        if episode_guard:
            if abs(z)<G_EP_RESET_Z:
                ep_side=0;ep_count=0
            else:
                cur=-1 if z>0 else (1 if z<0 else 0)
                if ep_side!=0 and cur!=0 and cur!=ep_side:
                    ep_side=0;ep_count=0

        if t<nextts:
            k+=1;continue

        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:
            conf=False;k+=1;continue

        if conf:
            side=cs
            fav=((cp-L5[k]) if side<0 else (H5[k]-cp))/ca
            adv=((H5[k]-cp) if side<0 else (cp-L5[k]))/ca
            if fav<0:fav=0.
            if adv<0:adv=0.
            if fav>mf:mf=fav
            if adv>ma:ma=adv
            cb-=1
            age=t-ct
            if cb<=0 or age>2700:
                skips[2]+=1;conf=False;k+=1;continue
            if ma>G_MAX_ADV:
                skips[3]+=1;conf=False;k+=1;continue
            target=cp+side*CONF_ATR*ca
            confirmed=(C5[k]>=target) if side>0 else (C5[k]<=target)
            if not confirmed:
                k+=1;continue
            same=(z<0.0) if side>0 else (z>0.0)
            if not same:
                skips[4]+=1;conf=False;k+=1;continue
            if abs(z)<G_MIN_ABS_Z:
                skips[5]+=1;conf=False;k+=1;continue
            response=mf/(ma+1e-9)
            if response<G_MIN_RESPONSE:
                skips[6]+=1;conf=False;k+=1;continue
            conf=False

            if episode_guard and ep_side==side and ep_count>=G_EP_MAX:
                skips[1]+=1;k+=1;continue
            if has and abs(C5[k]-last)<PAUSE_ATR*la:
                k+=1;continue

            entry=C5[k]
            rr,ex,reason=manage_cf191g(dt5,H5,L5,C5,k,side,entry,ca)
            R[n]=rr;ST[n]=ct;SIDE[n]=side;n+=1
            dc+=1;last=C5[k];la=ca;has=True;nextts=dt5[ex]+1
            if episode_guard:
                if ep_side!=side:ep_count=0
                ep_count+=1;ep_side=side
            k+=1;continue

        side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:
            k+=1;continue
        if episode_guard and ep_side==side and ep_count>=G_EP_MAX:
            skips[0]+=1;k+=1;continue
        if has and abs(C5[k]-last)<PAUSE_ATR*la:
            k+=1;continue

        conf=True;cs=side;cp=C5[k];ca=A5[k];ct=t;cb=9;mf=0.;ma=0.
        k+=1

    return R[:n],ST[:n],SIDE[:n],skips

def row(period,bot,variant,R,ST,SIDE,skips=None):
    m=metrics(R)
    pc=period_count(ST,R,'year' if period=='historical' else 'month')
    x={'period':period,'bot':bot,'variant':variant,**m,
       'positive_periods':pc['positive'],'periods_total':pc['total']}
    if skips is not None:
        x['skip_counts']='|'.join(str(int(v)) for v in skips)
    return x,pc

def run():
    ft,fz=lab43.load_flow()
    hist=lab43.load_hist()
    sec=lab43.load_sec()
    frames={
      'historical':lab43.prep(hist,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp())),
      'forward_2026':lab43.prep(sec,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    }

    rows=[];details={}
    for period,p in frames.items():
        # CF191s old/new.
        for guarded,name in [(False,'OLD_STRICT'),(True,'NEW_v196_REGIME_GUARD')]:
            R,ST,SIDE,sk=sim_cf191s(*p,guarded)
            x,pc=row(period,'CF191s',name,R,ST,SIDE,sk);rows.append(x)
            details[f'{period}_CF191s_{name}']={'periods':pc,'skips':sk.tolist(),
                'BUY':metrics(R[SIDE>0]),'SELL':metrics(R[SIDE<0])}

        # CF191g old/new episode guard.
        for eg,name in [(False,'OLD_v191g_POSITIVE_SKEW'),(True,'NEW_v195_EPISODE_GUARD')]:
            R,ST,SIDE,sk=sim_cf191g(*p,eg)
            x,pc=row(period,'CF191g',name,R,ST,SIDE,sk);rows.append(x)
            details[f'{period}_CF191g_{name}']={'periods':pc,'skips':sk.tolist(),
                'BUY':metrics(R[SIDE>0]),'SELL':metrics(R[SIDE<0])}

    # CF200 v2.04: management lock/audit does not alter valid frozen core.
    lab51.DATA=DATA
    for period,arr in [('historical',lab51.load_hist()),('forward_2026',lab51.load_2026())]:
        eidx,entry,atr,side,st,et,base=lab51.extract_fixed_entries(*arr)
        exp=lab51.EXPECT['historical' if period=='historical' else '2026_Mar_Aug']
        if len(base)!=exp['N'] or abs(float(base.sum())-exp['SumR'])>1e-6:
            raise RuntimeError(f'CF200 frozen parity fail {period}')
        for name in ['OLD_V200_FROZEN_CORE','NEW_v204_WINNER_PRESERVATION']:
            x,pc=row(period,'CF200',name,base,st,side,None);rows.append(x)
            details[f'{period}_CF200_{name}']={'periods':pc,'BUY':metrics(base[side>0]),'SELL':metrics(base[side<0])}

    df=pd.DataFrame(rows)
    df.to_csv(OUT/'comparison.csv',index=False)

    deltas=[]
    pairs=[('CF191s','OLD_STRICT','NEW_v196_REGIME_GUARD'),
           ('CF191g','OLD_v191g_POSITIVE_SKEW','NEW_v195_EPISODE_GUARD'),
           ('CF200','OLD_V200_FROZEN_CORE','NEW_v204_WINNER_PRESERVATION')]
    for period in ['historical','forward_2026']:
        for bot,a,b in pairs:
            A=df[(df.period==period)&(df.bot==bot)&(df.variant==a)].iloc[0]
            B=df[(df.period==period)&(df.bot==bot)&(df.variant==b)].iloc[0]
            deltas.append({'period':period,'bot':bot,
              'old_N':int(A.N),'new_N':int(B.N),'delta_N':int(B.N-A.N),
              'old_EV':A.EV,'new_EV':B.EV,'delta_EV':B.EV-A.EV,
              'old_PF':A.PF,'new_PF':B.PF,'delta_PF':B.PF-A.PF,
              'old_SumR':A.SumR,'new_SumR':B.SumR,'delta_SumR':B.SumR-A.SumR,
              'old_DD':A.MaxDD_R,'new_DD':B.MaxDD_R,'delta_DD':B.MaxDD_R-A.MaxDD_R,
              'old_R_DD':A.R_DD,'new_R_DD':B.R_DD})
    dd=pd.DataFrame(deltas);dd.to_csv(OUT/'old_vs_new.csv',index=False)

    result={'lab':'CROWDFADE_THREE_BOT_FIXES_HISTORICAL_REPLAY_LAB_053',
      'scope':'BTCUSDT only',
      'periods':{'historical':'2021-01-01..2025-12-31 M1','forward_shadow':'2026-03-01..2026-08-31 1-second'},
      'cost_proxy_bps':COST_BPS,
      'comparison':rows,'deltas':deltas,'details':details,
      'notes':[
        'CF191s v1.96 is a full stateful replay of old STRICT vs same-side + |confirm Z|>=0.75 + response>=0.50, with ExitZ0.75 retained.',
        'CF191g uses canonical completed M5 confirmation and positive-skew management (BE arm3.0/lock2.25 ATR, trail arm3.5/gap0.5 ATR); new variant adds max two entries per crowd episode, reset at |Z|<0.50 or sign flip.',
        'CF200 v2.04 does not alter the valid frozen Z2.05 core geometry. Historical result must be exactly identical; its purpose is config enforcement and exit-ownership audit.',
        '2026 Mar-Aug is reused forward-shadow/stress, not pristine OOS.',
        'Broker CFD spread/slippage parity is not represented; flat 0.5bps research cost proxy is used.',
        'BTCUSDT only: ETH/SOL transfer is not established by this replay.'
      ]}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))

    lines=['# LAB053 — THREE BOT FIXES HISTORICAL REPLAY','',
      'BTCUSDT causal stateful replay. Historical 2021–2025 + 2026 Mar–Aug forward shadow.','',
      '## Old vs new','',
      dd.to_markdown(index=False),'','## Full metrics','',df.to_markdown(index=False),'',
      '## Notes']+[f'- {x}' for x in result['notes']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    run()
