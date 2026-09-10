#!/usr/bin/env python3
# Runtime-only transport retention clamp. Research logic/gates remain in run_lab.py unchanged.
import pandas as pd
import run_lab as lab

retention_safe_start = lab.utc_now() - pd.Timedelta(days=29)
lab.REST_START = max(lab.REST_START, retention_safe_start)
lab.main()
