#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
SRC=HERE/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab055_base',SRC)
M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
_orig=M.load_and_reconstruct_router

def fixed_load_and_reconstruct_router():
    m=_orig()
    if 'atr14' not in m.columns and 'atr14_a' in m.columns:
        m['atr14']=m['atr14_a']
    return m

M.load_and_reconstruct_router=fixed_load_and_reconstruct_router
M.main()
