# LAB185 Initial Replay Results (2026-10-11)
BTC M5 2021-01..2026-08-10; historical close-only H4/H1/M15 pivot and M5 next-open replay. Hybrid: H4 last BOS context, H1 confirmed-swing sweep/reclaim, M15 2L2R swing or 1 ATR(H1) causal ZigZag within 12h, M5 retest or 3-bar BOS within 4h; structural sweep-wick stop 0.1 H1 ATR, closest known H1 pivot/48h/168h high-low target, RR>=1.5.
- 12191 combinations of two M15 detectors and two M5 executions meeting geometry (NOT independent trades).
- 5089 unique H1 sweep events with at least one eligible execution (~74.8/mo), not fully deoverlapped zone routes.
- Post-hoc LAB169 2754 waves: 639 union aligned (23.2%); M15 swing 467; M15 ZigZag 454; overlap 282; swing-only 185; ZigZag-only 172.
- Only 491 of 2754 waves covered if retaining first chronological entry per H1 sweep irrespective of modality/exec, showing selection sensitivity.
- H4 aligned/transition separated. No broker costs, actual TP-before-SL, cross-opportunity order conflicts, canonical LAB161 2680 parity, or persistent level life cycle.
IMPORTANT: this is a constrained hybrid, NOT a fully fair standalone Market Structure vs ZigZag benchmark. Different coverage from LAB184 (46.7%) is not evidence of deterioration because detection rules changed.
Source reproducible local code/files: lab185_run.py, lab185_finalize.py, LAB185_CAUSAL_ROUTES.csv, LAB185_WAVE_MATCHED.csv, LAB185_FIRST_ENTRY_PER_SETUP.csv, LAB185_UNIQUE_H1_SETUPS.csv, LAB185_FIRST_SETUP_SUMMARY.csv, LAB185_REPORT.md. Research only, no EA changes.