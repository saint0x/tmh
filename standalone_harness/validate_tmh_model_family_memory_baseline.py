#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path("/home/deepsaint/work/kv-tiered/tmh")
DEFAULT_BASELINE = ROOT / "artifacts/tmh_model_family_memory_baseline/model-family-v1"


def main() -> int:
    baseline = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BASELINE
    if not baseline.is_absolute():
        baseline = ROOT / baseline
    result = json.loads((baseline / "result.json").read_text())
    assert result["ok"] is True
    assert result["kv_layout"] == "tmh_fidelity_paged_kv"
    assert result["model_config_count"] >= 10
    assert result["pressure_case_count"] >= 30
    assert result["row_count"] >= 15_000
    assert result["old_kv_row_count"] >= 10_000
    assert result["plan_validation_pass_rate_pct"] == 100.0
    assert result["invariant_pass_rate_pct"] == 100.0
    assert result["promoted_old_warm_reduction_floor_pct"] >= 16.0
    assert result["promoted_public_number_pct"] >= 16.0

    model_summary = list(csv.DictReader((baseline / "model_summary.csv").open()))
    assert len(model_summary) == result["model_config_count"]
    assert all(float(row["pass_rate_pct"]) == 100.0 for row in model_summary)
    assert min(float(row["min_warm_reduction_vs_uniform_int8_pct"]) for row in model_summary if int(row["old_kv_row_count"]) > 0) == result["promoted_old_warm_reduction_floor_pct"]
    assert any(row["model_id"] == "Qwen/Qwen3-30B-A3B-GPTQ-Int4" for row in model_summary)
    assert any(row["model_id"] == "Qwen/Qwen2.5-7B-Instruct" for row in model_summary)

    budget_summary = list(csv.DictReader((baseline / "budget_summary.csv").open()))
    assert {float(row["budget_pct"]) for row in budget_summary} == set(result["budgets"])
    assert all(float(row["pass_rate_pct"]) == 100.0 for row in budget_summary)

    rows = list(csv.DictReader((baseline / "rows.csv").open()))
    assert len(rows) == result["row_count"]
    assert all(row["plan_validation_ok"] == "True" for row in rows)
    assert all(row["invariant_ok"] == "True" for row in rows)
    assert all(row["invariant_failures"] == "" for row in rows)

    print("tmh-model-family-baseline-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
