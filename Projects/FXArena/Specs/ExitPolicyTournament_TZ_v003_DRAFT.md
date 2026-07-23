# FXArena Exit Policy Tournament v003 — P4b Confirmation

- **Status:** DRAFT / NOT FROZEN
- **Reason not frozen:** the reviewer stated that three additions were coming, but the supplied message contains only the DD-convention and registry amendments. Remaining additions must be incorporated before preregistration.
- **Precondition:** v002.1 DD Convention Audit Replay completed.

## Primary candidate

```text
P4b_PRIMARY:
    tb_flag == true  -> frozen P4
    tb_flag == false -> frozen P5
```

One candidate only. No post-registration threshold, session, direction, symbol or parameter tuning.

## Gate 0 — canonical replay and DD convention

P0 must match the pinned fixture on all of the following:

- N = 3535;
- signal/episode IDs and chronology;
- gross outcome per trade;
- net outcome per trade;
- exit timestamp and exit reason;
- Total net R = pinned value within tolerance;
- **MaxDD on cumulative gross R = 14.415969R within tolerance**.

Any failure is STOP; RH2 and RH6 are not calculated.

## Dual DD reporting

To prevent another convention mismatch, every result and bootstrap row must report:

- `MaxDD_gross_canonical` — used for legacy RH2/RH6 comparability;
- `MaxDD_net_execution` — mandatory prop/economic diagnostic including costs.

The report must state the ordering key, tie-break key, starting equity convention and whether unrealized overlapping equity is modeled.

## Frozen gates

- RH1: original economic threshold unless explicitly amended before freeze.
- RH2-gross: original canonical ceiling.
- RH2-net: proposed additional execution-risk gate; exact threshold pending final preregistration.
- RH3–RH6: original definitions, with DD explicitly defined as gross for legacy comparability.
- Cost shocks on modified P5 exits: +0.025R, +0.05R and +0.10R.
- Dedup tables: all episodes, first episode per level, unique entry cluster, unique decision-time/direction.
- Untouched replication period or broker feed.
- Kill rule: disable P5 fallback if realized incremental execution drag exceeds +0.10R per modified exit.

## Required falsification table

The final report must include P0–P7 from v002 as the closed comparison catalogue, with failure locations:

- P1 adaptive TP;
- P2 adaptive timeout;
- P3 combined adaptive;
- P4 TB extension;
- P5 BE@60;
- P6 partial at +1R;
- P7 BE + partial.

Complex/adaptive heads may not disappear from the register merely because the simple hand wins.
