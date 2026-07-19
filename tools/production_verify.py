#!/usr/bin/env python3
import argparse
import csv
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path


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


def run_json(repo: Path, command: list[str], env: dict[str, str] | None = None) -> dict:
    proc = subprocess.run(host_command(command), cwd=repo, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed rc={proc.returncode}\ncmd={' '.join(command)}\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return json.loads(proc.stdout)


def run_text(repo: Path, command: list[str], env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(host_command(command), cwd=repo, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed rc={proc.returncode}\ncmd={' '.join(command)}\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return proc.stdout


def read_summary_rows(path: Path) -> list[dict[str, str]]:
    with path.open() as fh:
        return list(csv.DictReader(fh))


def budget_value(raw: str) -> float:
    return float(raw.strip())


def summary_index(rows: list[dict[str, str]]) -> dict[tuple[str, float], dict[str, str]]:
    return {(row["policy"], budget_value(row["budget_pct"])): row for row in rows}


def parse_json_tail(raw: str) -> dict | None:
    text = raw.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for marker in ["\n{", "{"]:
        index = text.rfind(marker)
        if index < 0:
            continue
        candidate = text[index + (1 if marker == "\n{" else 0) :]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def newest_manifest(results_root: Path, started_at: float) -> dict | None:
    manifests = sorted(
        results_root.glob("**/manifest_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in manifests:
        if path.stat().st_mtime + 1 < started_at:
            continue
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
    return None


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser()
    cli.add_argument("--model-preset", default="qwen_1_5b")
    cli.add_argument("--model")
    cli.add_argument("--sample-profile", default="stress")
    cli.add_argument("--page-tokens", type=int, default=16)
    cli.add_argument("--prompt-tokens", type=int, default=410)
    cli.add_argument("--eval-tokens", type=int, default=10)
    cli.add_argument("--gen-tokens", type=int, default=10)
    cli.add_argument("--budgets", default="100,50,25,12.5,6.25,0")
    cli.add_argument(
        "--policies",
        default="full_kv,recent_only,quantized_old_kv,fpa_no_plan,plan_v0_prompt_anchor_raw,plan_v1_anchor_k_protected,plan_v1_structured_protect",
    )
    cli.add_argument("--max-samples", type=int)
    cli.add_argument("--windows-per-doc", type=int)
    cli.add_argument("--window-stride-tokens", type=int, default=48)
    cli.add_argument("--suite-cases", default="needle,multihop,persona,numbers,code,conversation")
    cli.add_argument("--stress-samples", type=int)
    cli.add_argument("--model-dtype")
    cli.add_argument("--mps-memory-fraction", type=float)
    cli.add_argument("--output-dir")
    cli.add_argument("--real-eval-manifest")
    cli.add_argument(
        "--deep-scenario",
        default="results/production-pass.trace.scenarios/all.fozzy.json",
    )
    cli.add_argument("--deep-runs", type=int, default=5)
    cli.add_argument("--deep-seed", type=int, default=4516107740814868623)
    return cli


def append_if_present(command: list[str], flag: str, value) -> None:
    if value is None:
        return
    command.extend([flag, str(value)])


def main() -> int:
    args = parser().parse_args()

    repo = Path(__file__).resolve().parents[1]
    kv_root = repo.parent
    artifacts = repo / "artifacts"
    artifacts.mkdir(exist_ok=True)
    trace_path = artifacts / "production_verify.trace.fozzy"
    report_json_path = artifacts / "production_verify.report.json"
    report_md_path = artifacts / "production_verify.report.md"

    verify = run_json(repo, ["fozzy", "verify", "src/main.fzy", "--json"])
    strict_test = run_json(repo, ["fozzy", "test", "src/main.fzy", "--det", "--strict-verify", "--json"])
    doctor_project = run_json(repo, ["fozzy", "doctor", "project", ".", "--strict", "--json"])
    deep_doctor = run_json(
        repo,
        [
            "fozzy",
            "doctor",
            "--deep",
            "--scenario",
            args.deep_scenario,
            "--runs",
            str(args.deep_runs),
            "--seed",
            str(args.deep_seed),
            "--strict",
            "--json",
        ],
    )
    det_trace = run_json(
        repo,
        ["fozzy", "run", "src/main.fzy", "--det", "--record", str(trace_path), "--json"],
    )
    trace_verify = run_json(repo, ["fozzy", "trace", "verify", str(trace_path), "--strict", "--json"])
    trace_replay = run_json(repo, ["fozzy", "replay", str(trace_path), "--json"])
    trace_ci = run_json(repo, ["fozzy", "ci", str(trace_path), "--json"])
    unsafe_audit = run_json(repo, ["fozzy", "audit", "unsafe", ".", "--workspace", "--json"])
    unsafe_report = json.loads((repo / "src/.fz/unsafe-report.json").read_text())

    if args.real_eval_manifest:
        real_eval = json.loads(Path(args.real_eval_manifest).read_text())
    else:
        real_eval_command = [
            str(kv_root / ".venv/bin/python"),
            "python/kv_tiered_real/run_real_eval.py",
            "--model-preset",
            args.model_preset,
            "--sample-profile",
            args.sample_profile,
            "--page-tokens",
            str(args.page_tokens),
            "--prompt-tokens",
            str(args.prompt_tokens),
            "--eval-tokens",
            str(args.eval_tokens),
            "--gen-tokens",
            str(args.gen_tokens),
            "--budgets",
            args.budgets,
            "--policies",
            args.policies,
            "--window-stride-tokens",
            str(args.window_stride_tokens),
            "--suite-cases",
            args.suite_cases,
        ]
        append_if_present(real_eval_command, "--model", args.model)
        append_if_present(real_eval_command, "--max-samples", args.max_samples)
        append_if_present(real_eval_command, "--windows-per-doc", args.windows_per_doc)
        append_if_present(real_eval_command, "--stress-samples", args.stress_samples)
        append_if_present(real_eval_command, "--model-dtype", args.model_dtype)
        append_if_present(real_eval_command, "--mps-memory-fraction", args.mps_memory_fraction)
        append_if_present(real_eval_command, "--output-dir", args.output_dir)

        started_at = time.time()
        real_eval_stdout = run_text(kv_root, real_eval_command, env=os.environ.copy())
        real_eval = parse_json_tail(real_eval_stdout)
        if real_eval is None:
            real_eval = newest_manifest(kv_root / "results_real", started_at)
        if real_eval is None:
            raise RuntimeError("unable to parse or locate the real-eval manifest")
    overall_rows = read_summary_rows(Path(real_eval["summary_path"]))
    summary_by_kind_paths = real_eval.get("summary_by_kind_paths", {})
    focus_kind = "stress_suite" if "stress_suite" in summary_by_kind_paths else None
    if focus_kind is None and summary_by_kind_paths:
        focus_kind = sorted(summary_by_kind_paths)[0]
    focus_rows = read_summary_rows(Path(summary_by_kind_paths[focus_kind])) if focus_kind else overall_rows
    failure_rows = read_summary_rows(Path(real_eval["failure_summary_path"]))
    focus_by_policy_budget = summary_index(focus_rows)

    budgets = [item.strip() for item in args.budgets.split(",") if item.strip()]
    policies = [item.strip() for item in args.policies.split(",") if item.strip()]
    snapshot = []
    for budget in budgets:
        for policy in policies:
            row = focus_by_policy_budget.get((policy, budget_value(budget)))
            if row:
                snapshot.append(
                    {
                        "policy": policy,
                        "budget_pct": budget,
                        "quality_bps": float(row["quality_bps"]),
                        "top1_agreement_pct": float(row["top1_agreement_pct"]),
                        "top5_agreement_pct": float(row["top5_agreement_pct"]),
                        "exact_match_pct": float(row["exact_match_pct"]),
                        "contains_target_pct": float(row["contains_target_pct"]),
                        "task_score_pct": float(row.get("task_score_pct", 0.0)),
                        "task_score_delta_vs_quantized": float(row.get("task_score_delta_vs_quantized", 0.0)),
                        "avg_latency_ms": float(row["avg_latency_ms"]),
                        "hot_bytes": int(row["hot_bytes"]),
                        "warm_bytes": int(row["warm_bytes"]),
                        "cold_bytes": int(row["cold_bytes"]),
                        "warm_bytes_delta_vs_quantized": int(float(row.get("warm_bytes_delta_vs_quantized", 0.0))),
                        "task_gain_per_extra_warm_byte": float(row.get("task_gain_per_extra_warm_byte", 0.0)),
                        "failure_rate_pct": float(row["failure_rate_pct"]),
                    }
                )

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": real_eval["model"],
        "model_preset": real_eval.get("model_preset", args.model_preset),
        "sample_profile": real_eval.get("sample_profile", args.sample_profile),
        "page_tokens": args.page_tokens,
        "prompt_tokens": args.prompt_tokens,
        "eval_tokens": args.eval_tokens,
        "gen_tokens": args.gen_tokens,
        "budgets": budgets,
        "policies": policies,
        "verify_warnings": verify["warnings"],
        "verify_warning_codes": [item["code"] for item in verify["items"]],
        "strict_test_diagnostics": strict_test["diagnostics"],
        "doctor_project_warnings": doctor_project["warnings"],
        "deep_doctor_consistent": deep_doctor["determinism_audit"]["consistent"],
        "trace_verify_ok": trace_verify["ok"],
        "trace_replay_status": trace_replay["status"],
        "trace_ci_ok": trace_ci["ok"],
        "real_eval_results_dir": real_eval["results_dir"],
        "real_eval_run_path": real_eval["run_path"],
        "real_eval_sample_count": real_eval["sample_count"],
        "real_eval_sample_kinds": real_eval["sample_kinds"],
        "real_eval_summary_path": real_eval["summary_path"],
        "real_eval_focus_kind": focus_kind or "overall",
        "real_eval_focus_summary_path": summary_by_kind_paths.get(focus_kind, real_eval["summary_path"]),
        "real_eval_failure_summary_path": real_eval["failure_summary_path"],
        "focus_snapshot": snapshot,
        "failure_buckets": failure_rows,
        "unsafe_audit_ok": unsafe_audit["ok"],
        "unsafe_sites": unsafe_report["unsafe_sites"],
        "unsafe_unreasoned": unsafe_report["unreasoned"],
        "status": "model-agnostic production benchmark path verified",
        "remaining_warning_note": "Native fzy coverage remains source-level/runtime-unit verification; production benchmark authority is the explicit real-model harness.",
    }

    report = {
        "summary": summary,
        "verify": verify,
        "strict_test": strict_test,
        "doctor_project": doctor_project,
        "deep_doctor": deep_doctor,
        "det_trace": det_trace,
        "trace_verify": trace_verify,
        "trace_replay": trace_replay,
        "trace_ci": trace_ci,
        "real_eval": real_eval,
        "overall_rows": overall_rows,
        "focus_rows": focus_rows,
        "failure_rows": failure_rows,
        "unsafe_audit": unsafe_audit,
        "unsafe_report_excerpt": {
            "unsafe_sites": unsafe_report["unsafe_sites"],
            "unreasoned": unsafe_report["unreasoned"],
            "sites": unsafe_report["sites"],
        },
    }
    report_json_path.write_text(json.dumps(report, indent=2))

    md_lines = [
        "# Production Verify Report",
        "",
        f"Status: `{summary['status']}`",
        f"Generated at: `{summary['generated_at']}`",
        f"Model: `{summary['model']}`",
        f"Model preset: `{summary['model_preset']}`",
        f"Sample profile: `{summary['sample_profile']}`",
        f"Page tokens: `{summary['page_tokens']}`",
        f"Prompt tokens: `{summary['prompt_tokens']}`",
        f"Eval tokens: `{summary['eval_tokens']}`",
        f"Gen tokens: `{summary['gen_tokens']}`",
        "",
        "## Source Checks",
        "",
        f"- `fozzy verify src/main.fzy --json`: warnings=`{summary['verify_warnings']}` codes=`{','.join(summary['verify_warning_codes'])}`",
        f"- `fozzy test src/main.fzy --det --strict-verify --json`: diagnostics=`{summary['strict_test_diagnostics']}`",
        f"- `fozzy doctor project . --strict --json`: warnings=`{summary['doctor_project_warnings']}`",
        f"- deep deterministic doctor consistent: `{summary['deep_doctor_consistent']}`",
        f"- trace verify ok: `{summary['trace_verify_ok']}`",
        f"- trace replay status: `{summary['trace_replay_status']}`",
        f"- trace ci ok: `{summary['trace_ci_ok']}`",
        "",
        "## Real Model Benchmark",
        "",
        f"- results dir: `{summary['real_eval_results_dir']}`",
        f"- sample count: `{summary['real_eval_sample_count']}`",
        f"- sample kinds: `{','.join(summary['real_eval_sample_kinds'])}`",
        f"- focus kind: `{summary['real_eval_focus_kind']}`",
        f"- run json: `{summary['real_eval_run_path']}`",
        f"- summary csv: `{summary['real_eval_summary_path']}`",
        f"- focus summary csv: `{summary['real_eval_focus_summary_path']}`",
        f"- failure summary csv: `{summary['real_eval_failure_summary_path']}`",
        "",
        "| Policy | Budget | Quality BPS | Top1 % | Top5 % | Exact % | Contains % | Avg Latency ms | Hot Bytes | Warm Bytes | Cold Bytes | Failure % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in snapshot:
        md_lines.append(
            f"| {row['policy']} | {row['budget_pct']} | {row['quality_bps']:.3f} | {row['top1_agreement_pct']:.3f} | {row['top5_agreement_pct']:.3f} | {row['exact_match_pct']:.3f} | {row['contains_target_pct']:.3f} | {row['avg_latency_ms']:.3f} | {row['hot_bytes']} | {row['warm_bytes']} | {row['cold_bytes']} | {row['failure_rate_pct']:.3f} |"
        )
    md_lines.extend(
        [
            "",
            "## Remaining Warning",
            "",
            f"- {summary['remaining_warning_note']}",
            f"- unsafe sites: `{summary['unsafe_sites']}` unreasoned: `{summary['unsafe_unreasoned']}`",
            "",
        ]
    )
    report_md_path.write_text("\n".join(md_lines))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
