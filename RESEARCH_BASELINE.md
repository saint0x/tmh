# TMH Research Baseline

## Purpose

This document is the baseline for the TMH research program and the eventual arXiv paper path.

It is not the implementation spec.

It exists to capture:

- what the field already knows
- what our evidence currently supports
- what our evidence does not yet support
- what exact claims TMH should try to prove or falsify
- what benchmark matrix is needed before a paper is credible

The running nuanced findings ledger lives in:

- [FINDINGS.md](/Users/deepsaint/Desktop/kv-tiered/tmh/FINDINGS.md)

## Working Thesis

The current research thesis is:

> Transformer inference should be managed as a heterogeneous memory hierarchy rather than a uniform KV cache.

This is stronger than:

- "we found a better KV compression trick"

and more honest than:

- "we invented a new attention mechanism"

## The Lamp

The lamp that changed the direction of this project was simple:

- our runtime evidence kept showing meaningful gains from changed memory handling
- those gains did not cleanly support the claim that a fundamentally new attention primitive had been discovered
- the evidence kept pointing upward toward memory representation, residency, and movement

That contradiction matters.

It suggests the stronger abstraction is:

- memory first
- attention second

## Honest Position

Today, TMH is best positioned as:

- a transformer memory systems investigation
- an implementation and evaluation framework for heterogeneous KV management
- a research program about the operating system of transformer memory

It is not yet honestly positioned as:

- a proven new attention algorithm
- a finished paper claim
- a model-general law

## What The Field Already Established

### 1. Memory management is already central

`PagedAttention` and `vLLM` established that KV behavior must be treated as a memory-management problem, not just a kernel problem.

Primary source:

- [Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180)

High-level takeaway:

- fragmentation and dynamic allocation matter enough to dominate serving throughput
- OS-inspired abstractions are already valid in this space

### 2. Dynamic GPU memory layout is not the only systems answer

`vAttention` argues that the memory-management insight is correct, but the exact PagedAttention implementation tradeoff is not the only viable systems design.

Primary source:

- [vAttention: Dynamic Memory Management for Serving LLMs without PagedAttention](https://arxiv.org/abs/2405.04437)

High-level takeaway:

- the memory abstraction matters more than one specific paging implementation

### 3. KV importance is not uniform

Several papers show that only a subset of tokens, pages, or cache regions dominate useful behavior.

Primary sources:

- [H2O](https://arxiv.org/abs/2306.14048)
- [Scissorhands](https://arxiv.org/abs/2305.17118)
- [SnapKV](https://arxiv.org/abs/2404.14469)
- [Quest](https://arxiv.org/abs/2406.10774)

High-level takeaway:

- importance is sparse
- recency alone is not sufficient
- query dependence matters

### 4. K and V should not always be treated identically

The strongest direct support for our current intuition comes from the K/V asymmetry literature.

Primary sources:

- [KIVI](https://arxiv.org/abs/2402.02750)
- [LeanKV](https://arxiv.org/html/2412.03131v2)

High-level takeaway:

- keys and values can have different compression sensitivity
- differentiated treatment of KV components is a serious research direction, not a niche hunch

### 5. Layer and head structure matter

Several papers argue that memory value is not uniform across layers and heads.

Primary sources:

- [PyramidKV](https://arxiv.org/abs/2406.02069)
- [RazorAttention](https://arxiv.org/abs/2407.15891)
- [Ada-KV](https://arxiv.org/abs/2407.11550)

High-level takeaway:

- layer-aware and head-aware policies are likely necessary
- uniform budgets are likely suboptimal

### 6. Streaming and sink behavior matter

Some work shows that long-context behavior can fail or recover based on structurally important tokens rather than semantic importance alone.

Primary source:

- [Efficient Streaming Language Models with Attention Sinks](https://arxiv.org/abs/2309.17453)

High-level takeaway:

- not all important memory is semantically obvious
- a memory manager may need to account for structural anchors as well as content relevance

### 7. Production systems are already moving to tiered KV

Production-facing docs show that hierarchical KV is no longer a speculative idea.

Primary sources:

- [SGLang HiCache](https://docs.sglang.io/docs/advanced_features/hicache_design)
- [LMCache](https://docs.lmcache.ai/)

High-level takeaway:

- GPU, CPU, and remote tiers are already becoming operational KV hierarchy layers
- reuse, persistence, prefetch, and observability are becoming real product requirements

### 8. There is a broader long-memory lineage

There is adjacent work that changes the model or block structure itself to support long memory.

Primary sources:

- [Compressive Transformers](https://arxiv.org/abs/1911.05507)
- [Infini-Attention](https://arxiv.org/abs/2404.07143)

High-level takeaway:

- the broader community already believes transformer memory needs richer structures
- TMH differs by focusing on inference-time systems and memory management rather than immediately requiring a new trained architecture

## Where TMH Fits

TMH sits at the intersection of four existing lines:

1. Serving memory management
   PagedAttention, vAttention
2. KV compression and eviction
   H2O, Scissorhands, KIVI, SnapKV, PyramidKV, RazorAttention, Ada-KV, MiKV, LeanKV
3. Hierarchical storage and reuse
   HiCache, LMCache
4. Long-memory transformer ideas
   Compressive Transformer, Infini-Attention

The gap is that the field still mostly treats these as separate categories.

TMH’s potential contribution is to unify them under one explicit abstraction:

- transformer memory hierarchy

## Current Evidence From This Repo

The strongest internal evidence currently comes from:

- [manifest_combined.json](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/manifest_combined.json)
- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/summary_failures.csv)
- [production_verify.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify.report.md)

What that evidence supports:

- the runtime is real
- the live host-backed path can produce stable large-run evidence on a capable 1.5B instruction model
- `recent_only` is an invalid memory policy under stress
- `quantized_old_kv` is a strong simple baseline
- the current TMH-style policy separates from `quantized_old_kv` in the right direction on task behavior while using less warm memory
- the evidence is strong enough to justify a short research note built around the TMH framing

What that evidence does not support:

- a novel attention claim
- model generality
- workload generality
- a finished byte-efficiency story
- a claim that the current FPA heuristic is final

High-signal Qwen-250 snapshot:

- `recent_only`: `0.0` exact and `0.0` contains at every tested compressed budget
- `quantized_old_kv`: `46.0-46.4` exact and `64.0-64.4` contains across budgets
- `fidelity_paged_kv`: `46.4-48.0` exact and `64.8-66.4` contains across budgets
- FPA warm-memory footprint: about `16.1%` lower than `quantized_old_kv` at every tested budget
- FPA top-1 agreement is lower than `quantized_old_kv`, which reinforces that task behavior is the more useful target metric

Supportive cross-model validation now also exists on:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/HuggingFaceTB_SmolLM2-1.7B-Instruct_stress60/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/HuggingFaceTB_SmolLM2-1.7B-Instruct_stress60/summary_failures.csv)
- [production_verify_smollm2_60.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_smollm2_60.report.md)

High-signal SmolLM2-60 snapshot:

- `recent_only`: `0.0` exact and `0.0` contains at every tested compressed budget
- `quantized_old_kv`: `46.667` exact at every tested budget and `46.667-48.333` contains
- `fidelity_paged_kv`: `48.333` exact at every tested budget and `48.333-50.0` contains
- FPA warm-memory footprint: about `16.67%` lower than `quantized_old_kv` at every tested budget
- the same qualitative TMH result appears on a second model family, but at a smaller sample count than the frozen Qwen baseline

Supportive larger-model validation now also exists on:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/ibm-granite_granite-3.3-2b-instruct_stress60/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/ibm-granite_granite-3.3-2b-instruct_stress60/summary_failures.csv)
- [production_verify_granite_60.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_granite_60.report.md)

High-signal Granite-60 snapshot:

- `recent_only`: `1.667` exact / `1.667` contains at budget `50`, then `0.0` exact / `0.0` contains at budgets `25`, `12.5`, `6.25`, and `0`
- `quantized_old_kv`: `58.333` exact and `66.667` contains at every tested budget
- `fidelity_paged_kv`: `60.0` exact and `66.667` contains at every tested budget
- FPA warm-memory footprint: about `16.25%` lower than `quantized_old_kv` at every tested budget
- FPA latency is mostly better than `quantized_old_kv` on this model
- the same TMH shape now survives a larger ungated 2B-class model pass

There is now also a smaller but important compiler-boundary result:

- the first `TMHMemoryPlan` prototype can be compiled and executed end to end
- the plan-driven path changes behavior measurably on a focused Qwen run
- the first pinned prompt-anchor plan improved task behavior at some budgets, but overpaid in warm bytes
- that is evidence for the planner boundary, not yet evidence for the best planner

There is now also a first explicit planner-comparison result:

- `plan_v1_anchor_k_protected` improves materially over `plan_v0_prompt_anchor_raw`
- `plan_v1_structured_protect` does not materially separate from `plan_v1_anchor_k_protected`
- neither plan-v1 variant beats `fpa_no_plan` on the current 24-sample Qwen stress matrix

That is an important research result because it sharpens the question:

- the planner boundary looks real
- the current planner heuristics are not yet the winning TMH policy

There is now also a second explicit planner result that sharpens that read:

- `plan_v2_query_anchor_k_protected` protects only the last prompt page rather than the first prompt page
- on the focused `24`-sample Qwen stress matrix, it matches `fpa_no_plan` at budgets `50`, `25`, `12.5`, and `6.25`
- at budget `0`, it beats `fpa_no_plan` on task score and exact while remaining below `quantized_old_kv` on warm bytes

This does not yet prove that compiled planning is globally better than heuristic FPA.

It does show that:

- the choice of protected memory object matters
- query-anchor protection is a stronger planning primitive than prompt-head protection
- the next honest experiment is a larger confirmation sweep focused on `quantized_old_kv`, `fpa_no_plan`, and `plan_v2_query_anchor_k_protected`

That larger confirmation sweep now exists on:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary_failures.csv)

Observed shape:

- `plan_v2_query_anchor_k_protected` matches `fpa_no_plan` at budgets `50`, `25`, `12.5`, and `6.25`
- at budget `0`, it keeps a small task and exact edge over `fpa_no_plan`
- it remains below `quantized_old_kv` on warm bytes at every tested budget

That means the current research position is slightly stronger:

- compiled planning is now supported as a competitive policy family, not only as an architectural curiosity
- the next question is how to widen that edge through more selective structure-aware planning rather than whether the boundary matters at all

There is now also a third planner result that widens that edge in a concrete way:

- `plan_v3_query_anchor_numeric_head_k_protected` keeps the `plan_v2_query_anchor_k_protected` query-anchor protection
- it additionally upgrades numerically dense prompt-head pages instead of broadly pinning the prompt head

Completed probe artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary_per_sample.csv)

Observed shape:

- `plan_v3_query_anchor_numeric_head_k_protected` matches `plan_v2_query_anchor_k_protected` at budgets `50`, `25`, and `12.5`
- at `6.25` and `0`, it improves task score and contains over both `fpa_no_plan` and `plan_v2_query_anchor_k_protected`
- the extra gain is traceable to a recovered numeric-head failure while preserving the earlier multihop rescue

There is now a completed larger control:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_per_sample.csv)

Observed completed shape:

- budgets `50`, `25`, and `12.5`: `plan_v3_query_anchor_numeric_head_k_protected` matches both `fpa_no_plan` and `plan_v2_query_anchor_k_protected` on task and contains
- budget `6.25`: `plan_v3_query_anchor_numeric_head_k_protected` stays above both on task and contains
- budget `0`: the same shape holds again

That means the research position is stronger again:

- the planner family is no longer only competitive in probe runs
- selective structure-aware refinement can widen the edge at the tightest budgets
- the current open question is whether that gain stays narrow to numeric-head cases or generalizes to a broader class of structurally fragile prompt-head memory

There is now also a 30B served-model layout-pressure result on the GMK ROCm machine:

- model: `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- serving path: sock CLI over vendored vLLM
- standard measured endpoint corpus: `/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-023427/result.json`
- stronger repeated endpoint corpus: `/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-040954/result.json`
- maxfit near-context preflight corpus: `/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-040147/result.json`
- layout: `tmh_fidelity_paged_kv`
- page sizes swept: `8`, `16`, `32`, `64`
- hot budgets swept: `75`, `50`, `25`, `12.5`, `6.25`, `3.125`, `0`
- rows per sweep: `280`
- compiled plan ranges per sweep: `1080`
- plan validation: `100%`
- warm old-KV reduction versus same-hot uniform-int8 old KV: `16.667%` across every page size and budget

High-signal 30B interpretation:

- the memory-pressure side of the TMH claim survives a 30B served-model prompt corpus
- the stronger repeated endpoint corpus covers `3` runs after warmup at concurrency `1`, `2`, and `4`, with concurrency `4` reaching about `69-71` completion tok/s by case and streaming TTFT around `0.106-0.180s`
- near-context preflight prompts around `1.88k-1.90k` tokens still preserve the same old/warm KV reduction
- total effective KV reduction depends on the hot raw window and reaches about `15.1-16.5%` at `0%` hot in the maxfit sweep
- this is still layout-pressure evidence tied to real endpoint traffic, not proof that vLLM is executing TMH-managed KV internally

Primary 30B artifacts:

- [standard layout sweep report](/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_layout_sweep/20260719-035609/REPORT.md)
- [stronger standard endpoint report](/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-040954/REPORT.md)
- [stronger standard layout sweep report](/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_standard_runs3_layout_sweep/20260719-041243/REPORT.md)
- [maxfit layout sweep report](/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_maxfit_preflight_layout_sweep/20260719-040423/REPORT.md)
- [standard sweep Fozzy trace](/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_layout_sweep.trace.fozzy)
- [stronger standard sweep Fozzy trace](/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_standard_runs3_layout_sweep.trace.fozzy)
- [maxfit sweep Fozzy trace](/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_maxfit_preflight_layout_sweep.trace.fozzy)

## Honest Claim Boundary

Right now the strongest honest claim is:

- "we have evidence that transformer inference benefits from treating KV memory as heterogeneous, and that demoting old KV in fidelity is materially better than evicting it"
- "we now have early cross-model support for that claim on Qwen, SmolLM2, and Granite"
- "we now have 30B-class served-model layout-pressure support for the old/warm KV memory reduction claim"

The strongest claim we do not yet have license to make is:

- "we have proven a new universal transformer memory law"

## Research Claims To Falsify

The research program should attempt to falsify these claims:

1. Transformer memory is heterogeneous rather than flat.
2. Keys and values have meaningfully different fidelity sensitivity.
3. Layer and head structure matter enough to justify non-uniform budgets.
4. Semantic role or structural role matters beyond age and recency.
5. Hierarchical residency and fidelity management outperform a uniform cache under constrained budgets.
6. These design principles generalize across models and workloads.

## Alternative Outcomes To Accept

The project should remain intellectually honest about several possible outcomes:

- TMH is correct as an abstraction, but the current `fidelity_paged_kv` heuristic is not the right policy
- TMH is partially correct, but only for some model families or workloads
- the strongest gains come from tiered reuse and storage, not fidelity-aware compression
- the strongest gains come from K/V asymmetry, not semantic-role prediction
- the paper-worthy contribution is the framework and evaluation method more than the first winning heuristic

All of these are acceptable outcomes if the evidence supports them.

## Benchmark Matrix V1

The next benchmark matrix should be built around the research thesis rather than around one existing script layout.

### Model Axis

The matrix should eventually include:

- tiny deterministic debug model
- at least one stronger small autoregressive model
- at least one second architecture family
- longer-context-capable checkpoints when feasible

### Workload Axis

The matrix should include:

- needle recall
- long-range exact string recall
- instruction persistence
- multi-hop retention
- routing-heavy prompts
- payload-heavy prompts
- document-window tasks
- code-like dependency tasks
- failure-focused adversarial prompts

External benchmark families to align against:

- [LongBench](https://arxiv.org/abs/2308.14508)
- [RULER](https://arxiv.org/abs/2404.06654)
- [Infinity Bench](https://arxiv.org/abs/2402.13718)
- [BABILong](https://arxiv.org/abs/2406.10149)
- [LoCoMo-style long-term memory QA](https://arxiv.org/html/2510.23730v1)

### Memory Axis

The matrix should vary:

- hot-budget percentages
- context lengths
- page sizes
- local-only versus tiered modes
- residency thresholds
- prefetch thresholds

### Policy Axis

At minimum, compare:

- `full_kv`
- `paged_full_kv`
- `recent_only`
- `quantized_old_kv`
- current TMH mixed-fidelity policy

Then add targeted ablations:

- K-only degradation
- V-only degradation
- head-aware budgets
- layer-aware budgets
- role-aware budgets
- query-aware page selection
- tiered offload or reuse modes
- heuristic-only versus plan-driven FPA
- prompt-anchor ablations
- selective K-protected anchor plans
- query-anchor plans

### Metric Axis

The benchmark must report separately:

- exact-match and task success metrics
- top-1 agreement or similar behavior-preservation metrics
- TTFT
- end-to-end latency
- decode throughput
- effective bytes moved
- tier hit rates
- remap counts
- prefetch usefulness
- recompute cost when introduced
- quality per warm byte or equivalent task-gain-per-byte reporting

### Falsification Axis

A benchmark matrix is only useful if it can reject the thesis.

TMH should be considered weakened if:

- uniform baselines repeatedly match or beat heterogeneous policies across strong workloads
- K/V asymmetry does not generalize beyond narrow setups
- role-aware or layer-aware policies do not outperform simpler baselines
- hierarchy gains collapse on stronger models
- observed wins reduce to benchmark artifacts or measurement bugs

## Evaluation Philosophy

The evaluation should not ask:

- "can we make TMH win?"

It should ask:

- "what does transformer memory actually want?"

That means:

- preserving negative results
- publishing benchmark failures internally
- tracking where simpler baselines dominate
- refusing to convert runtime wins into overclaimed theory

## Draft Paper Direction

The most credible paper framing today looks like one of:

- `A Transformer Memory Hierarchy for Inference`
- `Tiered Transformer Memory`
- `Fidelity-Aware Memory Hierarchies for Transformer Inference`

The least credible framing today is:

- `we invented a new attention algorithm`

## Draft Paper Contribution Stack

If the project matures successfully, the paper should likely present:

1. A new abstraction for inference-time transformer memory.
2. A runtime architecture that operationalizes that abstraction.
3. A benchmark and falsification framework that evaluates heterogeneous memory policies.
4. A policy family showing that differentiated memory treatment is useful.
5. Honest limits and failure modes.

## arXiv Gate

We should not draft an arXiv paper until we have:

- repeated results across multiple model families
- repeated results across multiple workload families
- stable host-backed production evidence
- trustworthy memory-accounting metrics
- live runtime evidence with TMH-managed KV inside the serving path
- adversarial and failure-oriented testing
- evidence that the abstraction, not just one heuristic, survives stress

## Immediate Research Next Steps

1. Turn the current benchmark script into a thesis-driven benchmark matrix.
2. Make shard-based evaluation a first-class documented mode.
3. Stress K/V asymmetry directly.
4. Separate residency, fidelity, and reuse effects in the measurements.
5. Expand from tiny-model contradiction-finding to stronger small models.
6. Add plan-v1 ablations that test selective anchor protection rather than blunt raw/raw pinning.
7. Wire TMH-managed KV into the live sock/vendored-vLLM runtime path and rerun the same 30B traffic.
8. Keep the claim boundary honest at every step.

## North Star

> The goal is not to prove that one KV trick wins.
>
> The goal is to prove or disprove that transformers want a better memory model.
