# GC_XAU_REPEATED_FAILED_ATTACK_EPISODE_CLUSTER_AUDIT_LAB006C_PREREG

Status: PREREGISTERED_DESCRIPTIVE_CLUSTER_AUDIT

Purpose: convert raw LAB005 repeated_failed_attack signal counts into unique market episodes without changing signal logic.

Source: frozen LAB005 event ledger, MARKET_NOW rows only, one row per causal signal.

Clustering schemes:
- TIME_ONLY connected components with adjacent signal gap <=2m, <=5m, <=10m.
- SAME_DIRECTION connected components with adjacent signal gap <=2m, <=5m, <=10m and same predicted XAU direction.

Report separately ALL and QUIET_START.

Per scheme report:
- signals
- clusters
- clusters per trading day
- median/mean/p90 signals per cluster
- median cluster span
- share singleton clusters
- share clusters containing at least one +2 ATR signal
- share clusters containing at least one +3 ATR signal
- median number of +2/+3 signals inside winning clusters

No trading or threshold optimization. Descriptive only.