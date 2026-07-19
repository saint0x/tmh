#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tmh_adversarial_layout_stress import (
    SyntheticCase,
    precision_bytes,
    synthetic_cases,
    token_sum,
    validate_with_budget,
)
from tmh_only_30b_layout_bench import (
    KV_LAYOUT,
    ModelShape,
    compile_tmh_plan,
    load_shape,
    page_count,
    page_token_count,
)

DEFAULT_PAGE_TOKENS = "8,16,32,64,128"
DEFAULT_BUDGETS = "75,50,25,12.5,6.25,3.125,1,0"
DEFAULT_CONFIG_GLOB = "/home/deepsaint/.cache/huggingface/hub/models--*/snapshots/*/config.json"
DEFAULT_ENDPOINT_RESULT = Path("artifacts/sock_endpoint_pressure/20260719-040954/result.json")
DEFAULT_RUN_ID = "model-family-v1"


def parse_floats(raw: str) -> list[float]:
    return [float(item.strip()) for item in raw.split(",") if item.strip()]


def parse_ints(raw: str) -> list[int]:
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-model TMH production memory-pressure baseline from actual HF configs.")
    parser.add_argument("--config-glob", default=DEFAULT_CONFIG_GLOB)
    parser.add_argument("--endpoint-result", type=Path, default=DEFAULT_ENDPOINT_RESULT)
    parser.add_argument("--page-tokens", default=DEFAULT_PAGE_TOKENS)
    parser.add_argument("--budgets", default=DEFAULT_BUDGETS)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/tmh_model_family_memory_baseline"))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--exhaustive-layer-page-limit", type=int, default=200_000)
    return parser.parse_args()


def model_id_from_config(path: Path) -> str:
    raw = str(path)
    if "/models--" not in raw or "/snapshots/" not in raw:
        return path.parent.name
    return raw.split("/models--", 1)[1].split("/snapshots/", 1)[0].replace("--", "/")


def snapshot_from_config(path: Path) -> str:
    if "/snapshots/" not in str(path):
        return path.parent.name
    return str(path).split("/snapshots/", 1)[1].split("/", 1)[0]


def load_model_configs(pattern: str) -> list[dict[str, Any]]:
    records = []
    for path in sorted(Path("/").glob(pattern.removeprefix("/")) if pattern.startswith("/") else Path(".").glob(pattern)):
        try:
            shape = load_shape(path)
        except Exception:
            continue
        if shape.layer_count <= 0 or shape.kv_heads <= 0 or shape.head_dim <= 0:
            continue
        records.append(
            {
                "model_id": model_id_from_config(path),
                "snapshot": snapshot_from_config(path),
                "config_path": str(path),
                "shape": shape,
            }
        )
    return records


def endpoint_cases(endpoint_path: Path) -> list[SyntheticCase]:
    if not endpoint_path.exists():
        return []
    endpoint = json.loads(endpoint_path.read_text())
    preflight = {row["case"]: int(row["prompt_tokens"]) for row in endpoint.get("preflight", [])}
    cases = []
    for case in endpoint.get("cases", []):
        reqs = case["batches_by_concurrency"]["1"][0]["requests"]
        completion = int(round(statistics.fmean(int(req["completion_tokens"]) for req in reqs)))
        prompt = preflight.get(case["name"])
        if prompt is None:
            continue
        cases.append(SyntheticCase(f"endpoint_{case['name']}", f"endpoint_{case['category']}", prompt, completion))
    return cases


def all_pressure_cases(endpoint_path: Path) -> list[SyntheticCase]:
    dedup: dict[tuple[int, int, str], SyntheticCase] = {}
    for case in [*endpoint_cases(endpoint_path), *synthetic_cases()]:
        dedup[(case.prompt_tokens, case.completion_tokens, case.name)] = case
    return list(dedup.values())


def summarize_row(
    *,
    model: dict[str, Any],
    case: SyntheticCase,
    page_tokens: int,
    budget_pct: float,
    exhaustive_limit: int,
) -> dict[str, Any]:
    shape: ModelShape = model["shape"]
    total_tokens = max(1, case.prompt_tokens + case.completion_tokens)
    total_pages = page_count(total_tokens, page_tokens)
    prompt_pages = page_count(case.prompt_tokens, page_tokens)
    hot_pages = 0 if budget_pct <= 0 else min(total_pages, math.ceil(total_pages * budget_pct / 100.0))
    plan = compile_tmh_plan(shape, total_pages, prompt_pages, hot_pages)
    validation = validate_with_budget(shape, plan, exhaustive_limit)

    anchor_tokens = page_token_count(0, total_tokens, page_tokens)
    hot_tail_tokens = token_sum(max(1, plan.recent_start_page), total_pages - 1, total_tokens, page_tokens)
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
    same_hot_uniform_total = hot_bytes + uniform_old_int8_bytes

    compression_vs_raw = 0.0 if raw_equivalent_bytes <= 0 else 100.0 * (1.0 - effective_bytes / raw_equivalent_bytes)
    warm_reduction = 0.0 if uniform_old_int8_bytes <= 0 else 100.0 * (1.0 - warm_bytes / uniform_old_int8_bytes)
    total_reduction = 0.0 if same_hot_uniform_total <= 0 else 100.0 * (1.0 - effective_bytes / same_hot_uniform_total)
    invariant_failures: list[str] = []
    if not validation["ok"]:
        invariant_failures.extend(validation["failures"])
    if old_tokens > 0 and warm_reduction < 0:
        invariant_failures.append("negative warm reduction")
    if old_tokens > 0 and total_reduction < 0:
        invariant_failures.append("negative total reduction")
    if effective_bytes > raw_equivalent_bytes:
        invariant_failures.append("effective bytes exceed raw")

    return {
        "model_id": model["model_id"],
        "snapshot": model["snapshot"],
        "config_path": model["config_path"],
        "model_type": shape.model_type,
        "layer_count": shape.layer_count,
        "attention_heads": shape.attention_heads,
        "kv_heads": shape.kv_heads,
        "head_dim": shape.head_dim,
        "hidden_size": shape.hidden_size,
        "context_tokens": shape.context_tokens,
        "late_layer_start": shape.late_layer_start,
        "raw_dtype_bytes": shape.raw_dtype_bytes,
        "case": case.name,
        "category": case.category,
        "prompt_tokens": case.prompt_tokens,
        "completion_tokens": case.completion_tokens,
        "total_tokens": total_tokens,
        "page_tokens": page_tokens,
        "budget_pct": budget_pct,
        "total_pages": total_pages,
        "prompt_pages": prompt_pages,
        "requested_hot_pages": hot_pages,
        "old_tokens": old_tokens,
        "hot_bytes": hot_bytes,
        "warm_bytes": warm_bytes,
        "raw_equivalent_bytes": raw_equivalent_bytes,
        "effective_bytes": effective_bytes,
        "uniform_old_int8_bytes": uniform_old_int8_bytes,
        "compression_vs_raw_pct": round(compression_vs_raw, 3),
        "warm_reduction_vs_uniform_int8_pct": round(warm_reduction, 3),
        "total_reduction_vs_same_hot_uniform_int8_pct": round(total_reduction, 3),
        "plan_range_count": len(plan.ranges),
        "validation_mode": validation["validation_mode"],
        "checked_layer_pages": validation["checked_layer_pages"],
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


def summarize_models(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_model: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_model.setdefault(row["model_id"], []).append(row)
    summary = []
    for model_id, selected in sorted(by_model.items()):
        old_rows = [row for row in selected if int(row["old_tokens"]) > 0]
        shape = selected[0]
        summary.append(
            {
                "model_id": model_id,
                "model_type": shape["model_type"],
                "layer_count": shape["layer_count"],
                "kv_heads": shape["kv_heads"],
                "head_dim": shape["head_dim"],
                "late_layer_start": shape["late_layer_start"],
                "row_count": len(selected),
                "old_kv_row_count": len(old_rows),
                "pass_rate_pct": round(100.0 * statistics.fmean(1.0 if row["invariant_ok"] else 0.0 for row in selected), 3),
                "min_warm_reduction_vs_uniform_int8_pct": round(min(row["warm_reduction_vs_uniform_int8_pct"] for row in old_rows), 3) if old_rows else 0.0,
                "mean_warm_reduction_vs_uniform_int8_pct": round(statistics.fmean(row["warm_reduction_vs_uniform_int8_pct"] for row in old_rows), 3) if old_rows else 0.0,
                "min_total_reduction_vs_same_hot_uniform_int8_pct": round(min(row["total_reduction_vs_same_hot_uniform_int8_pct"] for row in old_rows), 3) if old_rows else 0.0,
                "min_compression_vs_raw_pct": round(min(row["compression_vs_raw_pct"] for row in selected), 3),
            }
        )
    return summary


def summarize_budgets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_budget: dict[float, list[dict[str, Any]]] = {}
    for row in rows:
        by_budget.setdefault(float(row["budget_pct"]), []).append(row)
    summary = []
    for budget, selected in sorted(by_budget.items()):
        old_rows = [row for row in selected if int(row["old_tokens"]) > 0]
        summary.append(
            {
                "budget_pct": budget,
                "row_count": len(selected),
                "old_kv_row_count": len(old_rows),
                "pass_rate_pct": round(100.0 * statistics.fmean(1.0 if row["invariant_ok"] else 0.0 for row in selected), 3),
                "min_warm_reduction_vs_uniform_int8_pct": round(min(row["warm_reduction_vs_uniform_int8_pct"] for row in old_rows), 3) if old_rows else 0.0,
                "mean_warm_reduction_vs_uniform_int8_pct": round(statistics.fmean(row["warm_reduction_vs_uniform_int8_pct"] for row in old_rows), 3) if old_rows else 0.0,
                "min_total_reduction_vs_same_hot_uniform_int8_pct": round(min(row["total_reduction_vs_same_hot_uniform_int8_pct"] for row in old_rows), 3) if old_rows else 0.0,
                "mean_total_reduction_vs_same_hot_uniform_int8_pct": round(statistics.fmean(row["total_reduction_vs_same_hot_uniform_int8_pct"] for row in old_rows), 3) if old_rows else 0.0,
            }
        )
    return summary


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# TMH Model-Family Memory Baseline",
        "",
        "This report measures the production TMH memory-plan logic across every locally cached Hugging Face model config.",
        "It promotes the conservative floor across supported configs rather than a single-model number.",
        "",
        f"- generated_at: `{result['generated_at']}`",
        f"- kv_layout: `{result['kv_layout']}`",
        f"- model_config_count: `{result['model_config_count']}`",
        f"- pressure_case_count: `{result['pressure_case_count']}`",
        f"- row_count: `{result['row_count']}`",
        f"- old_kv_row_count: `{result['old_kv_row_count']}`",
        f"- invariant_pass_rate_pct: `{result['invariant_pass_rate_pct']}`",
        f"- promoted_old_warm_reduction_floor_pct: `{result['promoted_old_warm_reduction_floor_pct']}`",
        f"- promoted_public_number_pct: `{result['promoted_public_number_pct']}`",
        "",
        "## Production Number",
        "",
        f"The supported-model floor is `{result['promoted_old_warm_reduction_floor_pct']}%` old/warm KV pressure reduction versus same-hot uniform-int8 old KV.",
        "",
        f"For external/product language, use `at least {result['promoted_public_number_pct']}% old/warm KV memory-pressure reduction across the tested production model-family baseline`.",
        "",
        "This is intentionally a floor, not an average. Total effective KV pressure reduction still depends on hot-window size, page rounding, and how much old KV exists in a request.",
        "",
        "## Model Summary",
        "",
        "| model | layers | kv heads | late start | rows | old rows | pass % | min warm reduction | mean warm reduction | min total reduction |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["model_summary"]:
        lines.append(
            f"| `{row['model_id']}` | {row['layer_count']} | {row['kv_heads']} | {row['late_layer_start']} | "
            f"{row['row_count']} | {row['old_kv_row_count']} | {row['pass_rate_pct']} | "
            f"{row['min_warm_reduction_vs_uniform_int8_pct']}% | {row['mean_warm_reduction_vs_uniform_int8_pct']}% | "
            f"{row['min_total_reduction_vs_same_hot_uniform_int8_pct']}% |"
        )
    lines += [
        "",
        "## Budget Summary",
        "",
        "| budget | rows | old rows | pass % | min warm reduction | mean warm reduction | min total reduction | mean total reduction |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["budget_summary"]:
        lines.append(
            f"| {row['budget_pct']} | {row['row_count']} | {row['old_kv_row_count']} | {row['pass_rate_pct']} | "
            f"{row['min_warm_reduction_vs_uniform_int8_pct']}% | {row['mean_warm_reduction_vs_uniform_int8_pct']}% | "
            f"{row['min_total_reduction_vs_same_hot_uniform_int8_pct']}% | {row['mean_total_reduction_vs_same_hot_uniform_int8_pct']}% |"
        )
    lines += [
        "",
        "## Boundary",
        "",
        "- The production memory-pressure number should be the conservative old/warm KV floor across supported model configs, not the Qwen-30B-only value.",
        "- The exact per-model reduction is determined by the model's layer count and TMH late-layer split.",
        "- The current supported-model floor is set by Qwen2.5 models with `28` layers and `late_layer_start=18`.",
        "- Total effective KV pressure reduction is workload-dependent because hot raw KV and prompt-anchor pages are intentionally preserved.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    models = load_model_configs(args.config_glob)
    if not models:
        raise SystemExit("no model configs found")
    cases = all_pressure_cases(args.endpoint_result)
    page_sizes = parse_ints(args.page_tokens)
    budgets = parse_floats(args.budgets)
    out_dir = args.out_dir / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        summarize_row(
            model=model,
            case=case,
            page_tokens=page_tokens,
            budget_pct=budget,
            exhaustive_limit=args.exhaustive_layer_page_limit,
        )
        for model in models
        for page_tokens in page_sizes
        for budget in budgets
        for case in cases
        if case.prompt_tokens + case.completion_tokens <= model["shape"].context_tokens
    ]
    old_rows = [row for row in rows if row["old_tokens"] > 0]
    model_summary = summarize_models(rows)
    budget_summary = summarize_budgets(rows)
    floor = round(min(row["min_warm_reduction_vs_uniform_int8_pct"] for row in model_summary if row["old_kv_row_count"] > 0), 3)
    public_floor = math.floor(floor * 10.0) / 10.0
    result = {
        "ok": all(row["invariant_ok"] for row in rows),
        "kv_layout": KV_LAYOUT,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config_glob": args.config_glob,
        "endpoint_result": str(args.endpoint_result),
        "model_config_count": len(models),
        "pressure_case_count": len(cases),
        "page_tokens": page_sizes,
        "budgets": budgets,
        "row_count": len(rows),
        "old_kv_row_count": len(old_rows),
        "checked_layer_pages": sum(int(row["checked_layer_pages"]) for row in rows),
        "plan_validation_pass_rate_pct": round(100.0 * statistics.fmean(1.0 if row["plan_validation_ok"] else 0.0 for row in rows), 3),
        "invariant_pass_rate_pct": round(100.0 * statistics.fmean(1.0 if row["invariant_ok"] else 0.0 for row in rows), 3),
        "promoted_old_warm_reduction_floor_pct": floor,
        "promoted_public_number_pct": public_floor,
        "model_summary": model_summary,
        "budget_summary": budget_summary,
        "rows": rows,
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(out_dir / "model_summary.csv", model_summary)
    write_csv(out_dir / "budget_summary.csv", budget_summary)
    write_csv(out_dir / "rows.csv", rows)
    write_report(out_dir / "REPORT.md", result)
    print(json.dumps({
        "ok": result["ok"],
        "report": str(out_dir / "REPORT.md"),
        "result": str(out_dir / "result.json"),
        "row_count": result["row_count"],
        "model_config_count": result["model_config_count"],
        "promoted_old_warm_reduction_floor_pct": result["promoted_old_warm_reduction_floor_pct"],
        "promoted_public_number_pct": result["promoted_public_number_pct"],
        "invariant_pass_rate_pct": result["invariant_pass_rate_pct"],
    }, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
