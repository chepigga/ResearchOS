# Python

Nine scripts reproduce the supplied LAB_001 pipeline. Set `XAU_DATA` to the directory containing `xau_m1.parquet` and intermediate artifacts. If unset, scripts use their own directory. All files pass Python syntax compilation; no full rerun was performed during import.

Known issue: `step8_oos2.py` and `step9_control.py` retain several copied `OOS-1` print labels even though their selection ranges target OOS-2 and CONTROL respectively.
