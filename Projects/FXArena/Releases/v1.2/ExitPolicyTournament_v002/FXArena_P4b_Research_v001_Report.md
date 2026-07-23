# FXArena Exit Policy Tournament v002 — P4 TB Deep Dive / P4b Research v001

## Verdict

**Exploratory GO for a frozen P4b rerun; not yet a formal PASS.**

Frozen candidate:

```text
P4b = if tb_flag == true: use P4 exit policy
      else:               use P5 exit policy
```

No new model, date/session/direction filter, threshold search, or retraining is introduced.

## Main result

| Policy | N | Total R | EV | MaxDD | PF | Negative months | Worst month |
|---|---:|---:|---:|---:|---:|---:|---:|
| P0 | 3535 | 1848.87 | 0.5230 | 15.827 | 2.861 | 1 | -0.22R |
| P4 | 3535 | 2134.36 | 0.6038 | 15.827 | 3.121 | 0 | +2.08R |
| P5 | 3535 | 1984.15 | 0.5613 | 15.812 | 4.310 | 0 | +4.54R |
| **P4b** | **3535** | **2256.51** | **0.6383** | **13.284** | **4.297** | **0** | **+4.59R** |

P4b versus P4:

- Total: **+122.16R**
- EV: **+0.0346R/trade**
- MaxDD: **-2.544R / -16.1%**
- PF: **3.121 → 4.297**

P4b versus P0:

- Total: **+407.64R / +22.0%**
- EV: **+0.1153R/trade**
- MaxDD: **-2.544R / -16.1%**

## What the TB flag actually does

- `tb_flag=True`: **1274 / 3535 trades (36.0%)**.
- P4 differs from P0 only on TB trades.
- P4 changes **624** flagged trades, all of which were P0 TP exits.
- Extension outcomes:
  - **379** reached the extended target: incremental **+379R**.
  - **236** timed out/gave back part of the 2R winner: incremental **-66.52R**.
  - **9** reversed to stop: incremental **-27R**.
- Net P4 improvement: **+285.48R**.
- Incremental P4 result was positive in **37/42 months** and in every calendar year.

TB is therefore a strong continuation regime, but it does **not** control the main drawdown cluster.

## Why P4 fails RH2

P4's MaxDD is exactly the same as P0: **15.827R**.

The drawdown from 2023-10-11 to 2023-10-23 contains 17 trades:

- 14 non-TB trades contributed **-12.53R**.
- 3 TB trades contributed **-3.30R**.
- None of the trades in that drawdown received a beneficial P4 exit change.

Therefore further tuning of the P4 target extension alone cannot reliably solve RH2. The missing protection is in the `tb_flag=False` branch.

## Why P5 is the natural non-TB fallback

On non-TB trades:

| Policy | N | Total R | EV | PF |
|---|---:|---:|---:|---:|
| P0/P4 | 2261 | 535.12 | 0.2367 | 1.672 |
| P5 | 2261 | 657.28 | 0.2907 | 2.385 |

P5 adds **+122.16R** on non-TB trades. This increment is positive in:

- every calendar year;
- both chronological halves;
- all seven available 6-month blocks.

P5 changed 1077 non-TB exits. Relative to P0 it rescued 191 eventual SL outcomes by about +1R each, while sacrificing 26 eventual TP outcomes by about -2R each. The aggregate remains positive.

## Temporal robustness

| Year | P0 | P4 | P4b | P4b − P4 |
|---|---:|---:|---:|---:|
| 2023 | 314.20 | 357.06 | 370.73 | +13.67R |
| 2024 | 568.92 | 652.31 | 681.22 | +28.91R |
| 2025 | 599.83 | 689.50 | 744.65 | +55.15R |
| 2026 | 365.91 | 435.49 | 459.91 | +24.42R |

Chronological halves:

- H1 P4b: **+972.62R**, EV **+0.5501R**.
- H2 P4b: **+1283.89R**, EV **+0.7266R**.

All 42 calendar months remain positive; worst month is **+4.59R**.

## Duplicate / cluster robustness

| Subset | N | P4b Total | P4b EV | P4b MaxDD | P4b PF |
|---|---:|---:|---:|---:|---:|
| All episodes | 3535 | 2256.51 | 0.6383 | 13.284 | 4.297 |
| First episode per level | 2342 | 1522.81 | 0.6502 | 10.088 | 4.306 |
| Unique entry-time/direction/entry/risk | 2783 | 1755.56 | 0.6308 | 9.144 | 4.376 |
| Unique decision-time/direction | 2109 | 1391.29 | 0.6597 | 7.857 | 4.358 |

The result does not disappear after removing repeated economic observations.

## Estimated RH6 bootstrap

The original tournament source code and bootstrap indices were not included in the archive. I therefore ran a calibrated paired moving-block bootstrap:

- 5000 iterations;
- 20-trade blocks;
- `DD bad` defined as candidate DD worsening by more than +0.5R, matching the archived RH6 probability convention.

P4b versus P0:

- Mean total improvement: **+406.74R**.
- 95% interval: **[+312.65R, +503.61R]**.
- `p_total_good`: **100.0%**.
- Mean DD change: **-3.82R**.
- `p_dd_bad`: **3.66%**.
- Estimated RH6: **PASS**.

P4b versus P4:

- Mean total improvement: **+120.46R**.
- 95% interval: **[+51.50R, +190.26R]**.
- Probability total improvement > 0: **100.0%**.
- Probability DD improves: **94.2%**.

Because the exact original bootstrap sampler is unavailable, this is an estimate, not the formal tournament verdict.

## Execution-cost stress

Extra cost was applied only to the 1077 non-TB trades where P5 changed the exit.

| Extra cost per changed exit | P4b Total | MaxDD | PF | Delta vs P4 |
|---:|---:|---:|---:|---:|
| 0.00R | 2256.51 | 13.284 | 4.297 | +122.16R |
| 0.025R | 2229.59 | 13.309 | 4.134 | +95.23R |
| 0.050R | 2202.66 | 13.334 | 3.984 | +68.31R |
| 0.100R | 2148.81 | 13.384 | 3.713 | +14.46R |
| 0.125R | 2121.89 | 13.409 | 3.591 | -12.47R |

P4b remains better than P4 until roughly **+0.113R** additional cost per modified P5 exit. This is a useful forward-execution kill threshold.

## Overfitting assessment

Reasons the candidate is relatively clean:

- only one binary router already produced by the frozen P4 model;
- both child policies already existed in the frozen P0-P7 tournament;
- no optimized threshold, hour, month, direction, or symbol;
- improvement is positive across years, halves, six-month blocks, and deduplicated subsets;
- observed DD reduction is structural: P5 protects the non-TB branch that created the P4 drawdown.

Remaining post-selection risk:

- P4b was selected after inspecting P0-P7 outcomes;
- P5 near-flat exits may be more execution-sensitive than the aggregate table suggests;
- formal RH5/RH6 for the composite router must be recomputed by the original tournament engine;
- the current dataset is not an untouched replication set.

## Frozen next step

Create **Exit Policy Tournament v003 — P4b Confirmation** with exactly one primary candidate:

```text
P4b_PRIMARY:
    tb_flag == true  -> frozen P4
    tb_flag == false -> frozen P5
```

No parameter changes after registration.

Required gates:

1. Exact P0 parity.
2. Recompute RH1-RH6 with the original sampler and seeds.
3. First-episode-per-level and unique-entry-cluster sanity tables.
4. Cost shocks: +0.025R, +0.05R, +0.10R on changed P5 exits.
5. Untouched replication period/broker feed.
6. Forward kill rule: disable P5 fallback if realized incremental execution drag exceeds **0.10R per modified exit**.

## Research verdict

**P4b is the first candidate in this tournament that simultaneously improves P4 economics and materially reduces observed MaxDD.** It is suitable for a frozen confirmation tournament, but not yet for EA implementation or production deployment.
