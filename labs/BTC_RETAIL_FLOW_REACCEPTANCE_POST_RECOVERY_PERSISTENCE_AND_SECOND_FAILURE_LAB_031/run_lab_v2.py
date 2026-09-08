#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab031_core', HERE/'run_lab.py')
L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
_orig=L.json.dumps

def _default(o):
    if isinstance(o,np.bool_): return bool(o)
    if isinstance(o,np.integer): return int(o)
    if isinstance(o,np.floating): return float(o)
    raise TypeError(f'Object of type {o.__class__.__name__} is not JSON serializable')

def _dumps(obj,*args,**kwargs):
    kwargs.setdefault('default',_default)
    return _orig(obj,*args,**kwargs)

L.json.dumps=_dumps
L.main()
