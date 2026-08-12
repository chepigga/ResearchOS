# U02 — BTC v283 Setup-Type Ablation (Preregistered)

Status: **PREPARED, execution blocked until U01 exact MT5 parity closes.**

## Canonical default universe
Only setup families reachable under unmodified v283 defaults are primary:

1. `B_CHoCH_BOS_BUY`
2. `B_CHoCH_BOS_SELL`
3. `C_OBFVG_MICRO_BUY`
4. `C_OBFVG_MICRO_SELL`

`A_RaidReclaim` and `D_EQH_EQL` are coded but not primary because `InpUseLiquidityFilter=false` makes their required raid/level state inactive. `E/F` are disabled by default. They may be tested later only as explicit feature-on ablations, never mixed into the canonical baseline.

## Primary entry-edge outcomes
To avoid contaminating entry quality with v283 native exits:
- forward close returns at 1h / 2h / 4h / 8h
- MFE / MAE at the same horizons
- spread-stressed versions
- BUY/SELL separate
- calendar-year transfer
- unique episode frequency/week after U08-style dedup diagnostics (raw frequency also reported here)

## Secondary native-exit outcomes
Deferred to U10.

## Required tables
- setup × side × year: N, freq/week, WR, EV, PF
- setup × side: MFE/MAE quantiles
- PRE score deciles within each setup (descriptive, no threshold tuning)
- SmartMock confidence distribution
- fraction blocked by each downstream gate

## No optimization rule
No changes to:
- SmartMock bases/bonuses
- PRE thresholds
- CHoCH/BOS definitions
- FVG/OB definitions
- `InpMinConf=68`
- gate thresholds
until U02/U03 have been reported exactly as coded.
