#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, types
from pathlib import Path
import numpy as np
import pandas as pd

LAB='CONTEXT_REVERSAL_COMPETITION_AND_STATE_BALANCE_AUDIT_LAB_011'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB010=ROOT/'labs'/'CONTEXT_INDICATOR_PUBLIC_SPEC_GAP_CLOSURE_AND_NEXT_CONTEXT_LAB_010'/'run_lab.py'
OLD=ROOT/'labs'/'CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001'/'run_lab.py'
REG=['EXPANSION','PULLBACK','REVERSAL','RANGE']


def load_module_hotfixed(path,name):
    t=path.read_text()
    # Technical compatibility only; identical to LAB010 successful workflow hotfixes.
    t=t.replace('d.stack.astype(float)','d["stack"].astype(float)').replace('(~d.stack)','(~d["stack"])')
    t=t.replace('stack=d.stack.fillna(False)','stack=d["stack"].fillna(False)')
    old="base=d.reset_index().rename(columns={'time':'h4_open'}).sort_values('h4_open')\n    z=pd.merge_asof(base,dc,left_on='h4_open',right_on='d1_available_time',direction='backward',allow_exact_matches=True)"
    new="base=d.reset_index().rename(columns={'time':'h4_open'}).sort_values('h4_open')\n    base['h4_open']=pd.to_datetime(base['h4_open'],utc=True).astype('datetime64[ns, UTC]')\n    dc['d1_available_time']=pd.to_datetime(dc['d1_available_time'],utc=True).astype('datetime64[ns, UTC]')\n    z=pd.merge_asof(base,dc,left_on='h4_open',right_on='d1_available_time',direction='backward',allow_exact_matches=True)"
    t=t.replace(old,new)
    m=types.ModuleType(name); m.__file__=str(path); exec(compile(t,str(path),'exec'),m.__dict__); return m


def winner(df):
    return df.idxmax(axis=1)


def machine_diagnostics(ctx,sm):
    cur=None; held=0; rows=[]; states=[]
    for idx,row in sm.iterrows():
        if row.isna().all():
            states.append(None); rows.append({'time':idx,'smooth_rev_winner':False,'blocker':'WARMUP'}); continue
        sc=row.fillna(-1e9).to_dict(); revwin=max(sc,key=sc.get)=='REVERSAL'
        if cur is None:
            cur=max(sc,key=sc.get); held=1; blocker='INIT'
        else:
            ar=ctx.loc[idx,'atr_ratio_public']; ar=1.0 if pd.isna(ar) else ar
            mh,gap=(4,12) if ar<.80 else ((2,5) if ar>1.35 else (3,8))
            oldcur=cur; oldheld=held
            adj=sc.copy(); adj[cur]=adj.get(cur,-1e9)+5
            ch=max(adj,key=adj.get)
            should=(ch!=cur and held>=mh and adj[ch]>adj[cur]+gap)
            blocker='NONE'
            if revwin and cur!='REVERSAL':
                if ch!='REVERSAL': blocker='INERTIA'
                elif oldheld<mh: blocker='MIN_HOLD'
                elif adj['REVERSAL']<=adj[oldcur]+gap: blocker='GAP'
                else: blocker='UNEXPECTED'
            if should: cur=ch; held=1
            else: held+=1
        states.append(cur)
        rows.append({'time':idx,'smooth_rev_winner':bool(revwin),'blocker':blocker})
    return pd.Series(states,index=sm.index),pd.DataFrame(rows).set_index('time')


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    old=load_module_hotfixed(OLD,'old011'); m=load_module_hotfixed(LAB010,'lab010_011')
    h1,meta=old.fetch_binance_futures_h1('2020-01','2026-07'); h4=old.to_h4(h1); d1=m.build_d1(h1,old); ctx,sm=m.build_router(h4,d1,old)
    raw=ctx[[f'score_{r.lower()}' for r in REG]].copy(); raw.columns=REG
    smooth=raw.rolling(3,min_periods=3).mean()
    warm=smooth.notna().all(axis=1)
    raww=winner(raw.loc[warm]); smw=winner(smooth.loc[warm])
    recon,diag=machine_diagnostics(ctx,smooth)
    mismatch=sum(not((pd.isna(x) and pd.isna(y)) or x==y) for x,y in zip(recon,ctx.regime))
    if mismatch: raise RuntimeError(f'frozen LAB010 parity failed: {mismatch}')

    widx=ctx.index[warm]
    active=(raw.loc[widx,'REVERSAL']>0)
    raw_rev=(raww=='REVERSAL'); smooth_rev=(smw=='REVERSAL'); full_rev=(ctx.loc[widx,'regime']=='REVERSAL')
    stage=pd.DataFrame([
      {'stage':'REVERSAL_SCORE_ACTIVE','n':int(active.sum()),'share':float(active.mean())},
      {'stage':'RAW_WINNER','n':int(raw_rev.sum()),'share':float(raw_rev.mean())},
      {'stage':'SMOOTH_WINNER','n':int(smooth_rev.sum()),'share':float(smooth_rev.mean())},
      {'stage':'FULL_MACHINE_CURRENT','n':int(full_rev.sum()),'share':float(full_rev.mean())},
    ])
    stage.to_csv(out/'stage_counts.csv',index=False)

    lost_score=int((active & ~smooth_rev).sum())
    lost_machine=int((smooth_rev & ~full_rev).sum())
    total_lost=lost_score+lost_machine
    score_share=lost_score/total_lost if total_lost else np.nan
    machine_share=lost_machine/total_lost if total_lost else np.nan

    block=diag.loc[widx].loc[smooth_rev.values & (~full_rev).values,'blocker'].value_counts().rename_axis('blocker').reset_index(name='n')
    block['share']=block.n/block.n.sum() if len(block) else np.nan; block.to_csv(out/'blocker_counts.csv',index=False)

    # Who beats Reversal when it is active but not the smoothed winner?
    lmask=active & ~smooth_rev
    win=pd.DataFrame({'winner':smw.loc[lmask.index[lmask]],'rev_score':smooth.loc[lmask.index[lmask],'REVERSAL']})
    win['winner_score']=[smooth.loc[i,w] for i,w in zip(win.index,win.winner)]
    win['margin']=win.winner_score-win.rev_score
    wsum=win.groupby('winner').agg(n=('winner','size'),median_margin=('margin','median'),mean_margin=('margin','mean')).reset_index()
    if len(wsum): wsum['share']=wsum.n/wsum.n.sum()
    wsum.to_csv(out/'winner_over_reversal.csv',index=False)

    tmp=ctx.loc[widx,['regime','atr_ratio_public','next_context']].copy(); tmp['year']=tmp.index.year
    tmp['raw_rev_win']=raw_rev.values; tmp['smooth_rev_win']=smooth_rev.values; tmp['full_rev']=full_rev.values
    year=tmp.groupby('year').agg(n=('regime','size'),raw_rev=('raw_rev_win','sum'),smooth_rev=('smooth_rev_win','sum'),full_rev=('full_rev','sum')).reset_index()
    for c in ['raw_rev','smooth_rev','full_rev']: year[c+'_share']=year[c]/year.n
    year.to_csv(out/'year_balance.csv',index=False)
    tmp['vol_state']=np.where(tmp.atr_ratio_public<.80,'LOW',np.where(tmp.atr_ratio_public>1.35,'HIGH','NORMAL'))
    vol=tmp.groupby('vol_state').agg(n=('regime','size'),raw_rev=('raw_rev_win','sum'),smooth_rev=('smooth_rev_win','sum'),full_rev=('full_rev','sum')).reset_index()
    for c in ['raw_rev','smooth_rev','full_rev']: vol[c+'_share']=vol[c]/vol.n
    vol.to_csv(out/'volatility_balance.csv',index=False)

    # Next-context conversion by proposed next state.
    r=ctx.regime; records=[]
    for state in REG:
        mask=ctx.next_context.eq(state) & r.notna()
        n=int(mask.sum()); realized=0
        for i in np.flatnonzero(mask.to_numpy()):
            if i+1<len(ctx) and r.iloc[i+1]==state and r.iloc[i]!=state: realized+=1
        records.append({'next_context':state,'bars':n,'next_bar_transition_to_state':realized,'conversion':realized/n if n else np.nan})
    pd.DataFrame(records).to_csv(out/'next_context_conversion.csv',index=False)

    # Transition adjacency: Reversal rank 1/2 within 1..3 bars before any actual transition.
    ranks=smooth.rank(axis=1,method='min',ascending=False)
    transitions=np.flatnonzero(r.ne(r.shift(1)).fillna(False).to_numpy())
    adj=[]
    for k in [1,2,3]:
        ix=[i-k for i in transitions if i-k>=0 and warm.iloc[i-k]]
        rr=ranks.iloc[ix]['REVERSAL'] if ix else pd.Series(dtype=float)
        adj.append({'bars_before_transition':k,'n':len(rr),'rank1_share':float((rr==1).mean()) if len(rr) else np.nan,'rank12_share':float((rr<=2).mean()) if len(rr) else np.nan})
    pd.DataFrame(adj).to_csv(out/'transition_adjacency.csv',index=False)

    full_share=float(full_rev.mean())
    if score_share>=.60: cause='SCORE_COMPETITION_DOMINANT'
    elif machine_share>=.60: cause='STATE_MACHINE_SUPPRESSION_DOMINANT'
    else: cause='MIXED_SUPPRESSION'
    rarity='REVERSAL_NOT_STRUCTURALLY_RARE' if full_share>=.005 else 'REVERSAL_STRUCTURALLY_RARE'
    verdict=f'{cause}__{rarity}'
    summary={'lab':LAB,'verdict':verdict,'dataset':meta,'h4_rows':len(ctx),'warm_rows':int(warm.sum()),'parity_mismatches':mismatch,
      'stage_counts':stage.to_dict('records'),'lost_score_competition_n':lost_score,'lost_state_machine_n':lost_machine,
      'score_competition_share_of_losses':score_share,'state_machine_share_of_losses':machine_share,
      'full_reversal_share':full_share,'blockers':block.to_dict('records'),'regime_counts':{str(k):int(v) for k,v in ctx.regime.value_counts().items()},
      'next_context_reversal_n':int(ctx.next_context.eq('REVERSAL').sum())}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','',f'- Frozen LAB010 parity mismatches: **{mismatch}**',f'- Warm H4 bars: **{int(warm.sum())}**',f'- Reversal active/raw/smoothed/full: **{int(active.sum())} / {int(raw_rev.sum())} / {int(smooth_rev.sum())} / {int(full_rev.sum())}**',f'- Score-competition losses: **{lost_score} ({score_share:.1%})**',f'- State-machine losses after smoothed Reversal winner: **{lost_machine} ({machine_share:.1%})**',f'- Full Reversal state share: **{full_share:.3%}**',f'- Next Context=Reversal bars: **{int(ctx.next_context.eq("REVERSAL").sum())}**','', '## Blockers']
    lines += [f"- {x['blocker']}: {int(x['n'])} ({x['share']:.1%})" for x in block.to_dict('records')]
    lines += ['', '## Winner over active Reversal']+[f"- {x['winner']}: {int(x['n'])}, median margin {x['median_margin']:.2f}" for x in wsum.to_dict('records')]
    (out/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__': main()
