# LAB017 post-hoc spatial interpretation — does not change frozen verdict

Frozen verdict remains `NO_BIAS_X_ROOM_RESIDUAL_EDGE`.

## 1. Simple open-space hypothesis fails and does not transfer

- Discovery-2023 CLEAR room: N=96, TP1.5 42.7%, EV +0.051R; BLOCKED TP1.5 35.4%, EV -0.143R.
- Confirmation CLEAR room: N=130, TP1.5 30.0%, EV -0.256R; BLOCKED TP1.5 33.5%, EV -0.167R.

Thus “more empty room is better” reverses OOS.

## 2. Destination identity matters more than scalar distance

Confirmation nearest destination:
- H1_SWING: N=436, TP1.5 36.7%, EV -0.091R.
- M15_SWING: N=1438, TP1.5 32.8%, EV -0.176R.
- CURRENT_SESSION: N=262, TP1.5 33.6%, EV -0.193R.
- VWAP: N=184, TP1.5 31.5%, EV -0.225R.
- PREV_SESSION: N=33, TP1.5 15.2%, EV -0.656R.

H1_SWING is relatively better in both 2023 and Confirmation; PREV_SESSION is poor in both. VWAP/current-session behavior deteriorates in Confirmation.

## 3. Distance is weak/non-monotonic

Nearest-room quintiles do not show monotonic TP1.5 improvement. Known levels can behave as magnets/destinations rather than pure barriers; scalar “room before obstacle” is too crude.

## 4. Weak transferable information

Grouped permutation AUC drops on Confirmation:
- BIAS_LOCATION +0.0141
- H1_ROOM +0.0077
- H1_STRUCTURE +0.0052
- SESSION_ROOM +0.0050
- M15_ROOM +0.0018
- M15_STRUCTURE +0.0005
- ROOM_AGGREGATE +0.0003
- VWAP_ROOM -0.0022

## 5. Direction asymmetry is not an authorized rescue

Frozen gate serial SELL EV is +0.075R while BUY is -0.236R, but OOS AUC is ~0.516 on both directions and SELL-only was not preregistered. No directional promotion is authorized.

## Research implication

If continued, the next spatial question should test destination **role/topology**: magnet vs rejection boundary, prior interaction/acceptance at the destination, approach state, and whether TP lies before, at, or through that destination. This requires a new preregistered LAB.
