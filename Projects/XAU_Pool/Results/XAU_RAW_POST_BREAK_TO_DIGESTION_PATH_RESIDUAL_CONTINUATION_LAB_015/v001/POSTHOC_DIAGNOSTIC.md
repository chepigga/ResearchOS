# LAB015 post-hoc diagnostic — does not change frozen verdict

Frozen verdict remains `NO_RAW_PATH_RESIDUAL_EDGE`.

## Raw-only weak ranking

The preregistered primary integration model `RAW_PRICE_PLUS_COMPACT` reached OOS AUC 0.5196. The raw-price-only model was slightly better at 0.5277, suggesting that adding the old compact representation diluted rather than strengthened the weak raw-path signal.

Raw-only Confirmation quintiles show a weak but monotonic gradient:
- Q1 TP1.5 30.8%, independent EV -0.226R
- Q2 31.4%, -0.192R
- Q3 33.0%, -0.190R
- Q4 34.4%, -0.153R
- Q5 36.9%, -0.100R

This does not become executable: even raw-only `p>=0.55` serial EV is -0.155R, PF 0.768. At `p>=0.65`, N is only 34 and EV is still approximately flat (-0.005R) with SELL negative.

## Where the weak information sits

Primary RAW+COMPACT grouped permutation importance:
- signed distance channel `x`: AUC drop ~0.0254
- directional candle body: ~0.0222
- drawdown from running high-water mark: ~0.0104
- raw one-minute return: negative/no stable incremental value
- mask/path length: ~0

Most influential clock positions are early/intermediate (`T2`, `T7`, `T17`), not exclusively the digestion end.

Interpretation: the raw clock-time trajectory contains some weak information about residual continuation, but it is not sufficiently stable or strong for economic routing. A plausible remaining representation issue is **event-time alignment**: a human recognizes phases such as initial expansion → peak → first pullback → recovery attempt → digestion, whose durations vary. Fixed minute slots may place equivalent market phases at different indices and dilute transfer.