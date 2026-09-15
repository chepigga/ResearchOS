# GC_XAU_TRANSFER_MAPPING_FORENSIC_001

## Verdict

**HISTORICAL TRANSFER COUNT FINGERPRINT REPRODUCED BY EXACT XAU M1 TIMESTAMP ELIGIBILITY.**

This forensic test uses only historical artifacts already available in the GC release and the reconstructed Rithmic confirmation candidate ledger. AMP OOS is not used.

### Inputs

- GC confirmation candidates: `RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CONFIRMED_EVENTS.csv`
- Historical XAU price history: release asset `XAUUSD_M1_2026.csv`
- XAU history SHA256: `0e0c75fab3516fb31d3db1f3d3a7a25a848c0340b1cbd894cca66e628f3ecb18`
- XAU history rows: 36,489
- XAU history coverage in file clock: `2026-08-03 01:05` through `2026-09-08 20:03`
- Reconstructed confirmations through 2026-09-08 UTC: 53 = 25 LONG / 28 SHORT
- Historical LAB022 transfer fingerprint: 51 = 23 BUY / 28 SELL

## Clock mapping

Testing integer hour offsets from reconstructed UTC `entry_eligible_utc` to the XAU M1 file clock gives the strongest alignment at **UTC + 2 hours**.

At +2h:

- exact XAU M1 timestamp exists: **51 / 53**
- within 1 minute: **51 / 53**
- within 5 minutes: **52 / 53**
- within 60 minutes: **53 / 53**

The two events without an exact XAU M1 row are both LONG. Therefore the exact-match split is:

- LONG: **23 / 25**
- SHORT: **28 / 28**
- total: **51 / 53**

This exactly reproduces the historical transfer count and side split: **51 = 23 BUY / 28 SELL**.

## The two discrepant LONG events

### LONG A — daily/session break

- GC core bar UTC: `2026-08-05 22:25`
- GC confirmation UTC: `2026-08-05 22:30`
- scheduled entry eligible UTC: `2026-08-05 22:35`
- mapped XAU file clock (+2h): `2026-08-06 00:35`
- previous XAU M1 row: `2026-08-05 23:49`
- next XAU M1 row: `2026-08-06 01:05`
- delay to first available XAU row: **30 minutes**

There is no XAU M1 bar at the exact scheduled entry timestamp. The signal falls inside the XAU history/session gap.

### LONG B — weekend reopen boundary

- GC core bar UTC: `2026-08-30 22:50`
- GC confirmation UTC: `2026-08-30 22:55`
- scheduled entry eligible UTC: `2026-08-30 23:00`
- mapped XAU file clock (+2h): `2026-08-31 01:00`
- previous XAU M1 row: `2026-08-28 23:49`
- next XAU M1 row: `2026-08-31 01:05`
- delay to first available XAU row: **5 minutes**

There is no XAU M1 bar at the exact scheduled entry timestamp. The first available row appears five minutes later at the weekly reopen.

## Interpretation

The historical 51-trade transfer fingerprint is reproduced exactly if the transfer layer requires an XAU M1 row at the scheduled `entry_eligible` timestamp and does **not carry a signal forward across a missing XAU bar/session boundary**.

Under this interpretation:

```text
53 reconstructed GC confirmations
- 2 LONG confirmations without exact XAU entry timestamp
= 51 executable historical transfers
= 23 BUY / 28 SELL
```

This strongly localizes the former `+2 LONG` discrepancy to the **GC→XAU transfer timestamp eligibility layer**, not to the reconstructed GC confirmation rule.

## Certification limit

This is a count-and-side fingerprint match, not yet bitwise historical proof, because the original LAB022 51-row trade ledger / exact transfer implementation has not been recovered. Therefore the appropriate status is:

`TRANSFER_TIMESTAMP_RULE_HIGH_CONFIDENCE_FINGERPRINT_MATCH`

and not yet `BITWISE_TRANSFER_CERTIFIED`.

No AMP OOS performance information was used to obtain this result.

## Reproducibility

GitHub Actions workflow: `.github/workflows/gc_xau_transfer_mapping_forensic_001.yml`

Workflow run used historical XAU release data and the frozen reconstructed confirmation candidate ledger only.
