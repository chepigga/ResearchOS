# Decision — Freeze P4b for confirmation only

- **Date:** 2026-07-23
- **Project:** FXArena
- **Decision status:** ACCEPTED FOR RESEARCH CONFIRMATION
- **Production status:** NO-GO
- **Supersedes:** no live or canonical strategy

## Decision

Register exactly one composite exit candidate for the next confirmation tournament:

```text
P4b_PRIMARY:
    tb_flag == true  -> frozen P4
    tb_flag == false -> frozen P5
```

## Evidence

- P0 canonical replay passed on 3535/3535 episodes.
- P4 had the strongest frozen-tournament economics: +2134.36R, EV +0.6038R, zero negative months.
- P4 formally failed RH2 and RH6.
- P4 drawdown was generated mainly by non-TB trades; P4 itself changes only TB trades.
- Routing the already-frozen P5 policy to non-TB trades produced +2256.51R, EV +0.6383R, MaxDD 13.284R and zero negative months.
- The P4b increment remained positive across years, halves, six-month blocks and deduplicated subsets.

## Constraints

1. P4 and P5 definitions remain frozen.
2. `tb_flag` remains the only router.
3. No new threshold, time, direction, session, symbol or score filter.
4. No EA or production implementation before a formal v003 confirmation pass.
5. ContPrimary live/demo-forward baseline remains untouched.
6. Execution kill threshold: +0.10R additional drag per modified P5 exit.

## Required next experiment

Run `Exit Policy Tournament v003 — P4b Confirmation` with exact P0 parity, original RH1-RH6 implementation and seeds, cluster/dedup sanity checks, explicit cost shocks and an untouched replication period or broker feed.
