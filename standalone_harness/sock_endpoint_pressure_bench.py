#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MODEL = "Qwen/Qwen3-30B-A3B-GPTQ-Int4"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
FILLER_FRAGMENTS = [
    "inventory ledgers", "rail manifests", "dock badges", "cabinet labels",
    "adapter notes", "weather shifts", "battery audits", "room transfers",
    "ticket stubs", "archive seals",
]

@dataclass(frozen=True)
class PressureCase:
    name: str
    category: str
    prompt: str
    target_hint: str
    max_tokens: int
    temperature: float = 0.0

def filler_passage(tag: str, theme: str, repeat: int, offset: int = 0) -> str:
    lines = []
    for idx in range(repeat):
        fragment = FILLER_FRAGMENTS[(idx + offset) % len(FILLER_FRAGMENTS)]
        lines.append(
            f"{theme} note {tag}-{idx:02d} mentions {fragment}, "
            f"timestamp lane-{(idx + offset) % 7}, review bucket r{(idx * 3 + offset) % 11}, "
            f"and routing marker gate-{(idx + 2) % 5}."
        )
    return " ".join(lines)

def build_pressure_suite(profile: str) -> list[PressureCase]:
    repeat = {"smoke": 8, "standard": 22, "maxfit": 34, "deep": 46}[profile]
    short_repeat = max(4, repeat // 2)
    long_repeat = repeat * 2
    return [
        PressureCase(
            "early_anchor_long_tail", "anchor_recall",
            "Preserve the anchor ANCHOR-ZX-48 as the controlling fact for the continuation. "
            + filler_passage("early", "archive", long_repeat, 0)
            + " Conclude by naming the controlling anchor exactly once.",
            "ANCHOR-ZX-48", 96,
        ),
        PressureCase(
            "middle_anchor_detour", "anchor_recall",
            filler_passage("mid-a", "routing", short_repeat, 2)
            + " The single retained marker is MIDDLE-KEEP-16. "
            + filler_passage("mid-b", "invoice", repeat, 4)
            + " Continue while keeping the retained marker stable.",
            "MIDDLE-KEEP-16", 128,
        ),
        PressureCase(
            "late_anchor_control", "late_control",
            filler_passage("late", "control", repeat, 1)
            + " Final control line: use LATE-CONTROL-77 as the active continuation marker and ignore earlier bookkeeping.",
            "LATE-CONTROL-77", 96,
        ),
        PressureCase(
            "decoy_collision", "confusable_recall",
            "Do not confuse ROUTE-SPECIAL-OMEGA with nearby decoys ROUTE-SPECIAL-OMICRON or ROUTE-SPECIAL-ORBIT. "
            + filler_passage("decoy", "routing", repeat, 3)
            + " The exact retained code remains ROUTE-SPECIAL-OMEGA despite the decoys. State the exact retained code.",
            "ROUTE-SPECIAL-OMEGA", 128,
        ),
        PressureCase(
            "routing_table", "structured_lookup",
            "Consult the routing table carefully. route-a maps to payload-hold with checksum ck-14. "
            "route-b maps to payload-defer with checksum ck-22. route-special maps to payload-kept with checksum ck-91. "
            + filler_passage("route", "manifest", repeat, 5)
            + " The continuation should preserve the selected route payload for route-special.",
            "payload-kept", 128,
        ),
        PressureCase(
            "structured_records", "structured_lookup",
            "Keep the focus record available. record analyst-0: owner Mira Chen; badge RC-70; zone Kyoto; revision rv-3. "
            "record analyst-1: owner Toma Vale; badge RC-71; zone Berlin; revision rv-4. "
            + filler_passage("records", "cabinet", repeat, 6)
            + " The focus record belongs to analyst-0. Report owner, badge, and zone.",
            "Mira Chen RC-70 Kyoto", 160,
        ),
        PressureCase(
            "instruction_persistence", "instruction_retention",
            "Answer in a compact style and keep the phrase 'answer compactly with the stable phrase ember-lake' stable. "
            + filler_passage("policy", "operator", long_repeat, 7)
            + " Redundant policy notes may appear, but the stable phrase remains the same.",
            "ember-lake", 128,
        ),
        PressureCase(
            "multi_hop_bridge", "multi_hop",
            "The artist lives in Kyoto. The artist exhibits at Gallery-7. "
            + filler_passage("bridge", "museum", repeat, 8)
            + " If the artist lives in Kyoto and Gallery-7 hosts the artist, keep both linked facts available.",
            "Kyoto Gallery-7", 160,
        ),
        PressureCase(
            "payload_dense", "dense_noise",
            "Retain the payload term verdict-archive. "
            + filler_passage("payload", "payload", long_repeat, 9)
            + " The continuation should keep the payload term visible while explaining why dense noise makes KV pressure harder.",
            "verdict-archive", 192,
        ),
        PressureCase(
            "long_generation_systems", "long_generation",
            "Write a production engineering analysis of tiered memory hierarchy under ROCm serving pressure. "
            "Discuss prompt prefill, KV residency, hot/warm/cold tiers, quantized old KV, fidelity-aware demotion, "
            "prefix reuse, batching, TTFT, decode throughput, and what evidence would falsify the thesis. "
            + filler_passage("systems", "systems", short_repeat, 1),
            "tiered memory hierarchy", 384, 0.2,
        ),
    ]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Standalone sock endpoint pressure harness for TMH 30B-class experiments.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--label", default="sock-qwen3-30b-a3b-gptq-int4")
    parser.add_argument("--profile", choices=["smoke", "standard", "maxfit", "deep"], default="standard")
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/sock_endpoint_pressure"))
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument("--concurrency-levels", default="1,2,4")
    parser.add_argument("--timeout-s", type=int, default=900)
    parser.add_argument("--case", action="append", help="Run only a named case. Can be repeated.")
    parser.add_argument("--stream-probe", action="store_true", help="Also measure streaming TTFT once per selected case.")
    parser.add_argument("--max-model-len", type=int, default=0, help="Generation cap. 0 uses /tokenize max_model_len.")
    parser.add_argument("--token-budget-margin", type=int, default=4, help="Reserved tokens below max_model_len.")
    parser.add_argument("--min-new-tokens", type=int, default=16, help="Fail preflight if a prompt leaves less than this many generation tokens.")
    parser.add_argument("--dry-run", action="store_true", help="Only run token preflight and write the report; do not issue completions.")
    return parser.parse_args()

def post_json(url: str, payload: dict[str, Any], timeout_s: int) -> dict[str, Any]:
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {url}: {detail}") from error

def stream_completion(url: str, payload: dict[str, Any], timeout_s: int) -> dict[str, Any]:
    stream_payload = dict(payload)
    stream_payload["stream"] = True
    stream_payload["stream_options"] = {"include_usage": True}
    request = urllib.request.Request(url, data=json.dumps(stream_payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    first_chunk_s = None
    chunks = []
    usage: dict[str, Any] = {}
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    break
                event = json.loads(data)
                if event.get("usage"):
                    usage = event["usage"]
                choice = (event.get("choices") or [{}])[0]
                text = choice.get("text") or ""
                if text and first_chunk_s is None:
                    first_chunk_s = time.perf_counter() - started
                chunks.append(text)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {url}: {detail}") from error
    elapsed_s = time.perf_counter() - started
    completion_tokens = int(usage.get("completion_tokens") or 0)
    return {
        "elapsed_s": round(elapsed_s, 4),
        "ttft_s": round(first_chunk_s, 4) if first_chunk_s is not None else None,
        "completion_tokens": completion_tokens,
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "completion_tok_per_s": round(completion_tokens / elapsed_s, 4) if completion_tokens and elapsed_s > 0 else None,
        "response_text": "".join(chunks),
    }


def tokenize_prompt(base_url: str, model: str, prompt: str, timeout_s: int) -> dict[str, int]:
    response = post_json(
        base_url.rstrip("/") + "/tokenize",
        {"model": model, "prompt": prompt},
        timeout_s,
    )
    return {
        "prompt_tokens": int(response.get("count") or 0),
        "max_model_len": int(response.get("max_model_len") or 0),
    }

def fit_suite_to_model_len(
    *,
    base_url: str,
    model: str,
    suite: list[PressureCase],
    requested_max_model_len: int,
    token_budget_margin: int,
    min_new_tokens: int,
    timeout_s: int,
) -> tuple[list[PressureCase], list[dict[str, Any]]]:
    fitted = []
    preflight = []
    observed_max_model_len = requested_max_model_len
    for case in suite:
        tokenized = tokenize_prompt(base_url, model, case.prompt, timeout_s)
        endpoint_max_model_len = tokenized["max_model_len"]
        if observed_max_model_len <= 0:
            observed_max_model_len = endpoint_max_model_len
        max_model_len = requested_max_model_len if requested_max_model_len > 0 else endpoint_max_model_len
        available_new_tokens = max_model_len - tokenized["prompt_tokens"] - token_budget_margin
        if available_new_tokens < min_new_tokens:
            raise ValueError(
                f"case {case.name} prompt_tokens={tokenized['prompt_tokens']} leaves "
                f"only {available_new_tokens} generation tokens under max_model_len={max_model_len}"
            )
        effective_max_tokens = min(case.max_tokens, available_new_tokens)
        fitted_case = PressureCase(
            case.name,
            case.category,
            case.prompt,
            case.target_hint,
            effective_max_tokens,
            case.temperature,
        )
        fitted.append(fitted_case)
        preflight.append({
            "case": case.name,
            "category": case.category,
            "prompt_tokens": tokenized["prompt_tokens"],
            "endpoint_max_model_len": endpoint_max_model_len,
            "requested_max_model_len": requested_max_model_len,
            "effective_max_model_len": max_model_len,
            "original_max_tokens": case.max_tokens,
            "effective_max_tokens": effective_max_tokens,
            "token_budget_margin": token_budget_margin,
        })
    return fitted, preflight

def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((pct / 100.0) * (len(ordered) - 1))))
    return ordered[idx]

def summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0, "p90": 0.0, "p95": 0.0}
    return {
        "min": round(min(values), 4), "max": round(max(values), 4),
        "mean": round(statistics.fmean(values), 4), "median": round(statistics.median(values), 4),
        "p90": round(percentile(values, 90), 4), "p95": round(percentile(values, 95), 4),
    }

def score_contains(text: str, target_hint: str) -> bool:
    text_norm = " ".join(text.lower().split())
    targets = [part.strip().lower() for part in target_hint.split() if part.strip()]
    return bool(targets) and all(target in text_norm for target in targets)

def run_one(url: str, model: str, case: PressureCase, timeout_s: int, run_index: int, request_index: int) -> dict[str, Any]:
    payload = {"model": model, "prompt": case.prompt, "max_tokens": case.max_tokens, "temperature": case.temperature}
    started = time.perf_counter()
    response = post_json(url, payload, timeout_s)
    elapsed_s = time.perf_counter() - started
    choice = (response.get("choices") or [{}])[0]
    usage = response.get("usage") or {}
    text = choice.get("text") or ""
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or 0)
    return {
        "run_index": run_index, "request_index": request_index, "elapsed_s": round(elapsed_s, 4),
        "prompt_tokens": int(usage.get("prompt_tokens") or 0), "completion_tokens": completion_tokens, "total_tokens": total_tokens,
        "completion_tok_per_s": round(completion_tokens / elapsed_s, 4) if elapsed_s > 0 else 0.0,
        "total_tok_per_s": round(total_tokens / elapsed_s, 4) if elapsed_s > 0 else 0.0,
        "finish_reason": choice.get("finish_reason"), "contains_target": score_contains(text, case.target_hint),
        "response_text": text, "raw_response": response,
    }

def run_batch(url: str, model: str, case: PressureCase, timeout_s: int, run_index: int, concurrency: int) -> dict[str, Any]:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(run_one, url, model, case, timeout_s, run_index, request_index + 1) for request_index in range(concurrency)]
        requests = [future.result() for future in futures]
    wall_s = round(time.perf_counter() - started, 4)
    completion_tokens = sum(request["completion_tokens"] for request in requests)
    total_tokens = sum(request["total_tokens"] for request in requests)
    return {
        "run_index": run_index, "concurrency": concurrency, "wall_s": wall_s,
        "aggregate_completion_tok_per_s": round(completion_tokens / wall_s, 4) if wall_s > 0 else 0.0,
        "aggregate_total_tok_per_s": round(total_tokens / wall_s, 4) if wall_s > 0 else 0.0,
        "contains_target_rate_pct": round(100.0 * sum(1 for request in requests if request["contains_target"]) / len(requests), 4),
        "requests": requests,
    }

def log_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)

def summarize_batches(batches: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "wall_s": summarize([batch["wall_s"] for batch in batches]),
        "aggregate_completion_tok_per_s": summarize([batch["aggregate_completion_tok_per_s"] for batch in batches]),
        "aggregate_total_tok_per_s": summarize([batch["aggregate_total_tok_per_s"] for batch in batches]),
        "contains_target_rate_pct": summarize([batch["contains_target_rate_pct"] for batch in batches]),
    }

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# sock Endpoint Pressure Benchmark", "",
        "This is a standalone TMH pressure harness result. It does not modify or import TMH production runtime code.", "",
        f"- label: `{result['label']}`", f"- model: `{result['model']}`", f"- endpoint: `{result['base_url']}`",
        f"- profile: `{result['profile']}`", f"- generated_at: `{result['generated_at']}`", f"- elapsed_s: `{result['elapsed_s']}`", "",
        "## Token Preflight", "",
        "| case | prompt tokens | original max new | effective max new | max model len |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in result.get("preflight", []):
        lines.append(
            f"| `{row['case']}` | {row['prompt_tokens']} | {row['original_max_tokens']} | "
            f"{row['effective_max_tokens']} | {row['effective_max_model_len']} |"
        )
    lines += [
        "",
        "## Throughput", "",
        "| case | category | concurrency | completion tok/s mean | wall s mean | contains target mean |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for case in result["cases"]:
        for concurrency, summary in case["summary_by_concurrency"].items():
            lines.append(
                f"| `{case['name']}` | `{case['category']}` | {concurrency} | "
                f"{summary['aggregate_completion_tok_per_s']['mean']} | {summary['wall_s']['mean']} | {summary['contains_target_rate_pct']['mean']} |"
            )
    if result.get("stream_probes"):
        lines += ["", "## Streaming TTFT Probes", "", "| case | ttft s | elapsed s | completion tok/s |", "| --- | ---: | ---: | ---: |"]
        for probe in result["stream_probes"]:
            lines.append(f"| `{probe['case']}` | {probe['ttft_s']} | {probe['elapsed_s']} | {probe['completion_tok_per_s']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main() -> int:
    args = parse_args()
    concurrency_levels = [int(item.strip()) for item in args.concurrency_levels.split(",") if item.strip()]
    if args.runs < 1 or args.warmup_runs < 0 or not concurrency_levels or any(level < 1 for level in concurrency_levels):
        raise ValueError("invalid run, warmup, or concurrency settings")
    suite = build_pressure_suite(args.profile)
    if args.case:
        selected = set(args.case)
        suite = [case for case in suite if case.name in selected]
        missing = selected.difference(case.name for case in suite)
        if missing:
            raise ValueError(f"unknown cases: {sorted(missing)}")
    suite, preflight = fit_suite_to_model_len(
        base_url=args.base_url,
        model=args.model,
        suite=suite,
        requested_max_model_len=args.max_model_len,
        token_budget_margin=args.token_budget_margin,
        min_new_tokens=args.min_new_tokens,
        timeout_s=args.timeout_s,
    )
    log_progress(
        f"preflight ok profile={args.profile} cases={len(suite)} "
        f"concurrency={','.join(str(level) for level in concurrency_levels)} runs={args.runs}"
    )
    url = args.base_url.rstrip("/") + "/v1/completions"
    started = time.perf_counter()
    case_results = []
    csv_rows = []
    if args.dry_run:
        generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        run_id = generated_at.replace(":", "").replace("-", "").replace("T", "-").removesuffix("Z")
        out_dir = args.out_dir / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "ok": True, "dry_run": True, "label": args.label, "model": args.model, "base_url": args.base_url,
            "profile": args.profile, "generated_at": generated_at, "elapsed_s": round(time.perf_counter() - started, 4),
            "runs": 0, "warmup_runs": 0, "concurrency_levels": concurrency_levels,
            "stream_probe_enabled": False, "preflight": preflight, "cases": [], "stream_probes": [],
        }
        json_path = out_dir / "result.json"
        md_path = out_dir / "REPORT.md"
        json_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        write_markdown(md_path, result)
        print(json.dumps({"ok": True, "dry_run": True, "json": str(json_path), "report": str(md_path), "case_count": len(preflight)}, sort_keys=True))
        return 0
    for case in suite:
        log_progress(f"case start {case.name} prompt_profile={args.profile}")
        warmups = [run_batch(url, args.model, case, args.timeout_s, idx + 1, 1) for idx in range(args.warmup_runs)]
        if warmups:
            log_progress(f"case warmup complete {case.name} warmups={len(warmups)}")
        batches_by_concurrency = {}
        summary_by_concurrency = {}
        for concurrency in concurrency_levels:
            log_progress(f"batch start {case.name} concurrency={concurrency} runs={args.runs}")
            batches = [run_batch(url, args.model, case, args.timeout_s, idx + 1, concurrency) for idx in range(args.runs)]
            batches_by_concurrency[str(concurrency)] = batches
            summary_by_concurrency[str(concurrency)] = summarize_batches(batches)
            log_progress(
                f"batch complete {case.name} concurrency={concurrency} "
                f"mean_completion_tok_s={summary_by_concurrency[str(concurrency)]['aggregate_completion_tok_per_s']['mean']}"
            )
            for batch in batches:
                csv_rows.append({
                    "case": case.name, "category": case.category, "concurrency": concurrency, "run_index": batch["run_index"],
                    "wall_s": batch["wall_s"], "completion_tokens": sum(req["completion_tokens"] for req in batch["requests"]),
                    "total_tokens": sum(req["total_tokens"] for req in batch["requests"]),
                    "aggregate_completion_tok_per_s": batch["aggregate_completion_tok_per_s"],
                    "aggregate_total_tok_per_s": batch["aggregate_total_tok_per_s"], "contains_target_rate_pct": batch["contains_target_rate_pct"],
                })
        case_results.append({**asdict(case), "warmups": warmups, "batches_by_concurrency": batches_by_concurrency, "summary_by_concurrency": summary_by_concurrency})
        log_progress(f"case complete {case.name}")
    stream_probes = []
    if args.stream_probe:
        for case in suite:
            log_progress(f"stream probe start {case.name}")
            payload = {"model": args.model, "prompt": case.prompt, "max_tokens": min(case.max_tokens, 128), "temperature": case.temperature}
            probe = stream_completion(url, payload, args.timeout_s)
            probe["case"] = case.name
            probe["category"] = case.category
            stream_probes.append(probe)
            log_progress(f"stream probe complete {case.name} ttft_s={probe['ttft_s']}")
    elapsed_s = round(time.perf_counter() - started, 4)
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = generated_at.replace(":", "").replace("-", "").replace("T", "-").removesuffix("Z")
    out_dir = args.out_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "ok": True, "label": args.label, "model": args.model, "base_url": args.base_url, "profile": args.profile,
        "generated_at": generated_at, "elapsed_s": elapsed_s, "runs": args.runs, "warmup_runs": args.warmup_runs,
        "concurrency_levels": concurrency_levels, "stream_probe_enabled": args.stream_probe, "preflight": preflight, "cases": case_results, "stream_probes": stream_probes,
    }
    json_path = out_dir / "result.json"
    csv_path = out_dir / "summary.csv"
    md_path = out_dir / "REPORT.md"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(csv_path, csv_rows)
    write_markdown(md_path, result)
    print(json.dumps({"ok": True, "json": str(json_path), "csv": str(csv_path), "report": str(md_path), "elapsed_s": elapsed_s, "case_count": len(case_results)}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
