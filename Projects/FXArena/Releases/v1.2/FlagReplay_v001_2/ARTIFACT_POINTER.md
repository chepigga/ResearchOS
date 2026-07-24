# Flag-Replay v001.2 complete artifact

- Local archive: `FXArena_FlagReplay_v001_2_output.zip`
- Archive bytes: `4188802`
- Archive SHA256: `43b46498efb5a71bfa4d9c139d7d1b9d2d1b1bcc7fc7d321ebe2b55eb4866b1e`
- Manifest: 22 payload files; local verification and ZIP integrity PASS.

The complete archive contains the full-universe `episode_tb_flags.csv.gz`, the 622 trailing-only flag rows, the 5000-row paired-bootstrap output, exact non-promoted P4b trailing candidate trades, the full replay runner, source hashes and all controls.

Large binary/CSV payloads are preserved in the complete local artifact rather than duplicated in the GitHub tree. The governed repository folder stores the report, verdict, transfer gates, control audits, generator source, sampler law, manifest and this pointer.

`trades_P4b_TRAILING_PINNED.csv.gz` was intentionally not created because frozen C3 failed. The candidate trade file is explicitly labelled `CANDIDATE_NOT_PINNED`.
