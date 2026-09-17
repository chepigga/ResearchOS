"""
sim.py — ЕТАЛОННИЙ симулятор CrowdFade. Один раз написаний, далі не переписується.

ЗАКОН ВІКНА:
  сигнал на закритті бару t  ->  усі рішення про заповнення на барах t+1 і далі
  рівень лімітки рахується ТІЛЬКИ від c[t] (сигнальної ціни)
  chase: ОДИН раз, рівень від c[t], активується з бару t+1+ca
  перевірка стопа на барі заповнення робиться ПЕРШОЮ

Порядок усередині бару i (як у реальності найгірший випадок):
  1. стоп
  2. беззбиток / трейлінг за mfe цього бару
  3. вихід за сигналом
"""
import numpy as np
import pandas as pd


def load(flow_path, kline_paths, spread_abs):
    """Повертає (c,h,l,atr,Z,T,cost). cost — половина спреду у частках ATR."""
    F = pd.read_csv(flow_path)
    F["time"] = pd.to_datetime(F.create_time)
    F = (F[F.sum_open_interest > 0]
         .sort_values("time").drop_duplicates("time").reset_index(drop=True))

    if isinstance(kline_paths, (list, tuple)):
        D = pd.concat([pd.read_csv(x) for x in kline_paths], ignore_index=True)
    else:
        D = pd.read_csv(kline_paths)
    D["time"] = pd.to_datetime(D["time"], format="%Y.%m.%d %H:%M")
    D = D.sort_values("time").drop_duplicates("time")
    D = D[(D.time >= F.time.min()) & (D.time <= F.time.max()) & (D.volume > 0)]
    D = D.reset_index(drop=True)

    c = D.close.values.astype(float)
    h = D.high.values.astype(float)
    l = D.low.values.astype(float)
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).rolling(14).mean().values

    M = pd.merge_asof(D[["time"]], F[["time", "count_long_short_ratio"]],
                      on="time", direction="backward", allow_exact_matches=False)
    ls = pd.Series(M.count_long_short_ratio.values)
    mm = ls.rolling(24).mean()
    sd = ls.rolling(24).std()
    Z = ((ls - mm) / sd.replace(0, np.nan)).values

    cost = spread_abs / 2.0 / np.nanmedian(atr)
    return c, h, l, atr, Z, D.time.values, cost


def simulate(c, h, l, atr, Z, T, cost,
             off=1.25, stop=1.00,
             chase=0.40, chase_after=4,          # chase=None -> вимкнено
             be_at=1.00, be_lock=0.30,           # be_at=None -> вимкнено
             arm=2.50, trail=0.50,               # arm=None  -> трейлінг вимкнено
             exit_z=1.00, hold=12, valid=24, pause=12,
             shuffle=False, seed=0, surr=None, detail=False):
    if surr is not None:
        c, h, l, atr = surr
    N = len(c)

    Zs = Z
    if shuffle:
        rs = np.random.default_rng(seed)
        Zs = np.array(Z, dtype=float)
        v = Zs[np.isfinite(Zs)]
        Zs[np.isfinite(Zs)] = rs.permutation(v)

    rows = []
    last = -10 ** 9
    n_signal = n_fill = n_chase_used = 0

    for t in range(400, N - hold - 2):
        if t - last < pause:
            continue
        z = Zs[t]
        a = atr[t - 1]
        if not np.isfinite(z) or not np.isfinite(a) or a <= 0:
            continue
        side = -1 if z >= 1.0 else (1 if z <= -1.0 else 0)
        if side == 0:
            continue
        n_signal += 1

        base = c[t]                                   # СИГНАЛЬНА ціна, не рухається
        lvl0 = base + off * a if side < 0 else base - off * a
        lvl1 = None
        if chase is not None:
            lvl1 = base + chase * a if side < 0 else base - chase * a
            # новий рівень мусить бути БЛИЖЧЕ до ринку, інакше сенсу немає
            if (lvl1 >= lvl0) if side < 0 else (lvl1 <= lvl0):
                lvl1 = None

        fill = None
        entry = None
        used_chase = False
        for i in range(t + 1, min(t + 1 + valid, N)):
            # який рівень ДІЄ на барі i
            if lvl1 is not None and (i - t) > chase_after:
                cur, isch = lvl1, True
            else:
                cur, isch = lvl0, False
            touched = (h[i] >= cur) if side < 0 else (l[i] <= cur)
            if touched:
                fill, entry, used_chase = i, cur, isch
                break
        if fill is None:
            continue

        n_fill += 1
        n_chase_used += used_chase
        last = t
        e = entry
        sl = e - side * stop * a
        res = None
        kind = "time"
        mfe = 0.0
        armed = False

        # бар заповнення: перевіряємо ТІЛЬКИ стоп (консервативно)
        if (h[fill] >= sl) if side < 0 else (l[fill] <= sl):
            res, kind = (sl - e) / a * side, "stop"
        else:
            for i in range(fill + 1, min(fill + 1 + hold, N)):
                fav = ((e - l[i]) if side < 0 else (h[i] - e)) / a
                if fav > mfe:
                    mfe = fav
                # 1) стоп
                if (h[i] >= sl) if side < 0 else (l[i] <= sl):
                    res = (sl - e) / a * side
                    kind = "trail" if armed else "stop"
                    break
                # 2) беззбиток
                if be_at is not None and mfe >= be_at:
                    ns = e + side * be_lock * a
                    if (ns < sl) if side < 0 else (ns > sl):
                        sl = ns
                # 3) трейлінг
                if arm is not None and mfe >= arm:
                    armed = True
                    ns = e + side * (mfe - trail) * a
                    if (ns < sl) if side < 0 else (ns > sl):
                        sl = ns
                # 4) вихід за сигналом
                zc = Zs[i]
                if exit_z and np.isfinite(zc):
                    if (zc <= -exit_z) if side < 0 else (zc >= exit_z):
                        res, kind = side * (c[i] - e) / a, "signal"
                        break
            if res is None:
                j = min(fill + hold, N - 1)
                res = side * (c[j] - e) / a

        rows.append(dict(t=T[t], R=(res - cost) / stop, kind=kind,
                         chase=used_chase, lag=fill - t, mfe=mfe))

    d = pd.DataFrame(rows)
    meta = dict(n_signal=n_signal, n_fill=n_fill,
                fill_rate=n_fill / max(n_signal, 1),
                chase_rate=n_chase_used / max(n_fill, 1))
    return (d, meta) if detail else d.R.values


def stats(R, years):
    R = np.asarray(R)
    se = R.std(ddof=1) / np.sqrt(len(R))
    eq = np.cumsum(R)
    dd = (np.maximum.accumulate(eq) - eq).max()
    w = R[R > 0]; ls_ = R[R < 0]
    run = best = 0
    for v in R:
        run = run + 1 if v < 0 else 0
        best = max(best, run)
    return dict(N=len(R), WR=(R > 0).mean(), EV=R.mean(), t=R.mean() / se,
                payoff=(w.mean() / abs(ls_.mean())) if len(ls_) else np.nan,
                Ryr=R.sum() / years, DD=dd, RDD=R.sum() / years / max(dd, 1e-9),
                streak=best)
