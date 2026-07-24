# Binary checkpoint backup

GitHub's connector cannot upload the 146 MB binary checkpoint directly. The complete checkpoint is preserved as three immutable Drive parts with SHA256 verification. The GitHub repository contains the recovery documentation, manifests, project state and all individual text releases.

## Parts

1. `FXArena_ContinuationCheckpoint_v1.2.zip.part00`
   - Drive: https://drive.google.com/file/d/13v-n-VWZjzggQRi01cpsxUGvs7OYXSzd/view
   - Size: 70,000,000 bytes
   - SHA256: `942896f944711201dd9b0311a3f3f9c194c8f0b2d02d935d3106e007f4cc6be9`

2. `FXArena_ContinuationCheckpoint_v1.2.zip.part01`
   - Drive: https://drive.google.com/file/d/1GV2oXvzdky3e2SqKtD1fsWzETE68RKGU/view
   - Size: 70,000,000 bytes
   - SHA256: `05c898981f8b47a64e062cb02889a4c7dded92f2816d6dbcd3e43240ac7c220b`

3. `FXArena_ContinuationCheckpoint_v1.2.zip.part02`
   - Drive: https://drive.google.com/file/d/1jYrzcJiSM_Xx5K4Ynqt70rLxaVtoD9rF/view
   - Size: 6,139,145 bytes
   - SHA256: `8bfefab8d9dde6301d5d6bfb856699d692d7814f67817b15f9755a5e12420d06`

## Reconstruction

```bash
sha256sum FXArena_ContinuationCheckpoint_v1.2.zip.part00
sha256sum FXArena_ContinuationCheckpoint_v1.2.zip.part01
sha256sum FXArena_ContinuationCheckpoint_v1.2.zip.part02

cat FXArena_ContinuationCheckpoint_v1.2.zip.part00 \
    FXArena_ContinuationCheckpoint_v1.2.zip.part01 \
    FXArena_ContinuationCheckpoint_v1.2.zip.part02 \
  > FXArena_ContinuationCheckpoint_v1.2.zip

sha256sum FXArena_ContinuationCheckpoint_v1.2.zip
```

Expected final ZIP SHA256:

`12e143be4e88a1f936311b2981e98567ccdbc9069c896bf8b6589c6a3137565a`

Expected final size: `146139145` bytes.

After extraction:

```bash
cd FXArena_ContinuationCheckpoint_v1.2
python Tools/reconstruct_chunked_files.py
python Tools/verify_manifest.py
```
