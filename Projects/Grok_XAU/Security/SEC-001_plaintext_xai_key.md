# SEC-001 — Plaintext xAI API key in legacy source

**Detected:** 2026-07-24  
**Severity:** HIGH  
**Status:** USER ACTION REQUIRED

## Finding

The supplied legacy `Grok_Core_XAU.mq5` contains an xAI API key as a literal `input string` default. Matching copies also exist in the user's historical File Library.

## Risk

Anyone with access to the source/file history can use the credential until it is revoked. Merely deleting the string from a new version does not invalidate the exposed key.

## Required action

1. Revoke or rotate the exposed key in the xAI account.
2. Never commit the original source containing the key.
3. Keep API-key inputs empty by default and provide secrets only at runtime.
4. Treat the old key as compromised even if no abuse is visible.

## Repository action

Only a redacted UTF-8 archival copy is stored. The original SHA256 is recorded for provenance; the secret-bearing bytes are not committed.
