# LAB026 pre-run parent parity patch

No outcomes had been run when this patch was made.

The first frozen runner correctly defined LAB026 research logic but called LAB025 helper functions with the LAB025 module itself instead of the exact LAB012 parent module required by LAB025's `dedupe/build_serial` helpers.

Research logic is unchanged. The patch only adds the exact LAB012 parent dependency and passes it to serial-universe helper calls.

- LAB012 parent SHA-256: `09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`
- patched local LAB026 runner SHA-256: `fc7f3862fdb4b7c0457c4598719f2620128ecb476ae89d9f04f86bc10c81d29e`
- outcomes observed before patch: none
- R:R threshold / expiry / health selector / fill logic / gates changed: no
