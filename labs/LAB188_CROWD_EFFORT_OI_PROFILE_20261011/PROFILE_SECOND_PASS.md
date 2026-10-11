# LAB188 Phase B — Volume Profile shape × L/S × OI (2026-10-11)

Frozen 5089 LAB186 first-entry H1 setups. Same costs-free M5 OHLC TP-first labels and known RR. Historical BTC M5 from user. Causal 24h prior 288 M5 bars only, 40 price bins, each M5 candle quote/base volume approximated UNIFORMLY within candle low-high. The profile is approximate, NOT trades-at-price/order book volume. Profile excludes the M5 entry bar. Profile value area constructed greedily from POC to 70% of approximate volume. Shapes D, P, b, DOUBLE use frozen LAB158/159-like heuristic. Profiles computed at M5 entry; available only before entry.

## Main findings
|Era|IN_VALUE n TP-first|OUTSIDE_VALUE n TP-first|
|---|---|---|
|TRAIN 2021–23|1983 21.08%|748 14.97%|
|VALID 2024|682 20.23%|248 15.32%|
|CHECK 2025–Aug26 (previously researched)|1055 18.58%|373 10.72%|
|ALL|3720 20.22%|1369 13.88%|

IN_VALUE median quoted RR 3.203 versus OUTSIDE 4.162. Higher TP-first in-value may be confounded by distance to target and stop, trade regime, side/year; NOT independent incremental predictive edge yet. Shape D/P/b/DOUBLE TP-first ordering DOES NOT remain stable across years, therefore reject universal shape-only filter.

Exploratory conjunction: WITH_CROWD + OI_BUILD + OUTSIDE_VALUE n117 TP-first 8.55% (2021–23 n70 8.57%, 2024 n13 15.38%, CHECK n34 5.88%). Same L/S×OI condition INSIDE_VALUE n207 TP-first 12.56%; 2024 n31 6.45%, CHECK n48 4.17%. Low N and confounding; no deployable filter claim.

### Important caveats
- Previous fitted historical research already examined profile (LAB158/159); CHECK period NOT pristine. Testing multiple rules creates selection bias.
- MAE and MFE averages have pathological outliers; do not interpret or present until risk-stops and path calculation QA.
- Source tick-volume distribution is approximate. To claim true HVN/LVN and POC need native price-level executions or a clearly disclosed model.
- TP-first alone is insufficient to claim positive EV, as median targets are large; expenses and orderbook fills not modeled.
- Same first-choice per H1 setup, no additional trade mining; no EA promotion.
- Need time-block bootstrap controlling for year, side, H4 regime, RR decile, sweep depth and L/S×OI strata, then genuinely untouched forward data.

Files: LAB188_PROFILE_FACTOR_ROWS.csv, LAB188_PROFILE_SHAPE_SUMMARY.csv, LAB188_PROFILE_INTERACTIONS.csv, LAB188_PROFILE_LOCATION_SUMMARY.csv, lab188_profile_audit.py.
