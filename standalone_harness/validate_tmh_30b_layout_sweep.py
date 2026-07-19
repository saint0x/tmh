#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

ROOT = Path("/home/deepsaint/work/kv-tiered/tmh")
DEFAULT_SWEEP = ROOT / "artifacts/tmh_30b_layout_sweep/20260719-035609"


def main() -> int:
    sweep = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SWEEP
    if not sweep.is_absolute():
        sweep = ROOT / sweep
    result = json.loads((sweep / "result.json").read_text())
    assert result["ok"] is True
    assert result["kv_layout"] == "tmh_fidelity_paged_kv"
    assert result["page_tokens"] == [8, 16, 32, 64]
    assert result["budgets"] == [75.0, 50.0, 25.0, 12.5, 6.25, 3.125, 0.0]
    assert result["row_count"] == 280
    assert result["plan_range_count"] == 1080

    summary = list(csv.DictReader((sweep / "sweep_summary.csv").open()))
    assert len(summary) == 28
    assert {row["page_tokens"] for row in summary} == {"8", "16", "32", "64"}
    assert {row["budget_pct"] for row in summary} == {"75.0", "50.0", "25.0", "12.5", "6.25", "3.125", "0.0"}
    assert all(float(row["plan_validation_pass_rate_pct"]) == 100.0 for row in summary)
    assert all(float(row["mean_warm_reduction_vs_uniform_int8_pct"]) == 16.667 for row in summary)

    rows = list(csv.DictReader((sweep / "rows.csv").open()))
    assert len(rows) == 280
    assert all(row["kv_layout"] if "kv_layout" in row else "tmh_fidelity_paged_kv" for row in rows)
    assert all(row["plan_validation_ok"] == "True" for row in rows)
    assert all(int(row["cold_pages"]) == 0 for row in rows)
    assert all(int(row["cold_bytes"]) == 0 for row in rows)
    assert all(float(row["warm_reduction_vs_uniform_int8_pct"]) == 16.667 for row in rows)

    plans = list(csv.DictReader((sweep / "plan_ranges.csv").open()))
    assert len(plans) == 1080
    assert {row["kv_layout"] for row in plans} == {"tmh_fidelity_paged_kv"}
    assert {row["authority"] for row in plans} == {"hard"}
    assert "dropped" not in {row["k_precision_name"] for row in plans}
    assert "dropped" not in {row["v_precision_name"] for row in plans}
    assert "cold" not in {row["residency_tier"] for row in plans}

    print("tmh-sweep-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
