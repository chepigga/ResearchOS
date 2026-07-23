# FXArena Status

- **Project:** FXArena
- **Updated:** 2026-07-23
- **Lifecycle status:** ACTIVE_RESEARCH / CRITICAL_AUDIT
- **Canonical live baseline:** C2 / ContPrimary unchanged
- **Frozen research control:** GEO* `MICRO30 / TP 2.0R / timeout 120 min`
- **Canonical GEO* metrics:** N=3535; Total net=+1848.87R; EV net=+0.523020R; gross MaxDD=14.415969R
- **Current audit finding:** v002 used net MaxDD 15.827253R against a gross-DD gate of 14.916R
- **v002 original verdict:** INVALIDATED due DD convention mismatch
- **Corrected deterministic finding:** all P1–P7 pass RH2 under canonical gross DD
- **Provisional corrected v002 winner:** P5 BE@60; exact gross-DD RH6 replay still required
- **P5 observed:** +1984.15R; EV +0.5613R; gross MaxDD 13.571548R; PF 4.310; 0 negative months
- **P4 observed:** +2134.36R; EV +0.6038R; gross MaxDD 14.415969R; estimated gross RH6 fail
- **P4b observed:** +2256.51R; EV +0.6383R; gross MaxDD 12.436807R; net MaxDD 13.283629R; 0 negative months
- **P4b status:** POST-HOC / exploratory GO for confirmation only
- **Production / EA status:** NO-GO
- **Current blocker:** exact original bootstrap sampler/seeds and completion of all reviewer additions before v003 freeze
- **Next action:** v002.1 DD Convention Audit Replay, then finalize v003 draft
