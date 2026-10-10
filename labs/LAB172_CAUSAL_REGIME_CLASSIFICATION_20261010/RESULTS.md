# LAB172 — Causal classification of LAB171 candidate routes
Date: 2026-10-10
Status: first pass — descriptive ONLY, not a trade quality or profitability model.

Input user-uploaded BTC M5 ZIP, 589793 bars, and frozen LAB171_NONOVERLAP_ROUTES.csv (11620 routes) with prior wave_id post-hoc annotations. Classifier never uses wave_id or future price path.

## Frozen price-only classification
- Last CLOSED H1 EMA50 and its 4-hour slope and close alignment, last CLOSED H4 EMA50 and 4-bar slope.
- REVERSAL when last 12 completed M5 candles swept prior high/low computed from preceding 48 candles ending 13 bars before signal, and signal close reclaimed level. Priority when H4 trend not with trade, otherwise after continuation.
- RANGE when previous 6 completed H1 candles show path efficiency <= .35, range width 1–4 prior H1 ATR, price near range edge (BUY <= 35%, SELL >= 65%) and H1/H4 not both aligned to trade.
- CONTINUATION when last closed H1/H4 both aligned with proposed side.
- UNCLASSIFIED otherwise. Priority: strong reversal, range, continuation, residual reversal; labels are exclusive and descriptive.
- Initial candidate detection, TP/SL and R:R are unchanged from LAB171. 'Noise' not independently verified; do not call unclassified routes noise.

|Engine|Routes|BUY|SELL|RR>=2|RR>=3|Mean/month|Matching routes to LAB169 hindsight wave|
|---|---:|---:|---:|---:|---:|---:|---:|
|CONTINUATION|3798|1937|1861|2644|1056|55.85|370|
|REVERSAL|2253|1056|1197|1553|610|33.13|150|
|RANGE|844|370|474|678|312|12.41|54|
|UNCLASSIFIED|4725|2282|2443|3258|1477|69.49|545|

Overall 11620; BUY 5645/SELL5975; wave-matched routes 1119, distinct LAB169 waves 1035 / 2754. Those wave IDs are hindsight labels used only for audit; not an input to classification. Aggregating distinct wave counts across engines may double-count waves. Full 2680 canonical LAB161 parity still outstanding.

Important: this classifier DOES NOT prove that continuation/reversal/range have any predictive edge. These are feasible geometric paths as defined by LAB171, not confirmed fills/profits. No OI/Crowd/Profile filters, no profitability, no production EA change.

Reproduce from user file LAB171_NONOVERLAP_ROUTES.csv and BTC M5 ZIP using lab172_run.py (local artifact). Outputs LAB172_CLASSIFIED_ROUTES.csv, LAB172_SUMMARY.csv, LAB172_MONTHLY.csv.
