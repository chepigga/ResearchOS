# BH_OOS_001v2 Input Index

**Status:** engine identified / uploaded data incomplete

| Required artifact | Purpose | Required coverage | Current state |
|---|---|---|---|
| `AK47_FT_EA_156.mq5` BH_SWEEP module | recovered MorrisCandle V2 signal engine source | v1.56 source / BH module v1.55 | received and audited |
| `AK47_FT_EA_156.ex5` | compiled companion provenance | supplied build | received; hash recorded |
| Isolated frozen oracle harness | exact control and OOS execution without EA live gates | derived from recovered BH module | not yet parity-approved |
| Original in-sample boundary or N=88 fixture | reproduce N=88 / EV=+0.276R | original IS window | missing |
| XAUUSD M15 same-feed CSV | warmup + OOS | 2024-12-01..2026-07-23 | partial upload received; insufficient coverage |
| Supplied `Grok_Core_XAU.mq5` | unrelated legacy reference only | n/a | received; not BH oracle |

## Correct source provenance

- filename: `AK47_FT_EA_156.mq5`
- declared version: `1.56`
- source size: 126,758 bytes
- source lines: 2,938
- SHA256: `838b3e180a139008c69792c0f122f3da66a590ef5e6ee98056056f0938311b65`
- classification: integrated FT EA containing independent mechanical `BH_SWEEP v1.55`
- BH lineage recorded in source: MorrisCandle V2 (2026-07-05) + EMA20
- control target recorded in source: `N=88 (B52/S36), EV=+0.276R`
- credential scan: no embedded API credential found

## Compiled companion

- filename: `AK47_FT_EA_156.ex5`
- size: 137,430 bytes
- SHA256: `40201896ac194c3194bf9a86a64e7dad4b7d8abc284a0ae4192e6491c4b390a2`
- use: provenance/runtime deployment only; not sufficient for source-level oracle audit

## Uploaded M15 file — incomplete

- filename: `XAUUSD_M15_202601020100_202607172345.csv`
- SHA256: `cf73c81110f2fc6451accee4b602750e4ab852ae2df656fde76dec4fa1915495`
- rows: `12,818`
- first bar: `2026-01-02 01:00:00`
- last bar: `2026-07-17 23:45:00`
- duplicate timestamps: `0`
- invalid OHLC rows: `0`
- verdict: unsuitable for formal Step 0 or Step 1 because it omits the 2024-12..2025 control history and the registered 2026-07-18..23 OOS tail
- audit: `Reports/BH_OOS_001v2_DataAudit_2026-07-24.md`

## Oracle parity warning

The BH signal-generation rules are present, but the integrated EA adds non-oracle execution gates. The standalone validation harness must exclude daily/portfolio/live broker gates and apply the preregistered `-0.05R/trade` correction externally.

See `Reports/BH_SWEEP_EngineAudit_v001.md`.

## Unrelated legacy file

- original filename: `Grok_Core_XAU.mq5`
- original encoding: UTF-16LE with CRLF
- SHA256 original upload: `c90e4db24b24d042bbc179cdc8250035a12b498e9c0cf69b9dab315b94382084`
- SHA256 UTF-8 conversion: `374fa7c44d44a787fbd6e382cf1eaa431b61b198824466cfb03f0c3b0124ed28`
- SHA256 redacted archival copy: `9256fab2f56e21a4ae2e5a570e4157c9c9073ae594e611d1ff2527615cb04f1f`
- classification: legacy AI-driven EA; not a MorrisCandle V2 / BH_SWEEP oracle
- security: plaintext xAI credential removed from archival copy