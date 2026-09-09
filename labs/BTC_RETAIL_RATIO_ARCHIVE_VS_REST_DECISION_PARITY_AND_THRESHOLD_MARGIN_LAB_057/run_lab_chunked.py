#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("lab057_base", HERE / "run_lab.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def download_rest_raw_chunked():
    # Transport-only fix: request <=480 five-minute observations per call so
    # Binance does not collapse a long requested range to its latest 500 rows.
    chunk = pd.Timedelta(minutes=5 * 480)
    start = M.REST_START
    end = M.ARCHIVE_END
    rows = []
    used_host = None
    t0 = start
    while t0 <= end:
        t1 = min(t0 + chunk - pd.Timedelta(milliseconds=1), end)
        data, used_host = M.get_rest_json(
            "/futures/data/globalLongShortAccountRatio",
            {
                "symbol": "BTCUSDT",
                "period": "5m",
                "startTime": int(t0.timestamp() * 1000),
                "endTime": int(t1.timestamp() * 1000),
                "limit": 500,
            },
        )
        if data:
            for x in data:
                rows.append({
                    "time": pd.to_datetime(int(x["timestamp"]), unit="ms", utc=True),
                    "ratio": float(x["longShortRatio"]),
                })
        t0 = t1 + pd.Timedelta(milliseconds=1)

    if not rows:
        raise RuntimeError("REST returned no ratio rows")
    d = pd.DataFrame(rows).sort_values("time").drop_duplicates("time", keep="last")
    d["time"] = d["time"] + M.REST_SHIFT
    d = d[(d.time >= M.REST_START + M.REST_SHIFT) & (d.time <= M.ARCHIVE_END)]
    return d.set_index("time")[["ratio"]], str(used_host)


M.download_rest_raw = download_rest_raw_chunked
M.main()
