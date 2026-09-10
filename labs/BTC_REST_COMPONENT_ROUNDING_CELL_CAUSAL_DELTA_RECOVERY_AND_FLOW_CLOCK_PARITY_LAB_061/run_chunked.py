#!/usr/bin/env python3
# Transport-only Binance retention + chunking wrapper. Research logic/gates in run_lab.py are unchanged.
from __future__ import annotations

import importlib.util
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("lab061_base", HERE / "run_lab.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

# Keep safely within Binance public 30-day retention.
M.REST_START = max(M.REST_START, M.utc_now() - pd.Timedelta(days=29))


def download_rest_raw_chunked(end_time: pd.Timestamp):
    # <=480 five-minute observations per request prevents Binance from collapsing
    # a long range to the latest 500 rows. Same endpoint/fields/alignment.
    chunk = pd.Timedelta(minutes=5 * 480)
    start = M.REST_START
    end = end_time
    rows = []
    used_host = None
    t0 = start
    while t0 <= end:
        t1 = min(t0 + chunk - pd.Timedelta(milliseconds=1), end)
        data, used_host = M.get_rest_json({
            "symbol": "BTCUSDT",
            "period": "5m",
            "startTime": int(t0.timestamp() * 1000),
            "endTime": int(t1.timestamp() * 1000),
            "limit": 500,
        })
        if data:
            for x in data:
                try:
                    rows.append({
                        "time": pd.to_datetime(int(x["timestamp"]), unit="ms", utc=True),
                        "ratio_reported": float(x["longShortRatio"]),
                        "longAccount": float(x["longAccount"]),
                        "shortAccount": float(x["shortAccount"]),
                    })
                except Exception:
                    pass
        t0 = t1 + pd.Timedelta(milliseconds=1)

    if not rows:
        raise RuntimeError("REST returned no rows")
    d = pd.DataFrame(rows).sort_values("time").drop_duplicates("time", keep="last")
    d["time"] = d["time"] + M.REST_SHIFT
    d = d[(d.time >= M.REST_START + M.REST_SHIFT) & (d.time <= end_time)]
    return d.set_index("time"), str(used_host)


M.download_rest_raw = download_rest_raw_chunked
M.main()
