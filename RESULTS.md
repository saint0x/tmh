# RESULTS

## Production Signoff

Status: `model-agnostic production benchmark path verified`

- The production benchmark mainline runs through the explicit real-model harness rather than a fixture-shaped default path.
- Tiny-model defaults were removed from the production entrypoints; model selection is explicit via `--model-preset` or `--model`.
- The verification wrapper supports both fresh live runs and artifact-backed regeneration from emitted real-eval manifests.
- The real harness now streams per-sample summaries to disk during long runs instead of keeping the entire evidence set only in memory.
- The Qwen stress path also includes a real MPS harness fix: page quantization no longer forces scalar device-to-host syncs via `float(max_abs)`.

## Verification Snapshot

- `fozzy verify src/main.fzy --json`: pass with `warnings: 0`
- `fozzy test src/main.fzy --det --strict-verify --json`: pass with `diagnostics: 0`
- `fozzy doctor project . --strict --json`: pass with `warnings: 0`
- `fozzy doctor --deep --scenario results/production-pass.trace.scenarios/all.fozzy.json --runs 5 --seed 4516107740814868623 --strict --json`: consistent
- `fozzy run src/main.fzy --det --record artifacts/production_verify.trace.fozzy --json`: pass
- `fozzy trace verify artifacts/production_verify.trace.fozzy --strict --json`: pass
- `fozzy replay artifacts/production_verify.trace.fozzy --json`: pass
- `fozzy ci artifacts/production_verify.trace.fozzy --json`: pass
- `fozzy audit unsafe . --workspace --json`: pass with `unsafe_sites: 0`

## Real Model Benchmark

Model: `Qwen/Qwen2.5-1.5B-Instruct`
Model preset: `qwen_1_5b`
Sample profile: `stress`
Page tokens: `16`
Prompt/Eval/Gen tokens: `410 / 10 / 10`
Sample count: `250`
Sample kinds: `stress_suite`
Budgets: `50`, `25`, `12.5`, `6.25`, `0`

This is now the mainline benchmark baseline for the TMH claim.

| Policy | Budget | Top1 % | Exact % | Contains % | Avg Latency ms | Hot Bytes | Warm Bytes | Cold Bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| full_kv | 100 | 100.000 | 46.400 | 64.400 | 15.861 | 455223 | 0 | 0 |
| recent_only | 50 | 32.179 | 0.000 | 0.000 | 14.706 | 233467 | 0 | 221755 |
| quantized_old_kv | 50 | 98.967 | 46.400 | 64.400 | 14.594 | 233467 | 887022 | 0 |
| fidelity_paged_kv | 50 | 98.573 | 47.600 | 66.000 | 12.143 | 233467 | 744464 | 0 |
| recent_only | 25 | 26.515 | 0.000 | 0.000 | 14.921 | 122738 | 0 | 332484 |
| quantized_old_kv | 25 | 98.907 | 46.000 | 64.000 | 11.868 | 122738 | 1329939 | 0 |
| fidelity_paged_kv | 25 | 98.433 | 48.000 | 66.400 | 12.093 | 122738 | 1116199 | 0 |
| recent_only | 12.5 | 24.483 | 0.000 | 0.000 | 14.427 | 66627 | 0 | 388595 |
| quantized_old_kv | 12.5 | 98.907 | 46.000 | 64.000 | 11.997 | 66627 | 1554383 | 0 |
| fidelity_paged_kv | 12.5 | 98.533 | 47.600 | 66.000 | 12.442 | 66627 | 1304572 | 0 |
| recent_only | 6.25 | 18.490 | 0.000 | 0.000 | 14.961 | 37955 | 0 | 417267 |
| quantized_old_kv | 6.25 | 98.907 | 46.000 | 64.400 | 12.074 | 37955 | 1669071 | 0 |
| fidelity_paged_kv | 6.25 | 98.460 | 47.200 | 65.200 | 12.064 | 37955 | 1400828 | 0 |
| recent_only | 0 | 22.960 | 0.000 | 0.000 | 12.790 | 0 | 0 | 0 |
| quantized_old_kv | 0 | 99.067 | 46.000 | 64.400 | 11.998 | 0 | 1772546 | 0 |
| fidelity_paged_kv | 0 | 98.387 | 46.400 | 64.800 | 11.943 | 0 | 1487672 | 0 |

## Main Findings

- `recent_only` remains invalid. It collapses to `0.0` exact and `0.0` contains at every compressed budget.
- `quantized_old_kv` remains the strong simple baseline. It preserves the baseline behavior shape under aggressive hot-cache budgets.
- `fidelity_paged_kv` still holds a differentiated win at `250` samples, but the edge is smaller and more stable than the `120` run suggested:
  - lower warm-memory footprint than `quantized_old_kv`
  - better task-level preservation than `quantized_old_kv` at every budget
  - lower top-token imitation than `quantized_old_kv`

## FPA vs Quantized

The `250`-sample aggregate preserves the same basic FPA tradeoff while tightening the claim.

- Warm-memory bytes are lower by about `16.1%` at every budget.
- Exact improves at every tested budget:
  - `50`: `46.4 -> 47.6`
  - `25`: `46.0 -> 48.0`
  - `12.5`: `46.0 -> 47.6`
  - `6.25`: `46.0 -> 47.2`
  - `0`: `46.0 -> 46.4`
- Contains improves or matches at every tested budget:
  - `50`: `64.4 -> 66.0`
  - `25`: `64.0 -> 66.4`
  - `12.5`: `64.0 -> 66.0`
  - `6.25`: `64.4 -> 65.2`
  - `0`: `64.4 -> 64.8`
- Top1 agreement is consistently lower:
  - roughly `98.39-98.57` for `fidelity_paged_kv`
  - roughly `98.91-99.07` for `quantized_old_kv`

## Failure Shape

- `recent_only` still fails destructively with `code_mismatch`, `memory_recall_failure`, `needle_recall_failure`, `numeric_mismatch`, `persona_drift`, `reasoning_mismatch`, plus heavy `degenerate_repetition` and `empty_output`.
- `quantized_old_kv` remains close to the baseline failure shape.
- `fidelity_paged_kv` is also baseline-like, and the `250` run makes the edge more concrete:
  - `50`: `exact_or_prefix_match 116 -> 119`, `reasoning_mismatch 38 -> 35`, `numeric_mismatch 9 -> 8`
  - `25`: `115 -> 120`, `39 -> 34`, `9 -> 8`
  - `12.5`: `115 -> 119`, `39 -> 35`, `9 -> 8`
  - `6.25`: `115 -> 118`, `39 -> 36`, `8 -> 9`
  - `0`: `115 -> 116`, `39 -> 39`, `8 -> 7`
- Persona drift remains effectively identical across `full_kv`, `quantized_old_kv`, and `fidelity_paged_kv` in this suite, so the FPA edge is coming from recall/reasoning preservation, not a universal reduction in all failure modes.

## Latency Read

- The earlier 60-sample picture made Python/MPS latency look like a likely loss for FPA.
- The 250-sample full-matrix run keeps the same broad read:
  - `50`: clear win, `12.143` vs `14.594` for `quantized_old_kv`
  - `25`: slight loss, `12.093` vs `11.868`
  - `12.5`: slight loss, `12.442` vs `11.997`
  - `6.25`: parity-to-slight win, `12.064` vs `12.074`
  - `0`: slight win, `11.943` vs `11.998`
- The honest interpretation is:
  - Python/MPS is no longer a clear argument against FPA
  - the main FPA claim should still be framed as a memory/quality result first
  - native mixed-fidelity kernels remain the proper place to judge final systems efficiency

## Research Interpretation

- This is evidence for a transformer memory hierarchy result, not evidence that a new attention primitive has been proven.
- The clean research story is now:
  - `recent_only` is an invalid memory policy.
  - `quantized_old_kv` is a strong, simple baseline.
  - `fidelity_paged_kv` is a lower-memory variant that preserves and modestly improves task outcomes under memory pressure.
- The stronger takeaway from the 250-sample run is that top-1 agreement is not the right north star.
- Task behavior under constrained memory is the real target, and on that metric FPA is now ahead.

## Cross-Model Validation

Supportive second-model validation has now been completed on:

- `HuggingFaceTB/SmolLM2-1.7B-Instruct`
- `60` deterministic stress samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policies: `full_kv`, `recent_only`, `quantized_old_kv`, `fidelity_paged_kv`

The same qualitative shape holds.

- `recent_only` again collapses to `0.0` exact and `0.0` contains at every compressed budget.
- `quantized_old_kv` again preserves baseline-like behavior.
- `fidelity_paged_kv` again uses about `16.67%` less warm memory than `quantized_old_kv`.
- `fidelity_paged_kv` again improves task metrics over `quantized_old_kv`:
  - exact: `46.667 -> 48.333` at every tested budget
  - contains: `46.667 -> 50.0` at budgets `50`, `25`, `12.5`, and `6.25`
  - contains: `48.333 -> 48.333` at budget `0`

This is not yet a frozen second flagship baseline, but it is real cross-model support for the TMH framing:

- eviction fails
- compressed retention survives
- mixed-fidelity retention remains differentiated

Supportive larger-model validation has now also been completed on:

- `ibm-granite/granite-3.3-2b-instruct`
- `60` deterministic stress samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policies: `full_kv`, `recent_only`, `quantized_old_kv`, `fidelity_paged_kv`

The Granite result is especially useful because it is:

- ungated in this environment
- larger than the earlier Qwen/SmolLM2 validation models
- still consistent with the TMH story

Observed Granite shape:

- `recent_only` nearly fully collapses:
  - `50`: `1.667` exact / `1.667` contains
  - `25`, `12.5`, `6.25`, `0`: `0.0` exact / `0.0` contains
- `quantized_old_kv` preserves baseline behavior:
  - `58.333` exact at every budget
  - `66.667` contains at every budget
- `fidelity_paged_kv` remains differentiated:
  - `60.0` exact at every budget
  - `66.667` contains at every budget
  - about `16.25%` lower warm memory than `quantized_old_kv`
  - mostly lower latency than `quantized_old_kv`

This means the current evidence chain now includes:

- one frozen flagship baseline on Qwen-250
- one supportive cross-model validation on SmolLM2-60
- one supportive larger-model validation on Granite-60

## Native Runtime Observability

The native runtime now emits direct K/V fidelity census fields in residency artifacts:

- `raw_k_pages`
- `int8_k_pages`
- `int4_k_pages`
- `dropped_k_pages`
- `raw_v_pages`
- `int8_v_pages`
- `int4_v_pages`
- `dropped_v_pages`

This matters architecturally because it stops forcing report-time inference from policy names alone. Mixed-fidelity structure is now directly visible in the runtime’s own artifact surface.

## 30B ROCm Served-Model Layout Pressure

Status: `served-model layout-pressure thesis confirmed`

The 30B validation path now uses a live sock/vendored-vLLM endpoint on the GMK ROCm machine:

- model: `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- endpoint: `http://127.0.0.1:8000`
- server context: `2048`
- served baseline corpus: `artifacts/sock_endpoint_pressure/20260719-023427/result.json`
- stronger served corpus: `artifacts/sock_endpoint_pressure/20260719-040954/result.json`
- near-context preflight corpus: `artifacts/sock_endpoint_pressure/20260719-040147/result.json`

The standalone TMH harness compiles one page-native layout only:

- layout: `tmh_fidelity_paged_kv`
- prompt anchor: pinned `raw/raw`
- recent tail: hot `raw/raw`
- old early/middle-layer K/V: `int8/int4`
- old late-layer K/V: `int8/int8`
- cold/dropped KV: none

The standard 30B layout run produced:

- rows: `50`
- compiled plan ranges: `190`
- checked layer-pages: `149040`
- plan validation: `100%`
- cold bytes: `0`
- dropped K/V pages: `0`

The expanded 30B sweep produced:

- page sizes: `8`, `16`, `32`, `64`
- hot budgets: `75`, `50`, `25`, `12.5`, `6.25`, `3.125`, `0`
- rows: `280`
- compiled plan ranges: `1080`
- plan validation: `100%`
- warm old-KV reduction versus same-hot uniform-int8 old KV: `16.667%` across every swept page size and budget

Total effective KV reduction depends on how much KV remains hot/raw:

| page tokens | total reduction at 75% hot | total reduction at 0% hot |
| ---: | ---: | ---: |
| `8` | `2.271%` | `16.381%` |
| `16` | `2.133%` | `16.100%` |
| `32` | `1.903%` | `15.553%` |
| `64` | `1.574%` | `14.515%` |

The maxfit preflight sweep pushed the same 2048-context endpoint close to its loaded context ceiling:

- highest prompt-token cases: about `1.88k-1.90k`
- completion pressure source: `effective_max_tokens`
- rows: `280`
- compiled plan ranges: `1080`
- plan validation: `100%`
- warm old-KV reduction: `16.667%` across every swept page size and budget
- total effective reduction at `0%` hot: `15.106-16.463%`, depending on page size

The stronger standard endpoint run added repeated live serving measurements:

- profile: `standard`
- runs: `3`
- warmup runs: `1`
- concurrency levels: `1`, `2`, `4`
- elapsed wall time: `796.1613s`
- stream probes: `10`
- mean completion throughput shape:
  - concurrency `1`: about `28.875-30.186` tok/s by case
  - concurrency `2`: about `35.588-37.123` tok/s by case
  - concurrency `4`: about `69.126-71.287` tok/s by case
- mean streaming TTFT range: about `0.106-0.180s`

The layout sweep regenerated from that stronger served corpus matched the earlier standard sweep:

- rows: `280`
- compiled plan ranges: `1080`
- plan validation: `100%`
- warm old-KV reduction: `16.667%` across every swept page size and budget

Interpretation:

- The original `16-17%` warm-memory reduction has held at 30B served-model scale.
- The result is strongest when stated as old/warm KV pressure reduction; total effective pressure reduction is lower when most KV remains hot/raw, as expected.
- The 30B evidence is currently a compiled layout-pressure validation tied to real sock endpoint traffic, not yet a live vLLM runtime executing TMH-managed KV internally.

## Artifact Paths

- production verify json: `/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify.report.json`
- production verify markdown: `/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify.report.md`
- production verify trace: `/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify.trace.fozzy`
- production verify markdown, frozen Qwen baseline: `/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_qwen_250.report.md`
- production verify markdown, SmolLM2 cross-model validation: `/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_smollm2_60.report.md`
- production verify markdown, Granite larger-model validation: `/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_granite_60.report.md`
- real eval combined manifest: `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/manifest_combined.json`
- real eval combined summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/summary.csv`
- real eval combined stress summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/summary_stress_suite.csv`
- real eval combined failure summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/summary_failures.csv`
- real eval tail manifest: `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_tail/manifest_20260702_034155.json`
- SmolLM2 validation manifest: `/Users/deepsaint/Desktop/kv-tiered/results_real/HuggingFaceTB_SmolLM2-1.7B-Instruct_stress60/manifest_20260702_064110.json`
- SmolLM2 validation summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/HuggingFaceTB_SmolLM2-1.7B-Instruct_stress60/summary.csv`
- SmolLM2 validation failure summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/HuggingFaceTB_SmolLM2-1.7B-Instruct_stress60/summary_failures.csv`
- Granite validation manifest: `/Users/deepsaint/Desktop/kv-tiered/results_real/ibm-granite_granite-3.3-2b-instruct_stress60/manifest_20260702_084407.json`
- Granite validation summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/ibm-granite_granite-3.3-2b-instruct_stress60/summary.csv`
- Granite validation failure summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/ibm-granite_granite-3.3-2b-instruct_stress60/summary_failures.csv`
- planner-matrix v1 manifest: `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v1/manifest_20260702_105624.json`
- planner-matrix v1 summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v1/summary.csv`
- planner-matrix v1 failure summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v1/summary_failures.csv`
- planner-matrix v3 control summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary.csv`
- planner-matrix v3 control failure summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_failures.csv`
- planner-matrix v3 control per-sample summary csv: `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_per_sample.csv`
- 30B sock endpoint pressure report: `/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-023427/REPORT.md`
- 30B stronger sock endpoint pressure report: `/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-040954/REPORT.md`
- 30B TMH-only layout report: `/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_only_30b_layout/20260719-034739/REPORT.md`
- 30B TMH layout sweep report: `/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_layout_sweep/20260719-035609/REPORT.md`
- 30B stronger standard layout sweep report: `/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_standard_runs3_layout_sweep/20260719-041243/REPORT.md`
- 30B maxfit preflight report: `/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-040147/REPORT.md`
- 30B maxfit preflight layout sweep report: `/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_maxfit_preflight_layout_sweep/20260719-040423/REPORT.md`
- 30B TMH layout sweep Fozzy trace: `/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_layout_sweep.trace.fozzy`
- 30B stronger standard layout sweep Fozzy trace: `/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_standard_runs3_layout_sweep.trace.fozzy`
- 30B maxfit preflight layout sweep Fozzy trace: `/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_maxfit_preflight_layout_sweep.trace.fozzy`

## Planner Matrix V1

The first explicit planner matrix now lives at:

- `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v1/summary.csv`
- `/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v1/summary_failures.csv`

Scope:

- model: `Qwen/Qwen2.5-1.5B-Instruct`
- samples: `24`
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policies:
  - `quantized_old_kv`
  - `fpa_no_plan`
  - `plan_v0_prompt_anchor_raw`
  - `plan_v1_anchor_k_protected`
  - `plan_v1_structured_protect`

High-signal outcome:

- `recent_only` still fails decisively
- `fpa_no_plan` beats `quantized_old_kv` on task score at budgets `50`, `25`, `12.5`, and `6.25` while using less warm memory
- `plan_v0_prompt_anchor_raw` matches those gains at the higher budgets but overpays in warm bytes and slips at `6.25`
- `plan_v1_anchor_k_protected` removes most of the raw-anchor byte tax relative to `plan_v0`
- `plan_v1_structured_protect` is nearly identical to `plan_v1_anchor_k_protected` on this run
- neither plan-v1 variant surpasses `fpa_no_plan` on the current `24`-sample matrix

Representative numbers:

- budget `50`
  - `quantized_old_kv`: task `60.417`, warm `803174`
  - `fpa_no_plan`: task `64.583`, warm `674092`
  - `plan_v1_anchor_k_protected`: task `64.583`, warm `864556`
- budget `25`
  - `quantized_old_kv`: task `60.417`, warm `1203308`
  - `fpa_no_plan`: task `64.583`, warm `1009919`
  - `plan_v1_anchor_k_protected`: task `64.583`, warm `1200383`
- budget `6.25`
  - `quantized_old_kv`: task `60.417`, warm `1529452`
  - `fpa_no_plan`: task `62.5`, warm `1283647`
  - `plan_v1_anchor_k_protected`: task `60.417`, warm `1474111`

## Planner Matrix V2

The next focused planner revision isolates the query anchor instead of the prompt head:

- model: `Qwen/Qwen2.5-1.5B-Instruct`
- samples: `24`
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policies:
  - `quantized_old_kv`
  - `fpa_no_plan`
  - `plan_v2_query_anchor_k_protected`

Artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary_per_sample.csv)

High-signal outcome:

- `plan_v2_query_anchor_k_protected` is the first explicit planner variant that is actually competitive with `fpa_no_plan`
- at budgets `50`, `25`, and `12.5`, it matches `fpa_no_plan` exactly on task score while preserving the same warm-memory footprint
- at budget `6.25`, it still matches `fpa_no_plan` on task score with only a small warm-byte increase
- at budget `0`, it improves on `fpa_no_plan`:
  - task: `62.5` vs `60.417`
  - exact: `54.167` vs `50.0`
  - contains: both `70.833`
- even at budget `0`, `plan_v2_query_anchor_k_protected` remains below `quantized_old_kv` on warm bytes:
  - `1463986` vs `1608320`

Representative numbers:

- budget `50`
  - `quantized_old_kv`: task `60.417`, warm `803174`
  - `fpa_no_plan`: task `64.583`, warm `674092`
  - `plan_v2_query_anchor_k_protected`: task `64.583`, warm `674092`
- budget `6.25`
  - `quantized_old_kv`: task `60.417`, warm `1529452`
  - `fpa_no_plan`: task `62.5`, warm `1283647`
  - `plan_v2_query_anchor_k_protected`: task `62.5`, warm `1293038`
- budget `0`
  - `quantized_old_kv`: task `60.417`, warm `1608320`
  - `fpa_no_plan`: task `60.417`, warm `1349840`
  - `plan_v2_query_anchor_k_protected`: task `62.5`, warm `1463986`

Interpretation:

- the planner story is now materially stronger than after v1
- protecting the query anchor is a better compile-time object than protecting the first prompt page
- the remaining question is not whether a compiled plan can matter
- it is whether `plan_v2_query_anchor_k_protected` keeps this edge when sample count scales beyond `24`

## Planner Matrix V2 Confirmation

The larger confirmation sweep for `plan_v2_query_anchor_k_protected` now exists on:

- model: `Qwen/Qwen2.5-1.5B-Instruct`
- samples: `60`
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policies:
  - `quantized_old_kv`
  - `fpa_no_plan`
  - `plan_v2_query_anchor_k_protected`

Artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary_per_sample.csv)

High-signal outcome:

- `plan_v2_query_anchor_k_protected` confirms as a real planner direction rather than a 24-sample accident
- at budgets `50`, `25`, and `12.5`, it matches `fpa_no_plan` exactly on task score, exact, contains, and warm bytes
- at budget `6.25`, it still matches `fpa_no_plan` on task score, exact, and contains while paying only `6931` extra warm bytes
- at budget `0`, it beats `fpa_no_plan`:
  - task: `60.0` vs `59.167`
  - exact: `51.667` vs `50.0`
  - contains: both `68.333`
- at budget `0`, it still uses less warm memory than `quantized_old_kv`:
  - `1488023` vs `1649536`

Representative numbers:

- budget `50`
  - `quantized_old_kv`: task `59.167`, warm `825896`
  - `fpa_no_plan`: task `60.833`, warm `693163`
  - `plan_v2_query_anchor_k_protected`: task `60.833`, warm `693163`
- budget `6.25`
  - `quantized_old_kv`: task `59.167`, warm `1571337`
  - `fpa_no_plan`: task `60.0`, warm `1318800`
  - `plan_v2_query_anchor_k_protected`: task `60.0`, warm `1325731`
- budget `0`
  - `quantized_old_kv`: task `59.167`, warm `1649536`
  - `fpa_no_plan`: task `59.167`, warm `1384432`
  - `plan_v2_query_anchor_k_protected`: task `60.0`, warm `1488023`

Interpretation:

- the v2 planner result holds up at larger sample count
- the planner is not yet broadly better than heuristic FPA
- but it is now honestly supported as competitive at moderate budgets and slightly better at the tightest budget
- that is enough to keep `TMHMemoryPlan` on the main research path

## Planner Matrix V3

The next planner revision adds selective numeric-head protection on top of the query-anchor plan:

- model: `Qwen/Qwen2.5-1.5B-Instruct`
- samples: `24`
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policies:
  - `quantized_old_kv`
  - `fpa_no_plan`
  - `plan_v2_query_anchor_k_protected`
  - `plan_v3_query_anchor_numeric_head_k_protected`

Artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary_per_sample.csv)

Probe outcome:

- `plan_v3_query_anchor_numeric_head_k_protected` stays equal to `plan_v2_query_anchor_k_protected` at budgets `50`, `25`, and `12.5`
- at budget `6.25`, it improves over both `fpa_no_plan` and `plan_v2_query_anchor_k_protected`:
  - task `64.583` vs `62.5`
  - contains `75.0` vs `70.833`
- at budget `0`, it improves again:
  - task `64.583` vs `60.417` for `fpa_no_plan`
  - task `64.583` vs `62.5` for `plan_v2_query_anchor_k_protected`
  - contains `75.0` vs `70.833`

Representative numbers:

- budget `6.25`
  - `quantized_old_kv`: task `60.417`, warm `1529452`
  - `fpa_no_plan`: task `62.5`, warm `1283647`
  - `plan_v2_query_anchor_k_protected`: task `62.5`, warm `1293038`
  - `plan_v3_query_anchor_numeric_head_k_protected`: task `64.583`, warm `1324782`
- budget `0`
  - `quantized_old_kv`: task `60.417`, warm `1608320`
  - `fpa_no_plan`: task `60.417`, warm `1349840`
  - `plan_v2_query_anchor_k_protected`: task `62.5`, warm `1463986`
  - `plan_v3_query_anchor_numeric_head_k_protected`: task `64.583`, warm `1495730`

Probe interpretation:

- `plan_v3_query_anchor_numeric_head_k_protected` was the first planner variant to move beyond simple competitiveness with heuristic FPA
- the gain was not broad or mysterious
- it came from preserving the multihop rescue already found by `plan_v2` and adding a recovered numeric-head case at the tightest budgets
- the extra warm-byte cost over `plan_v2_query_anchor_k_protected` was real but modest relative to the recovered task behavior

## Planner Matrix V3 Control

The larger completed control now exists at:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_per_sample.csv)

Scope:

- model: `Qwen/Qwen2.5-1.5B-Instruct`
- samples: `60`
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policies:
  - `quantized_old_kv`
  - `fpa_no_plan`
  - `plan_v2_query_anchor_k_protected`
  - `plan_v3_query_anchor_numeric_head_k_protected`

High-signal outcome:

- `plan_v3_query_anchor_numeric_head_k_protected` matches `fpa_no_plan` and `plan_v2_query_anchor_k_protected` at budgets `50`, `25`, and `12.5`
  - task `60.833`
  - contains `70.0`
- at budget `6.25`, `plan_v3_query_anchor_numeric_head_k_protected` is ahead:
  - `quantized_old_kv`: task `59.167`, warm `1571337`
  - `fpa_no_plan`: task `60.0`, warm `1318800`
  - `plan_v2_query_anchor_k_protected`: task `60.0`, warm `1325731`
  - `plan_v3_query_anchor_numeric_head_k_protected`: task `60.833`, warm `1357475`
- at budget `0`, it stays ahead:
  - `quantized_old_kv`: task `59.167`, warm `1649536`
  - `fpa_no_plan`: task `59.167`, warm `1384432`
  - `plan_v2_query_anchor_k_protected`: task `60.0`, warm `1488023`
  - `plan_v3_query_anchor_numeric_head_k_protected`: task `60.833`, warm `1519767`

Failure-shape outcome:

- `plan_v3_query_anchor_numeric_head_k_protected` preserves the same broad better-than-quantized failure shape as `fpa_no_plan` and `plan_v2_query_anchor_k_protected`
- the differentiator over `plan_v2_query_anchor_k_protected` remains the recovered numeric-head case:
  - at budgets `6.25` and `0`, `plan_v2_query_anchor_k_protected` has `numeric_mismatch 2` and `contains_target 10`
  - at the same budgets, `plan_v3_query_anchor_numeric_head_k_protected` has `numeric_mismatch 1` and `contains_target 11`
- the per-sample artifact shows the concrete rescued case is still `suite_numbers_015`

Interpretation:

- the planner boundary is now supported by a finished larger control, not only a 24-sample probe
- the first selective planner now matches heuristic FPA at moderate budgets and beats it at the tightest budgets
- the edge remains narrow and interpretable rather than diffuse
- that is exactly the kind of result worth freezing for paper-facing claims
