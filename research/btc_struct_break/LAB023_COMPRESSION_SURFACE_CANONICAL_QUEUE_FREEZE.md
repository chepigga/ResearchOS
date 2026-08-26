# LAB023 canonical queue operational freeze

Date: 2026-08-26
Status: FROZEN BEFORE CALCULATION

This addendum defines the pooled queue unambiguously for the fresh compression-surface discovery.

## Event generation and de-duplication
- Generate BUY and SELL release events independently from the frozen LAB018 compression definition.
- For each direction, after a release is emitted, suppress further releases in that same direction until either its 8-bar retest window expires or that event reaches a fill decision.
- BUY and SELL event clocks remain independent until trade admission.

## Retest/fill
- Retest begins on the bar after release and is valid for 8 M15 bars.
- The first bar whose range touches the retest level is the candidate fill bar.
- At that fill bar compute the latest confirmed opposite-side pivot-5, pivot age, unviolated status, ATR14 and riskATR.

## Broad canonical trade eligibility for the surface
The surface queue itself MUST NOT depend on an age/risk cell.
A candidate fill is broadly eligible if:
1. a confirmed opposite-side pivot-5 exists before fill;
2. pivot is unviolated after confirmation through the bar before fill;
3. stop is on the correct side of entry;
4. ATR14 is finite and positive;
5. riskATR is finite and >0.

No age threshold and no riskATR threshold are applied before queue admission.

## Pooled BUY+SELL family queue
- One active compression-family position globally across both BUY and SELL.
- If a broadly eligible candidate fill occurs while another compression-family position is active, mark it `BLOCKED_ACTIVE_POSITION`; it does not enter and does not alter the active trade.
- If BUY and SELL broadly eligible fills occur on the same M15 timestamp while flat, adverse deterministic tie-break is: process the event whose release occurred earlier; if same release timestamp, SELL before BUY. Persist the tie-break fields.
- Accepted trade uses stop at the frozen pivot, TP=2.3R, BE at +1R, cost=0.06R, adverse same-bar ordering.
- Active state ends at the simulated exit bar/time.

## Surface membership
- Every accepted trade is assigned exactly one pivot-age bin and one riskATR bin from the preregistered 5x5 grid.
- Primary reported surface uses accepted SELL trades only.
- BUY accepted trades are retained in provenance because they causally block later SELL entries.

This canonical broad queue is a NEW discovery definition. It is not claimed to reproduce LAB018/LAB020 trade counts.
