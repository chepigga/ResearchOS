#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
ARC = OUT / "canonical_recent_archive.csv"
REST = OUT / "official_https_www_binance_com.csv"

arc = pd.read_csv(ARC, parse_dates=["time"])
rest = pd.read_csv(REST, parse_dates=["time"])
rest["time_aligned"] = rest.time - pd.Timedelta(minutes=5)
j = arc.merge(rest, left_on="time", right_on="time_aligned", how="inner")
for c in ["archive_ratio", "ratio", "longAccount", "shortAccount"]:
    j[c] = pd.to_numeric(j[c], errors="coerce")
j = j.dropna(subset=["archive_ratio", "ratio", "longAccount", "shortAccount"])

r = j.archive_ratio.to_numpy(float)
p = r / (1.0 + r)
q = 1.0 / (1.0 + r)
la = j.longAccount.to_numpy(float)
sa = j.shortAccount.to_numpy(float)
rr = j.ratio.to_numpy(float)

# Diagnostic only: nearest-4-decimal consistency, never used to promote a source.
long_round_match = np.isclose(np.round(p, 4), la, atol=5e-12)
short_round_match = np.isclose(np.round(q, 4), sa, atol=5e-12)
ratio_round_archive_match = np.isclose(np.round(r, 4), rr, atol=5e-12)
account_ratio = la / sa
ratio_from_accounts_match = np.isclose(np.round(account_ratio, 4), rr, atol=5e-12)

# Rounding-cell intersection implied by both 4-decimal account shares.
eps = 0.00005
p_lo = np.maximum(la - eps, 1.0 - (sa + eps))
p_hi = np.minimum(la + eps, 1.0 - (sa - eps))
valid = p_lo <= p_hi
# allow boundary numerical fuzz only
inside_p = valid & (p >= p_lo - 1e-12) & (p <= p_hi + 1e-12)
r_lo = p_lo / (1.0 - p_lo)
r_hi = p_hi / (1.0 - p_hi)
inside_r = valid & (r >= r_lo - 1e-12) & (r <= r_hi + 1e-12)

metrics = {
    "diagnostic_status": "POSTHOC_LINEAGE_ONLY_NOT_A_PROMOTION_GATE",
    "overlap_n": int(len(j)),
    "archive_implied_longAccount_round4_match_share": float(long_round_match.mean()),
    "archive_implied_shortAccount_round4_match_share": float(short_round_match.mean()),
    "archive_implied_both_accounts_round4_match_share": float((long_round_match & short_round_match).mean()),
    "rest_reported_ratio_equals_round4_archive_ratio_share": float(ratio_round_archive_match.mean()),
    "rest_reported_ratio_equals_round4_of_rest_long_short_accounts_share": float(ratio_from_accounts_match.mean()),
    "component_rounding_cell_valid_share": float(valid.mean()),
    "archive_implied_long_fraction_inside_rest_component_rounding_cell_share": float(inside_p.mean()),
    "archive_ratio_inside_rest_component_implied_ratio_interval_share": float(inside_r.mean()),
    "component_implied_ratio_interval_width": {
        "p50": float(np.nanmedian(r_hi-r_lo)),
        "p95": float(np.nanquantile(r_hi-r_lo, .95)),
        "max": float(np.nanmax(r_hi-r_lo)),
    },
}
(OUT / "lineage_rounding_diagnostic.json").write_text(json.dumps(metrics, indent=2))
print(json.dumps(metrics, indent=2))
