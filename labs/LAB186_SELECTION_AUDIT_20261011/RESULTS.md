# LAB186 — Selection audit, 2026-10-11

Frozen LAB185 12,191 candidate variants, 5,089 H1 setups. First chronologically available candidate versus noncausal retrospective maximum geometry RR and minimum realized MAE; causal gate on known H1 sweep >=0.3/0.5 ATR(H1) and reclaim displacement >=0.3 ATR(H1).

|Selector|H1 setups|Median quoted RR|Median intratrade MAE R|TP-first % on M5 OHLC|Distinct aligned LAB169 waves|
|--|--:|--:|--:|--:|--:|
|First chronological|5089|3.416|1.151|18.51|491|
|Retrospective max-quoted-RR among future candidates|5089|4.529|1.169|20.00|554|
|Retrospective minimum MAE|5089|2.970|1.070|24.52|605|
|First with known sweep>=0.3 H1 ATR|2421|2.824|1.112|21.27|295|
|First with sweep>=0.5|1275|2.504|1.097|22.67|171|
|First with reclaim displacement>=0.3|2520|3.260|1.133|18.73|295|
|First with both sweep>=0.3 and reclaim>=0.3|1093|2.649|1.087|22.23|156|

Oracle rows are **not causal**. MAE computed from M5 bars only until first TP/SL hit (SL-first if ambiguous) or 24h; not executable tick-accurate. Not a validated trade strategy. H1 sweep/reclaim gate computed from previously known level and completed reclaim close. This is diagnostic, no optimization and no EA changes. Historical 2754 LAB169 waves only; canonical 2680 LAB161 parity pending. Raw per-entry and report files generated locally: LAB186_ALL_ENTRIES_AUDITED.csv, LAB186_FIRST_ENTRY_BASELINE.csv, LAB186_SELECTION_SUMMARY.csv, LAB186_SELECTION_AUDIT_REPORT.md, lab186_selection_audit.py.