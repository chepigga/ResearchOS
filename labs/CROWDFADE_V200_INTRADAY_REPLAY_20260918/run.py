import json, math, urllib.parse, urllib.request, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE="https://fapi.binance.com"
START=datetime(2026,9,15,0,0,tzinfo=timezone.utc)
END=datetime(2026,9,18,18,15,tzinfo=timezone.utc)
SYMS=["BTCUSDT","ETHUSDT","SOLUSDT"]

def ms(dt): return int(dt.timestamp()*1000)
def iso(t): return datetime.fromtimestamp(t/1000,timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def get(path, params, tries=5):
    url=BASE+path+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"ResearchOS-CrowdFadeReplay/1.0"})
    last=None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req,timeout=20) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last=e; time.sleep(1+i)
    raise RuntimeError(f"GET failed {url}: {last}")

def fetch_crowd(sym,start,end):
    out=[]; cur=ms(start); endms=ms(end)
    while cur<=endms:
        rows=get("/futures/data/globalLongShortAccountRatio",{"symbol":sym,"period":"5m","limit":500,"startTime":cur,"endTime":endms})
        if not rows: break
        for x in rows:
            t=int(x["timestamp"])
            if t<=endms: out.append((t,float(x["longShortRatio"])))
        nxt=int(rows[-1]["timestamp"])+1
        if nxt<=cur: break
        cur=nxt
        if len(rows)<500: break
    d={t:r for t,r in out}
    return sorted(d.items())

def fetch_klines(sym,interval,start,end,limit=1500):
    out=[]; cur=ms(start); endms=ms(end)
    while cur<=endms:
        rows=get("/fapi/v1/klines",{"symbol":sym,"interval":interval,"limit":limit,"startTime":cur,"endTime":endms})
        if not rows: break
        for x in rows:
            ot=int(x[0]); ct=int(x[6])
            if ot<=endms:
                out.append({"ot":ot,"ct":ct,"o":float(x[1]),"h":float(x[2]),"l":float(x[3]),"c":float(x[4])})
        nxt=int(rows[-1][0])+1
        if nxt<=cur: break
        cur=nxt
        if len(rows)<limit: break
    d={x["ot"]:x for x in out}
    return [d[k] for k in sorted(d)]

def z_series(crowd):
    out=[]; vals=[]
    for t,r in crowd:
        vals.append(r)
        if len(vals)>=72:
            w=vals[-72:]; m=sum(w)/72.0
            v=sum(x*x for x in w)/72.0-m*m
            sd=math.sqrt(max(v,0.0))
            out.append((t,(r-m)/sd if sd>1e-12 else 0.0,r,m,sd))
    return out

def atr_m15(bars):
    res={}
    for i,b in enumerate(bars):
        if i<14: continue
        trs=[]
        for j in range(i-13,i+1):
            pc=bars[j-1]["c"]; q=bars[j]
            trs.append(max(q["h"]-q["l"],abs(q["h"]-pc),abs(q["l"]-pc)))
        res[b["ct"]]=sum(trs)/14.0
    return res

def replay(symbols,data):
    state={s:{"conf":None,"pending":None,"pos":None,"last_entry":None,"daycount":{},"events":[]} for s in symbols}
    minute_maps={s:{b["ot"]:b for b in data[s]["m1"]} for s in symbols}
    m15maps={s:{b["ct"]:b for b in data[s]["m15"] if b["ct"]<=ms(END)} for s in symbols}
    zlists={s:data[s]["z"] for s in symbols}; zidx={s:0 for s in symbols}; lastz={s:None for s in symbols}
    atrs={s:data[s]["atr"] for s in symbols}
    t=(ms(START)//60000)*60000; t1=ms(END)
    while t<=t1:
        for s in symbols:
            zl=zlists[s]
            while zidx[s]<len(zl) and zl[zidx[s]][0]<=t+59999:
                lastz[s]=zl[zidx[s]]; zidx[s]+=1
        for s in symbols:
            st=state[s]; mb=minute_maps[s].get(t)
            if mb is None: continue
            p=st["pending"]
            if p:
                if t>=p["expires"]:
                    st["events"].append({"time":iso(t),"event":"LIMIT_EXPIRE","side":p["side"],"limit":p["entry"],"z":p["z"]})
                    st["pending"]=None
                elif t>=p["active_from"]:
                    hit=(mb["l"]<=p["entry"]) if p["side"]=="BUY" else (mb["h"]>=p["entry"])
                    if hit:
                        st["pos"]={**p,"fill_time":t}; st["pending"]=None; st["last_entry"]=(p["entry"],p["atr"])
                        dc=datetime.fromtimestamp(t/1000,timezone.utc).date().isoformat()
                        st["daycount"][dc]=st["daycount"].get(dc,0)+1
                        st["events"].append({"time":iso(t),"event":"FILL","side":p["side"],"entry":p["entry"],"sl":p["sl"],"tp":p["tp"],"z":p["z"],"signal_time":p["signal_time"],"confirm_time":p["confirm_time"]})
            p=st["pos"]
            if p:
                slhit=(mb["l"]<=p["sl"]) if p["side"]=="BUY" else (mb["h"]>=p["sl"])
                tphit=(mb["h"]>=p["tp"]) if p["side"]=="BUY" else (mb["l"]<=p["tp"])
                reason=None; px=None
                if slhit and tphit: reason="SL_AMBIG"; px=p["sl"]
                elif slhit: reason="SL"; px=p["sl"]
                elif tphit: reason="TP"; px=p["tp"]
                elif t-p["fill_time"]>=24*3600*1000: reason="TIME"; px=mb["c"]
                if reason:
                    st["events"].append({"time":iso(t),"event":"EXIT","side":p["side"],"reason":reason,"price":px})
                    st["pos"]=None
        close_ms=t+59999
        for s in symbols:
            b=m15maps[s].get(close_ms)
            if b is None or lastz[s] is None: continue
            st=state[s]; z=lastz[s][1]; atr=atrs[s].get(close_ms)
            if not atr or atr<=0: continue
            c=st["conf"]
            if c:
                side=c["side"]; a=c["atr"]; sig=c["sigpx"]
                confirmed=(b["c"]>=sig+0.25*a) if side=="BUY" else (b["c"]<=sig-0.25*a)
                if not confirmed:
                    c["left"]-=1
                    if c["left"]<=0:
                        st["events"].append({"time":iso(close_ms),"event":"CONFIRM_TIMEOUT","side":side,"z":z})
                        st["conf"]=None
                    continue
                st["conf"]=None
                if st["pending"] or st["pos"]: continue
                entry=b["c"]-0.60*a if side=="BUY" else b["c"]+0.60*a
                sl=entry-4.5*a if side=="BUY" else entry+4.5*a
                tp=entry+10.0*a if side=="BUY" else entry-10.0*a
                st["pending"]={"side":side,"entry":entry,"sl":sl,"tp":tp,"atr":a,"z":z,
                    "active_from":close_ms+1,"expires":close_ms+1+20*60*1000,
                    "signal_time":c["signal_time"],"confirm_time":iso(close_ms)}
                st["events"].append({"time":iso(close_ms),"event":"CONFIRM_PASS_LIMIT","side":side,"z":z,"close":b["c"],"atr":a,"limit":entry})
                continue
            if st["pending"] or st["pos"]: continue
            side="SELL" if z>=2.5 else ("BUY" if z<=-2.5 else None)
            if not side: continue
            if st["last_entry"]:
                ep,ea=st["last_entry"]
                if ea>0 and abs(b["c"]-ep)/ea<1.0:
                    st["events"].append({"time":iso(close_ms),"event":"PAUSE_BLOCK","side":side,"z":z})
                    continue
            dc=datetime.fromtimestamp(close_ms/1000,timezone.utc).date().isoformat()
            if st["daycount"].get(dc,0)>=3:
                st["events"].append({"time":iso(close_ms),"event":"DAYMAX_BLOCK","side":side,"z":z})
                continue
            st["conf"]={"side":side,"sigpx":b["c"],"atr":atr,"left":4,"signal_time":iso(close_ms)}
            st["events"].append({"time":iso(close_ms),"event":"ARM","side":side,"z":z,"close":b["c"],"atr":atr})
    return state

data={}
for s in SYMS:
    crowd=fetch_crowd(s,START-timedelta(hours=8),END)
    m15=fetch_klines(s,"15m",START-timedelta(hours=8),END)
    data[s]={"z":z_series(crowd),"m15":m15,"m1":fetch_klines(s,"1m",START,END),"atr":atr_m15(m15)}

results={}
for label,syms in [("BTC_ONLY",["BTCUSDT"]),("MULTI_BTC_ETH_SOL",SYMS)]:
    st=replay(syms,data); target={}
    for s in syms: target[s]=[e for e in st[s]["events"] if e["time"].startswith("2026-09-18")]
    results[label]={
        "arms":sum(e["event"]=="ARM" for s in syms for e in target[s]),
        "confirms":sum(e["event"]=="CONFIRM_PASS_LIMIT" for s in syms for e in target[s]),
        "fills":sum(e["event"]=="FILL" for s in syms for e in target[s]),
        "by_symbol":target}

out={"window":{"start":START.isoformat(),"end":END.isoformat()},"results":results,
"notes":["Binance USD-M globalLongShortAccountRatio 5m, rolling 72 population SD.","Canonical M15 ATR14 SMA true range.","Frozen gates: |Z|>=2.5, 0.25 ATR completed-close confirmation within 4 M15 bars, 0.60 ATR passive limit, TTL20m, ATR pause1.0, max3/day/symbol, SL4.5ATR, TP10ATR, hold24h.","Execution-touch replay uses Binance 1m OHLC; broker spread/margin/basis are not applied."]}
p=Path("labs/CROWDFADE_V200_INTRADAY_REPLAY_20260918"); p.mkdir(parents=True,exist_ok=True)
(p/"result.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
lines=["# CROWDFADE V200 INTRADAY REPLAY — 2026-09-18",""]
for label,r in results.items():
    lines += [f"## {label}",f"- ARMs: **{r['arms']}**",f"- Confirmed limits: **{r['confirms']}**",f"- Filled trades: **{r['fills']}**",""]
    for s,evs in r["by_symbol"].items():
        lines.append(f"### {s}")
        for e in evs: lines.append("- "+json.dumps(e,ensure_ascii=False))
        lines.append("")
(p/"RESULT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({k:{x:v[x] for x in ("arms","confirms","fills")} for k,v in results.items()},indent=2))
