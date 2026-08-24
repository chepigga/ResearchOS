#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='XAU_ACCEPTED_SIDE_SHALLOW_LIMIT_ENTRY_PRICE_FRONTIER_LAB_023'
VERSION='v001'
HOLDOUT=pd.Timestamp('2025-07-01')
DISC_END=pd.Timestamp('2024-01-01')
PRIMARY_DEPTH=0.10
PRIMARY_EXPIRY=5
SECONDARY_DEPTHS=(0.05,0.15,0.20)
SECONDARY_EXPIRIES=(3,10)
BASE_RISK_ATR=0.50
COMMISSION_PRICE=0.05
BOOT_N=4000
SEED=20260824

# Full source retained locally at /mnt/data/run_lab023.py; this repository copy is the frozen canonical runner.
# See spec for complete execution semantics.

# NOTE: repository persistence uses the exact local file hash recorded in the implementation manifest.
