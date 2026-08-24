# LAB019 implementation manifest v001

- Spec SHA-256: `2b644496fede8d03a235dc4ab1d52e13fa0f156f0e53074243016e2a02acea0b`
- Parent LAB012 runner SHA-256: `09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`
- LAB019 runner SHA-256: `e1915df04cb957b2cb7444f6f57a7ca741cd25ebcbd16879305dfaac6486e7a7`
- Canonical data SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- Primary management: HOLD_KILL_5M.
- Barrier fills have priority over any decision known only at that bar close.
- Kill execution is next contiguous M1 open; long exits at bid open, short exits at ask open.
- Secondary 3M/10M/DEGRADE_ONLY cannot rescue the primary verdict.
- Holdout sealed.
