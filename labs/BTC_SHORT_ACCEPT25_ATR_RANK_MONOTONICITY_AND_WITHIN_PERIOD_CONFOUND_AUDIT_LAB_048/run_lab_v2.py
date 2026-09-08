#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab048_base',HERE/'run_lab.py')
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
_orig_dumps=base.json.dumps

def _safe_dumps(obj,*args,**kwargs):
    def _default(o):
        if isinstance(o,(np.bool_,)): return bool(o)
        if isinstance(o,(np.integer,)): return int(o)
        if isinstance(o,(np.floating,)): return float(o)
        raise TypeError(f'Object of type {o.__class__.__name__} is not JSON serializable')
    kwargs.setdefault('default',_default)
    return _orig_dumps(obj,*args,**kwargs)

base.json.dumps=_safe_dumps
base.main()
