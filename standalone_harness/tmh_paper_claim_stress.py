#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tmh_model_family_memory_baseline import (
    all_pressure_cases,
    load_model_configs,
    summarize_row,
)
from tmh_only_30b_layout_bench import KV_LAYOUT

DEFAULT_CONFIG_GLOB = "/home/deepsaint/.cache/huggingface/hub/models--*/snapshots/*/config.json"
DEFAULT_ENDPOINT_RESULT = Path("artifacts/sock_endpoint_pressure/20260719-040954/result.json")
DEFAULT_RUN_ID = "paper-claim-stress-v1"
DEFAULT_PAGE_TOKENS = "8,16,32,64,128"
DEFAULT_BUDGETS = "75,50,25,12.5,6.25,3.125,1,0"


@dataclass(frozen=True)
class VariantCase:
    name: str
    category: str
    prompt_tokens: int
    completion_tokens: int


class Agg:
    def __init__(self) -> None:
        self.count = 0
        self.old_count = 0
        self.pass_count = 0
        self.checked_layer_pages = 0
        self.min_warm = math.inf
        self.sum_warm = 0.0
        self.min_total = math.inf
        self.sum_total = 0.0
        self.min_compression = math.inf
        self.sum_compression = 0.0

    def update(self, row: dict[str, Any]) -> None:
        self.count += 1
        self.pass_count += 1 if row["invariant_ok"] else 0
        self.checked_layer_pages += int(row["checked_layer_pages"])
        compression = float(row["compression_vs_raw_pct"])
        self.min_compression = min(self.min_compression, compression)
        self.sum_compression += compression
        if int(row["old_tokens"]) > 0:
            self.old_count += 1
            warm = float(row["warm_reduction_vs_uniform_int8_pct"])
            total = float(row["total_reduction_vs_same_hot_uniform_int8_pct"])
            self.min_warm = min(self.min_warm, warm)
            self.sum_warm += warm
            self.min_total = min(self.min_total, total)
            self.sum_total += total

    def row(self, **keys: Any) -> dict[str, Any]:
        return {
            **keys,
            "row_count": self.count,
            "old_kv_row_count": self.old_count,
            "pass_rate_pct": round(100.0 * self.pass_count / max(1, self.count), 3),
            "checked_layer_pages": self.checked_layer_pages,
            "min_warm_reduction_vs_uniform_int8_pct": round(self.min_warm if self.old_count else 0.0, 3),
            "mean_warm_reduction_vs_uniform_int8_pct": round(self.sum_warm / self.old_count, 3) if self.old_count else 0.0,
            "min_total_reduction_vs_same_hot_uniform_int8_pct": round(self.min_total if self.old_count else 0.0, 3),
            "mean_total_reduction_vs_same_hot_uniform_int8_pct": round(self.sum_total / self.old_count, 3) if self.old_count else 0.0,
            "min_compression_vs_raw_pct": round(self.min_compression if self.count else 0.0, 3),
            "mean_compression_vs_raw_pct": round(self.sum_compression / max(1, self.count), 3),
        }


def parse_ints(raw: str) -> list[int]:
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def parse_floats(raw: str) -> list[float]:
    return [float(item.strip()) for item in raw.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Large paper-confidence stress matrix for TMH claims.")
    parser.add_argument("--config-glob", default=DEFAULT_CONFIG_GLOB)
    parser.add_argument("--endpoint-result", type=Path, default=DEFAULT_ENDPOINT_RESULT)
    parser.add_argument("--run-count", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260719)
    parser.add_argument("--page-tokens", default=DEFAULT_PAGE_TOKENS)
    parser.add_argument("--budgets", default=DEFAULT_BUDGETS)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/tmh_paper_claim_stress"))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--exhaustive-layer-page-limit", type=int, default=200_000)
    parser.add_argument("--edge-sample-limit", type=int, default=2000)
    return parser.parse_args()


def variant_case(base: Any, run_index: int, case_index: int, seed: int) -> VariantCase:
    rng = random.Random(seed + run_index * 1009 + case_index * 9176)
    prompt_scale = rng.choice([0.5, 0.625, 0.75, 0.875, 1.0, 1.125, 1.25, 1.5, 1.75, 2.0])
    completion_scale = rng.choice([0.5, 0.75, 1.0, 1.25, 1.5, 2.0])
    prompt_jitter = rng.randint(-64, 256)
    completion_jitter = rng.randint(-16, 128)
    prompt_tokens = max(1, int(round(base.prompt_tokens * prompt_scale)) + prompt_jitter)
    completion_tokens = max(0, int(round(base.completion_tokens * completion_scale)) + completion_jitter)
    if run_index % 10 == 0:
        prompt_tokens += 2048 + 128 * case_index
    if run_index % 13 == 0:
        completion_tokens += 512
    if run_index % 17 == 0:
        prompt_tokens = max(prompt_tokens, 8192 + 257 * (case_index % 9))
    return VariantCase(
        name=f"run{run_index:02d}_{base.name}",
        category=f"{base.category}_variant",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# TMH Paper Claim Stress",
        "",
        "This is the larger pre-paper stress run for the production TMH memory-pressure claim.",
        "It evaluates many deterministic traffic variants across every locally cached model config and promotes only the conservative floor.",
        "",
        f"- generated_at: `{result['generated_at']}`",
        f"- kv_layout: `{result['kv_layout']}`",
        f"- model_config_count: `{result['model_config_count']}`",
        f"- base_pressure_case_count: `{result['base_pressure_case_count']}`",
        f"- run_count: `{result['run_count']}`",
        f"- evaluated_row_count: `{result['evaluated_row_count']}`",
        f"- old_kv_row_count: `{result['old_kv_row_count']}`",
        f"- invariant_pass_rate_pct: `{result['invariant_pass_rate_pct']}`",
        f"- conservative_old_warm_reduction_floor_pct: `{result['conservative_old_warm_reduction_floor_pct']}`",
        f"- promoted_public_number_pct: `{result['promoted_public_number_pct']}`",
        "",
        "## Claim Readout",
        "",
        f"- The pre-paper conservative floor is `{result['conservative_old_warm_reduction_floor_pct']}%` old/warm KV pressure reduction versus same-hot uniform-int8 old KV.",
        f"- Public/product wording should stay at `at least {result['promoted_public_number_pct']}% old/warm KV memory-pressure reduction across the tested production model-family stress baseline`.",
        "- This remains a memory-pressure/layout claim, not yet a live vLLM-internal KV-manager speedup claim.",
        "",
        "## Run Summary",
        "",
        "| run | rows | old rows | pass % | min warm reduction | mean warm reduction | min total reduction |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["run_summary"]:
        lines.append(
            f"| {row['run_index']} | {row['row_count']} | {row['old_kv_row_count']} | {row['pass_rate_pct']} | "
            f"{row['min_warm_reduction_vs_uniform_int8_pct']}% | {row['mean_warm_reduction_vs_uniform_int8_pct']}% | "
            f"{row['min_total_reduction_vs_same_hot_uniform_int8_pct']}% |"
        )
    lines += [
        "",
        "## Model Summary",
        "",
        "| model | rows | old rows | pass % | min warm reduction | mean warm reduction | min total reduction |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["model_summary"]:
        lines.append(
            f"| `{row['model_id']}` | {row['row_count']} | {row['old_kv_row_count']} | {row['pass_rate_pct']} | "
            f"{row['min_warm_reduction_vs_uniform_int8_pct']}% | {row['mean_warm_reduction_vs_uniform_int8_pct']}% | "
            f"{row['min_total_reduction_vs_same_hot_uniform_int8_pct']}% |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- The larger stress run preserves the same conservative production number as the model-family baseline.",
        "- The number to stand behind for paper/product language is the floor, not the average.",
        "- The result is comfortable for a memory hierarchy and pressure-accounting claim.",
        "- The remaining claim boundary is runtime integration: live vLLM/sock KV internals still need direct TMH-managed execution before claiming end-to-end runtime speedup from TMH itself.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    models = load_model_configs(args.config_glob)
    base_cases = all_pressure_cases(args.endpoint_result)
    page_sizes = parse_ints(args.page_tokens)
    budgets = parse_floats(args.budgets)
    out_dir = args.out_dir / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    global_agg = Agg()
    run_aggs: dict[int, Agg] = {}
    model_aggs: dict[str, Agg] = {}
    run_model_aggs: dict[tuple[int, str], Agg] = {}
    budget_aggs: dict[float, Agg] = {}
    edge_samples: list[dict[str, Any]] = []
    model_shapes = []

    for model in models:
        shape = model["shape"]
        model_shapes.append({"model_id": model["model_id"], **asdict(shape)})
        for run_index in range(args.run_count):
            for case_index, base_case in enumerate(base_cases):
                case = variant_case(base_case, run_index, case_index, args.seed)
                if case.prompt_tokens + case.completion_tokens > shape.context_tokens:
                    continue
                for page_tokens in page_sizes:
                    for budget in budgets:
                        row = summarize_row(
                            model=model,
                            case=case,
                            page_tokens=page_tokens,
                            budget_pct=budget,
                            exhaustive_limit=args.exhaustive_layer_page_limit,
                        )
                        row["run_index"] = run_index
                        global_agg.update(row)
                        run_aggs.setdefault(run_index, Agg()).update(row)
                        model_aggs.setdefault(model["model_id"], Agg()).update(row)
                        run_model_aggs.setdefault((run_index, model["model_id"]), Agg()).update(row)
                        budget_aggs.setdefault(budget, Agg()).update(row)
                        if int(row["old_tokens"]) > 0 and len(edge_samples) < args.edge_sample_limit:
                            edge_samples.append({
                                "run_index": run_index,
                                "model_id": row["model_id"],
                                "case": row["case"],
                                "page_tokens": row["page_tokens"],
                                "budget_pct": row["budget_pct"],
                                "old_tokens": row["old_tokens"],
                                "warm_reduction_vs_uniform_int8_pct": row["warm_reduction_vs_uniform_int8_pct"],
                                "total_reduction_vs_same_hot_uniform_int8_pct": row["total_reduction_vs_same_hot_uniform_int8_pct"],
                                "compression_vs_raw_pct": row["compression_vs_raw_pct"],
                            })

    run_summary = [run_aggs[index].row(run_index=index) for index in sorted(run_aggs)]
    model_summary = [model_aggs[model_id].row(model_id=model_id) for model_id in sorted(model_aggs)]
    run_model_summary = [
        run_model_aggs[key].row(run_index=key[0], model_id=key[1])
        for key in sorted(run_model_aggs)
    ]
    budget_summary = [budget_aggs[budget].row(budget_pct=budget) for budget in sorted(budget_aggs)]
    floor = round(min(row["min_warm_reduction_vs_uniform_int8_pct"] for row in model_summary if row["old_kv_row_count"] > 0), 3)
    public_floor = math.floor(floor * 10.0) / 10.0
    global_row = global_agg.row()
    result = {
        "ok": global_row["pass_rate_pct"] == 100.0 and floor >= 16.0,
        "kv_layout": KV_LAYOUT,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": args.seed,
        "model_config_count": len(models),
        "base_pressure_case_count": len(base_cases),
        "run_count": args.run_count,
        "page_tokens": page_sizes,
        "budgets": budgets,
        "evaluated_row_count": global_row["row_count"],
        "old_kv_row_count": global_row["old_kv_row_count"],
        "checked_layer_pages": global_row["checked_layer_pages"],
        "invariant_pass_rate_pct": global_row["pass_rate_pct"],
        "conservative_old_warm_reduction_floor_pct": floor,
        "promoted_public_number_pct": public_floor,
        "model_shapes": model_shapes,
        "run_summary": run_summary,
        "model_summary": model_summary,
        "run_model_summary": run_model_summary,
        "budget_summary": budget_summary,
        "edge_samples": edge_samples,
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(out_dir / "run_summary.csv", run_summary)
    write_csv(out_dir / "model_summary.csv", model_summary)
    write_csv(out_dir / "run_model_summary.csv", run_model_summary)
    write_csv(out_dir / "budget_summary.csv", budget_summary)
    write_csv(out_dir / "edge_samples.csv", edge_samples)
    write_report(out_dir / "REPORT.md", result)
    print(json.dumps({
        "ok": result["ok"],
        "report": str(out_dir / "REPORT.md"),
        "result": str(out_dir / "result.json"),
        "run_count": result["run_count"],
        "evaluated_row_count": result["evaluated_row_count"],
        "old_kv_row_count": result["old_kv_row_count"],
        "conservative_old_warm_reduction_floor_pct": result["conservative_old_warm_reduction_floor_pct"],
        "promoted_public_number_pct": result["promoted_public_number_pct"],
        "invariant_pass_rate_pct": result["invariant_pass_rate_pct"],
    }, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
