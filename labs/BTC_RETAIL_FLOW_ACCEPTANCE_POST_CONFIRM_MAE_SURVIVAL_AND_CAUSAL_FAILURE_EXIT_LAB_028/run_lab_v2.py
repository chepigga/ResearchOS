#!/usr/bin/env python3
# Reporting-only compatibility wrapper. No scientific rule or calculation changes.
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab028',HERE/'run_lab.py')
L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
_orig=L.policy_metrics

class AttrDict(dict):
    def __getattr__(self,name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

def wrapped_policy_metrics(*args,**kwargs):
    return AttrDict(_orig(*args,**kwargs))

L.policy_metrics=wrapped_policy_metrics
L.main()
