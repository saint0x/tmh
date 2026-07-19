# TMH

## Purpose

This document is the architectural reference for `Transformer Memory Hierarchy`.

It captures:

- how the project got here
- what the strongest honest empirical claim is
- what TMH now means architecturally
- why `TMHMemoryPlan` is the next serious primitive
- what the first implementation should and should not try to do
- where ongoing nuanced findings are being logged for the paper path

The running nuanced findings ledger lives in:

- [FINDINGS.md](/Users/deepsaint/Desktop/kv-tiered/tmh/FINDINGS.md)

## How We Got Here

The project did not begin with this framing.

It began closer to:

- can we compress KV?
- can we keep old KV cheaper?
- can a fidelity-aware page policy preserve model behavior?

The runtime and benchmark work changed the abstraction boundary.

Repeated evidence across:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `HuggingFaceTB/SmolLM2-1.7B-Instruct`
- `ibm-granite/granite-3.3-2b-instruct`
- `Qwen/Qwen3-30B-A3B-GPTQ-Int4` served through sock/vendored vLLM on ROCm for layout-pressure validation

kept showing the same qualitative pattern:

1. `recent_only` fundamentally changes behavior under memory pressure.
2. `quantized_old_kv` preserves baseline behavior much better.
3. `fidelity_paged_kv` consistently improves the memory/task trade-off modestly while reducing warm-memory footprint by about `16%`.

That changed the working thesis.

The project is no longer best described as:

- a new attention mechanism
- one more KV quantization trick

It is better described as:

- a runtime model for transformer memory

## Strongest Honest Claim

The strongest honest claim currently supported by the data is:

> Transformer inference benefits from explicitly managing KV memory as a heterogeneous hierarchy rather than treating all KV state as uniform.

More concretely:

- evicting old KV is not a viable memory policy under stress
- retaining old KV in compressed form preserves behavior substantially better
- a fidelity-aware retention policy can improve task outcomes modestly while reducing warm-memory footprint
- at 30B served-model scale, the compiled TMH layout preserves a `16.667%` old/warm KV pressure reduction across swept page sizes and hot budgets

This is stronger than the starting claim, but still narrower than a universal law.

TMH is supported.

Universal generality is not yet proven.

## The Architectural Problem

The current runtime before this step looked like:

Prefill
  ↓
Raw page construction
  ↓
BlockManager infers page treatment from:
  - recency
  - layer position
  - policy label
  - hot-window geometry
  ↓
Decode

That was enough to validate TMH as an abstraction.

But it left one major weakness:

- `BlockManager` was still guessing after memory had already been created

It knew where a page was.

It did not know what the page meant.

## The New Primitive

The next serious primitive is:

`TMHMemoryPlan`

The architecture becomes:

Prefill
  ↓
TMH Prefill Compiler
  ↓
TMHMemoryPlan
  ↓
BlockManager
  ↓
Decode Runtime

This is the crucial shift:

before:
  `BlockManager` guesses from recency, layer, and policy label

after:
  `BlockManager` executes a compiled memory plan and adapts only when runtime pressure requires it

That is a stronger systems abstraction.

## Why Prefill Is The Right Place

Prefill is the one phase where the runtime has the richest information.

During prefill, the system can know:

- full prompt extent
- prompt boundaries
- system prompt and instruction regions
- retrieved context spans
- repeated boilerplate
- prompt head vs prompt tail
- stable token positions before decode begins

Decode does not have this full-context view.

Decode sees one token step at a time.

So the right question is not:

- should decode guess better?

It is:

- how much of the memory hierarchy can be synthesized correctly before decode begins?

## What TMHMemoryPlan Should Be

The first version should stay page-native.

It should not jump immediately to a semantic memory DAG.

The right v1 shape is a compiled page-range intent object.

Example:

`PageRangePlan`

- `layer_range`
- `token_start`
- `token_end`
- `semantic_class`
- `pin`
- `k_precision`
- `v_precision`
- `residency_tier`
- `promotion_priority`
- `demotion_priority`
- `recompute_priority`
- `authority`

The important field for runtime behavior is `authority`.

It allows a distinction between:

- hard constraint
- default
- hint

That makes the plan authoritative but revisable.

## The v0 Compiler

The first implementation should be simple and robust.

It should not depend on learned salience, unstable heuristics, or opaque semantic classifiers.

The first useful signals are:

- prompt head
- prompt body
- recent decode tail
- late-layer old memory
- plain old compressed history

This repo’s first small runtime implementation uses exactly that style.

For the current `fidelity_paged_kv` path, the compiler now emits a minimal page-native plan that:

- pins the first prompt page as a `prompt_anchor`
- keeps recent tail pages `raw/raw`
- keeps older history at reduced fidelity
- preserves late-layer value fidelity more than earlier layers

This is intentionally modest.

It is not the full research destination.

It is the first compile/execute proof point.

## The First Prototype In This Repo

The first small prototype now exists in two aligned places:

- [tmh_plan.fzy](/Users/deepsaint/Desktop/kv-tiered/tmh/src/runtime/tmh_plan.fzy)
- [run_real_eval.py](/Users/deepsaint/Desktop/kv-tiered/python/kv_tiered_real/run_real_eval.py)

The current implementation is intentionally conservative.

It does not attempt rich semantic classification yet.

Instead it compiles a simple plan for the `fidelity_paged_kv` path:

- first prompt page:
  - semantic class: `prompt_anchor`
  - pinned
  - `raw/raw`
- recent tail pages:
  - semantic class: `recent_tail`
  - `raw/raw`
- older history:
  - earlier layers: `int8/int4`
  - later layers: `int8/int8`

The runtime path then executes that plan rather than deriving the first prompt anchor only from generic recency/layer heuristics.

## 30B Served-Model Layout Evidence

The GMK ROCm validation pass adds a larger served-model evidence tier without changing sock production code.

Setup:

- model: `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- serving path: sock CLI over vendored vLLM
- endpoint: OpenAI-compatible completions and tokenize APIs
- server context: `2048`
- standard endpoint corpus: `artifacts/sock_endpoint_pressure/20260719-023427/result.json`
- stronger standard endpoint corpus: `artifacts/sock_endpoint_pressure/20260719-040954/result.json`
- maxfit preflight corpus: `artifacts/sock_endpoint_pressure/20260719-040147/result.json`

The standalone TMH harness compiles the same page-native plan shape used by the runtime concept:

- `prompt_anchor`: pinned `raw/raw`
- `recent_tail`: hot `raw/raw`
- `prefill_payload`: warm `int8/int4`
- `late_layer_payload`: warm `int8/int8`
- authority: `hard`

Standard measured endpoint sweep:

- page sizes: `8`, `16`, `32`, `64`
- hot budgets: `75`, `50`, `25`, `12.5`, `6.25`, `3.125`, `0`
- rows: `280`
- compiled plan ranges: `1080`
- plan validation: `100%`
- warm old-KV reduction versus same-hot uniform-int8 old KV: `16.667%` everywhere

Stronger repeated standard endpoint run:

- runs: `3`
- warmup runs: `1`
- concurrency levels: `1`, `2`, `4`
- elapsed wall time: `796.1613s`
- concurrency `4` throughput: about `69-71` completion tok/s by case
- streaming TTFT: about `0.106-0.180s`
- regenerated layout sweep: `280` rows, `1080` compiled plan ranges, `100%` plan validation, `16.667%` warm old-KV reduction everywhere

Maxfit near-context preflight sweep:

- prompt lengths: up to about `1.9k` tokens under the `2048` context cap
- rows: `280`
- compiled plan ranges: `1080`
- plan validation: `100%`
- warm old-KV reduction: `16.667%` everywhere
- total effective reduction at `0%` hot: `15.106-16.463%`, depending on page size

Interpretation:

- this confirms the memory-pressure side of the TMH claim at 30B served-model scale
- total effective savings are hot-window dependent, so the precise paper-safe statement is about old/warm KV pressure
- the next runtime milestone is to move from standalone layout-pressure validation to live TMH-managed KV execution inside the serving path

## What The Prototype Taught Us

The first benchmark pass on the plan-driven prototype was:

- model: `Qwen/Qwen2.5-1.5B-Instruct`
- samples: `24`
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- artifacts:
  - [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_tmh_plan_v0/summary.csv)
  - [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_tmh_plan_v0/summary_failures.csv)
  - [production_verify_qwen24_tmh_plan_v0.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_qwen24_tmh_plan_v0.report.md)

The result is important because it is mixed.

That is exactly the kind of thing we want to learn early.

At budgets `50`, `25`, and `12.5`:

- `quantized_old_kv`: `50.0` exact / `70.833` contains
- plan-driven `fidelity_paged_kv`: `54.167` exact / `75.0` contains

So the prototype improved task behavior meaningfully on that focused run.

But it also increased warm-memory footprint relative to `quantized_old_kv`:

- `50`: about `29.1%` higher warm bytes
- `25`: about `14.1%` higher warm bytes
- `12.5`: about `9.6%` higher warm bytes

At tighter budgets `6.25` and `0`:

- exact advantage disappeared
- contains advantage disappeared or reversed
- warm-memory overhead remained positive

This teaches an important lesson:

> the compile/execute boundary looks promising, but the first pinned prompt-anchor policy is too expensive in its current form to claim a better memory/quality trade-off overall

That is a good outcome.

It means the new primitive is doing real work and exposing real tradeoffs, not merely rephrasing the old heuristic.

The key lesson is not "plan v0 won."

The key lesson is:

- the planner boundary is real
- the first raw/raw anchor strategy is too blunt
- the next serious objective is quality per warm byte, not quality at any cost

## The Runtime Split

TMH should now be thought of as two cooperating subsystems.

### TMH Prefill Compiler

Responsible for:

- memory classification
- initial fidelity selection
- pinning decisions
- range-level residency intent
- emitting `TMHMemoryPlan`

### TMH Decode Runtime

Responsible for:

- executing the plan
- promotion
- demotion
- spill behavior
- adaptation under runtime pressure
- reporting planned vs realized layout

This is a much cleaner boundary than one large heuristic block manager.

## How This Fits The Current Code

Before this step:

- [session.fzy](/Users/deepsaint/Desktop/kv-tiered/tmh/src/runtime/session.fzy) computed session geometry and hot-window state
- [block_manager.fzy](/Users/deepsaint/Desktop/kv-tiered/tmh/src/runtime/block_manager.fzy) derived page treatment heuristically
- [residency.fzy](/Users/deepsaint/Desktop/kv-tiered/tmh/src/runtime/residency.fzy) reported what happened after the fact

After this step:

- [tmh_plan.fzy](/Users/deepsaint/Desktop/kv-tiered/tmh/src/runtime/tmh_plan.fzy) provides the first page-native `TMHMemoryPlan` compiler
- `session.manager_of(...)` now routes the main session path through a planned build
- `BlockManager` can execute a compiled plan instead of only deriving treatment from generic policy heuristics

This does not yet eliminate all heuristic logic.

It begins the transition.

## What This First Implementation Does Not Yet Do

It does not yet:

- classify retrieved documents explicitly
- classify code or numeric spans semantically
- use attention maps during prefill
- build token-object graphs
- learn the compiler
- compare planned vs realized memory layout in artifacts directly

Those are later steps.

The current job is proving the boundary is worth having.

## Why This Matters For The Paper

This reframes the project more cleanly:

Observation:

- transformer memory is heterogeneous

Failure mode:

- eviction changes behavior catastrophically

Baseline:

- compressed retention is surprisingly strong

Contribution:

- a fidelity-aware transformer memory hierarchy improves the memory/task trade-off

Extension:

- TMH is best understood as a compile/execute model for transformer memory

That is a stronger paper than:

- “we made one KV quantization policy somewhat better”

## Current Research Direction

The implementation and paper should now treat:

- TMH as the contribution
- `fidelity_paged_kv` as policy `v1`
- `TMHMemoryPlan` as the next primitive
- the prefill compiler as the next major subsystem
- decode as execution plus correction, not blind policy guessing

The next revision should likely make the prompt-anchor plan less blunt:

- smaller anchor coverage
- partial-fidelity anchoring
- selective pinning by prompt segment
- or softer authority levels rather than unconditional raw retention

The leading next comparisons should be:

- `quantized_old_kv`
- `fpa_no_plan`
- `plan_v0_prompt_anchor_raw`
- `plan_v1_anchor_k_protected`
- `plan_v1_structured_protect`
- `plan_v2_query_anchor_k_protected`

The leading next benchmark metric should be:

- `task_gain_per_extra_warm_byte`

That comparison surface is now implemented in the real-model harness, along with:

- `task_score_pct`
- `task_score_delta_vs_quantized`
- `warm_bytes_delta_vs_quantized`

## First Explicit Planner Matrix

The first explicit planner matrix has now been run on:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `24` stress samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policies:
  - `quantized_old_kv`
  - `fpa_no_plan`
  - `plan_v0_prompt_anchor_raw`
  - `plan_v1_anchor_k_protected`
  - `plan_v1_structured_protect`
  - `plan_v2_query_anchor_k_protected`

Artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v1/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v1/summary_failures.csv)

The first honest result was:

- `plan_v0_prompt_anchor_raw` confirmed the original concern
  - higher-budget gains
  - too much warm-byte tax
  - real degradation at tight budgets
- `plan_v1_anchor_k_protected` successfully removed most of that tax
- `plan_v1_structured_protect` did not materially separate from `plan_v1_anchor_k_protected`
- neither plan-v1 variant beat `fpa_no_plan` on this matrix

That means:

- the compile/execute boundary remains justified
- the first selective planner is cleaner than v0
- the planner policy itself is not yet the best-performing TMH policy

The next focused revision then changed the anchor target itself:

- `plan_v2_query_anchor_k_protected` protects only the last prompt page rather than the first prompt page
- this is a better match for the memory object decode is likely to route back through under pressure

Artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary_per_sample.csv)

The v2 result is the first planner outcome that is actually competitive:

- at budgets `50`, `25`, and `12.5`, `plan_v2_query_anchor_k_protected` matches `fpa_no_plan` on task score and warm bytes
- at budget `6.25`, it still matches `fpa_no_plan` on task score with only a small warm-byte increase
- at budget `0`, it beats `fpa_no_plan` on task score and exact while staying below `quantized_old_kv` on warm bytes

That means the architectural read has sharpened again:

- compiled planning is not just implementable
- the identity of the protected memory object matters materially
- query-anchor protection is a stronger planning primitive than prompt-head protection
- the next planner work should focus on selective query and structure protection rather than broad prompt pinning

That read now survives a larger `60`-sample confirmation sweep:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary_failures.csv)

Confirmed shape:

- at budgets `50`, `25`, and `12.5`, `plan_v2_query_anchor_k_protected` matches `fpa_no_plan` exactly on task score and warm bytes
- at budget `6.25`, it still matches `fpa_no_plan` on task score with only a very small warm-byte increase
- at budget `0`, it keeps a small task and exact edge over `fpa_no_plan` while remaining below `quantized_old_kv` on warm bytes

That is not enough to claim that compiled planning has surpassed heuristic FPA in general.

It is enough to say:

- the planner boundary is real
- the planner policy family is now behaviorally competitive
- query-anchor selection is a better first-class planning object than prompt-head anchoring

The next planner revision now refines that further:

- `plan_v3_query_anchor_numeric_head_k_protected` keeps the query-anchor protection from `plan_v2_query_anchor_k_protected`
- it adds selective numeric-head protection instead of broad prompt-head protection

Artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary_per_sample.csv)

Observed shape:

- at budgets `50`, `25`, and `12.5`, `plan_v3_query_anchor_numeric_head_k_protected` is flat with `plan_v2_query_anchor_k_protected`
- at budgets `6.25` and `0`, it widens the edge:
  - task `64.583` vs `62.5` for `plan_v2_query_anchor_k_protected`
  - contains `75.0` vs `70.833`
- the recovered gain comes from fixing a numeric-head failure while preserving the multihop rescue already gained by `plan_v2_query_anchor_k_protected`

That sharpens the current architectural read again:

- the best planning object is not "prompt head" in general
- it is a small set of structurally fragile prompt-head spans plus the query anchor
- selective head protection is more promising than generic head pinning

This is a good research outcome.

It narrows the next question:

> can a compiled memory plan generalize this selective structure-aware edge beyond numeric-head recovery, or is the current durable gain specifically a small set of prompt-head failure families layered on top of the query-anchor win?

That question is now grounded by a completed larger control:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_per_sample.csv)

Observed control shape:

- at budgets `50`, `25`, and `12.5`, `plan_v3_query_anchor_numeric_head_k_protected` remains flat with `fpa_no_plan` and `plan_v2_query_anchor_k_protected`
- at budgets `6.25` and `0`, it keeps the low-budget edge:
  - task `60.833` vs `60.0` for `plan_v2_query_anchor_k_protected`
  - task `60.833` vs `59.167-60.0` for the simpler baselines
  - contains `70.0` vs `68.333`
- the recovered failure family is still specific and interpretable:
  - `suite_numbers_015` flips from `numeric_mismatch` under `plan_v2_query_anchor_k_protected` to `contains_target` under `plan_v3_query_anchor_numeric_head_k_protected`

That means the current architectural read is sharper:

- `TMHMemoryPlan` is not only a viable boundary
- selective structure-aware planning can produce a repeatable incremental gain on top of heuristic FPA
- the right next move is not more blunt prompt-head protection
- it is testing whether this narrow recovered-family pattern generalizes to other structured prompt-head memory classes

## Bottom Line

The architectural shift is:

from:

- memory policy inferred after construction

to:

- memory layout synthesized before decode and revised under pressure

That is the real step forward.
