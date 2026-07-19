#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path("/home/deepsaint/work/kv-tiered/tmh")
DEFAULT_STRESS = ROOT / "artifacts/tmh_adversarial_layout_stress/robust-stress-v1"


def main() -> int:
    stress_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_STRESS
    if not stress_dir.is_absolute():
        stress_dir = ROOT / stress_dir
    result = json.loads((stress_dir / "result.json").read_text())
    assert result["ok"] is True
    assert result["kv_layout"] == "tmh_fidelity_paged_kv"
    assert result["row_count"] >= 16_000
    assert result["old_kv_row_count"] >= 9_000
    assert result["plan_validation_pass_rate_pct"] == 100.0
    assert result["invariant_pass_rate_pct"] == 100.0
    assert result["cold_or_dropped_violation_count"] == 0
    assert result["negative_total_reduction_count"] == 0
    assert result["qwen_warm_reduction_pct"] == 16.667
    assert "qwen3_30b_a3b_gqa" in set(result["shapes"])
    assert "small_all_late_boundary" in set(result["shapes"])
    assert set(result["page_tokens"]) == {1, 2, 3, 4, 7, 8, 16, 31, 32, 64, 127, 128, 256, 512}
    assert set(result["budgets"]) == {100.0, 99.0, 90.0, 75.0, 50.0, 33.333, 25.0, 12.5, 6.25, 3.125, 1.0, 0.0}

    summary = list(csv.DictReader((stress_dir / "summary.csv").open()))
    assert len(summary) == len(result["shapes"]) * len(result["budgets"])
    assert all(float(row["pass_rate_pct"]) == 100.0 for row in summary)
    assert any(row["shape"] == "small_all_late_boundary" and float(row["min_warm_reduction_vs_uniform_int8_pct"]) == 0.0 for row in summary)
    assert all(float(row["min_total_reduction_vs_same_hot_uniform_int8_pct"]) >= 0.0 for row in summary)

    rows = list(csv.DictReader((stress_dir / "rows.csv").open()))
    assert len(rows) == result["row_count"]
    assert all(row["plan_validation_ok"] == "True" for row in rows)
    assert all(row["invariant_ok"] == "True" for row in rows)
    assert all(row["invariant_failures"] == "" for row in rows)
    qwen_old_rows = [row for row in rows if row["shape"] == "qwen3_30b_a3b_gqa" and int(row["old_tokens"]) > 0]
    assert qwen_old_rows
    assert {float(row["warm_reduction_vs_uniform_int8_pct"]) for row in qwen_old_rows} == {16.667}

    print("tmh-adversarial-stress-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
