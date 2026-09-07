#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab025_base',HERE/'run_lab.py')
L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)

class AttrDict(dict):
    def __getattr__(self,name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

_orig=L.summarize_policy

def summarize_policy_attr(*args,**kwargs):
    return AttrDict(_orig(*args,**kwargs))

L.summarize_policy=summarize_policy_attr

if __name__=='__main__':
    L.main()
