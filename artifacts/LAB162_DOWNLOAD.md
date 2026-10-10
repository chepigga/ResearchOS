# LAB162 full archive

The ZIP is stored in three binary parts because of the connector request-size limit. Download all three files in this folder, then concatenate in order (do not unzip individual parts):

```bash
cat LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES.zip.part001 LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES.zip.part002 LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES.zip.part003 > LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES.zip
sha256sum LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES.zip
```

Expected SHA256: `0b61c0f0c07d5e4e81db4ab797b2050896baed8c4ffcd6918d8f931222ddab47`.

Full ZIP size: 22,327,049 bytes. It contains all wave trajectories, encounters, internal legs, reports, figures, code and validation; the reproducible intermediate pickle is excluded.
