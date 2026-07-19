# TMH Paper Draft Support

## Purpose

This note exists to directly support the first real TMH paper draft.

It is not the full paper.

It is the staging ground for:

- the exact claim ladder
- the current evidence table
- the honest boundaries
- the most likely reviewer questions
- the next evidence needed before an arXiv-ready draft

## Working Paper Claim

The strongest current draft claim is:

> Transformer inference benefits from explicitly managing KV memory fidelity in the runtime rather than treating all KV state as uniform.

This is stronger and more accurate than:

- "we found a better KV compression trick"
- "we invented a new attention mechanism"

## Claim Ladder

### Claim 0: Runtime Reality

We have a real runtime and benchmark path, not just a toy simulation.

Support:

- real-model harness
- host-backed artifact production
- deterministic scenario tooling
- policy-comparable production reports

### Claim 1: Eviction Fails

Old KV cannot simply be dropped under stress.

Support:

- `recent_only` catastrophically fails on Qwen-250
- `recent_only` catastrophically fails on SmolLM2-60

### Claim 2: Compressed Retention Works

Old KV does not need to remain hot and raw to preserve behavior.

Support:

- `quantized_old_kv` remains near-baseline on both Qwen and SmolLM2

### Claim 3: Mixed-Fidelity Runtime Management Is Useful

A mixed-fidelity policy can reduce warm-memory footprint while modestly improving task behavior.

Support:

- `fidelity_paged_kv` beats `quantized_old_kv` on exact/contains across the frozen Qwen-250 baseline
- `fidelity_paged_kv` beats `quantized_old_kv` on the supportive SmolLM2-60 validation
- warm-memory reduction remains stable at about `16-17%`
- 30B ROCm served-model layout sweeps preserve the same `16.667%` old/warm KV pressure reduction across page sizes and hot budgets

### Claim 4: TMH Is A Better Abstraction Boundary

The project’s evidence is better explained by heterogeneous memory management than by a new attention primitive.

Support:

- the same qualitative pattern survives across multiple models
- top-1 imitation and task behavior diverge
- the strongest wins are shaped like memory/behavior tradeoffs, not kernel novelty alone

### Claim 5: Compile/Execute Is A Plausible Next Runtime Boundary

The project now has initial evidence that a prefill-compiled memory plan is a meaningful systems primitive.

Support:

- `TMHMemoryPlan` now exists in the runtime and real-model harness
- the decode/runtime path can consume a compiled plan without breaking the benchmark flow
- plan-driven behavior moved measurably on the focused Qwen run
- the first prototype also produced a useful negative result, which is strong evidence that the boundary is real rather than decorative

## Current Evidence Table

### Qwen2.5-1.5B-Instruct

Flagship baseline:

- samples: `250`
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- result:
  - `recent_only`: `0.0` exact / `0.0` contains at every budget
  - `quantized_old_kv`: `46.0-46.4` exact / `64.0-64.4` contains
  - `fidelity_paged_kv`: `46.4-48.0` exact / `64.8-66.4` contains
  - FPA warm memory: about `16.1%` lower than `quantized_old_kv`

Primary artifacts:

- [manifest_combined.json](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/manifest_combined.json)
- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/summary_failures.csv)
- [production_verify_qwen_250.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_qwen_250.report.md)

### SmolLM2-1.7B-Instruct

Supportive cross-model validation:

- samples: `60`
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- result:
  - `recent_only`: `0.0` exact / `0.0` contains at every budget
  - `quantized_old_kv`: `46.667` exact / `46.667-48.333` contains
  - `fidelity_paged_kv`: `48.333` exact / `48.333-50.0` contains
  - FPA warm memory: about `16.67%` lower than `quantized_old_kv`

Primary artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/HuggingFaceTB_SmolLM2-1.7B-Instruct_stress60/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/HuggingFaceTB_SmolLM2-1.7B-Instruct_stress60/summary_failures.csv)
- [production_verify_smollm2_60.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_smollm2_60.report.md)

### Third-Model Slot

This slot has now been filled with a larger ungated model:

- `ibm-granite/granite-3.3-2b-instruct`
- `60` stress samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`

Observed shape:

- `recent_only` still collapses as a policy:
  - `50`: `1.667` exact / `1.667` contains
  - `25`, `12.5`, `6.25`, `0`: `0.0` exact / `0.0` contains
- `quantized_old_kv` preserves baseline behavior:
  - exact: `58.333` at every tested budget
  - contains: `66.667` at every tested budget
- `fidelity_paged_kv` remains differentiated:
  - exact: `60.0` at every tested budget
  - contains: `66.667` at every tested budget
  - warm memory: about `16.25%` lower than `quantized_old_kv`
  - latency: mostly lower than `quantized_old_kv`, with near-parity at `12.5`

Primary artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/ibm-granite_granite-3.3-2b-instruct_stress60/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/ibm-granite_granite-3.3-2b-instruct_stress60/summary_failures.csv)
- [production_verify_granite_60.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_granite_60.report.md)

### Qwen3-30B-A3B-GPTQ-Int4 On ROCm

Served-model layout-pressure validation:

- model: `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- serving path: sock CLI over vendored vLLM on ROCm
- endpoint profile: OpenAI-compatible completions endpoint
- server context: `2048`
- layout under test: `tmh_fidelity_paged_kv`
- page sizes swept: `8`, `16`, `32`, `64`
- hot budgets swept: `75`, `50`, `25`, `12.5`, `6.25`, `3.125`, `0`

Observed shape:

- standard measured endpoint corpus:
  - rows: `280`
  - compiled plan ranges: `1080`
  - plan validation: `100%`
  - warm old-KV reduction versus same-hot uniform-int8 old KV: `16.667%` across all page sizes and budgets
  - total effective KV reduction at `0%` hot: `14.515-16.381%`, depending on page size
- stronger standard endpoint corpus:
  - live runs: `3`
  - warmup runs: `1`
  - concurrency levels: `1`, `2`, `4`
  - elapsed wall time: `796.1613s`
  - mean completion throughput by case: about `28.875-30.186` tok/s at concurrency `1`, `35.588-37.123` tok/s at concurrency `2`, and `69.126-71.287` tok/s at concurrency `4`
  - streaming TTFT range: about `0.106-0.180s`
  - regenerated layout sweep: `280` rows, `1080` compiled plan ranges, `100%` plan validation, `16.667%` warm old-KV reduction everywhere
- maxfit preflight corpus:
  - prompt lengths pushed to about `1.88k-1.90k` tokens under the `2048` context cap
  - rows: `280`
  - compiled plan ranges: `1080`
  - plan validation: `100%`
  - warm old-KV reduction: `16.667%` across all page sizes and budgets
  - total effective KV reduction at `0%` hot: `15.106-16.463%`, depending on page size

Primary artifacts:

- [standard endpoint report](/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-023427/REPORT.md)
- [standard layout sweep report](/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_layout_sweep/20260719-035609/REPORT.md)
- [stronger standard endpoint report](/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-040954/REPORT.md)
- [stronger standard layout sweep report](/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_standard_runs3_layout_sweep/20260719-041243/REPORT.md)
- [maxfit endpoint preflight report](/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-040147/REPORT.md)
- [maxfit layout sweep report](/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_maxfit_preflight_layout_sweep/20260719-040423/REPORT.md)
- [standard sweep Fozzy trace](/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_layout_sweep.trace.fozzy)
- [stronger standard sweep Fozzy trace](/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_standard_runs3_layout_sweep.trace.fozzy)
- [maxfit sweep Fozzy trace](/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_maxfit_preflight_layout_sweep.trace.fozzy)

Paper-facing interpretation:

- This is the first 30B-class evidence that the memory-pressure result survives served-model prompt shapes on the AMD/ROCm machine.
- The clean paper claim is not that total memory drops by `16.667%` in every serving configuration. The precise claim is that the old/warm KV component drops by `16.667%` versus a same-hot uniform-int8 old-KV baseline; total effective KV pressure approaches that value as the hot raw window shrinks.
- This is layout-pressure evidence tied to real endpoint traffic. The next systems evidence must wire TMH-managed KV into the live vLLM runtime path and measure actual runtime effects under the same traffic.

### TMHMemoryPlan Prototype

Focused compiler-boundary check:

- model: `Qwen/Qwen2.5-1.5B-Instruct`
- samples: `24`
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policy shape:
  - prompt-anchor pinned `raw/raw`
  - recent tail `raw/raw`
  - older pages mixed by layer

Observed shape:

- at `50`, `25`, and `12.5`, plan-driven `fidelity_paged_kv` beat `quantized_old_kv` on exact and contains
- warm memory also increased materially versus `quantized_old_kv`
- at `6.25` and `0`, the quality edge faded while the warm-byte overhead remained

Primary lesson:

- the compile/execute boundary is real
- plan v0 is too blunt to claim the best quality/memory trade-off
- the next metric should be quality relative to warm-byte cost

Primary artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_tmh_plan_v0/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_tmh_plan_v0/summary_failures.csv)
- [production_verify_qwen24_tmh_plan_v0.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_qwen24_tmh_plan_v0.report.md)

### Explicit Planner Matrix V1

The next explicit planner matrix now exists on:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `24` stress samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`

Primary artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v1/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v1/summary_failures.csv)

Observed shape:

- `plan_v1_anchor_k_protected` successfully removes most of the byte tax introduced by `plan_v0_prompt_anchor_raw`
- `plan_v1_structured_protect` does not meaningfully separate from `plan_v1_anchor_k_protected`
- neither plan-v1 variant beats `fpa_no_plan` on quality per warm byte
- `fpa_no_plan` remains the strongest policy in this matrix

Paper-relevant lesson:

- the runtime boundary is increasingly justified
- the current planner heuristics are not yet the headline empirical win
- the paper should treat `TMHMemoryPlan` as a serious runtime direction, but not yet as the best policy family

### Explicit Planner Matrix V2

The next focused planner matrix now adds a more surgical anchor target on:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `24` stress samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`

Primary artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary_per_sample.csv)

Observed shape:

- `plan_v2_query_anchor_k_protected` protects only the last prompt page rather than the first prompt page
- at budgets `50`, `25`, and `12.5`, it matches `fpa_no_plan` on task score and warm bytes
- at budget `6.25`, it still matches `fpa_no_plan` on task score with only a small warm-byte increase
- at budget `0`, it beats `fpa_no_plan` on task score and exact while remaining below `quantized_old_kv` on warm bytes

Paper-relevant lesson:

- the planner story is now stronger than "the boundary exists but heuristics lag"
- a compiled plan can become competitive once it protects the right memory object
- the right object appears closer to the query anchor than the prompt head
- this is still not license to claim planner dominance in general until the same shape survives a larger sweep

### Explicit Planner Matrix V2 Confirmation

That larger sweep has now been completed on:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `60` stress-suite samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`

Primary artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary_per_sample.csv)

Observed shape:

- `plan_v2_query_anchor_k_protected` matches `fpa_no_plan` exactly at budgets `50`, `25`, and `12.5`
- it still matches `fpa_no_plan` at `6.25` with only a negligible warm-byte increase
- at `0`, it improves over `fpa_no_plan`:
  - task `59.167 -> 60.0`
  - exact `50.0 -> 51.667`
  - contains unchanged at `68.333`
- at `0`, it still uses less warm memory than `quantized_old_kv`

Paper-relevant lesson:

- the planner result now survives a meaningfully larger confirmation sweep
- the right honest paper line is no longer merely "planner boundary exists"
- it is "a compiled query-anchor planner is competitive with heuristic FPA and slightly better at the tightest tested budget"
- the draft should still avoid claiming that the planner family is already the main empirical win of TMH overall

### Explicit Planner Matrix V3 Probe

The next planner revision now adds selective numeric-head protection on top of the query-anchor plan:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `24` stress-suite samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`

Primary artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary_per_sample.csv)

Observed shape:

- `plan_v3_query_anchor_numeric_head_k_protected` stays flat with `plan_v2_query_anchor_k_protected` at budgets `50`, `25`, and `12.5`
- at budget `6.25`, it improves over both `fpa_no_plan` and `plan_v2_query_anchor_k_protected`:
  - task `62.5 -> 64.583`
  - contains `70.833 -> 75.0`
- at budget `0`, it improves again:
  - task `62.5 -> 64.583` over `plan_v2_query_anchor_k_protected`
  - task `60.417 -> 64.583` over `fpa_no_plan`
  - contains `70.833 -> 75.0`

Paper-relevant lesson:

- this is the first planner variant that moves beyond mere competitiveness with heuristic FPA
- the gain is narrow and interpretable rather than diffuse
- query-anchor protection appears necessary for the multihop rescue
- selective numeric-head protection appears to recover a separate tight-budget failure family

### Explicit Planner Matrix V3 Completed Control

The larger control is now complete:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_per_sample.csv)

Observed completed shape:

- budgets `50`, `25`, and `12.5`:
  - `fpa_no_plan`: task `60.833`, contains `70.0`
  - `plan_v2_query_anchor_k_protected`: task `60.833`, contains `70.0`
  - `plan_v3_query_anchor_numeric_head_k_protected`: task `60.833`, contains `70.0`
- budget `6.25`:
  - `fpa_no_plan`: task `60.0`, contains `68.333`
  - `plan_v2_query_anchor_k_protected`: task `60.0`, contains `68.333`
  - `plan_v3_query_anchor_numeric_head_k_protected`: task `60.833`, contains `70.0`
- budget `0`:
  - `fpa_no_plan`: task `59.167`, contains `68.333`
  - `plan_v2_query_anchor_k_protected`: task `60.0`, contains `68.333`
  - `plan_v3_query_anchor_numeric_head_k_protected`: task `60.833`, contains `70.0`

Paper-relevant lesson:

- the `v3` direction is now frozen by a completed larger sweep rather than only supported by a partial run
- the gain remains concentrated in the same numeric-head recovery rather than turning into unexplained drift
- this is exactly the form of planner evidence we want for the draft: modest, repeatable, and interpretable

## Reviewer-Critical Points

These are the questions the draft must answer cleanly.

1. Why is this not just another KV quantization paper?
2. Why is the right framing runtime memory hierarchy rather than policy-specific tuning?
3. Why should exact/contains matter more than top-1 agreement here?
4. How robust is the claim across models, workloads, and budgets?
5. Is the policy win real if latency is only neutral?
6. Why is `TMHMemoryPlan` more than repackaged heuristics?
7. How should plan quality be judged relative to memory cost?

## Honest Answers

### Why not just quantization?

Because the evidence is not only that compression helps.

The evidence is that:

- eviction and demotion behave qualitatively differently
- K and V can be treated asymmetrically
- runtime residency policy is part of the algorithmic surface
- the same general pattern now holds across Qwen 1.5B, SmolLM2 1.7B, and Granite 3.3 2B

### Why not call this a new attention mechanism?

Because the strongest stable effects are about:

- what memory stays resident
- at what fidelity
- in what tier
- with what behavior tradeoff

That is a memory-management result first.

### Why do task metrics matter more than top-1?

Because the runs show that higher top-1 imitation does not necessarily produce better task outcomes under memory pressure.

The system goal is preserved behavior, not token-by-token imitation.

### Why does the compile/execute framing matter?

Because the old runtime architecture decided memory treatment mostly after memory had already been created.

`TMHMemoryPlan` introduces a stronger boundary:

- prefill can classify and propose memory intent while it still has the richest prompt context
- decode can execute and revise rather than guessing everything reactively

The first prototype does not prove the best planner yet.

It does show that the planner boundary is implementable and behaviorally meaningful.

## Draft Structure Suggestion

1. Introduction
2. Why flat KV is the wrong abstraction
3. TMH abstraction
4. Runtime design
5. Policies and ablations
6. Evaluation
7. Limitations
8. Future work

## Next Evidence Needed

1. One more modern model family result.
2. At least one workload-family expansion beyond the current stress suite.
3. Native mixed-fidelity timing beyond Python/MPS-dominated execution.
4. Additional observability for tier hits, byte movement, and K/V fidelity composition.
5. A minimal classifier-style plan to test whether the current `v3` edge comes from general structural categories rather than benchmark-specific tuning.

## Current Bottom Line

The draft should now treat:

- TMH as the contribution
- FPA as policy v1
- Qwen-250 as the flagship evidence
- SmolLM2-60 as supportive cross-model evidence
- Granite-60 as larger-model supportive evidence
- the next major step as workload expansion plus plan-v1 ablations rather than another emergency model switch
