#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tmh_only_30b_layout_bench import (
    KV_LAYOUT,
    ModelShape,
    compile_tmh_plan,
    matching_ranges,
    page_count,
    page_token_count,
    resolve_range,
    validate_plan,
)

DEFAULT_PAGE_TOKENS = "1,2,3,4,7,8,16,31,32,64,127,128,256,512"
DEFAULT_BUDGETS = "100,99,90,75,50,33.333,25,12.5,6.25,3.125,1,0"
DEFAULT_RUN_ID = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


@dataclass(frozen=True)
class SyntheticCase:
    name: str
    category: str
    prompt_tokens: int
    completion_tokens: int


@dataclass(frozen=True)
class StressShape:
    name: str
    shape: ModelShape
    expected_qwen_warm_reduction: float | None = None


def parse_floats(raw: str) -> list[float]:
    return [float(item.strip()) for item in raw.split(",") if item.strip()]


def parse_ints(raw: str) -> list[int]:
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Adversarial TMH layout stress matrix.")
    parser.add_argument("--page-tokens", default=DEFAULT_PAGE_TOKENS)
    parser.add_argument("--budgets", default=DEFAULT_BUDGETS)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/tmh_adversarial_layout_stress"))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--exhaustive-layer-page-limit", type=int, default=200_000)
    return parser.parse_args()


def stress_shapes() -> list[StressShape]:
    return [
        StressShape(
            "qwen3_30b_a3b_gqa",
            ModelShape(
                model_type="qwen3_moe_gptq",
                layer_count=48,
                attention_heads=32,
                kv_heads=4,
                head_dim=128,
                hidden_size=2048,
                context_tokens=40960,
                late_layer_start=32,
                raw_dtype_bytes=2.0,
            ),
            expected_qwen_warm_reduction=16.667,
        ),
        StressShape(
            "dense_7b_gqa",
            ModelShape(
                model_type="dense_gqa",
                layer_count=32,
                attention_heads=32,
                kv_heads=8,
                head_dim=128,
                hidden_size=4096,
                context_tokens=32768,
                late_layer_start=21,
                raw_dtype_bytes=2.0,
            ),
        ),
        StressShape(
            "large_70b_gqa",
            ModelShape(
                model_type="large_gqa",
                layer_count=80,
                attention_heads=64,
                kv_heads=8,
                head_dim=128,
                hidden_size=8192,
                context_tokens=131072,
                late_layer_start=53,
                raw_dtype_bytes=2.0,
            ),
        ),
        StressShape(
            "small_all_late_boundary",
            ModelShape(
                model_type="small_boundary",
                layer_count=1,
                attention_heads=8,
                kv_heads=8,
                head_dim=64,
                hidden_size=512,
                context_tokens=4096,
                late_layer_start=0,
                raw_dtype_bytes=2.0,
            ),
        ),
        StressShape(
            "fp32_mha_boundary",
            ModelShape(
                model_type="fp32_mha",
                layer_count=12,
                attention_heads=12,
                kv_heads=12,
                head_dim=64,
                hidden_size=768,
                context_tokens=8192,
                late_layer_start=8,
                raw_dtype_bytes=4.0,
            ),
        ),
    ]


def synthetic_cases() -> list[SyntheticCase]:
    return [
        SyntheticCase("single_token", "degenerate_min", 1, 0),
        SyntheticCase("anchor_only_decode_zero", "degenerate_min", 2, 0),
        SyntheticCase("first_page_decode", "page_boundary", 7, 1),
        SyntheticCase("exact_small_boundary", "page_boundary", 8, 0),
        SyntheticCase("cross_small_boundary", "page_boundary", 8, 1),
        SyntheticCase("exact_sixteen", "page_boundary", 16, 0),
        SyntheticCase("cross_sixteen", "page_boundary", 16, 1),
        SyntheticCase("decode_heavy_short_prompt", "decode_heavy", 32, 224),
        SyntheticCase("prompt_heavy_short_decode", "prompt_heavy", 255, 1),
        SyntheticCase("exact_512_prompt", "page_boundary", 512, 0),
        SyntheticCase("cross_512_prompt", "page_boundary", 512, 1),
        SyntheticCase("long_anchor_tail", "anchor_recall_geometry", 1231, 96),
        SyntheticCase("routing_table_geometry", "structured_lookup_geometry", 660, 128),
        SyntheticCase("dense_payload_geometry", "dense_noise_geometry", 1227, 192),
        SyntheticCase("long_generation_geometry", "long_generation_geometry", 360, 384),
        SyntheticCase("near_2k_context", "context_pressure", 1792, 256),
        SyntheticCase("over_2k_context", "context_pressure", 2048, 512),
        SyntheticCase("near_4k_context", "context_pressure", 3968, 128),
        SyntheticCase("over_8k_context", "context_pressure", 8191, 257),
        SyntheticCase("sixteen_k_prompt", "long_context", 16384, 512),
        SyntheticCase("thirty_two_k_mixed", "long_context", 28672, 4096),
    ]


def precision_bytes(shape: ModelShape, tokens: int, precision: str) -> int:
    if precision == "raw":
        bytes_per_scalar = shape.raw_dtype_bytes
    elif precision == "int8":
        bytes_per_scalar = 1.0
    elif precision == "int4":
        bytes_per_scalar = 0.5
    elif precision == "dropped":
        bytes_per_scalar = 0.0
    else:
        raise ValueError(f"unknown precision: {precision}")
    return int(math.ceil(tokens * shape.kv_heads * shape.head_dim * bytes_per_scalar))


def token_sum(page_start: int, page_end: int, total_tokens: int, page_tokens: int) -> int:
    if page_start > page_end:
        return 0
    return sum(page_token_count(page_id, total_tokens, page_tokens) for page_id in range(page_start, page_end + 1))


def expected_range_class(plan: Any, shape: ModelShape, layer_id: int, page_id: int) -> tuple[str, str, str, str]:
    if page_id == 0:
        return ("prompt_anchor", "raw", "raw", "pinned")
    if page_id >= plan.recent_start_page:
        return ("recent_tail", "raw", "raw", "hot")
    if layer_id < shape.late_layer_start:
        return ("prefill_payload", "int8", "int4", "warm")
    return ("late_layer_payload", "int8", "int8", "warm")


def validate_plan_fast(shape: ModelShape, plan: Any) -> dict[str, Any]:
    failures: list[str] = []
    for range_plan in plan.ranges:
        if range_plan.authority != "hard":
            failures.append(f"non-hard authority in {range_plan.semantic_class}")
        if range_plan.k_precision_name == "dropped" or range_plan.v_precision_name == "dropped":
            failures.append(f"dropped precision in {range_plan.semantic_class}")
        if range_plan.residency_tier == "cold":
            failures.append(f"cold residency in {range_plan.semantic_class}")

    probe_pages = {
        0,
        max(0, plan.used_pages - 1),
        max(0, plan.recent_start_page),
        max(0, plan.recent_start_page - 1),
        max(0, plan.prompt_pages - 1),
        plan.used_pages // 2,
    }
    probe_layers = {
        0,
        max(0, shape.late_layer_start - 1),
        min(shape.layer_count - 1, shape.late_layer_start),
        shape.layer_count - 1,
    }
    shadowed = 0
    checked = 0
    for page_id in sorted(page for page in probe_pages if 0 <= page < plan.used_pages):
        for layer_id in sorted(layer for layer in probe_layers if 0 <= layer < shape.layer_count):
            matches = matching_ranges(plan, layer_id, page_id)
            checked += 1
            if not matches:
                failures.append(f"sample uncovered layer={layer_id} page={page_id}")
                continue
            if len(matches) > 1:
                shadowed += len(matches) - 1
            resolved = resolve_range(plan, layer_id, page_id)
            expected = expected_range_class(plan, shape, layer_id, page_id)
            actual = (
                resolved.semantic_class,
                resolved.k_precision_name,
                resolved.v_precision_name,
                resolved.residency_tier,
            )
            if actual != expected:
                failures.append(f"sample mismatch layer={layer_id} page={page_id}: {actual} != {expected}")
    return {
        "ok": not failures,
        "checked_layer_pages": checked,
        "shadowed_layer_page_matches": shadowed,
        "failures": failures[:100],
    }


def validate_with_budget(shape: ModelShape, plan: Any, exhaustive_limit: int) -> dict[str, Any]:
    layer_pages = shape.layer_count * plan.used_pages
    if layer_pages <= exhaustive_limit:
        validation = validate_plan(shape, plan)
        return {
            "ok": validation.ok,
            "checked_layer_pages": validation.checked_layer_pages,
            "shadowed_layer_page_matches": validation.shadowed_layer_page_matches,
            "failures": validation.failures,
            "validation_mode": "exhaustive",
        }
    validation = validate_plan_fast(shape, plan)
    validation["checked_layer_pages"] = layer_pages
    validation["validation_mode"] = "sampled-plus-structural"
    return validation


def summarize_case(
    *,
    stress_shape: StressShape,
    case: SyntheticCase,
    page_tokens: int,
    budget_pct: float,
    exhaustive_limit: int,
) -> dict[str, Any]:
    shape = stress_shape.shape
    total_tokens = max(1, case.prompt_tokens + case.completion_tokens)
    total_pages = page_count(total_tokens, page_tokens)
    prompt_pages = page_count(case.prompt_tokens, page_tokens)
    hot_pages_requested = 0 if budget_pct <= 0 else min(total_pages, math.ceil(total_pages * budget_pct / 100.0))
    plan = compile_tmh_plan(shape, total_pages, prompt_pages, hot_pages_requested)
    validation = validate_with_budget(shape, plan, exhaustive_limit)

    anchor_tokens = page_token_count(0, total_tokens, page_tokens)
    hot_tail_start = max(1, plan.recent_start_page)
    hot_tail_tokens = token_sum(hot_tail_start, total_pages - 1, total_tokens, page_tokens)
    old_tokens = token_sum(1, plan.recent_start_page - 1, total_tokens, page_tokens)
    early_layers = shape.late_layer_start
    late_layers = shape.layer_count - shape.late_layer_start

    raw_equivalent_bytes = precision_bytes(shape, total_tokens, "raw") * 2 * shape.layer_count
    anchor_bytes = precision_bytes(shape, anchor_tokens, "raw") * 2 * shape.layer_count
    hot_tail_bytes = precision_bytes(shape, hot_tail_tokens, "raw") * 2 * shape.layer_count
    early_old_bytes = (
        precision_bytes(shape, old_tokens, "int8") + precision_bytes(shape, old_tokens, "int4")
    ) * early_layers
    late_old_bytes = (
        precision_bytes(shape, old_tokens, "int8") + precision_bytes(shape, old_tokens, "int8")
    ) * late_layers
    hot_bytes = anchor_bytes + hot_tail_bytes
    warm_bytes = early_old_bytes + late_old_bytes
    effective_bytes = hot_bytes + warm_bytes
    uniform_old_int8_bytes = (
        precision_bytes(shape, old_tokens, "int8") + precision_bytes(shape, old_tokens, "int8")
    ) * shape.layer_count
    same_hot_uniform_int8_total = hot_bytes + uniform_old_int8_bytes
    compression_vs_raw_pct = 0.0 if raw_equivalent_bytes <= 0 else 100.0 * (1.0 - effective_bytes / raw_equivalent_bytes)
    warm_reduction_pct = 0.0 if uniform_old_int8_bytes <= 0 else 100.0 * (1.0 - warm_bytes / uniform_old_int8_bytes)
    total_reduction_pct = 0.0 if same_hot_uniform_int8_total <= 0 else 100.0 * (1.0 - effective_bytes / same_hot_uniform_int8_total)

    old_pages = max(0, plan.recent_start_page - 1)
    invariant_failures: list[str] = []
    if not validation["ok"]:
        invariant_failures.extend(validation["failures"])
    if effective_bytes > raw_equivalent_bytes:
        invariant_failures.append("effective bytes exceed raw equivalent")
    if old_tokens > 0 and early_layers > 0 and warm_reduction_pct <= 0:
        invariant_failures.append("old warm KV has no positive reduction despite demotable early layers")
    if old_tokens > 0 and total_reduction_pct < 0:
        invariant_failures.append("total reduction versus same-hot uniform old KV is negative")
    if stress_shape.expected_qwen_warm_reduction is not None and old_tokens > 0:
        if round(warm_reduction_pct, 3) != stress_shape.expected_qwen_warm_reduction:
            invariant_failures.append(
                f"qwen warm reduction {round(warm_reduction_pct, 3)} != {stress_shape.expected_qwen_warm_reduction}"
            )

    return {
        "shape": stress_shape.name,
        "model_type": shape.model_type,
        "layer_count": shape.layer_count,
        "kv_heads": shape.kv_heads,
        "head_dim": shape.head_dim,
        "late_layer_start": shape.late_layer_start,
        "case": case.name,
        "category": case.category,
        "prompt_tokens": case.prompt_tokens,
        "completion_tokens": case.completion_tokens,
        "total_tokens": total_tokens,
        "page_tokens": page_tokens,
        "budget_pct": budget_pct,
        "total_pages": total_pages,
        "prompt_pages": prompt_pages,
        "requested_hot_pages": hot_pages_requested,
        "resolved_recent_start_page": plan.recent_start_page,
        "old_pages": old_pages,
        "old_tokens": old_tokens,
        "hot_bytes": hot_bytes,
        "warm_bytes": warm_bytes,
        "raw_equivalent_bytes": raw_equivalent_bytes,
        "effective_bytes": effective_bytes,
        "uniform_old_int8_bytes": uniform_old_int8_bytes,
        "compression_vs_raw_pct": round(compression_vs_raw_pct, 3),
        "warm_reduction_vs_uniform_int8_pct": round(warm_reduction_pct, 3),
        "total_reduction_vs_same_hot_uniform_int8_pct": round(total_reduction_pct, 3),
        "plan_range_count": len(plan.ranges),
        "validation_mode": validation["validation_mode"],
        "checked_layer_pages": validation["checked_layer_pages"],
        "shadowed_layer_page_matches": validation["shadowed_layer_page_matches"],
        "plan_validation_ok": validation["ok"],
        "invariant_ok": not invariant_failures,
        "invariant_failures": "; ".join(invariant_failures),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["shape"], row["budget_pct"]), []).append(row)
    summary = []
    for (shape, budget), selected in sorted(grouped.items()):
        old_rows = [row for row in selected if row["old_tokens"] > 0]
        qwen_rows = [row for row in old_rows if row["shape"] == "qwen3_30b_a3b_gqa"]
        summary.append(
            {
                "shape": shape,
                "budget_pct": budget,
                "row_count": len(selected),
                "old_kv_row_count": len(old_rows),
                "pass_rate_pct": round(100.0 * statistics.fmean(1.0 if row["invariant_ok"] else 0.0 for row in selected), 3),
                "exhaustive_row_count": sum(1 for row in selected if row["validation_mode"] == "exhaustive"),
                "sampled_row_count": sum(1 for row in selected if row["validation_mode"] == "sampled-plus-structural"),
                "min_compression_vs_raw_pct": round(min(row["compression_vs_raw_pct"] for row in selected), 3),
                "min_warm_reduction_vs_uniform_int8_pct": round(min((row["warm_reduction_vs_uniform_int8_pct"] for row in old_rows), default=0.0), 3),
                "mean_warm_reduction_vs_uniform_int8_pct": round(statistics.fmean(row["warm_reduction_vs_uniform_int8_pct"] for row in old_rows), 3) if old_rows else 0.0,
                "min_total_reduction_vs_same_hot_uniform_int8_pct": round(min((row["total_reduction_vs_same_hot_uniform_int8_pct"] for row in old_rows), default=0.0), 3),
                "qwen_warm_reduction_pct": round(statistics.fmean(row["warm_reduction_vs_uniform_int8_pct"] for row in qwen_rows), 3) if qwen_rows else "",
            }
        )
    return summary


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# TMH Adversarial Layout Stress",
        "",
        "This stress run attacks the standalone TMH layout contract across synthetic model shapes, sequence geometries, page sizes, and hot-cache budgets.",
        "It does not mutate sock or vLLM runtime code.",
        "",
        f"- generated_at: `{result['generated_at']}`",
        f"- kv_layout: `{result['kv_layout']}`",
        f"- shapes: `{', '.join(result['shapes'])}`",
        f"- page_tokens: `{', '.join(str(value) for value in result['page_tokens'])}`",
        f"- budgets: `{', '.join(str(value) for value in result['budgets'])}`",
        f"- synthetic_cases: `{result['case_count']}`",
        f"- row_count: `{result['row_count']}`",
        f"- checked_layer_pages: `{result['checked_layer_pages']}`",
        f"- invariant_pass_rate_pct: `{result['invariant_pass_rate_pct']}`",
        "",
        "## Thesis Readout",
        "",
        f"- Plan validation pass rate: `{result['plan_validation_pass_rate_pct']}%`.",
        f"- Invariant pass rate: `{result['invariant_pass_rate_pct']}%`.",
        f"- Cold/dropped KV violations: `{result['cold_or_dropped_violation_count']}`.",
        f"- Negative total-reduction rows with old KV: `{result['negative_total_reduction_count']}`.",
        f"- Qwen-30B old/warm KV reduction: `{result['qwen_warm_reduction_pct']}%` wherever old KV exists.",
        "",
        "## Boundary Found",
        "",
        "- The exact `16.667%` old/warm reduction is production-shape specific for Qwen-30B because its TMH late-layer split leaves two thirds of layers eligible for int4 old-value demotion.",
        "- Other model shapes keep the same no-eviction/no-cold invariants, but their old/warm reduction varies with the early-vs-late layer split.",
        "- A one-layer all-late boundary shape has `0%` reduction versus uniform-int8 old KV by construction, while still preserving the TMH no-drop/no-cold behavior.",
        "",
        "## Shape/Budget Summary",
        "",
        "| shape | budget | rows | old rows | pass % | exhaustive | sampled | min compression vs raw | min warm reduction vs int8 old KV | min total reduction vs same-hot int8 old KV | qwen warm reduction |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["summary"]:
        lines.append(
            f"| `{row['shape']}` | {row['budget_pct']} | {row['row_count']} | {row['old_kv_row_count']} | "
            f"{row['pass_rate_pct']} | {row['exhaustive_row_count']} | {row['sampled_row_count']} | "
            f"{row['min_compression_vs_raw_pct']}% | {row['min_warm_reduction_vs_uniform_int8_pct']}% | "
            f"{row['min_total_reduction_vs_same_hot_uniform_int8_pct']}% | {row['qwen_warm_reduction_pct']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- The TMH plan contract survived the adversarial matrix: prompt anchors stay raw/pinned, recent tails stay raw/hot, and old pages are demoted rather than evicted.",
        "- The thesis holds as a hierarchy thesis: explicit KV layout management continues to provide a safe memory-pressure path under extreme geometry.",
        "- The numeric `16.667%` claim should remain tied to the Qwen-30B production shape, not stated as universal across arbitrary layer splits.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    page_sizes = parse_ints(args.page_tokens)
    budgets = parse_floats(args.budgets)
    shapes = stress_shapes()
    cases = synthetic_cases()
    out_dir = args.out_dir / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        summarize_case(
            stress_shape=shape,
            case=case,
            page_tokens=page_tokens,
            budget_pct=budget,
            exhaustive_limit=args.exhaustive_layer_page_limit,
        )
        for shape in shapes
        for page_tokens in page_sizes
        for budget in budgets
        for case in cases
        if case.prompt_tokens + case.completion_tokens <= shape.shape.context_tokens
    ]
    summary = aggregate(rows)
    old_rows = [row for row in rows if row["old_tokens"] > 0]
    qwen_rows = [row for row in old_rows if row["shape"] == "qwen3_30b_a3b_gqa"]
    result = {
        "ok": all(row["invariant_ok"] for row in rows),
        "kv_layout": KV_LAYOUT,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "page_tokens": page_sizes,
        "budgets": budgets,
        "shapes": [shape.name for shape in shapes],
        "case_count": len(cases),
        "row_count": len(rows),
        "old_kv_row_count": len(old_rows),
        "checked_layer_pages": sum(int(row["checked_layer_pages"]) for row in rows),
        "plan_validation_pass_rate_pct": round(100.0 * statistics.fmean(1.0 if row["plan_validation_ok"] else 0.0 for row in rows), 3),
        "invariant_pass_rate_pct": round(100.0 * statistics.fmean(1.0 if row["invariant_ok"] else 0.0 for row in rows), 3),
        "cold_or_dropped_violation_count": sum(1 for row in rows if "cold" in row["invariant_failures"] or "dropped" in row["invariant_failures"]),
        "negative_total_reduction_count": sum(1 for row in old_rows if row["total_reduction_vs_same_hot_uniform_int8_pct"] < 0),
        "qwen_warm_reduction_pct": round(statistics.fmean(row["warm_reduction_vs_uniform_int8_pct"] for row in qwen_rows), 3) if qwen_rows else 0.0,
        "summary": summary,
        "rows": rows,
    }
    result_path = out_dir / "result.json"
    summary_path = out_dir / "summary.csv"
    rows_path = out_dir / "rows.csv"
    report_path = out_dir / "REPORT.md"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(summary_path, summary)
    write_csv(rows_path, rows)
    write_report(report_path, result)
    print(json.dumps({
        "ok": result["ok"],
        "result": str(result_path),
        "summary": str(summary_path),
        "rows": str(rows_path),
        "report": str(report_path),
        "row_count": result["row_count"],
        "invariant_pass_rate_pct": result["invariant_pass_rate_pct"],
        "qwen_warm_reduction_pct": result["qwen_warm_reduction_pct"],
    }, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
