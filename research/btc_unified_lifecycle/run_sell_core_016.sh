#!/usr/bin/env bash
set -euo pipefail
cd research/btc_unified_lifecycle
python -m py_compile sell_core_016_2026_edge_source_decomposition.py
python sell_core_016_2026_edge_source_decomposition.py
cat sell_core_016_out/REPORT.md
