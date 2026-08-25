# OLD_PROTECTED_PIVOT_ASYMMETRIC_EVENT_REPLICATION_LAB_019 — RESULT

Date: 2026-08-25
Preregistration: b8b578dd14bbc5a426b028242d8515fc84d9ad57

Formal verdict: `COMPRESSION_SELL_CONDITIONAL_REPLICATION_PASS__FAILED_RESPONSE_BUY_REJECTED`

## COMPRESSION_RELEASE SELL
- DEV: N=63, EV +0.094R, PF 1.16
- VAL: N=60, EV +0.109R, PF 1.24, MaxDD 3.42R
- VAL years: 2023 +0.037R, 2024 +0.113R, 2025 +0.177R (3/3 positive)
- 1.5x costs: EV +0.079R, PF 1.17
- exact M1 replay 2024-2025: N=41, 100% fill/outcome agreement, EV +0.142R, PF 1.31
- 2026 shadow (not verdict): N=17, EV +0.128R, PF 1.32
- passes all preregistered seed gates

## FAILED_RESPONSE_RELEASE BUY
- DEV: N=80, EV +0.147R, PF 1.30
- VAL: N=82, EV +0.106R, PF 1.21
- 2023 contributes 98.7% of total VAL net sumR
- exact M1 replay 2024-2025: EV +0.002R, PF 1.00
- 2026 shadow (not verdict): N=22, EV -0.324R, PF 0.56
- rejected on temporal concentration / decay

## Portfolio
Preregistered 3-engine portfolio remains positive but fails DD admission.

Strong secondary candidate after rejecting Failed BUY:
`BREAK_RETEST CORE + COMPRESSION_RELEASE SELL`
- DEV: N=94, EV +0.163R, PF 1.30
- VAL: N=87, 29 trades/year, EV +0.214R, PF 1.53, sum +18.63R, MaxDD 4.30R
- VAL years: 2023 +0.276R, 2024 +0.092R, 2025 +0.264R (3/3 positive)
- 1.5x costs: EV +0.184R, PF 1.43, MaxDD 4.96R
- 5-trade block-bootstrap EV 95% CI: [+0.032, +0.418]

No independent second BTC M15 venue dataset was available, so no venue-replication claim is made.
