# LAB021 operationalization addendum

Date: 2026-08-26
Status: FROZEN BEFORE LAB021 CALCULATION

The original v002 trade output persists exact fill indices but not exact cross/confirmation timestamps. Therefore, for BREAK_RETEST only, R4/R5 pre-event state is operationalized on the final 8 fully known M15 bars immediately preceding the actual fill. This remains causal and avoids reconstructing an ambiguous historical cross timestamp.

For COMPRESSION_RELEASE the pre-event window remains the 8 completed M15 bars preceding the release bar because release_idx is explicitly persisted/reconstructed.

R3 tested-and-held uses a fixed ATR14(fill) normalizer throughout its pre-fill path test; no future ATR is used.

R2 nested ancestor uses the nearest qualifying older same-side pivot in price space: highest qualifying older low for BUY, lowest qualifying older high for SELL. If multiple pivots share the same level, choose the most recent. The ancestor is selected without outcome information. R2 PnL is re-simulated using that ancestor as the structural stop and a fresh 2.3R target, with the standard +1R BE rule and 0.06R cost.
