#!/usr/bin/env python3
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab044_base',HERE/'run_lab.py')
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
_orig=base.load_inputs

def _fixed_load_inputs():
    m=_orig()
    if 'atr14' not in m.columns and 'atr14_a' in m.columns:
        m['atr14']=m['atr14_a']
    return m

base.load_inputs=_fixed_load_inputs
base.main()
