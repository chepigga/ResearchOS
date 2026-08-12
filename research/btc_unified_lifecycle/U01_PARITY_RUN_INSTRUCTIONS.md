# U01 parity run — exact v283 source

Purpose: close source/execution parity **before** any profitability interpretation.

## Strategy Tester
- EA: `Grok_BTC_Core_Leveraged_v283_ORACLE.mq5` (source SHA256 `88b8acff6ae26f020fa3f0b08474364233ab9d38eacdf3f1c600f9d0d9ba40e7`)
- Symbol: `BTCUSD`
- TF: `M15`
- Model: `Every tick based on real ticks`
- Period: **2026-08-01 00:00 through 2026-08-10 23:59** (or through the latest real-tick data available on the same broker)
- Inputs: **Reset to v283 defaults**. Critical: `InpMockMode=true`, `InpMockUseSmartAI=true`.
- No optimization.

## What to return
After the test, upload the Strategy Tester **Journal/log file**. No screenshots are needed.

v283 already emits the markers needed by the automated parser:
`D1_PARITY`, `EMA_PARITY`, `PRE_SCORE_BTC`, `SMART_MOCK`, `ORACLE_GATE_BLOCK`, `BOS_ONLY_BLOCK`, `KNIFE_BTC`, `LATE_ENTRY_BLOCK`, `EXEC_EVENT`.

Do not edit the source just for logging; the existing v283 logging is sufficient.
