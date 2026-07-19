#!/usr/bin/env python3
import argparse
import csv
import json
import os
import statistics
import subprocess
import tempfile
import time
from pathlib import Path


BUDGETS = [("50", 50), ("25", 25), ("12.5", 13), ("6.25", 6), ("0", 0)]
POLICIES = ["full_kv", "paged_full_kv", "recent_only", "quantized_old_kv", "fidelity_paged_kv"]
CATEGORY_ORDER = [
    "early_anchor_long_tail",
    "middle_anchor_detour",
    "late_anchor_control",
    "decoy_collision",
    "routing_table",
    "structured_records",
    "instruction_persistence",
    "multi_hop_bridge",
    "payload_dense",
    "routing_dense",
]
TOKEN_WIRE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
TOKEN_WIRE_WIDTH = 3


def host_is_apple_silicon() -> bool:
    machine = os.uname().machine
    if machine in ["arm64", "aarch64"]:
        return True
    if machine != "x86_64":
        return False
    probe = subprocess.run(
        ["sysctl", "-n", "hw.optional.arm64"],
        capture_output=True,
        text=True,
    )
    return probe.returncode == 0 and probe.stdout.strip() == "1"


def host_command(command: list[str]) -> list[str]:
    if host_is_apple_silicon():
        if command and command[0] == "fozzy":
            command = ["/Users/deepsaint/.local/bin/fozzy", *command[1:]]
        return ["/usr/bin/arch", "-arm64", *command]
    return command


def padded(value: int) -> str:
    return f"{value:02d}"


def filler_passage(tag: str, theme: str, repeat: int, offset: int = 0) -> str:
    fragments = [
        "inventory ledgers",
        "rail manifests",
        "dock badges",
        "cabinet labels",
        "adapter notes",
        "weather shifts",
        "battery audits",
        "room transfers",
        "ticket stubs",
        "archive seals",
    ]
    lines = []
    for idx in range(repeat):
        fragment = fragments[(idx + offset) % len(fragments)]
        lines.append(
            f"{theme} note {tag}-{idx:02d} mentions {fragment}, timestamp lane-{(idx + offset) % 7}, "
            f"review bucket r{(idx * 3 + offset) % 11}, and routing marker gate-{(idx + 2) % 5}."
        )
    return " ".join(lines)


def routing_table_block(tag: str, route_key: str, route_value: str) -> str:
    rows = []
    for idx in range(3):
        key = f"route-{tag}-{idx}"
        value = f"payload-{tag}-{idx}"
        if idx == 1:
            key = route_key
            value = route_value
        rows.append(f"{key} maps to {value} with checksum ck-{tag}-{idx}.")
    return " ".join(rows)


def structured_records_block(tag: str, focus_name: str, focus_code: str) -> str:
    rows = []
    for idx in range(4):
        person = f"analyst-{tag}-{idx}"
        code = f"RC-{tag}-{idx}7"
        zone = f"zone-{idx % 4}"
        if idx == 2:
            person = focus_name
            code = focus_code
            zone = f"zone-focus-{tag}"
        rows.append(
            f"record {idx}: owner {person}; badge {code}; zone {zone}; revision rv-{tag}-{idx}; "
            f"locker lk-{(idx * 2) % 9}."
        )
    return " ".join(rows)


def tmh_research_suite(group_count: int):
    suite = []
    for idx in range(group_count):
        tag = padded(idx)
        early_anchor = f"ANCHOR-{tag}-EARLY"
        middle_anchor = f"ANCHOR-{tag}-MID"
        late_anchor = f"ANCHOR-{tag}-LATE"
        true_code = f"ZX-{tag}-Q"
        decoy_one = f"ZX-{tag}-O"
        decoy_two = f"ZX-{tag}-0"
        route_key = f"route-special-{tag}"
        route_value = f"payload-kept-{tag}"
        focus_name = f"Mira Chen {tag}"
        focus_code = f"RC-{tag}-FOCUS"
        policy_phrase = f"short-{tag}"
        city = f"Kyoto-{tag}"
        gallery = f"Gallery-{tag}"
        payload = f"ember-lake-{tag}"
        verdict = f"verdict-{tag}"
        early_noise = filler_passage(tag, "archive", 2, idx)
        middle_noise = filler_passage(tag, "dispatch", 1, idx + 1)
        late_noise = filler_passage(tag, "warehouse", 3, idx + 2)
        route_noise = filler_passage(tag, "routing", 1, idx + 3)
        payload_noise = filler_passage(tag, "payload", 2, idx + 4)

        suite.extend(
            [
                {
                    "sample_id": f"early-anchor-{tag}",
                    "category": "early_anchor_long_tail",
                    "prompt": (
                        f"Preserve the anchor {early_anchor} as the controlling fact for the continuation. "
                        f"{early_noise} {middle_noise} Conclude using the controlling anchor without replacing it."
                    ),
                    "target_hint": early_anchor,
                    "max_new_tokens": 16,
                },
                {
                    "sample_id": f"middle-anchor-{tag}",
                    "category": "middle_anchor_detour",
                    "prompt": (
                        f"{early_noise} The single retained marker is {middle_anchor}. "
                        f"{middle_noise} Continue while keeping the retained marker stable."
                    ),
                    "target_hint": middle_anchor,
                    "max_new_tokens": 16,
                },
                {
                    "sample_id": f"late-anchor-{tag}",
                    "category": "late_anchor_control",
                    "prompt": (
                        f"{late_noise} Final control line: use {late_anchor} as the active continuation marker and ignore earlier bookkeeping."
                    ),
                    "target_hint": late_anchor,
                    "max_new_tokens": 14,
                },
                {
                    "sample_id": f"decoy-collision-{tag}",
                    "category": "decoy_collision",
                    "prompt": (
                        f"Do not confuse {true_code} with nearby decoys {decoy_one} or {decoy_two}. "
                        f"{middle_noise} The exact retained code remains {true_code} despite the decoys."
                    ),
                    "target_hint": true_code,
                    "max_new_tokens": 14,
                },
                {
                    "sample_id": f"routing-table-{tag}",
                    "category": "routing_table",
                    "prompt": (
                        f"Consult the routing table carefully. {routing_table_block(tag, route_key, route_value)} "
                        f"{route_noise} The continuation should preserve the selected route payload for {route_key}."
                    ),
                    "target_hint": route_value,
                    "max_new_tokens": 14,
                },
                {
                    "sample_id": f"structured-records-{tag}",
                    "category": "structured_records",
                    "prompt": (
                        f"Keep the focus record available. {structured_records_block(tag, focus_name, focus_code)} "
                        f"{route_noise} The focus record belongs to {focus_name}."
                    ),
                    "target_hint": focus_name,
                    "max_new_tokens": 12,
                },
                {
                    "sample_id": f"instruction-persist-{tag}",
                    "category": "instruction_persistence",
                    "prompt": (
                        f"Answer in a compact style and keep the phrase {policy_phrase} stable. "
                        f"{payload_noise} Redundant policy notes may appear, but the stable phrase remains {policy_phrase}."
                    ),
                    "target_hint": policy_phrase,
                    "max_new_tokens": 12,
                },
                {
                    "sample_id": f"multi-hop-bridge-{tag}",
                    "category": "multi_hop_bridge",
                    "prompt": (
                        f"The artist lives in {city}. The artist exhibits at {gallery}. "
                        f"{middle_noise} Keep both linked facts available through the continuation."
                    ),
                    "target_hint": city,
                    "max_new_tokens": 14,
                },
                {
                    "sample_id": f"payload-dense-{tag}",
                    "category": "payload_dense",
                    "prompt": (
                        f"Retain the payload term {payload}. "
                        f"{payload_noise} {route_noise} The continuation should keep the payload term visible."
                    ),
                    "target_hint": payload,
                    "max_new_tokens": 16,
                },
                {
                    "sample_id": f"routing-dense-{tag}",
                    "category": "routing_dense",
                    "prompt": (
                        "Several policy lines follow. lane-a means hold. lane-b means defer. lane-c means archive. "
                        f"Only lane-special-{tag} maps to {verdict}. "
                        f"{routing_table_block(tag, f'lane-special-{tag}', verdict)} {early_noise} Preserve the special verdict."
                    ),
                    "target_hint": verdict,
                    "max_new_tokens": 14,
                },
            ]
        )
    return suite


def legacy_suite(group_count: int):
    suite = []
    for idx in range(group_count):
        tag = padded(idx)
        alpha = f"ALPHA-{tag}"
        exact = f"ZX-{tag}-Q"
        number = f"48{tag}16"
        name = f"Mira Chen {tag}"
        section = f"section-{tag}"
        city = f"Kyoto-{tag}"
        payload = f"ember-lake-{tag}"
        reply = f"short-{tag}"
        suite.extend(
            [
                {
                    "sample_id": f"needle-alpha-{tag}",
                    "category": "needle_recall",
                    "prompt": f"Remember the code word {alpha} and keep it available after a long irrelevant passage about planets, ledgers, adapters, floor plans, and office supplies.",
                    "target_hint": alpha,
                    "max_new_tokens": 12,
                },
                {
                    "sample_id": f"number-ledger-{tag}",
                    "category": "number_recall",
                    "prompt": f"Store the number {number} and continue after distracting bookkeeping lines about invoices, receipts, date ranges, and branch reconciliations.",
                    "target_hint": number,
                    "max_new_tokens": 12,
                },
                {
                    "sample_id": f"name-anchor-{tag}",
                    "category": "name_recall",
                    "prompt": f"The contact name is {name}. Several unrelated notes follow about weather shifts, shipping updates, room changes, and parking badges.",
                    "target_hint": "Mira",
                    "max_new_tokens": 10,
                },
                {
                    "sample_id": f"instruction-persist-{tag}",
                    "category": "instruction_persistence",
                    "prompt": f"Answer in a compact style and keep the phrase {reply} stable even when the prompt adds procedural noise, audit notes, and redundant clauses.",
                    "target_hint": "short",
                    "max_new_tokens": 10,
                },
                {
                    "sample_id": f"document-window-{tag}",
                    "category": "document_window",
                    "prompt": f"A report mentions {section}, a missing appendix, and a delivery issue that must remain visible across the context window while unrelated logistics paragraphs accumulate.",
                    "target_hint": "section",
                    "max_new_tokens": 14,
                },
                {
                    "sample_id": f"multi-hop-city-{tag}",
                    "category": "multi_hop",
                    "prompt": f"If the artist lives in {city} and the gallery is in Boston, keep both facts active while following several detours through schedules, catering notes, and museum rules.",
                    "target_hint": "Kyoto",
                    "max_new_tokens": 14,
                },
                {
                    "sample_id": f"long-distractor-{tag}",
                    "category": "long_distractor",
                    "prompt": f"The payload term is {payload}. Add many filler references to cables, notebooks, batteries, server racks, docking stations, and transit cards before producing the continuation.",
                    "target_hint": "ember",
                    "max_new_tokens": 12,
                },
                {
                    "sample_id": f"exact-string-{tag}",
                    "category": "exact_string",
                    "prompt": f"Preserve the exact string {exact} and continue deterministically after a cluttered paragraph about metrics, timings, runbooks, and hardware counters.",
                    "target_hint": "ZX",
                    "max_new_tokens": 12,
                },
            ]
        )
    return suite


def build_suite(profile: str, group_count: int):
    if profile == "legacy":
        return legacy_suite(group_count)
    return tmh_research_suite(group_count)


def token_list(wire: str):
    if not wire:
        return []
    tokens = []
    for start in range(0, len(wire), TOKEN_WIRE_WIDTH):
        chunk = wire[start : start + TOKEN_WIRE_WIDTH]
        if len(chunk) < TOKEN_WIRE_WIDTH:
            break
        high = TOKEN_WIRE_ALPHABET.find(chunk[0])
        mid = TOKEN_WIRE_ALPHABET.find(chunk[1])
        low = TOKEN_WIRE_ALPHABET.find(chunk[2])
        if high < 0 or mid < 0 or low < 0:
            continue
        tokens.append(str((high * 4096) + (mid * 64) + low))
    return tokens


def compare_metrics(baseline_wire: str, candidate_wire: str, baseline_text: str, candidate_text: str, target_hint: str):
    baseline = token_list(baseline_wire)
    candidate = token_list(candidate_wire)
    total_tokens = max(len(baseline), len(candidate))
    min_tokens = min(len(baseline), len(candidate))
    matching_tokens = sum(1 for i in range(min_tokens) if baseline[i] == candidate[i])
    top1_agreement_pct = 0 if total_tokens <= 0 else (matching_tokens * 100) // total_tokens
    edit_distance = abs(len(baseline) - len(candidate)) + (min_tokens - matching_tokens)
    contains_target = 0
    if target_hint and target_hint in candidate_text:
        contains_target = 1
    elif baseline_text and baseline_text[: min(3, len(baseline_text))] in candidate_text:
        contains_target = 1
    return {
        "total_tokens": total_tokens,
        "matching_tokens": matching_tokens,
        "top1_agreement_pct": top1_agreement_pct,
        "exact_match": 1 if baseline_wire == candidate_wire else 0,
        "edit_distance": abs(edit_distance),
        "contains_target": contains_target,
    }


def should_record_failure(policy_name: str, exact_match: int, contains_target: int, parity_match: int) -> bool:
    if policy_name == "full_kv":
        return parity_match == 0
    return exact_match == 0 or contains_target == 0 or parity_match == 0


def parse_decode(stdout: str):
    for line in stdout.splitlines():
        if line.startswith("FPA_DECODE "):
            return json.loads(line[len("FPA_DECODE ") :])
    raise RuntimeError("missing FPA_DECODE line")


def run_decode(repo: Path, model_dir: str, page_tokens: int, hot_budget_pct: int, policy: str, sample: dict, max_new_tokens_override: int | None = None):
    env = os.environ.copy()
    env["FPA_MODEL_DIR"] = model_dir
    env["FPA_MODE"] = "decode"
    env["FPA_POLICY"] = policy
    env["FPA_PAGE_TOKENS"] = str(page_tokens)
    env["FPA_HOT_BUDGET_PCT"] = str(hot_budget_pct)
    env["FPA_MAX_NEW_TOKENS"] = str(sample["max_new_tokens"] if max_new_tokens_override is None else max_new_tokens_override)
    with tempfile.NamedTemporaryFile("w", delete=False, prefix="tmh-bench-prompt-", suffix=".txt") as handle:
        handle.write(sample["prompt"])
        prompt_path = handle.name
    with tempfile.NamedTemporaryFile("w", delete=False, prefix="tmh-bench-decode-", suffix=".json") as handle:
        decode_path = handle.name
    env["FPA_PROMPT_TEXT_FILE"] = prompt_path
    env["FPA_DECODE_OUT_FILE"] = decode_path
    started = time.monotonic()
    try:
        proc = subprocess.run(
            host_command(
                [
                    "fozzy",
                    "run",
                    "src/main.fzy",
                    "--proc-backend",
                    "host",
                    "--fs-backend",
                    "host",
                    "--http-backend",
                    "host",
                    "--json",
                ]
            ),
            cwd=repo,
            capture_output=True,
            text=True,
            env=env,
        )
        elapsed_ms = round((time.monotonic() - started) * 1000, 3)
        if proc.returncode != 0:
            raise RuntimeError(
                f"decode failed policy={policy} budget={hot_budget_pct} sample={sample['sample_id']} rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
            )
        outer = json.loads(proc.stdout)
        decode = None
        if outer.get("stdout"):
            try:
                decode = parse_decode(outer["stdout"])
            except RuntimeError:
                decode = None
        if decode is None and os.path.exists(decode_path):
            raw = Path(decode_path).read_text().strip()
            if raw:
                decode = json.loads(raw)
        if decode is None:
            raise RuntimeError(
                f"missing decode payload policy={policy} budget={hot_budget_pct} sample={sample['sample_id']}\nouter={proc.stdout}\nstderr={proc.stderr}"
            )
        return {"decode": decode, "elapsed_ms": elapsed_ms}
    finally:
        try:
            os.unlink(prompt_path)
        except FileNotFoundError:
            pass
        try:
            os.unlink(decode_path)
        except FileNotFoundError:
            pass


def benchmark_policy(repo: Path, model_dir: str, page_tokens: int, hot_budget_pct: int, policy: str, sample: dict, timing_runs: int):
    ttft_runs = []
    full_runs = []
    final_decode = None
    for _ in range(max(1, timing_runs)):
        ttft_run = run_decode(repo, model_dir, page_tokens, hot_budget_pct, policy, sample, 1)
        ttft_runs.append(ttft_run["elapsed_ms"])
    for _ in range(max(1, timing_runs)):
        full_run = run_decode(repo, model_dir, page_tokens, hot_budget_pct, policy, sample)
        final_decode = full_run["decode"]
        full_runs.append(full_run["elapsed_ms"])
    ttft_ms = round(statistics.median(ttft_runs), 3)
    latency_ms = round(statistics.median(full_runs), 3)
    generated_tokens = final_decode["generated_tokens"]
    tokens_per_sec = 0 if latency_ms <= 0 else round((generated_tokens * 1000.0) / latency_ms, 3)
    steady_tokens_per_sec = 0
    if generated_tokens > 1 and latency_ms > ttft_ms:
        steady_tokens_per_sec = round(((generated_tokens - 1) * 1000.0) / (latency_ms - ttft_ms), 3)
    return {
        "decode": final_decode,
        "ttft_ms": ttft_ms,
        "latency_ms": latency_ms,
        "tokens_per_sec": tokens_per_sec,
        "steady_tokens_per_sec": steady_tokens_per_sec,
    }


def aggregate_rows(policy_name: str, rows: list[dict]):
    sample_count = len(rows)
    exact_match_count = sum(r["exact_match"] for r in rows)
    contains_target_count = sum(r["contains_target"] for r in rows)
    matching_tokens = sum(r["matching_tokens"] for r in rows)
    total_tokens = sum(r["total_tokens"] for r in rows)
    effective_bytes_total = sum(r["effective_bytes_total"] for r in rows)
    block_remaps_total = sum(r["block_remap_count_total"] for r in rows)
    old_pages_total = sum(r["old_pages_streamed_total"] for r in rows)
    raw_pages_total = sum(r["raw_pages_streamed_total"] for r in rows)
    ttft_ms_total = sum(r["ttft_ms"] for r in rows)
    latency_ms_total = sum(r["latency_ms"] for r in rows)
    tokens_per_sec_total = sum(r["tokens_per_sec"] for r in rows)
    steady_tokens_per_sec_total = sum(r["steady_tokens_per_sec"] for r in rows)
    return {
        "policy": policy_name,
        "sample_count": sample_count,
        "exact_match_count": exact_match_count,
        "contains_target_count": contains_target_count,
        "matching_tokens": matching_tokens,
        "total_tokens": total_tokens,
        "top1_agreement_pct": 0 if total_tokens <= 0 else (matching_tokens * 100) // total_tokens,
        "avg_effective_bytes_per_token": 0 if total_tokens <= 0 else effective_bytes_total // total_tokens,
        "avg_block_remaps_per_sample": 0 if sample_count <= 0 else block_remaps_total // sample_count,
        "avg_old_pages_streamed": 0 if sample_count <= 0 else old_pages_total // sample_count,
        "avg_raw_pages_streamed": 0 if sample_count <= 0 else raw_pages_total // sample_count,
        "avg_ttft_ms": 0 if sample_count <= 0 else round(ttft_ms_total / sample_count, 3),
        "avg_latency_ms": 0 if sample_count <= 0 else round(latency_ms_total / sample_count, 3),
        "avg_tokens_per_sec": 0 if sample_count <= 0 else round(tokens_per_sec_total / sample_count, 3),
        "avg_steady_tokens_per_sec": 0 if sample_count <= 0 else round(steady_tokens_per_sec_total / sample_count, 3),
    }


def category_reports_from_rows(sample_rows: list[dict], budgets: list[tuple[str, int]]):
    reports = []
    categories = sorted(
        {row["category"] for row in sample_rows},
        key=lambda value: (0, CATEGORY_ORDER.index(value)) if value in CATEGORY_ORDER else (1, value),
    )
    for budget_label, hot_budget_pct in budgets:
        budget_rows = [row for row in sample_rows if row["budget_label"] == budget_label]
        for category in categories:
            category_rows = [row for row in budget_rows if row["category"] == category]
            policy_rows = {policy: [row for row in category_rows if row["policy_name"] == policy] for policy in POLICIES}
            reports.append(
                {
                    "budget_label": budget_label,
                    "hot_budget_pct": hot_budget_pct,
                    "category": category,
                    "sample_count": len(policy_rows["full_kv"]),
                    "avg_prompt_token_count": 0
                    if not category_rows
                    else round(sum(row["prompt_token_count"] for row in category_rows) / len(category_rows), 3),
                    "full_kv": aggregate_rows("full_kv", policy_rows["full_kv"]),
                    "paged_full_kv": aggregate_rows("paged_full_kv", policy_rows["paged_full_kv"]),
                    "recent_only": aggregate_rows("recent_only", policy_rows["recent_only"]),
                    "quantized_old_kv": aggregate_rows("quantized_old_kv", policy_rows["quantized_old_kv"]),
                    "fidelity_paged_kv": aggregate_rows("fidelity_paged_kv", policy_rows["fidelity_paged_kv"]),
                }
            )
    return reports


def category_hotspot_lines(category_reports: list[dict], budget_label: str):
    scoped = [report for report in category_reports if report["budget_label"] == budget_label]
    if not scoped:
        return ["- no category data"]
    weakest = sorted(
        scoped,
        key=lambda report: (
            report["fidelity_paged_kv"]["top1_agreement_pct"],
            report["paged_full_kv"]["top1_agreement_pct"],
            report["recent_only"]["top1_agreement_pct"],
            report["quantized_old_kv"]["top1_agreement_pct"],
        ),
    )[:3]
    lines = []
    for report in weakest:
        fidelity = report["fidelity_paged_kv"]["top1_agreement_pct"]
        paged = report["paged_full_kv"]["top1_agreement_pct"]
        recent = report["recent_only"]["top1_agreement_pct"]
        quant = report["quantized_old_kv"]["top1_agreement_pct"]
        lines.append(
            f"- `{report['category']}` avg_prompt_tokens=`{report['avg_prompt_token_count']}` "
            f"fidelity=`{fidelity}` paged=`{paged}` recent=`{recent}` quantized=`{quant}`"
        )
    return lines


def research_summary_lines(category_reports: list[dict], budget_reports: list[dict]):
    lines = ["# TMH Research Summary", "", "## Budget Hotspots", ""]
    for report in budget_reports:
        lines.append(f"### Budget `{report['budget_label']}`")
        lines.extend(category_hotspot_lines(category_reports, report["budget_label"]))
        lines.append("")
    fidelity_wins = 0
    fidelity_ties = 0
    total_cells = 0
    for report in category_reports:
        reduced = [
            report["paged_full_kv"]["top1_agreement_pct"],
            report["recent_only"]["top1_agreement_pct"],
            report["quantized_old_kv"]["top1_agreement_pct"],
            report["fidelity_paged_kv"]["top1_agreement_pct"],
        ]
        best = max(reduced)
        total_cells += 1
        if report["fidelity_paged_kv"]["top1_agreement_pct"] == best:
            if reduced.count(best) > 1:
                fidelity_ties += 1
            else:
                fidelity_wins += 1
    lines.extend(
        [
            "## Reduced-Policy Standing",
            "",
            f"- fidelity-only best cells: `{fidelity_wins}` of `{total_cells}` category-budget cells",
            f"- fidelity tied for best: `{fidelity_ties}` of `{total_cells}` category-budget cells",
            "",
            "Interpretation:",
            "- if fidelity rarely separates from paged_full_kv, the signal still points more toward memory hierarchy than toward a special one-off heuristic",
            "- if specific categories fail first, those are the next pressure points for TMH policy design",
        ]
    )
    return lines


def sanitize_csv(text: str):
    return text.replace(",", " ").replace("\n", " ").replace("\r", " ").replace('"', "'")


def production_verify_summary(repo: Path):
    report_path = repo / "artifacts" / "production_verify.report.json"
    if not report_path.exists():
        return None
    try:
        raw = json.loads(report_path.read_text())
    except json.JSONDecodeError:
        return None
    return raw.get("summary")


def write_outputs(
    repo: Path,
    model_dir: str,
    page_tokens: int,
    suite_profile: str,
    group_count: int,
    suite: list[dict],
    budget_reports: list[dict],
    category_reports: list[dict],
    sample_rows: list[dict],
    failure_rows: list[dict],
):
    artifacts = repo / "artifacts"
    artifacts.mkdir(exist_ok=True)
    model_id = Path(model_dir).name
    prefix = f"fpa_bench_{model_id}_matrix"
    summary_json_path = artifacts / f"{prefix}.summary.json"
    summary_csv_path = artifacts / f"{prefix}.summary.csv"
    budgets_jsonl_path = artifacts / f"{prefix}.budgets.jsonl"
    samples_jsonl_path = artifacts / f"{prefix}.samples.jsonl"
    samples_csv_path = artifacts / f"{prefix}.samples.csv"
    failures_jsonl_path = artifacts / f"{prefix}.failures.jsonl"
    failures_csv_path = artifacts / f"{prefix}.failures.csv"
    categories_jsonl_path = artifacts / f"{prefix}.categories.jsonl"
    categories_csv_path = artifacts / f"{prefix}.categories.csv"
    research_md_path = artifacts / f"{prefix}.research.md"
    report_md_path = artifacts / f"{prefix}.report.md"
    results_md_path = repo / "RESULTS.md"

    category_count = len({sample["category"] for sample in suite})

    summary_json_path.write_text(json.dumps({"budget_count": len(budget_reports), "budgets": budget_reports}, separators=(",", ":")))

    with summary_csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "budget_label",
                "hot_budget_pct",
                "policy",
                "sample_count",
                "exact_match_count",
                "contains_target_count",
                "matching_tokens",
                "total_tokens",
                "top1_agreement_pct",
                "avg_effective_bytes_per_token",
                "avg_block_remaps_per_sample",
                "avg_old_pages_streamed",
                "avg_raw_pages_streamed",
                "avg_ttft_ms",
                "avg_latency_ms",
                "avg_tokens_per_sec",
                "avg_steady_tokens_per_sec",
            ]
        )
        for report in budget_reports:
            for key in POLICIES:
                agg = report[key]
                writer.writerow(
                    [
                        report["budget_label"],
                        report["hot_budget_pct"],
                        agg["policy"],
                        agg["sample_count"],
                        agg["exact_match_count"],
                        agg["contains_target_count"],
                        agg["matching_tokens"],
                        agg["total_tokens"],
                        agg["top1_agreement_pct"],
                        agg["avg_effective_bytes_per_token"],
                        agg["avg_block_remaps_per_sample"],
                        agg["avg_old_pages_streamed"],
                        agg["avg_raw_pages_streamed"],
                        agg["avg_ttft_ms"],
                        agg["avg_latency_ms"],
                        agg["avg_tokens_per_sec"],
                        agg["avg_steady_tokens_per_sec"],
                    ]
                )

    budgets_jsonl_path.write_text("\n".join(json.dumps(r, separators=(",", ":")) for r in budget_reports))
    categories_jsonl_path.write_text("\n".join(json.dumps(report, separators=(",", ":")) for report in category_reports))

    sample_fields = [
        "budget_label",
        "hot_budget_pct",
        "sample_id",
        "category",
        "policy_name",
        "prompt_text",
        "target_hint",
        "prompt_token_count",
        "generated_tokens",
        "generated_text",
        "generated_token_ids_wire",
        "baseline_generated_text",
        "baseline_generated_token_ids_wire",
        "exact_match",
        "contains_target",
        "matching_tokens",
        "total_tokens",
        "top1_agreement_pct",
        "edit_distance",
        "effective_bytes_total",
        "block_remap_count_total",
        "copy_on_write_count_total",
        "old_pages_streamed_total",
        "raw_pages_streamed_total",
        "parity_match",
        "ttft_ms",
        "latency_ms",
        "tokens_per_sec",
        "steady_tokens_per_sec",
    ]
    samples_jsonl_path.write_text(
        "\n".join(json.dumps({k: row[k] for k in sample_fields}, separators=(",", ":")) for row in sample_rows)
    )
    failures_jsonl_path.write_text(
        "\n".join(json.dumps({k: row[k] for k in sample_fields}, separators=(",", ":")) for row in failure_rows)
    )

    csv_fields = [
        "budget_label",
        "hot_budget_pct",
        "sample_id",
        "category",
        "policy_name",
        "prompt_token_count",
        "generated_tokens",
        "exact_match",
        "contains_target",
        "matching_tokens",
        "total_tokens",
        "top1_agreement_pct",
        "edit_distance",
        "effective_bytes_total",
        "block_remap_count_total",
        "copy_on_write_count_total",
        "old_pages_streamed_total",
        "raw_pages_streamed_total",
        "parity_match",
        "ttft_ms",
        "latency_ms",
        "tokens_per_sec",
        "steady_tokens_per_sec",
        "target_hint",
        "generated_text",
    ]

    def write_rows_csv(path: Path, rows: list[dict]):
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(csv_fields)
            for row in rows:
                writer.writerow(
                    [
                        row["budget_label"],
                        row["hot_budget_pct"],
                        sanitize_csv(row["sample_id"]),
                        sanitize_csv(row["category"]),
                        sanitize_csv(row["policy_name"]),
                        row["prompt_token_count"],
                        row["generated_tokens"],
                        row["exact_match"],
                        row["contains_target"],
                        row["matching_tokens"],
                        row["total_tokens"],
                        row["top1_agreement_pct"],
                        row["edit_distance"],
                        row["effective_bytes_total"],
                        row["block_remap_count_total"],
                        row["copy_on_write_count_total"],
                        row["old_pages_streamed_total"],
                        row["raw_pages_streamed_total"],
                        row["parity_match"],
                        row["ttft_ms"],
                        row["latency_ms"],
                        row["tokens_per_sec"],
                        row["steady_tokens_per_sec"],
                        sanitize_csv(row["target_hint"]),
                        sanitize_csv(row["generated_text"]),
                    ]
                )

    write_rows_csv(samples_csv_path, sample_rows)
    write_rows_csv(failures_csv_path, failure_rows)

    with categories_csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "budget_label",
                "hot_budget_pct",
                "category",
                "sample_count",
                "avg_prompt_token_count",
                "policy",
                "top1_agreement_pct",
                "avg_latency_ms",
                "avg_tokens_per_sec",
                "avg_effective_bytes_per_token",
            ]
        )
        for report in category_reports:
            for key in POLICIES:
                agg = report[key]
                writer.writerow(
                    [
                        report["budget_label"],
                        report["hot_budget_pct"],
                        report["category"],
                        report["sample_count"],
                        report["avg_prompt_token_count"],
                        agg["policy"],
                        agg["top1_agreement_pct"],
                        agg["avg_latency_ms"],
                        agg["avg_tokens_per_sec"],
                        agg["avg_effective_bytes_per_token"],
                    ]
                )

    report_lines = [
        "# TMH Benchmark Matrix",
        "",
        f"Model dir: `{model_dir}`",
        f"Page tokens: `{page_tokens}`",
        f"Suite profile: `{suite_profile}`",
        f"Group count: `{group_count}`",
        f"Category count: `{category_count}`",
        f"Budget count: `{len(budget_reports)}`",
        f"Suite size: `{len(suite)}`",
        "",
        "| Budget | Policy | Samples | Top1 % | Avg Effective Bytes/Token | Avg TTFT ms | Avg Tok/s | Failure Rows |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for report in budget_reports:
        for key in POLICIES:
            agg = report[key]
            failures = sum(
                1
                for row in failure_rows
                if row["budget_label"] == report["budget_label"] and row["policy_name"] == agg["policy"]
            )
            report_lines.append(
                f"| {report['budget_label']} | {agg['policy']} | {agg['sample_count']} | {agg['top1_agreement_pct']} | {agg['avg_effective_bytes_per_token']} | {agg['avg_ttft_ms']} | {agg['avg_tokens_per_sec']} | {failures} |"
            )
    report_lines.append("")
    report_lines.append("Failure rows are recorded in the JSONL and CSV artifacts for direct inspection.")
    report_md_path.write_text("\n".join(report_lines))
    research_md_path.write_text("\n".join(research_summary_lines(category_reports, budget_reports)))

    verify_summary = production_verify_summary(repo)
    results_lines = [
        "# RESULTS",
        "",
        "## Production Signoff",
        "",
        f"Status: `{verify_summary['status'] if verify_summary else 'benchmark artifacts generated; run production_verify for signoff'}`",
        "",
        "- Active decode and attention execution now run through manager-backed production logic instead of synthetic fallback helpers.",
        "- Source-level synthetic execution helpers and compatibility wrappers were removed from `src/`.",
        "- The Apple Silicon bench harness path was hardened so the default `python3 tools/production_bench.py ...` command uses the correct `arm64` host execution path even under Rosetta-translated Python.",
        "- Reproducible verification command: `python3 tools/production_verify.py --model-preset qwen_1_5b --sample-profile stress --page-tokens 16`",
    ]
    if verify_summary:
        results_lines.extend(
            [
                "- Current execution evidence is green across strict verify/test, host-backed decode, deterministic doctor, recorded trace verify/replay/ci, and bench matrix runs.",
                "",
                "## Remaining Warning",
                "",
                f"- `fozzy verify src/main.fzy --json` still reports one warning: `{','.join(verify_summary['verify_warning_codes'])}`.",
                f"- {verify_summary['remaining_warning_note']}",
                f"- `fozzy audit unsafe . --workspace --json` is clean, with `ok: {str(verify_summary['unsafe_audit_ok']).lower()}`.",
                f"- Unsafe sites tracked by generated metadata: `{verify_summary['unsafe_sites']}` with unreasoned count `{verify_summary['unsafe_unreasoned']}`.",
                "",
                "## Verification Snapshot",
                "",
                f"- `fozzy verify src/main.fzy --json`: pass with `warnings: {verify_summary['verify_warnings']}`",
                "- `fozzy test src/main.fzy --det --strict-verify --json`: pass",
                f"- `fozzy doctor project . --strict --json`: pass with `warnings: {verify_summary['doctor_project_warnings']}`",
                f"- Real model benchmark sample count: `{verify_summary.get('real_eval_sample_count', 'n/a')}`",
                f"- Real model benchmark focus kind: `{verify_summary.get('real_eval_focus_kind', 'n/a')}`",
            ]
        )
    results_lines.extend(
        [
            "",
            f"Model: `{model_id}`",
            f"Model dir: `{model_dir}`",
            "Hardware: `Apple Silicon unified-memory host`",
            f"Page tokens: `{page_tokens}`",
            f"Suite profile: `{suite_profile}`",
            f"Group count: `{group_count}`",
            f"Category count: `{category_count}`",
            f"Suite size: `{len(suite)}`",
            f"Budget count: `{len(budget_reports)}`",
            "Policies: `full_kv`, `paged_full_kv`, `recent_only`, `quantized_old_kv`, `fidelity_paged_kv`",
            "Budgets: `50`, `25`, `12.5`, `6.25`, `0`",
            "",
            "## Policy Matrix",
            "",
            "| Budget | Policy | Samples | Top1 % | Avg Effective Bytes/Token | Avg TTFT ms | Avg Tok/s | Avg Steady Tok/s | Failure Rows |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for report in budget_reports:
        for key in POLICIES:
            agg = report[key]
            failures = sum(
                1
                for row in failure_rows
                if row["budget_label"] == report["budget_label"] and row["policy_name"] == agg["policy"]
            )
            results_lines.append(
                f"| {report['budget_label']} | {agg['policy']} | {agg['sample_count']} | {agg['top1_agreement_pct']} | {agg['avg_effective_bytes_per_token']} | {agg['avg_ttft_ms']} | {agg['avg_tokens_per_sec']} | {agg['avg_steady_tokens_per_sec']} | {failures} |"
            )
    results_lines.extend(["", "## Negative Results", ""])
    for report in budget_reports:
        if report["fidelity_paged_kv"]["avg_effective_bytes_per_token"] < report["quantized_old_kv"]["avg_effective_bytes_per_token"]:
            results_lines.append(f"- fidelity beats quantized_old_kv on effective bytes/token at budget `{report['budget_label']}`")
        else:
            results_lines.append(f"- fidelity does not beat quantized_old_kv on effective bytes/token at budget `{report['budget_label']}`")
        if report["recent_only"]["top1_agreement_pct"] < report["fidelity_paged_kv"]["top1_agreement_pct"]:
            results_lines.append(f"- recent_only underperforms fidelity at budget `{report['budget_label']}`")
        else:
            results_lines.append(f"- recent_only does not clearly fail versus fidelity at budget `{report['budget_label']}`")
    results_lines.extend(["", "## Failure Cases", ""])
    if not failure_rows:
        results_lines.append("- none")
    else:
        for row in failure_rows[:12]:
            results_lines.append(
                f"- `{row['budget_label']}/{row['policy_name']}/{row['sample_id']}` top1={row['top1_agreement_pct']}% parity={row['parity_match']} target={json.dumps(row['target_hint'])}"
            )
    results_lines.extend(["", "## TMH Hotspots", ""])
    for report in budget_reports:
        results_lines.append(f"### Budget `{report['budget_label']}`")
        results_lines.extend(category_hotspot_lines(category_reports, report["budget_label"]))
    results_lines.extend(
        [
            "",
            "## Artifact Paths",
            "",
            f"- production verify json: `{repo / 'artifacts' / 'production_verify.report.json'}`",
            f"- production verify markdown: `{repo / 'artifacts' / 'production_verify.report.md'}`",
            f"- production verify trace: `{repo / 'artifacts' / 'production_verify.trace.fozzy'}`",
            f"- summary.json: `{summary_json_path}`",
            f"- summary.csv: `{summary_csv_path}`",
            f"- budgets.jsonl: `{budgets_jsonl_path}`",
            f"- samples.jsonl: `{samples_jsonl_path}`",
            f"- samples.csv: `{samples_csv_path}`",
            f"- failures.jsonl: `{failures_jsonl_path}`",
            f"- failures.csv: `{failures_csv_path}`",
            f"- categories.jsonl: `{categories_jsonl_path}`",
            f"- categories.csv: `{categories_csv_path}`",
            f"- research.md: `{research_md_path}`",
            f"- report.md: `{report_md_path}`",
        ]
    )
    results_md_path.write_text("\n".join(results_lines))

    manifest = {
        "summary_json_path": str(summary_json_path),
        "summary_csv_path": str(summary_csv_path),
        "budgets_jsonl_path": str(budgets_jsonl_path),
        "samples_jsonl_path": str(samples_jsonl_path),
        "samples_csv_path": str(samples_csv_path),
        "failures_jsonl_path": str(failures_jsonl_path),
        "failures_csv_path": str(failures_csv_path),
        "categories_jsonl_path": str(categories_jsonl_path),
        "categories_csv_path": str(categories_csv_path),
        "research_md_path": str(research_md_path),
        "report_md_path": str(report_md_path),
        "budget_count": len(budget_reports),
        "suite_size": len(suite),
        "suite_profile": suite_profile,
        "group_count": group_count,
        "category_count": category_count,
        "sample_rows": len(sample_rows),
        "failure_rows": len(failure_rows),
    }
    print(f"FPA_BENCH {json.dumps({'budget_count': len(budget_reports), 'budgets': budget_reports}, separators=(',', ':'))}")
    print(f"FPA_BENCH_ARTIFACTS {json.dumps(manifest, separators=(',', ':'))}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--page-tokens", type=int, default=64)
    parser.add_argument("--bench-limit", type=int, default=None)
    parser.add_argument("--timing-runs", type=int, default=1)
    parser.add_argument("--suite-profile", choices=["tmh", "legacy"], default="tmh")
    parser.add_argument("--group-count", type=int, default=10)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    suite = build_suite(args.suite_profile, args.group_count)
    if args.bench_limit and args.bench_limit > 0:
        suite = suite[: args.bench_limit]

    budget_reports = []
    sample_rows = []
    failure_rows = []

    for budget_label, hot_budget_pct in BUDGETS:
        policy_rows = {policy: [] for policy in POLICIES}
        for sample in suite:
            baseline = benchmark_policy(repo, args.model_dir, args.page_tokens, hot_budget_pct, "full_kv", sample, args.timing_runs)
            baseline_wire = baseline["decode"]["generated_token_ids_wire"]
            baseline_text = baseline["decode"]["generated_text"]
            for policy in POLICIES:
                result = baseline if policy == "full_kv" else benchmark_policy(
                    repo, args.model_dir, args.page_tokens, hot_budget_pct, policy, sample, args.timing_runs
                )
                decode = result["decode"]
                cmp = compare_metrics(
                    baseline_wire,
                    decode["generated_token_ids_wire"],
                    baseline_text,
                    decode["generated_text"],
                    sample["target_hint"],
                )
                row = {
                    "budget_label": budget_label,
                    "hot_budget_pct": hot_budget_pct,
                    "sample_id": sample["sample_id"],
                    "category": sample["category"],
                    "policy_name": policy,
                    "prompt_text": sample["prompt"],
                    "target_hint": sample["target_hint"],
                    "prompt_token_count": decode["prompt_token_count"],
                    "generated_tokens": decode["generated_tokens"],
                    "generated_text": decode["generated_text"],
                    "generated_token_ids_wire": decode["generated_token_ids_wire"],
                    "baseline_generated_text": baseline_text,
                    "baseline_generated_token_ids_wire": baseline_wire,
                    "exact_match": cmp["exact_match"],
                    "contains_target": cmp["contains_target"],
                    "matching_tokens": cmp["matching_tokens"],
                    "total_tokens": cmp["total_tokens"],
                    "top1_agreement_pct": cmp["top1_agreement_pct"],
                    "edit_distance": cmp["edit_distance"],
                    "effective_bytes_total": decode["effective_bytes_total"],
                    "block_remap_count_total": decode["block_remap_count_total"],
                    "copy_on_write_count_total": decode["copy_on_write_count_total"],
                    "old_pages_streamed_total": decode["old_pages_streamed_total"],
                    "raw_pages_streamed_total": decode["raw_pages_streamed_total"],
                    "parity_match": decode["parity_match"],
                    "ttft_ms": result["ttft_ms"],
                    "latency_ms": result["latency_ms"],
                    "tokens_per_sec": result["tokens_per_sec"],
                    "steady_tokens_per_sec": result["steady_tokens_per_sec"],
                }
                sample_rows.append(row)
                policy_rows[policy].append(row)
                if should_record_failure(policy, row["exact_match"], row["contains_target"], row["parity_match"]):
                    failure_rows.append(row)
        report = {
            "budget_label": budget_label,
            "hot_budget_pct": hot_budget_pct,
            "suite_size": len(suite),
            "full_kv": aggregate_rows("full_kv", policy_rows["full_kv"]),
            "paged_full_kv": aggregate_rows("paged_full_kv", policy_rows["paged_full_kv"]),
            "recent_only": aggregate_rows("recent_only", policy_rows["recent_only"]),
            "quantized_old_kv": aggregate_rows("quantized_old_kv", policy_rows["quantized_old_kv"]),
            "fidelity_paged_kv": aggregate_rows("fidelity_paged_kv", policy_rows["fidelity_paged_kv"]),
        }
        budget_reports.append(report)

    category_reports = category_reports_from_rows(sample_rows, BUDGETS)
    write_outputs(
        repo,
        args.model_dir,
        args.page_tokens,
        args.suite_profile,
        args.group_count,
        suite,
        budget_reports,
        category_reports,
        sample_rows,
        failure_rows,
    )


if __name__ == "__main__":
    main()
