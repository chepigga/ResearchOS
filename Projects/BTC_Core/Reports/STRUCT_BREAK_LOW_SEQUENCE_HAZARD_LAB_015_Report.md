# STRUCT_BREAK_LOW_SEQUENCE_HAZARD_LAB_015

**Date:** 2026-08-25  
**Status:** COMPLETED  
**Preregistration:** `4f3e72d6e9593becbed1018819d64a7aacad4dd4`  
**Verdict:** `LOW_HAZARD_PREDICTABLE__SEQUENCE_ADDS_NO_INCREMENTAL_EDGE__EXIT_NOT_VALIDATED`

## Population
Frozen LAB008 LOW30. Primary population further requires alive, below +1R and below old entry at LOW30.
- DEV: 158
- VAL: 183

Within 120m after LOW, VAL competing outcomes:
- reclaim before stop: 126
- stop before reclaim: 41
- censored: 16

## Prediction
DEV-trained standardized L2 logistic, C=0.3, checkpoint every 5m, equal setup weights.

| Model | DEV AUC | VAL AUC |
|---|---:|---:|
| NET_R + elapsed | 0.828 | **0.800** |
| Snapshot | 0.828 | **0.796** |
| Full sequence | 0.833 | **0.797** |

The full sequence does not add material OOS information beyond current distance-to-entry/stop. Current NET_R is the dominant standardized coefficient (~-0.953).

## Frozen q75 high-hazard trigger
VAL:
- N=72 triggers
- resolved N=59
- SL-before-reclaim precision = 64.4% (fails prereg >=75%)
- median trigger = 10m after LOW
- median warning before stop among true failures = 22.5m
- average exit = -0.682R

## Why policy fails
Among 72 triggered VAL setups, final canonical outcomes:
- 56 SL: early exit saves about +20.92R total
- 11 BE: early exit loses about -6.62R
- 5 TP +2.3R: early exit loses about -14.59R

Net effect is approximately -0.29R across triggered trades.

## Full portfolio VAL
| Policy | EV/trade | MaxDD |
|---|---:|---:|
| HOLD | **-0.0315R** | **38.78R** |
| Immediate LOW exit | -0.0443R | 51.43R |
| Sequence hazard exit | **-0.0319R** | **39.27R** |

Paired sequence-policy improvement vs HOLD:
- mean -0.0004R/trade
- 95% CI [-0.0226,+0.0189]
- positive only 1/3 VAL years

## M1 replication
2024–2025 exact M1 replay:
- M5/M1 competing-event classification agreement: 100%
- frozen M5 triggers valid before event on M1: 100%

## Interpretation
Post-LOW failure hazard is genuinely predictable, but mostly because price is already near the stop. A more sophisticated M5 price sequence does not produce incremental OOS information or a profitable exit policy.

# Verdict
`LOW_HAZARD_PREDICTABLE__SEQUENCE_ADDS_NO_INCREMENTAL_EDGE__EXIT_NOT_VALIDATED`

The price-only sequence branch is exhausted enough that the next defensible information source should be outside simple M5 path transforms, e.g. event-local microstructure during the LOW/recovery battle.
