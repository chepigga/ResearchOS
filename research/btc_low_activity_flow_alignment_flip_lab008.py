import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

# Reuse the frozen LAB007 event engine. LAB008 changes only the hypothesis test.
import btc_pre_bos_aggressive_flow_lab007 as lab7

LAB = "BTC_LOW_ACTIVITY_FLOW_ALIGNMENT_FLIP_LAB_008"
DISCOVERY_START = pd.Timestamp("2023-01-01 00:00:00")
DISCOVERY_END = pd.Timestamp("2025-12-31 23:59:59")
EXPOSED_AUDIT_YEAR = 2026
INDEPENDENT_YEARS = [2019, 2020, 2021, 2022]

# Frozen family from LAB007. No new feature search in LAB008.
LOW_FEATURES = ["counter_volume_z_3", "total_volume_z_6", "trades_z_12"]
ALIGN_FEATURE = "flow_delta_12"       # >0 = taker flow aligned with future BOS direction
FLIP_FEATURE = "flow_flip_3v3"        # >0 = last 3 bars improve vs previous 3 bars


def build_all_events():
    # LAB007 began at 2023. LAB008 deliberately opens the untouched pre-2023 history.
    lab7.START = pd.Timestamp("2019-09-08 00:00:00")
    m = lab7.load_m15("btc15")
    h = lab7.make_h1(m)
    atr = lab7.atr_sma(m)
    hp = lab7.build_pivots(h, 3600)
    lp = lab7.build_pivots(m, 900)
    sig = lab7.generate_signals(m, atr, hp, lp)
    ev = []
    for s in sig:
        e = lab7.build_event(m, atr, s)
        if e is not None:
            ev.append(e)
    out = pd.DataFrame(ev)
    out["signal_time"] = pd.to_datetime(out.signal_time)
    return m, sig, out


def freeze_thresholds(discovery):
    # Q20 thresholds are exactly the low-activity family that replicated best in LAB007.
    return {
        "counter_volume_z_3_q20": float(discovery.counter_volume_z_3.quantile(0.20)),
        "total_volume_z_6_q20": float(discovery.total_volume_z_6.quantile(0.20)),
        "trades_z_12_q20": float(discovery.trades_z_12.quantile(0.20)),
        "align_threshold": 0.0,
        "flip_threshold": 0.0,
    }


def apply_frozen_state(d, thr):
    x = d.copy()
    x["low_counter_vol_3"] = (x.counter_volume_z_3 <= thr["counter_volume_z_3_q20"]).astype(int)
    x["low_total_vol_6"] = (x.total_volume_z_6 <= thr["total_volume_z_6_q20"]).astype(int)
    x["low_trades_12"] = (x.trades_z_12 <= thr["trades_z_12_q20"]).astype(int)
    x["low_activity_score"] = x[["low_counter_vol_3", "low_total_vol_6", "low_trades_12"]].sum(axis=1)
    x["flow_align_12"] = (x.flow_delta_12 > thr["align_threshold"]).astype(int)
    x["flow_flip_3v3_pos"] = (x.flow_flip_3v3 > thr["flip_threshold"]).astype(int)
    x["flow_align_or_flip"] = ((x.flow_align_12 == 1) | (x.flow_flip_3v3_pos == 1)).astype(int)
    x["flow_align_and_flip"] = ((x.flow_align_12 == 1) & (x.flow_flip_3v3_pos == 1)).astype(int)
    x["frozen_state_score"] = x.low_activity_score + x.flow_align_12 + x.flow_flip_3v3_pos
    return x


def rule_masks(d):
    # PRIMARY is frozen before reading independent 2019-2022 results.
    return {
        "PRIMARY_LOW2_X_ALIGN_OR_FLIP": (d.low_activity_score >= 2) & (d.flow_align_or_flip == 1),
        "LOW2_ONLY": d.low_activity_score >= 2,
        "LOW2_X_ALIGN": (d.low_activity_score >= 2) & (d.flow_align_12 == 1),
        "LOW2_X_FLIP": (d.low_activity_score >= 2) & (d.flow_flip_3v3_pos == 1),
        "LOW2_X_ALIGN_AND_FLIP": (d.low_activity_score >= 2) & (d.flow_align_and_flip == 1),
        "LOW3_X_ALIGN_OR_FLIP": (d.low_activity_score >= 3) & (d.flow_align_or_flip == 1),
    }


def metric(name, sample, mask):
    base = float(sample.is_large.mean()) if len(sample) else np.nan
    g = sample.loc[mask]
    if len(g) == 0:
        return dict(rule=name, n=0, large=0, large_rate=np.nan, baseline=base,
                    lift_pp=np.nan, fail_rate=np.nan, coverage=0.0)
    rate = float(g.is_large.mean())
    return dict(
        rule=name,
        n=int(len(g)),
        large=int(g.is_large.sum()),
        large_rate=rate,
        baseline=base,
        lift_pp=100.0 * (rate - base),
        fail_rate=float(g.is_fail.mean()),
        coverage=float(len(g) / len(sample)),
    )


def eval_rules(sample, sample_name):
    rows = []
    for name, mask in rule_masks(sample).items():
        r = metric(name, sample, mask)
        r["sample"] = sample_name
        rows.append(r)
    return rows


def score_table(sample, sample_name):
    rows = []
    base = float(sample.is_large.mean()) if len(sample) else np.nan
    for score in range(0, 6):
        g = sample[sample.frozen_state_score == score]
        if len(g) == 0:
            continue
        rows.append(dict(
            sample=sample_name,
            score=score,
            n=len(g),
            large=int(g.is_large.sum()),
            large_rate=float(g.is_large.mean()),
            baseline=base,
            lift_pp=100*(float(g.is_large.mean())-base),
            fail_rate=float(g.is_fail.mean()),
        ))
    return rows


def score_metrics(sample):
    if len(sample) < 20 or sample.is_large.nunique() < 2:
        return dict(auc=np.nan, ap=np.nan, brier=np.nan, top20_rate=np.nan, top20_n=0)
    s = sample.frozen_state_score.to_numpy(float)
    y = sample.is_large.to_numpy(int)
    # Convert discrete frozen score to an in-sample monotone probability map only for Brier.
    # AUC/AP depend on rank and do not fit test labels.
    p = 1.0 / (1.0 + np.exp(-(s - 2.5)))
    q = np.quantile(s, .80)
    top = s >= q
    return dict(
        auc=float(roc_auc_score(y, s)),
        ap=float(average_precision_score(y, s)),
        brier=float(brier_score_loss(y, p)),
        top20_rate=float(y[top].mean()),
        top20_n=int(top.sum()),
    )


def yearly_primary(d):
    rows = []
    for y, g in d.groupby("year"):
        m = rule_masks(g)["PRIMARY_LOW2_X_ALIGN_OR_FLIP"]
        r = metric("PRIMARY_LOW2_X_ALIGN_OR_FLIP", g, m)
        r["year"] = int(y)
        rows.append(r)
    return rows


def main():
    m, sig, e = build_all_events()
    print("============================================================")
    print(LAB)
    print("M15", len(m), m.time.min(), m.time.max())
    print("ALL SIGNALS", len(sig), "EVENTS", len(e), "LARGE", int(e.is_large.sum()), "RATE", round(100*e.is_large.mean(), 3))

    discovery = e[(e.signal_time >= DISCOVERY_START) & (e.signal_time <= DISCOVERY_END)].copy()
    exposed = e[e.year == EXPOSED_AUDIT_YEAR].copy()
    independent = e[e.year.isin(INDEPENDENT_YEARS)].copy()

    print("DISCOVERY 2023-2025", len(discovery), "LARGE", int(discovery.is_large.sum()), "RATE", round(100*discovery.is_large.mean(), 3))
    print("EXPOSED 2026", len(exposed), "LARGE", int(exposed.is_large.sum()), "RATE", round(100*exposed.is_large.mean(), 3))
    print("INDEPENDENT 2019-2022", len(independent), "LARGE", int(independent.is_large.sum()), "RATE", round(100*independent.is_large.mean(), 3))

    thr = freeze_thresholds(discovery)
    print("\nFROZEN THRESHOLDS FROM 2023-2025 ONLY")
    for k, v in thr.items():
        print(k, v)

    discovery = apply_frozen_state(discovery, thr)
    exposed = apply_frozen_state(exposed, thr)
    independent = apply_frozen_state(independent, thr)

    # Full events get states for export, but thresholds remain frozen on discovery.
    allx = apply_frozen_state(e, thr)

    rules_rows = []
    rules_rows += eval_rules(discovery, "DISCOVERY_2023_2025")
    rules_rows += eval_rules(exposed, "EXPOSED_2026")
    rules_rows += eval_rules(independent, "INDEPENDENT_2019_2022")
    rules = pd.DataFrame(rules_rows)

    print("\nFROZEN RULE RESULTS")
    print(rules.to_string(index=False))

    score_rows = []
    score_rows += score_table(discovery, "DISCOVERY_2023_2025")
    score_rows += score_table(exposed, "EXPOSED_2026")
    score_rows += score_table(independent, "INDEPENDENT_2019_2022")
    scores = pd.DataFrame(score_rows)

    print("\nFROZEN SCORE TABLE")
    print(scores.to_string(index=False))

    ym = pd.DataFrame(yearly_primary(allx))
    print("\nPRIMARY YEARLY")
    print(ym.to_string(index=False))

    sm = {
        "discovery": score_metrics(discovery),
        "exposed_2026": score_metrics(exposed),
        "independent_2019_2022": score_metrics(independent),
    }
    print("\nFROZEN SCORE RANK METRICS")
    for k, v in sm.items():
        print(k, v)

    # Additional fixed ablation: does alignment/flip improve LOW2 versus LOW2 alone?
    def find_rule(sample_name, rule_name):
        z = rules[(rules["sample"] == sample_name) & (rules["rule"] == rule_name)]
        return z.iloc[0].to_dict() if len(z) else {}

    ablation = []
    for sample_name in ["DISCOVERY_2023_2025", "EXPOSED_2026", "INDEPENDENT_2019_2022"]:
        low = find_rule(sample_name, "LOW2_ONLY")
        pri = find_rule(sample_name, "PRIMARY_LOW2_X_ALIGN_OR_FLIP")
        if low and pri:
            ablation.append(dict(
                sample=sample_name,
                low2_n=low["n"], low2_rate=low["large_rate"],
                primary_n=pri["n"], primary_rate=pri["large_rate"],
                alignment_flip_increment_pp=100*(pri["large_rate"]-low["large_rate"]),
            ))
    ablation = pd.DataFrame(ablation)
    print("\nALIGNMENT/FLIP INCREMENT OVER LOW2")
    print(ablation.to_string(index=False))

    out = Path("lab008")
    out.mkdir(exist_ok=True)
    allx.to_csv(out / f"{LAB}_EVENTS.csv", index=False)
    rules.to_csv(out / f"{LAB}_RULES.csv", index=False)
    scores.to_csv(out / f"{LAB}_SCORE.csv", index=False)
    ym.to_csv(out / f"{LAB}_YEARLY.csv", index=False)
    ablation.to_csv(out / f"{LAB}_ABLATION.csv", index=False)

    primary_ind = find_rule("INDEPENDENT_2019_2022", "PRIMARY_LOW2_X_ALIGN_OR_FLIP")
    low_ind = find_rule("INDEPENDENT_2019_2022", "LOW2_ONLY")

    verdict = {
        "lab": LAB,
        "hypothesis_frozen": "low aggressive-flow activity + future-direction alignment/positive flow flip before BOS",
        "target": "clean MFE >= 2.5R within 32 M15 bars before structural SL",
        "source": "Binance BTCUSDT 15m taker-ratio executed-flow proxy",
        "threshold_source": "2023-2025 only",
        "thresholds": thr,
        "primary_rule": "LOW_ACTIVITY_SCORE>=2 AND (FLOW_DELTA_12>0 OR FLOW_FLIP_3V3>0)",
        "independent_replication": primary_ind,
        "independent_low2_only": low_ind,
        "score_metrics": sm,
        "note": "2026 was already exposed in LAB007 and is diagnostic only. 2019-2022 is the independent replication set for LAB008.",
    }
    with open(out / "verdict.json", "w") as f:
        json.dump(verdict, f, indent=2)

    report = [
        f"# {LAB}", "",
        "Strict replication of the LAB007 finding. No new feature search.", "",
        "## Frozen hypothesis", "",
        "LOW ACTIVITY is the count of three LAB007 features below their 2023-2025 Q20 thresholds: counter_volume_z_3, total_volume_z_6, trades_z_12.",
        "FLOW ALIGNMENT = normalized 12-bar taker delta > 0 in the future BOS direction.",
        "FLOW FLIP = last-3-bar normalized taker delta improves versus the previous 3 bars.",
        "PRIMARY = LOW_ACTIVITY_SCORE >= 2 AND (ALIGNMENT OR FLIP).", "",
        "2026 is NOT claimed as fresh OOS because LAB007 already inspected it. Independent replication is 2019-2022, which LAB007 did not use.", "",
        "## Frozen thresholds", "", "```json", json.dumps(thr, indent=2), "```", "",
        "## Rule results", "", rules.to_markdown(index=False), "",
        "## Alignment/flip ablation over LOW2", "", ablation.to_markdown(index=False), "",
        "## Frozen state score", "", scores.to_markdown(index=False), "",
        "## Primary yearly transfer", "", ym.to_markdown(index=False), "",
        "## Rank metrics", "", "```json", json.dumps(sm, indent=2), "```",
    ]
    (out / f"{LAB}_REPORT.md").write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
