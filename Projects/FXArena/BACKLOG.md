# FXArena Backlog

## FXA-TBFLAG-REPLAY-001 — Flag-Replay v001.2

- **Priority:** P0
- **Status:** COMPLETED / STOP-ALARM C3 / NOT PROMOTED
- **Generator control:** PASS 3535/3535, 0 mismatches
- **Archived P4b replay:** PASS, 0 exit-time mismatches
- **Universe artifact:** 291659 episode flags; 57811 TB
- **Trailing completion:** 3515/3515 flags; 1244 TB; 622 trailing-only resolved, 196 TB
- **Economics:** P0 +1889.61R / DD 14.416R; P4b +2277.31R / DD 10.618R
- **Gates:** C1 PASS; C2 PASS; C3 FAIL; C4 PASS at 100%
- **C3 failure:** one negative month, 2023-02 = -2.040R, while P0 has zero negative months
- **Pin:** `trades_P4b_TRAILING_PINNED` NOT CREATED
- **Candidate:** preserved as `trades_P4b_TRAILING_CANDIDATE_NOT_PINNED.csv.gz`
- **Result:** `Releases/v1.2/FlagReplay_v001_2/`
- **Prohibited:** retroactively relax C3, tune flag thresholds, or promote candidate under the current session

## FXA-P4C-CAUSAL — Strictly causal P4 exit policy

- **Priority:** P0 / PRE-DEPLOY
- **Status:** NEW FROZEN SPEC REQUIRED
- **Reason:** archived P4b applies a flag observed after the first 30-minute window retrospectively from trade inception
- **Required policy:** start with P0 TP2; only extend to TP3 if the trade remains open when the flag becomes observable
- **Controls:** reproduce archived feature generator; compare causal P4c against GEO*-TRAILING under new preregistered gates
- **Prohibited:** use the current Flag-Replay result as proof that causal P4c passes

## FXA-C3-ADJUDICATION — Transfer-gate governance

- **Priority:** P1 / DECISION
- **Status:** OPTIONAL NEW SPEC
- **Question:** whether a single isolated negative month can be accepted when total, gross DD, all years and paired bootstrap are materially better
- **Boundary:** any revised calendar gate must be preregistered and applied symmetrically; it cannot amend Flag-Replay v001.2 post hoc

## FXA-CLOSURE-0011 — Monthly vs trailing canonicalization

- **Priority:** P0
- **Status:** COMPLETED / LIVE P0 PIN CREATED
- **Monthly:** N=3535, +1848.874807R, gross DD 14.415969R
- **Trailing:** N=3515, +1889.613320R, gross DD 14.415969R
- **Rule:** live comparisons only against TRAILING; research comparisons only against MONTHLY
- **Result:** `Releases/v1.2/Closure_v001_1/`

## FXA-ENTRY-001 — Entry Lab v001

- **Status:** COMPLETED / CLOSED F10
- **Winner:** E0 `market @ D3+60s`
- **Reopen only if:** genuinely new causal entry information appears

## FXA-SESSION-001 — Session & Time-of-Day Lab v001

- **Status:** COMPLETED / CLOSED F9
- **Verdict:** no session veto; hour-level filters prohibited

## FXA-SELECT-001 — Selection & Sizing Lab v001

- **Status:** COMPLETED
- **Part A:** FAIL SA2/SA5
- **Part B:** monthly/trailing difference resolved through separate canonical baselines

## FXA-SIZING-002 — Sizing risk-shape research

- **Status:** CLOSED FOR CURRENT 0.7/1.0/1.3 POLICY

## FXA-EXIT-003L — Exit Tournament v003-lite

- **Status:** MONTHLY CONFIRMED / TRAILING CANDIDATE NOT PROMOTED
- **Monthly:** P4b +2256.51R, gross DD 12.436807R
- **Trailing:** P4b +2277.31R, gross DD 10.618R, but FAIL C3
- **Prohibited:** promote P4b to EA before a valid transfer/deploy decision and exact execution closure

## FXA-DEPLOY-EXIT — Deferred deploy tests

- **Priority:** P0 / PRE-EA
- **Status:** BLOCKED
- **Tasks:** causal-policy decision, exact tick ExecutionReplay, spread stress, R1 Dukascopy and R2 forward A/B

## FXA-DATA-001 — Verify external release assets

- **Status:** ACTIVE
- **Immediate needs:** deploy-replay inputs and exact execution convention
