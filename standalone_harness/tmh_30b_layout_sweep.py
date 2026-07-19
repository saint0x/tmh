#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tmh_only_30b_layout_bench import (
    DEFAULT_ENDPOINT_RESULT,
    DEFAULT_MODEL_CONFIG,
    KV_LAYOUT,
    aggregate,
    case_completion_tokens,
    invariant_summary,
    load_shape,
    parse_budgets,
    plan_records,
    summarize_case,
)

DEFAULT_PAGE_TOKENS = "8,16,32,64"
DEFAULT_BUDGETS = "75,50,25,12.5,6.25,3.125,0"


def parse_ints(raw: str) -> list[int]:
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep the single TMH 30B KV layout across page sizes and hot budgets.")
    parser.add_argument("--endpoint-result", type=Path, default=DEFAULT_ENDPOINT_RESULT)
    parser.add_argument("--model-config", type=Path, default=DEFAULT_MODEL_CONFIG)
    parser.add_argument("--page-tokens", default=DEFAULT_PAGE_TOKENS)
    parser.add_argument("--budgets", default=DEFAULT_BUDGETS)
    parser.add_argument(
        "--dry-run-completions",
        choices=["effective-max"],
        default="effective-max",
        help="When endpoint-result is preflight-only, synthesize completion pressure from this source.",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/tmh_30b_layout_sweep"))
    return parser.parse_args()


def same_hot_uniform_int8_reduction(row: dict[str, Any]) -> float:
    if row["warm_bytes"] <= 0:
        return 0.0
    uniform_warm = row["warm_bytes"] / (1.0 - (1.0 / 6.0))
    uniform_total = row["hot_bytes"] + uniform_warm
    if uniform_total <= 0:
        return 0.0
    return 100.0 * (1.0 - (row["effective_bytes"] / uniform_total))


def warm_reduction_vs_uniform_int8(row: dict[str, Any]) -> float:
    if row["warm_bytes"] <= 0:
        return 0.0
    uniform_warm = row["warm_bytes"] / (1.0 - (1.0 / 6.0))
    return 100.0 * (1.0 - (row["warm_bytes"] / uniform_warm))


def write_dict_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def synthesize_endpoint_from_preflight(endpoint: dict[str, Any], completion_source: str) -> dict[str, Any]:
    if endpoint.get("cases"):
        return endpoint
    if not endpoint.get("dry_run"):
        raise ValueError("endpoint result has no measured cases and is not marked dry_run")
    if completion_source != "effective-max":
        raise ValueError(f"unsupported dry-run completion source: {completion_source}")
    cases = []
    stream_probes = []
    for row in endpoint.get("preflight", []):
        completion_tokens = int(row["effective_max_tokens"])
        prompt_tokens = int(row["prompt_tokens"])
        total_tokens = prompt_tokens + completion_tokens
        request = {
            "completion_tokens": completion_tokens,
            "contains_target": False,
            "elapsed_s": 0.0,
            "finish_reason": "synthetic_preflight",
            "prompt_tokens": prompt_tokens,
            "request_index": 1,
            "response_text": "",
            "run_index": 1,
            "total_tokens": total_tokens,
        }
        summary = {
            "aggregate_completion_tok_per_s": {"mean": 0.0},
            "contains_target_rate_pct": {"mean": 0.0},
            "wall_s": {"mean": 0.0},
        }
        cases.append(
            {
                "name": row["case"],
                "category": row["category"],
                "target_hint": "",
                "max_tokens": completion_tokens,
                "temperature": 0.0,
                "warmups": [],
                "batches_by_concurrency": {"1": [{"requests": [request]}]},
                "summary_by_concurrency": {"1": summary, "2": summary},
            }
        )
        stream_probes.append({"case": row["case"], "ttft_s": 0.0})
    synthesized = dict(endpoint)
    synthesized["cases"] = cases
    synthesized["stream_probes"] = stream_probes
    synthesized["layout_completion_source"] = completion_source
    return synthesized


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# TMH 30B Layout Sweep",
        "",
        "This report sweeps one KV layout only: `tmh_fidelity_paged_kv`.",
        "It reuses the real 30B sock endpoint traffic corpus and varies page size plus hot-window budget.",
        "",
        f"- model: `{result['endpoint']['model']}`",
        f"- endpoint_result: `{result['endpoint_result']}`",
        f"- kv_layout: `{result['kv_layout']}`",
        f"- completion_source: `{result['completion_source']}`",
        f"- page_tokens: `{', '.join(str(x) for x in result['page_tokens'])}`",
        f"- budgets: `{', '.join(str(x) for x in result['budgets'])}`",
        f"- generated_at: `{result['generated_at']}`",
        "",
        "## Sweep Summary",
        "",
        "| page tokens | hot budget | cases | effective bytes/token | compression vs raw | warm reduction vs int8 old KV | total reduction vs same-hot int8 old KV | plan pass |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["sweep_summary"]:
        lines.append(
            f"| {row['page_tokens']} | {row['budget_pct']} | {row['case_count']} | "
            f"{row['mean_effective_bytes_per_token']} | {row['mean_compression_vs_raw_pct']}% | "
            f"{row['mean_warm_reduction_vs_uniform_int8_pct']}% | "
            f"{row['mean_total_reduction_vs_same_hot_uniform_int8_pct']}% | "
            f"{row['plan_validation_pass_rate_pct']}% |"
        )
    lines += [
        "",
        "## Readout",
        "",
        "- The old/warm KV reduction remains `16.667%` wherever old KV exists, because the layout keeps old K int8, early/middle old V int4, and late old V int8.",
        "- Total effective KV pressure reduction depends on how much of the context is still hot raw KV.",
        "- Smaller hot windows move total effective reduction closer to the old/warm KV reduction ceiling.",
        "- Page size changes can slightly move totals because prompt-anchor and tail pages round differently, but the no-eviction invariant stays fixed.",
        "- This is still a layout-pressure sweep, not live runtime execution with TMH fused inside vLLM.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    endpoint = synthesize_endpoint_from_preflight(json.loads(args.endpoint_result.read_text()), args.dry_run_completions)
    shape = load_shape(args.model_config)
    budgets = parse_budgets(args.budgets)
    page_sizes = parse_ints(args.page_tokens)
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = generated_at.replace(":", "").replace("-", "").replace("T", "-").removesuffix("Z")
    out_dir = args.out_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, Any]] = []
    all_plans: list[dict[str, Any]] = []
    sweep_summary: list[dict[str, Any]] = []
    for page_tokens in page_sizes:
        rows = [
            summarize_case(endpoint, shape, case, budget, page_tokens)
            for budget in budgets
            for case in endpoint["cases"]
        ]
        row_dicts = [asdict(row) for row in rows]
        for row in row_dicts:
            row["warm_reduction_vs_uniform_int8_pct"] = round(warm_reduction_vs_uniform_int8(row), 3)
            row["total_reduction_vs_same_hot_uniform_int8_pct"] = round(same_hot_uniform_int8_reduction(row), 3)
        all_rows.extend(row_dicts)
        all_plans.extend(plan_records(endpoint, shape, budgets, page_tokens))
        invariants = invariant_summary(rows)
        for budget in budgets:
            selected = [row for row in row_dicts if row["budget_pct"] == budget]
            base = aggregate(rows, budget)
            base.update(
                {
                    "page_tokens": page_tokens,
                    "mean_warm_reduction_vs_uniform_int8_pct": round(statistics.fmean(row["warm_reduction_vs_uniform_int8_pct"] for row in selected), 3),
                    "mean_total_reduction_vs_same_hot_uniform_int8_pct": round(statistics.fmean(row["total_reduction_vs_same_hot_uniform_int8_pct"] for row in selected), 3),
                    "checked_layer_pages": invariants["checked_layer_pages"],
                    "cases_with_failures": invariants["cases_with_failures"],
                    "cold_bytes_total": invariants["cold_bytes_total"],
                }
            )
            sweep_summary.append(base)

    result = {
        "ok": True,
        "kv_layout": KV_LAYOUT,
        "endpoint_result": str(args.endpoint_result),
        "completion_source": endpoint.get("layout_completion_source", "measured_endpoint_completions"),
        "model_config": str(args.model_config),
        "endpoint": {k: endpoint[k] for k in ["model", "base_url", "profile", "generated_at", "elapsed_s"] if k in endpoint},
        "model_shape": asdict(shape),
        "page_tokens": page_sizes,
        "budgets": budgets,
        "generated_at": generated_at,
        "row_count": len(all_rows),
        "plan_range_count": len(all_plans),
        "sweep_summary": sweep_summary,
        "rows": all_rows,
    }
    result_path = out_dir / "result.json"
    summary_path = out_dir / "sweep_summary.csv"
    rows_path = out_dir / "rows.csv"
    plans_path = out_dir / "plan_ranges.csv"
    report_path = out_dir / "REPORT.md"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    write_dict_csv(summary_path, sweep_summary)
    write_dict_csv(rows_path, all_rows)
    write_dict_csv(plans_path, all_plans)
    write_report(report_path, result)
    print(json.dumps({
        "ok": True,
        "result": str(result_path),
        "summary": str(summary_path),
        "rows": str(rows_path),
        "plans": str(plans_path),
        "report": str(report_path),
        "row_count": len(all_rows),
        "plan_range_count": len(all_plans),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
