# XAU_DESTINATION_ROLE_MAGNET_VS_REJECTION_TOPOLOGY_LAB_018 — Spec v001

Date: 2026-08-24
Status: PREREGISTERED / PRE-HOLDOUT / RESEARCH ONLY

## 1. Question
LAB017 rejected the scalar hypothesis `more empty room => better residual TP1.5`. A known level ahead can behave as a destination/magnet rather than a barrier. LAB018 tests whether the **role/topology of the nearest known destination** at the frozen digestion-close decision clock contains transferable OOS information about residual continuation.

Primary question:

> Given the frozen LAB009 strong bias and frozen LAB012 digestion next-open entry, does causal information about the nearest destination's identity, prior interaction history, approach geometry, and TP placement improve `P(TP1.5 before SL1.0)` beyond LAB017 bias+room context?

No entry rule, SL, TP, event universe, or target is changed.

## 2. Frozen lineage
- Canonical M1 dataset SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- LAB008 break census SHA-256: `c9cba1459a60ef9c3bb308e751ebae95840f48a24f94754808862a180832ccdb`
- LAB012 frozen runner SHA-256: `09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`
- Frozen LAB017 parent-event rebuild SHA-256: `83be6298befc9c016c7aec297d3e48a3040258c6d070bae25af4e3c3c11481c2`
- Holdout cutoff: `2025-07-01 00:00`, never read.
- Discovery: break_time < 2024-01-01.
- Confirmation: 2024-01-01 <= break_time < 2025-07-01.
- Discovery-2023 is a transfer diagnostic only.

## 3. Universe / entry / target — unchanged
Universe is the frozen LAB012 strong-bias digestion universe with causal next-M1-open entry after digestion close.

Primary target:
- `RESIDUAL_TP15=1` iff the frozen 1.5R TP is reached before the frozen 1.0R SL from the frozen executable entry.
- Otherwise 0.

Secondary target: frozen 2R economics only.

No post-hoc entry, SL, TP, horizon, or direction changes are allowed.

## 4. Candidate destination set — frozen
At decision time (digestion close), construct the same known destination families as LAB017:
1. other anchored VWAP bands: MID/HIGH/LOW except the broken source level;
2. previous-session high/low;
3. current-session running high/low;
4. nearest causally confirmed M15 5-bar swing ahead in bias direction;
5. nearest causally confirmed H1 5-bar swing ahead in bias direction.

The **nearest positive signed-distance candidate** is the primary destination. If none exists, `OPEN_SPACE` is used and topology interaction fields are missing/neutral; it is not treated as a tested level.

## 5. Destination identity / placement features
Frozen features known at decision time:
- destination type;
- destination price;
- signed room in ATR and R;
- destination age in minutes when meaningful (swing/session-derived level);
- `tp15_minus_destination_atr = 0.75 - room_atr`;
- TP placement category:
  - `TP_BEFORE_DEST` if room > 0.90 ATR;
  - `TP_NEAR_DEST` if 0.60 <= room <= 0.90 ATR;
  - `TP_BEYOND_DEST` if room < 0.60 ATR;
  - `OPEN_SPACE` when no destination exists.
These are geometry descriptors, not trade filters.

## 6. Historical destination interaction topology — causal only
Treat the current destination price as a fixed horizontal reference and inspect only bars fully known before the decision clock.

Primary lookback: last 240 M1 bars before decision.
Touch tolerance: `0.05 * ATR0`.
A touch bar is one whose `[low, high]` intersects destination +/- tolerance.
Distinct touch episodes are separated by >=5 consecutive non-touch bars.

For each completed touch episode whose diagnostic future is fully before decision, inspect the next 10 completed M1 closes and classify the historical response relative to current bias direction:
- `ACCEPT`: at least 7/10 closes are beyond the destination in bias direction and terminal close >= +0.05 ATR beyond it;
- `REJECT`: terminal close <= -0.15 ATR back from destination in the anti-bias direction, or max anti-bias excursion <= -0.20 ATR before any +0.10 ATR acceptance;
- `MIXED`: neither.

Causal topology features:
- touch episode count in 60m / 240m;
- completed evaluable touch count;
- accept count / reject count / mixed count;
- accept rate / reject rate with denominator floor handled explicitly;
- last touch age;
- last evaluable response class;
- minimum inter-touch interval;
- repeated-approach count;
- destination freshness flag (0 completed touch episodes in 240m).

Frozen role label:
- `FRESH`: no completed touch episodes;
- `ACCEPTANCE_DOMINANT`: >=2 evaluable episodes and accept_rate >=0.60 and accept_count > reject_count;
- `REJECTION_DOMINANT`: >=2 evaluable episodes and reject_rate >=0.60 and reject_count > accept_count;
- `REPEATED_MAGNET`: >=2 touch episodes, reject_rate <0.40, and last touch age <=120m;
- `MIXED`: otherwise.

Role is descriptive only; no direct trade rule is authorized.

## 7. Current approach topology
Using only completed M1 bars up to digestion close:
- signed distance to destination now;
- change in destination distance over last 3, 5, 10, 15 minutes;
- directional approach speed (ATR/min) over 3/5/10/15m;
- approach efficiency = net progress toward destination / total absolute path over 5/10/15m;
- number of directional closes toward destination over last 5/10m;
- current pullback from closest approach in last 15m;
- whether distance has compressed monotonically over 3 bars / 5 bars;
- whether the destination was touched during the current post-break lifecycle before digestion close;
- if touched, whether price is currently accepted beyond, rejected back, or sitting on the same side.

No future bar after digestion close is used.

## 8. Context retained from LAB017
To isolate destination topology, retain frozen LAB017 context:
- `p_accept`;
- elapsed minutes;
- current signed location / peak / move spent / drawdown / path efficiency;
- scalar room features;
- M15/H1 range/EMA/structure fields;
- session range position;
- fixed-clock raw path only as a secondary integrated benchmark.

## 9. Models — fixed learner
Use the exact fixed HGB learner family used in LAB017:
- HistGradientBoostingClassifier
- learning_rate 0.05
- max_iter 200
- max_leaf_nodes 15
- min_samples_leaf 30
- l2_regularization 1.0
- max_bins 64
- early_stopping False
- random_state 20260824

No hyperparameter tuning.

Models:
A. `BIAS_X_ROOM_BASELINE` — frozen LAB017 bias + room representation.
B. `DESTINATION_TOPOLOGY_ONLY` — destination identity + placement + historical role + current approach topology.
C. `BIAS_X_DESTINATION_TOPOLOGY` — A + B. **Primary.**
D. `BIAS_X_DESTINATION_TOPOLOGY_PLUS_FIXED_RAW` — primary + frozen raw path. Secondary.

## 10. Primary routing threshold
Frozen semantic threshold:
- `TOPOLOGY_ARMED = p_residual >= 0.55` from primary model C.

No threshold tuning after outcomes.

## 11. Primary metrics
Confirmation OOS:
- AUC / Brier / logloss for all models;
- primary minus LAB017 baseline AUC;
- week-cluster bootstrap CI of AUC difference;
- coverage / TP1.5 precision / rejected TP rate;
- weekly bootstrap selection gap;
- frozen serial 1.5R economics: EV, PF, TP, trades/week, max DD, worst day, max consecutive losses, BUY/SELL EV, +$0.10 stress;
- 2R survival;
- Discovery-2023 transfer;
- routed-minus-baseline weekly lift.

Diagnostics only:
- role label table;
- destination type x role table;
- TP placement category table;
- historical touch-count buckets;
- last-response table;
- approach-speed quintiles;
- grouped permutation importance.

## 12. Frozen gates
G0 DATA_CAUSALITY: no feature at/after executable entry; holdout sealed; all hashes match.
G1 POWER: Confirmation >=1500 events, routed serial >=250, >=2 trades/week.
G2 TOPOLOGY_RESIDUAL_AUC: primary AUC >=0.60.
G3 TOPOLOGY_ADDS_OVER_ROOM: AUC increment >=+0.03 and weekly CI lower bound >0.
G4 SELECTION_QUALITY: selected TP>=0.48, gap>=+0.12 and weekly gap CI lower bound >0.
G5 CONFIRMATION_EV: routed serial EV>0 and PF>1.
G6 WEEK_CLUSTER_CI: weekly mean-R CI lower bound >0.
G7 DISCOVERY_TRANSFER: Discovery-2023 and Confirmation independent routed EV >0.
G8 2R_SURVIVAL: serial 2R EV >=0.
G9 DIRECTION_BREADTH: BUY EV>0 and SELL EV>0.
G10 PROP_DD_PROXY: max DD<=20R and worst day>-16R.
G11 COST_STRESS: +$0.10 stress EV >0.
G12 ROUTER_LIFT: routed EV > all-digestion baseline and weekly lift CI lower bound >0.

## 13. Verdict hierarchy
- `DESTINATION_TOPOLOGY_RESIDUAL_EXECUTABLE_EDGE` if all gates pass.
- `DESTINATION_TOPOLOGY_EDGE_NOT_PROP_READY` if predictive/economic core passes but prop-readiness secondary gates fail.
- `DESTINATION_ROLE_ADDS_INFORMATION_BUT_NO_ECONOMIC_SELECTION` if G2/G3 pass but economics fail.
- `DESTINATION_ROLE_SELECTS_EDGE_WITHOUT_FULL_ROBUSTNESS` if G2/G3/G4/G5 pass but robustness/transfer gates fail.
- otherwise `NO_DESTINATION_ROLE_RESIDUAL_EDGE`.

## 14. Governance
- Holdout >=2025-07-01 remains sealed.
- No rescue split by direction, destination type, role, TP placement, session, or threshold after outcomes.
- A positive H1-only / SELL-only / one-role result is diagnostic only unless separately preregistered and replicated.
- No EA/live allocation authorized by this LAB alone.
