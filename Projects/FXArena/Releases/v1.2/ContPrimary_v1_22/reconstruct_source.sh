#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PARTS="$ROOT/source_parts"
OUT="$ROOT/../../../Code/MQL5/FXArena_ContPrimary_v122.mq5"
EXPECTED="d9cabc9267d0bf8bff6d42d4f4faddcbf138cd87f2a7494e78d0f372550b781d"

mkdir -p "$(dirname "$OUT")"

cat "$PARTS"/FXArena_ContPrimary_v122.mq5.xz.b64.part* \
  | base64 -d \
  | xz -dc \
  > "$OUT"

printf '%s  %s\n' "$EXPECTED" "$OUT" | sha256sum -c -

test "$(wc -c < "$OUT" | tr -d ' ')" = "182189"
grep -q '#property version   "1.22"' "$OUT"
grep -q '777001' "$OUT"

echo "FXArena_ContPrimary_v122.mq5 reconstructed and verified."
