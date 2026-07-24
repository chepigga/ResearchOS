# FXArena Artifact Dependency Map

## Primary inputs

- `FXArena_Release_v1.1_COMPLETE.zip`: ResearchOS source release and historical fixtures.
- `FXArena_LevelBattleEvents_v003_EVENT_STREAM_EURUSD_M5.zip`: event stream containing acceptance states.
- `FXArena_LevelBattleRounds_v003_EVENT_STREAM_EURUSD_M5.csv.gz`: round/episode state table.
- `FXArena_LevelBattleLevels_v003_EVENT_STREAM_EURUSD_M5.csv.gz`: level metadata.
- `EURUSD_M1_202301020005_202607172354.csv.gz`: M1 replay data from tradingticks v1.0.

## Laboratory chain

1. Exit Policy Tournament v002 + DD Audit
2. Exit Tournament v003-lite
3. Selection & Sizing v001
4. Closure v001.1 — canonical MONTHLY/TRAILING split
5. Entry Lab v001 — F10
6. Session Timing v001 — F9
7. P4b Research v001
8. Flag Replay v001.2
9. P4c Causal v001
10. PC5-r Resolution v001 — final P4c closure
11. REV Confirmation v001 — F11

## Immutable release packages in the binary checkpoint

- `FXArena_ExitPolicyTournament_v002_output(1).zip`
- `FXArena_ExitPolicy_v002_DD_Audit.zip`
- `FXArena_ExitTournament_v003_lite_output.zip`
- `FXArena_SelectionSizing_v001_output_FINAL.zip`
- `FXArena_Closure_v001_1_output.zip`
- `FXArena_EntryLab_v001_output.zip`
- `FXArena_SessionTiming_v001_output.zip`
- `FXArena_P4b_Research_v001.zip`
- `FXArena_FlagReplay_v001_2_output.zip`
- `FXArena_P4c_Causal_v001_output.zip`
- `FXArena_PC5r_Resolution_v001_output.zip`
- `FXArena_REV_Confirmation_v001_output.zip`

## Continuation boundary

Any future study should load the ResearchOS v1.1 release, the five primary input artifacts and the relevant immutable laboratory ZIP. The global state is summarized in `PROJECT_STATE_2026-07-24.md`.
