#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path("/home/deepsaint/work/kv-tiered/tmh")
DEFAULT_STRESS = ROOT / "artifacts/tmh_paper_claim_stress/paper-claim-stress-v1"


def main() -> int:
    stress = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_STRESS
    if not stress.is_absolute():
        stress = ROOT / stress
    result = json.loads((stress / "result.json").read_text())
    assert result["ok"] is True
    assert result["kv_layout"] == "tmh_fidelity_paged_kv"
    assert result["run_count"] >= 40
    assert result["model_config_count"] >= 15
    assert result["base_pressure_case_count"] >= 30
    assert result["evaluated_row_count"] >= 650_000
    assert result["old_kv_row_count"] >= 450_000
    assert result["invariant_pass_rate_pct"] == 100.0
    assert result["conservative_old_warm_reduction_floor_pct"] >= 16.0
    assert result["promoted_public_number_pct"] >= 16.0

    run_summary = list(csv.DictReader((stress / "run_summary.csv").open()))
    assert len(run_summary) == result["run_count"]
    assert all(float(row["pass_rate_pct"]) == 100.0 for row in run_summary)
    assert min(float(row["min_warm_reduction_vs_uniform_int8_pct"]) for row in run_summary if int(row["old_kv_row_count"]) > 0) >= 16.0

    model_summary = list(csv.DictReader((stress / "model_summary.csv").open()))
    assert len(model_summary) == result["model_config_count"]
    assert all(float(row["pass_rate_pct"]) == 100.0 for row in model_summary)
    assert min(float(row["min_warm_reduction_vs_uniform_int8_pct"]) for row in model_summary if int(row["old_kv_row_count"]) > 0) == result["conservative_old_warm_reduction_floor_pct"]

    run_model_summary = list(csv.DictReader((stress / "run_model_summary.csv").open()))
    assert len(run_model_summary) == result["run_count"] * result["model_config_count"]
    assert all(float(row["pass_rate_pct"]) == 100.0 for row in run_model_summary)

    budget_summary = list(csv.DictReader((stress / "budget_summary.csv").open()))
    assert {float(row["budget_pct"]) for row in budget_summary} == set(result["budgets"])
    assert all(float(row["pass_rate_pct"]) == 100.0 for row in budget_summary)

    print("tmh-paper-claim-stress-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
