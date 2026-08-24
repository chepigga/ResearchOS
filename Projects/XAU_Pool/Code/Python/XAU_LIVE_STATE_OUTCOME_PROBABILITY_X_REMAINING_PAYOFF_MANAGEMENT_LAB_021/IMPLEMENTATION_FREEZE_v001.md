# LAB021 implementation freeze v001

Status: PRE-OUTCOME CODE FREEZE

- LAB: `XAU_LIVE_STATE_OUTCOME_PROBABILITY_X_REMAINING_PAYOFF_MANAGEMENT_LAB_021`
- Spec SHA-256: `7502efce209783b47599f2256ab2df7ac7448b0814f75e4334580be28316450b`
- Runner SHA-256: `7d4de4232dc0c6a6c1f6af8dccc543537f0c699acc55ff1b2d2f5ad433fe990b`
- XAU M1 cache SHA-256: `ec05163508f6f69c9688e5e50e1f418f6ca64aba42f17cf8d6504775df147ef8`
- Frozen setup cache SHA-256: `83526be03cb66ff596c3949138e7e8935cd12b9f8783a41adaf5f2c04d4ccfda`
- LAB012 parent runner SHA-256: `09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`
- LAB020 reference runner SHA-256: `8e0cd8dc09d5a9d48fab7b951091e836e8d4f276943cd1663192314f8f0ae78d`

Frozen implementation invariants:
- imports LAB020 causal snapshot builder unchanged;
- terminal classes are TP / SL (incl. SAME_BAR_LOSS) / TIME;
- Discovery-only TIME terminal mean payoff is computed separately for 1.5R and 2R;
- fixed HistGradientBoostingClassifier parameters from preregistration;
- each trade has total snapshot training weight 1;
- EXIT_NOW iff `EV_HOLD_terminal - current_R <= 0`;
- exit executes next contiguous M1 open and cannot override a prior frozen TP/SL;
- holdout is never read.
