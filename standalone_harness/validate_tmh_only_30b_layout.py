#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from tmh_only_30b_layout_bench import (
    KV_LAYOUT,
    case_completion_tokens,
    compile_tmh_plan,
    invariant_summary,
    load_shape,
    page_count,
    parse_budgets,
    summarize_case,
    validate_plan,
)

ROOT = Path("/home/deepsaint/work/kv-tiered/tmh")
ENDPOINT_RESULT = ROOT / "artifacts/sock_endpoint_pressure/20260719-023427/result.json"
MODEL_CONFIG = Path(
    "/home/deepsaint/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B-GPTQ-Int4/"
    "snapshots/9b534e4318b7ebc3c961a839f13eb18b1833f441/config.json"
)


def main() -> int:
    endpoint = json.loads(ENDPOINT_RESULT.read_text())
    shape = load_shape(MODEL_CONFIG)
    budgets = parse_budgets("50,25,12.5,6.25,0")
    rows = [
        summarize_case(endpoint, shape, case, budget, 16)
        for budget in budgets
        for case in endpoint["cases"]
    ]
    invariants = invariant_summary(rows)
    assert invariants["layout_count"] == 1
    assert invariants["kv_layout"] == KV_LAYOUT
    assert invariants["validation_pass_rate_pct"] == 100.0
    assert invariants["cases_with_failures"] == 0
    assert invariants["cold_bytes_total"] == 0
    assert invariants["dropped_k_pages_total"] == 0
    assert invariants["dropped_v_pages_total"] == 0
    assert all(row.plan_validation_ok for row in rows)
    assert all(row.plan_range_count in (3, 4) for row in rows)

    preflight = {row["case"]: int(row["prompt_tokens"]) for row in endpoint["preflight"]}
    for case in endpoint["cases"]:
        prompt_tokens = preflight[case["name"]]
        total_tokens = prompt_tokens + case_completion_tokens(case)
        used_pages = page_count(total_tokens, 16)
        prompt_pages = page_count(prompt_tokens, 16)
        plan = compile_tmh_plan(shape, used_pages, prompt_pages, hot_pages=0)
        validation = validate_plan(shape, plan)
        assert validation.ok
        assert plan.ranges[0].semantic_class == "prompt_anchor"
        assert plan.ranges[0].k_precision_name == "raw"
        assert plan.ranges[0].v_precision_name == "raw"
        assert plan.ranges[-1].semantic_class == "late_layer_payload"

    print("tmh-plan-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
