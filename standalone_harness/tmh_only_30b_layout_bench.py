#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_ENDPOINT_RESULT = Path("artifacts/sock_endpoint_pressure/20260719-023427/result.json")
DEFAULT_MODEL_CONFIG = Path(
    "/home/deepsaint/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B-GPTQ-Int4/"
    "snapshots/9b534e4318b7ebc3c961a839f13eb18b1833f441/config.json"
)
DEFAULT_BUDGETS = "50,25,12.5,6.25,0"
KV_LAYOUT = "tmh_fidelity_paged_kv"
PLAN_AUTHORITY = "hard"

@dataclass(frozen=True)
class ModelShape:
    model_type: str
    layer_count: int
    attention_heads: int
    kv_heads: int
    head_dim: int
    hidden_size: int
    context_tokens: int
    late_layer_start: int
    raw_dtype_bytes: float

@dataclass(frozen=True)
class PageRangePlan:
    layer_start: int
    layer_end: int
    page_start: int
    page_end: int
    semantic_class: str
    pin: int
    k_precision_name: str
    v_precision_name: str
    residency_tier: str
    promotion_priority: int
    demotion_priority: int
    recompute_priority: int
    authority: str

    def matches(self, layer_id: int, page_id: int) -> bool:
        return self.layer_start <= layer_id <= self.layer_end and self.page_start <= page_id <= self.page_end

@dataclass(frozen=True)
class CompiledTMHPlan:
    kv_layout: str
    prompt_pages: int
    recent_start_page: int
    used_pages: int
    ranges: list[PageRangePlan]

@dataclass(frozen=True)
class PlanValidation:
    ok: bool
    checked_layer_pages: int
    shadowed_layer_page_matches: int
    failures: list[str]

@dataclass(frozen=True)
class LayoutSummary:
    case: str
    category: str
    budget_pct: float
    prompt_tokens: int
    measured_completion_tokens: int
    total_tokens: int
    page_tokens: int
    total_pages: int
    hot_pages: int
    pinned_pages: int
    warm_pages: int
    cold_pages: int
    raw_k_pages: int
    raw_v_pages: int
    int8_k_pages: int
    int8_v_pages: int
    int4_v_pages: int
    raw_equivalent_bytes: int
    hot_bytes: int
    warm_bytes: int
    cold_bytes: int
    effective_bytes: int
    effective_bytes_per_token: float
    compression_vs_raw_pct: float
    endpoint_completion_tok_s_c1: float
    endpoint_completion_tok_s_c2: float
    endpoint_ttft_s: float | None
    contains_target_c1_pct: float
    contains_target_c2_pct: float
    plan_range_count: int
    resolved_layer_pages: int
    shadowed_layer_page_matches: int
    plan_validation_ok: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TMH-only 30B layout benchmark using a real sock endpoint run as traffic input.")
    parser.add_argument("--endpoint-result", type=Path, default=DEFAULT_ENDPOINT_RESULT)
    parser.add_argument("--model-config", type=Path, default=DEFAULT_MODEL_CONFIG)
    parser.add_argument("--page-tokens", type=int, default=16)
    parser.add_argument("--budgets", default=DEFAULT_BUDGETS)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/tmh_only_30b_layout"))
    return parser.parse_args()


def parse_budgets(raw: str) -> list[float]:
    return [float(item.strip()) for item in raw.split(",") if item.strip()]


def load_shape(config_path: Path) -> ModelShape:
    cfg = json.loads(config_path.read_text())
    hidden_size = int(cfg["hidden_size"])
    attention_heads = int(cfg["num_attention_heads"])
    kv_heads = int(cfg.get("num_key_value_heads", attention_heads))
    head_dim = int(cfg.get("head_dim", hidden_size // attention_heads))
    layer_count = int(cfg["num_hidden_layers"])
    context_tokens = int(cfg.get("max_position_embeddings", 0))
    # TMH protects the final third by default; this matches the native runtime convention.
    late_layer_start = max(0, (layer_count * 2) // 3)
    dtype = str(cfg.get("torch_dtype", "bfloat16")).lower()
    raw_dtype_bytes = 4.0 if dtype in {"float32", "fp32"} else 2.0
    return ModelShape(
        model_type=str(cfg.get("model_type", "unknown")),
        layer_count=layer_count,
        attention_heads=attention_heads,
        kv_heads=kv_heads,
        head_dim=head_dim,
        hidden_size=hidden_size,
        context_tokens=context_tokens,
        late_layer_start=late_layer_start,
        raw_dtype_bytes=raw_dtype_bytes,
    )


def page_count(tokens: int, page_tokens: int) -> int:
    return max(1, math.ceil(max(1, tokens) / page_tokens))


def bytes_for(shape: ModelShape, tokens: int, precision: str) -> int:
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


def page_token_count(page_id: int, total_tokens: int, page_tokens: int) -> int:
    start = page_id * page_tokens
    end = min(total_tokens, start + page_tokens)
    return max(0, end - start)


def case_completion_tokens(case: dict[str, Any]) -> int:
    reqs = case["batches_by_concurrency"]["1"][0]["requests"]
    return int(round(statistics.fmean([int(req["completion_tokens"]) for req in reqs])))


def stream_ttft(stream_probes: list[dict[str, Any]], case_name: str) -> float | None:
    for probe in stream_probes:
        if probe.get("case") == case_name:
            value = probe.get("ttft_s")
            return None if value is None else float(value)
    return None


def compile_tmh_plan(shape: ModelShape, used_pages: int, prompt_pages: int, hot_pages: int) -> CompiledTMHPlan:
    recent_start_page = used_pages if hot_pages <= 0 else max(0, used_pages - hot_pages)
    ranges: list[PageRangePlan] = [
        PageRangePlan(
            layer_start=0,
            layer_end=shape.layer_count - 1,
            page_start=0,
            page_end=0,
            semantic_class="prompt_anchor",
            pin=1,
            k_precision_name="raw",
            v_precision_name="raw",
            residency_tier="pinned",
            promotion_priority=100,
            demotion_priority=0,
            recompute_priority=0,
            authority=PLAN_AUTHORITY,
        )
    ]
    if recent_start_page < used_pages:
        ranges.append(
            PageRangePlan(
                layer_start=0,
                layer_end=shape.layer_count - 1,
                page_start=recent_start_page,
                page_end=used_pages - 1,
                semantic_class="recent_tail",
                pin=0,
                k_precision_name="raw",
                v_precision_name="raw",
                residency_tier="hot",
                promotion_priority=100,
                demotion_priority=0,
                recompute_priority=0,
                authority=PLAN_AUTHORITY,
            )
        )
    old_start_page = 1 if prompt_pages > 0 else 0
    old_end_page = recent_start_page - 1
    if old_start_page <= old_end_page and shape.late_layer_start > 0:
        ranges.append(
            PageRangePlan(
                layer_start=0,
                layer_end=shape.late_layer_start - 1,
                page_start=old_start_page,
                page_end=old_end_page,
                semantic_class="prefill_payload",
                pin=0,
                k_precision_name="int8",
                v_precision_name="int4",
                residency_tier="warm",
                promotion_priority=25,
                demotion_priority=75,
                recompute_priority=50,
                authority=PLAN_AUTHORITY,
            )
        )
    if old_start_page <= old_end_page and shape.late_layer_start < shape.layer_count:
        ranges.append(
            PageRangePlan(
                layer_start=shape.late_layer_start,
                layer_end=shape.layer_count - 1,
                page_start=old_start_page,
                page_end=old_end_page,
                semantic_class="late_layer_payload",
                pin=0,
                k_precision_name="int8",
                v_precision_name="int8",
                residency_tier="warm",
                promotion_priority=35,
                demotion_priority=65,
                recompute_priority=50,
                authority=PLAN_AUTHORITY,
            )
        )
    return CompiledTMHPlan(
        kv_layout=KV_LAYOUT,
        prompt_pages=prompt_pages,
        recent_start_page=recent_start_page,
        used_pages=used_pages,
        ranges=ranges,
    )


def matching_ranges(plan: CompiledTMHPlan, layer_id: int, page_id: int) -> list[PageRangePlan]:
    return [range_plan for range_plan in plan.ranges if range_plan.matches(layer_id, page_id)]


def resolve_range(plan: CompiledTMHPlan, layer_id: int, page_id: int) -> PageRangePlan:
    matches = matching_ranges(plan, layer_id, page_id)
    if not matches:
        raise ValueError(f"TMH plan leaves layer={layer_id} page={page_id} uncovered")
    return matches[0]


def validate_plan(shape: ModelShape, plan: CompiledTMHPlan) -> PlanValidation:
    failures: list[str] = []
    shadowed = 0
    for page_id in range(plan.used_pages):
        for layer_id in range(shape.layer_count):
            matches = matching_ranges(plan, layer_id, page_id)
            if not matches:
                failures.append(f"uncovered layer={layer_id} page={page_id}")
                continue
            if len(matches) > 1:
                shadowed += len(matches) - 1
            resolved = matches[0]
            if resolved.authority != PLAN_AUTHORITY:
                failures.append(f"non-hard authority layer={layer_id} page={page_id}: {resolved.authority}")
            if resolved.k_precision_name == "dropped" or resolved.v_precision_name == "dropped":
                failures.append(f"dropped precision layer={layer_id} page={page_id}")
            if resolved.residency_tier == "cold":
                failures.append(f"cold residency layer={layer_id} page={page_id}")
            if page_id == 0 and resolved.semantic_class != "prompt_anchor":
                failures.append(f"page 0 did not resolve to prompt_anchor at layer={layer_id}")
            if page_id >= plan.recent_start_page and page_id != 0 and resolved.semantic_class != "recent_tail":
                failures.append(f"recent tail page did not resolve hot layer={layer_id} page={page_id}")
            if 0 < page_id < plan.recent_start_page and layer_id < shape.late_layer_start:
                if (resolved.k_precision_name, resolved.v_precision_name, resolved.residency_tier) != ("int8", "int4", "warm"):
                    failures.append(f"early old page mismatch layer={layer_id} page={page_id}")
            if 0 < page_id < plan.recent_start_page and layer_id >= shape.late_layer_start:
                if (resolved.k_precision_name, resolved.v_precision_name, resolved.residency_tier) != ("int8", "int8", "warm"):
                    failures.append(f"late old page mismatch layer={layer_id} page={page_id}")
    checked = plan.used_pages * shape.layer_count
    return PlanValidation(ok=not failures, checked_layer_pages=checked, shadowed_layer_page_matches=shadowed, failures=failures[:100])


def summarize_case(endpoint: dict[str, Any], shape: ModelShape, case: dict[str, Any], budget: float, page_tokens: int) -> LayoutSummary:
    prompt_tokens = int(next(row["prompt_tokens"] for row in endpoint["preflight"] if row["case"] == case["name"]))
    completion_tokens = case_completion_tokens(case)
    total_tokens = prompt_tokens + completion_tokens
    pages = page_count(total_tokens, page_tokens)
    prompt_pages = page_count(prompt_tokens, page_tokens)
    hot_pages = 0 if budget <= 0 else min(pages, math.ceil(pages * budget / 100.0))
    plan = compile_tmh_plan(shape, pages, prompt_pages, hot_pages)
    validation = validate_plan(shape, plan)
    if not validation.ok:
        raise ValueError(f"invalid TMH plan for case={case['name']} budget={budget}: {validation.failures[:5]}")

    hot_bytes = 0
    warm_bytes = 0
    raw_equivalent_bytes = 0
    raw_k_pages = raw_v_pages = int8_k_pages = int8_v_pages = int4_v_pages = 0
    pinned_page_ids: set[int] = set()
    hot_page_ids: set[int] = set()
    warm_page_ids: set[int] = set()
    cold_page_ids: set[int] = set()
    for page_id in range(pages):
        tokens = page_token_count(page_id, total_tokens, page_tokens)
        for layer_id in range(shape.layer_count):
            resolved = resolve_range(plan, layer_id, page_id)
            raw_equivalent_bytes += bytes_for(shape, tokens, "raw") * 2
            k_bytes = bytes_for(shape, tokens, resolved.k_precision_name)
            v_bytes = bytes_for(shape, tokens, resolved.v_precision_name)
            if resolved.residency_tier == "pinned":
                pinned_page_ids.add(page_id)
                hot_bytes += k_bytes + v_bytes
            elif resolved.residency_tier == "hot":
                hot_page_ids.add(page_id)
                hot_bytes += k_bytes + v_bytes
            elif resolved.residency_tier == "warm":
                warm_page_ids.add(page_id)
                warm_bytes += k_bytes + v_bytes
            else:
                cold_page_ids.add(page_id)
            if resolved.k_precision_name == "raw":
                raw_k_pages += 1
            elif resolved.k_precision_name == "int8":
                int8_k_pages += 1
            if resolved.v_precision_name == "raw":
                raw_v_pages += 1
            elif resolved.v_precision_name == "int8":
                int8_v_pages += 1
            elif resolved.v_precision_name == "int4":
                int4_v_pages += 1
    effective_bytes = hot_bytes + warm_bytes
    compression = 0.0 if raw_equivalent_bytes <= 0 else 100.0 * (1.0 - (effective_bytes / raw_equivalent_bytes))
    c1 = case["summary_by_concurrency"]["1"]
    c2 = case["summary_by_concurrency"].get("2", c1)
    return LayoutSummary(
        case=case["name"],
        category=case["category"],
        budget_pct=budget,
        prompt_tokens=prompt_tokens,
        measured_completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        page_tokens=page_tokens,
        total_pages=pages,
        hot_pages=len(hot_page_ids),
        pinned_pages=len(pinned_page_ids),
        warm_pages=len(warm_page_ids),
        cold_pages=len(cold_page_ids),
        raw_k_pages=raw_k_pages,
        raw_v_pages=raw_v_pages,
        int8_k_pages=int8_k_pages,
        int8_v_pages=int8_v_pages,
        int4_v_pages=int4_v_pages,
        raw_equivalent_bytes=raw_equivalent_bytes,
        hot_bytes=hot_bytes,
        warm_bytes=warm_bytes,
        cold_bytes=0,
        effective_bytes=effective_bytes,
        effective_bytes_per_token=round(effective_bytes / max(1, total_tokens), 3),
        compression_vs_raw_pct=round(compression, 3),
        endpoint_completion_tok_s_c1=float(c1["aggregate_completion_tok_per_s"]["mean"]),
        endpoint_completion_tok_s_c2=float(c2["aggregate_completion_tok_per_s"]["mean"]),
        endpoint_ttft_s=stream_ttft(endpoint.get("stream_probes", []), case["name"]),
        contains_target_c1_pct=float(c1["contains_target_rate_pct"]["mean"]),
        contains_target_c2_pct=float(c2["contains_target_rate_pct"]["mean"]),
        plan_range_count=len(plan.ranges),
        resolved_layer_pages=validation.checked_layer_pages,
        shadowed_layer_page_matches=validation.shadowed_layer_page_matches,
        plan_validation_ok=validation.ok,
    )


def plan_records(endpoint: dict[str, Any], shape: ModelShape, budgets: list[float], page_tokens: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    preflight = {row["case"]: int(row["prompt_tokens"]) for row in endpoint["preflight"]}
    for budget in budgets:
        for case in endpoint["cases"]:
            prompt_tokens = preflight[case["name"]]
            completion_tokens = case_completion_tokens(case)
            total_tokens = prompt_tokens + completion_tokens
            pages = page_count(total_tokens, page_tokens)
            hot_pages = 0 if budget <= 0 else min(pages, math.ceil(pages * budget / 100.0))
            plan = compile_tmh_plan(shape, pages, page_count(prompt_tokens, page_tokens), hot_pages)
            validation = validate_plan(shape, plan)
            for ordinal, range_plan in enumerate(plan.ranges):
                record = asdict(range_plan)
                record.update(
                    {
                        "case": case["name"],
                        "budget_pct": budget,
                        "kv_layout": KV_LAYOUT,
                        "range_ordinal": ordinal,
                        "used_pages": plan.used_pages,
                        "prompt_pages": plan.prompt_pages,
                        "recent_start_page": plan.recent_start_page,
                        "plan_validation_ok": validation.ok,
                        "shadowed_layer_page_matches": validation.shadowed_layer_page_matches,
                    }
                )
                records.append(record)
    return records


def write_csv(path: Path, rows: list[LayoutSummary]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_dict_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def invariant_summary(rows: list[LayoutSummary]) -> dict[str, Any]:
    return {
        "validation_pass_rate_pct": round(100.0 * statistics.fmean(1.0 if row.plan_validation_ok else 0.0 for row in rows), 3),
        "checked_layer_pages": sum(row.resolved_layer_pages for row in rows),
        "cases_with_failures": sum(1 for row in rows if not row.plan_validation_ok),
        "total_shadowed_layer_page_matches": sum(row.shadowed_layer_page_matches for row in rows),
        "cold_bytes_total": sum(row.cold_bytes for row in rows),
        "dropped_k_pages_total": 0,
        "dropped_v_pages_total": 0,
        "layout_count": 1,
        "kv_layout": KV_LAYOUT,
    }


def aggregate(rows: list[LayoutSummary], budget: float) -> dict[str, Any]:
    selected = [row for row in rows if row.budget_pct == budget]
    return {
        "budget_pct": budget,
        "case_count": len(selected),
        "mean_effective_bytes_per_token": round(statistics.fmean(row.effective_bytes_per_token for row in selected), 3),
        "mean_compression_vs_raw_pct": round(statistics.fmean(row.compression_vs_raw_pct for row in selected), 3),
        "mean_hot_bytes": round(statistics.fmean(row.hot_bytes for row in selected), 3),
        "mean_warm_bytes": round(statistics.fmean(row.warm_bytes for row in selected), 3),
        "mean_endpoint_completion_tok_s_c1": round(statistics.fmean(row.endpoint_completion_tok_s_c1 for row in selected), 3),
        "mean_endpoint_completion_tok_s_c2": round(statistics.fmean(row.endpoint_completion_tok_s_c2 for row in selected), 3),
        "mean_ttft_s": round(statistics.fmean(row.endpoint_ttft_s for row in selected if row.endpoint_ttft_s is not None), 4),
        "mean_contains_target_c1_pct": round(statistics.fmean(row.contains_target_c1_pct for row in selected), 3),
        "mean_contains_target_c2_pct": round(statistics.fmean(row.contains_target_c2_pct for row in selected), 3),
        "plan_validation_pass_rate_pct": round(100.0 * statistics.fmean(1.0 if row.plan_validation_ok else 0.0 for row in selected), 3),
        "mean_shadowed_layer_page_matches": round(statistics.fmean(row.shadowed_layer_page_matches for row in selected), 3),
    }


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# TMH-Only 30B Layout Benchmark",
        "",
        "This standalone report benchmarks one KV layout only: `tmh_fidelity_paged_kv`.",
        "It does not compare legacy layouts and does not mutate TMH production source.",
        "",
        f"- model: `{result['endpoint']['model']}`",
        f"- sock endpoint result: `{result['endpoint_result']}`",
        f"- kv_layout: `{result['kv_layout']}`",
        f"- page_tokens: `{result['page_tokens']}`",
        f"- generated_at: `{result['generated_at']}`",
        f"- plan_ranges: `{result['plan_ranges_csv']}`",
        f"- invariant_report: `{result['invariant_report_json']}`",
        "",
        "## Model Shape",
        "",
        "| field | value |",
        "| --- | ---: |",
    ]
    shape = result["model_shape"]
    for key in ["layer_count", "attention_heads", "kv_heads", "head_dim", "hidden_size", "context_tokens", "late_layer_start", "raw_dtype_bytes"]:
        lines.append(f"| `{key}` | `{shape[key]}` |")
    lines += [
        "",
        "## Budget Summary",
        "",
        "| budget | cases | mean effective bytes/token | mean compression vs raw | mean c1 tok/s | mean c2 tok/s | mean TTFT s | contains c1 | plan pass |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["budget_summary"]:
        lines.append(
            f"| {row['budget_pct']} | {row['case_count']} | {row['mean_effective_bytes_per_token']} | "
            f"{row['mean_compression_vs_raw_pct']}% | {row['mean_endpoint_completion_tok_s_c1']} | "
            f"{row['mean_endpoint_completion_tok_s_c2']} | {row['mean_ttft_s']} | {row['mean_contains_target_c1_pct']}% | "
            f"{row['plan_validation_pass_rate_pct']}% |"
        )
    invariants = result["invariants"]
    lines += [
        "",
        "## Plan Invariants",
        "",
        "| invariant | value |",
        "| --- | ---: |",
        f"| validation_pass_rate_pct | `{invariants['validation_pass_rate_pct']}` |",
        f"| checked_layer_pages | `{invariants['checked_layer_pages']}` |",
        f"| cases_with_failures | `{invariants['cases_with_failures']}` |",
        f"| total_shadowed_layer_page_matches | `{invariants['total_shadowed_layer_page_matches']}` |",
        f"| cold_bytes_total | `{invariants['cold_bytes_total']}` |",
        f"| dropped_k_pages_total | `{invariants['dropped_k_pages_total']}` |",
        f"| dropped_v_pages_total | `{invariants['dropped_v_pages_total']}` |",
        f"| layout_count | `{invariants['layout_count']}` |",
    ]
    lines += [
        "",
        "## Case Detail At 25% Hot Budget",
        "",
        "| case | total tokens | pages | hot | pinned | warm | ranges | effective bytes/token | compression vs raw | c1 tok/s | c2 tok/s | contains c1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["rows"]:
        if row["budget_pct"] == 25.0:
            lines.append(
                f"| `{row['case']}` | {row['total_tokens']} | {row['total_pages']} | {row['hot_pages']} | {row['pinned_pages']} | "
                f"{row['warm_pages']} | {row['plan_range_count']} | {row['effective_bytes_per_token']} | {row['compression_vs_raw_pct']}% | "
                f"{row['endpoint_completion_tok_s_c1']} | {row['endpoint_completion_tok_s_c2']} | {row['contains_target_c1_pct']}% |"
            )
    lines += [
        "",
        "## Interpretation",
        "",
        "- This is the TMH layout ledger for the real 30B sock traffic profile, not a legacy policy matrix.",
        "- The harness compiles a page-native TMH plan before computing memory pressure, matching the source-level `TMHMemoryPlan` shape.",
        "- Plan ranges are resolved in native order: prompt anchor first, recent tail second, old history after that.",
        "- `cold_bytes` remains zero by design: TMH demotes old KV fidelity instead of evicting it.",
        "- The prompt anchor is pinned raw with hard authority.",
        "- Earlier and middle-layer old values use int4; late-layer old values stay int8; all old keys stay int8.",
        "- Endpoint tok/s and TTFT are copied from the live sock 30B run so layout pressure and serving behavior stay tied to the same traffic corpus.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    budgets = parse_budgets(args.budgets)
    endpoint = json.loads(args.endpoint_result.read_text())
    shape = load_shape(args.model_config)
    rows = [
        summarize_case(endpoint, shape, case, budget, args.page_tokens)
        for budget in budgets
        for case in endpoint["cases"]
    ]
    plans = plan_records(endpoint, shape, budgets, args.page_tokens)
    invariants = invariant_summary(rows)
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = generated_at.replace(":", "").replace("-", "").replace("T", "-").removesuffix("Z")
    out_dir = args.out_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "result.json"
    csv_path = out_dir / "summary.csv"
    plan_json_path = out_dir / "plan_ranges.json"
    plan_csv_path = out_dir / "plan_ranges.csv"
    invariant_path = out_dir / "invariants.json"
    report_path = out_dir / "REPORT.md"
    result = {
        "ok": True,
        "kv_layout": KV_LAYOUT,
        "endpoint_result": str(args.endpoint_result),
        "model_config": str(args.model_config),
        "endpoint": {k: endpoint[k] for k in ["model", "base_url", "profile", "generated_at", "elapsed_s"] if k in endpoint},
        "model_shape": asdict(shape),
        "page_tokens": args.page_tokens,
        "budgets": budgets,
        "generated_at": generated_at,
        "plan_ranges_json": str(plan_json_path),
        "plan_ranges_csv": str(plan_csv_path),
        "invariant_report_json": str(invariant_path),
        "invariants": invariants,
        "budget_summary": [aggregate(rows, budget) for budget in budgets],
        "rows": [asdict(row) for row in rows],
    }
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    plan_json_path.write_text(json.dumps(plans, indent=2, sort_keys=True), encoding="utf-8")
    invariant_path.write_text(json.dumps(invariants, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(csv_path, rows)
    write_dict_csv(plan_csv_path, plans)
    write_report(report_path, result)
    print(json.dumps({
        "ok": True,
        "json": str(json_path),
        "csv": str(csv_path),
        "plan_ranges": str(plan_csv_path),
        "invariants": str(invariant_path),
        "report": str(report_path),
        "row_count": len(rows),
        "plan_range_rows": len(plans),
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
