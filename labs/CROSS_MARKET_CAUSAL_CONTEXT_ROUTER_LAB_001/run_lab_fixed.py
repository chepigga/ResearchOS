#!/usr/bin/env python3
"""Technical hotfix only: preserve preregistered LAB logic and fix pandas DataFrame.stack name collision."""
from pathlib import Path

p = Path(__file__).with_name('run_lab.py')
src = p.read_text()
src = src.replace("d.stack.astype(float)", "d['stack'].astype(float)")
src = src.replace("(~d.stack).astype(float)", "(~d['stack']).astype(float)")
ns = {'__name__': '__main__', '__file__': str(p)}
exec(compile(src, str(p), 'exec'), ns, ns)
