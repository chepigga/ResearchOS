# LAB019 pre-run groupby patch v001

No LAB019 verdict/report metrics were read before this patch.

The replay failed in weekly paired-lift aggregation because `groupby('week').diff` resolved to the pandas method rather than the column named `diff`. The patch changes only this reporting expression to `groupby('week')['diff'].mean()`.

Trade simulation, management logic, timers, fills, costs, targets, universe and gates are unchanged.

Patched LAB019 runner SHA-256: `4f46ef20904d5ceb1b368aa83fc374a7e5d7a9b62772e8837b10be7442b0f021`.
