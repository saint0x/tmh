# TMH Spec

## Identity

TMH stands for `Transformer Memory Hierarchy`.

This project is no longer framed as a search for a new attention primitive. It is now framed as a transformer-memory-systems project whose job is to discover, implement, and validate a better memory model for inference than a flat KV cache.

The current `fidelity_paged_kv` policy remains in the codebase as one active policy label under the broader TMH umbrella. It is not the thesis. It is one probe into the thesis.

The running research findings log lives in:

- [FINDINGS.md](/Users/deepsaint/Desktop/kv-tiered/tmh/FINDINGS.md)

## Core Thesis

The active thesis is:

> Transformer inference wants a heterogeneous memory hierarchy, not a flat KV cache.

Put differently:

- attention is not the only layer that matters
- memory representation and memory movement dominate real serving behavior
- KV state is not uniformly valuable
- different parts of transformer memory deserve different residency, fidelity, and reuse policies

## First-Principles Read

Reality:

- decode latency is heavily affected by memory movement
- KV state has real residency, bandwidth, storage, and fidelity costs
- not all prior tokens matter equally to future generation
- keys and values may have different sensitivity to degradation
- layer position, reuse probability, semantic role, and head behavior likely matter
- cross-request reuse can materially change serving economics

Interpretation:

- KV should be treated as a flat cache
- all pages should share one representation
- all pages should share one lifecycle
- K and V should be managed symmetrically
- attention math is always the most useful explanatory layer

The work so far keeps exposing contradictions between those layers. That contradiction is the lamp.

## Problem Statement

Modern transformer inference typically assumes:

- one broad KV abstraction
- one dominant residency model
- one main precision story
- one primary lifecycle for cached states

That assumption is likely too weak.

TMH exists to answer:

1. Which parts of transformer memory must stay high-fidelity?
2. Which parts can be compressed or demoted?
3. Which parts should be pinned, prefetched, or shared?
4. Which parts can be recomputed instead of stored?
5. Which distinctions are actually causal:
   layer, head, age, role, K/V split, or workload type?

## What TMH Means

TMH treats transformer memory as a hierarchy across several dimensions at once:

- residency tier
  GPU hot state, colder local state, and potentially remote or persistent state
- fidelity tier
  raw, quantized, summarized, sparse, or otherwise transformed state
- access tier
  always resident, query-selected, prefetched, or retrieved on demand
- semantic tier
  pages with different roles, reuse probabilities, and failure sensitivity

The right mental model is closer to an operating system for transformer memory than to a single KV compression trick.

## System Scope

The current system is intended to support:

- page-based KV management
- mixed memory representations
- policy-driven page treatment
- deterministic host-backed benchmarking
- production-style artifact generation
- future benchmark expansion across models, workloads, budgets, and policies

The system is explicitly being steered toward a single honest production path for runtime evidence rather than duplicated synthetic reporting logic.

## Current Runtime Direction

At the runtime level, the project is converging on these architectural ideas:

- pages are the natural management unit
- policy should be expressed against canonical runtime state, not ad hoc report-time reconstruction
- report generation should flow from real runtime outputs through one canonical writer path
- shardable evaluation is a first-class production capability, not an embarrassment
- memory accounting must eventually be as trustworthy as latency accounting
- prefill should increasingly compile memory intent rather than leaving all treatment decisions to reactive decode-time heuristics

## Current Policy Surface

The current benchmark surface still uses these policy names:

- `full_kv`
- `paged_full_kv`
- `recent_only`
- `quantized_old_kv`
- `fidelity_paged_kv`

Interpret them as follows:

- `full_kv` is the flat-memory control
- `paged_full_kv` isolates the value of paging and canonical page management
- `recent_only` is a deliberately lossy locality-only baseline
- `quantized_old_kv` is a simpler reduced-fidelity baseline
- `fidelity_paged_kv` is the current TMH-style mixed-fidelity policy probe

These labels are still useful experimentally, but the project thesis sits above them.

One additional distinction now matters for future experiments:

- heuristic-only FPA
- plan-driven FPA

That split should become explicit in future benchmark matrices.

The real-model harness now exposes that split directly through:

- `fpa_no_plan`
- `plan_v0_prompt_anchor_raw`
- `plan_v1_anchor_k_protected`
- `plan_v1_structured_protect`

## What Has Been Proven

The engineering runtime is real:

- paged KV exists
- mixed representations exist
- policy-driven KV management exists
- deterministic host-backed benchmarking exists
- production-style artifacts and reporting exist
- served-model layout-pressure validation now exists on a 30B-class ROCm endpoint

The runtime and reporting path are now materially more honest than they were earlier:

- fake or synthetic report paths were removed
- the top-level matrix path now uses canonical budget artifacts
- bench execution no longer relies on duplicate native bench writers
- larger evidence can be produced with sharded top-level execution

## Current Evidence

The strongest current evidence lives in:

- [manifest_combined.json](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/manifest_combined.json)
- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/summary_failures.csv)
- [production_verify.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify.report.md)
- [production_verify_qwen_250.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_qwen_250.report.md)

That baseline covers:

- 250 stress samples
- 5 budgets
- 4 production-relevant policies in the real-model harness
- one capable 1.5B instruction-tuned model

Supportive cross-model validation also now exists in:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/HuggingFaceTB_SmolLM2-1.7B-Instruct_stress60/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/HuggingFaceTB_SmolLM2-1.7B-Instruct_stress60/summary_failures.csv)
- [production_verify_smollm2_60.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_smollm2_60.report.md)
- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/ibm-granite_granite-3.3-2b-instruct_stress60/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/ibm-granite_granite-3.3-2b-instruct_stress60/summary_failures.csv)
- [production_verify_granite_60.report.md](/Users/deepsaint/Desktop/kv-tiered/tmh/artifacts/production_verify_granite_60.report.md)

Served-model 30B layout-pressure validation now exists in:

- [standard endpoint report](/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-023427/REPORT.md)
- [standard layout sweep report](/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_layout_sweep/20260719-035609/REPORT.md)
- [stronger standard endpoint report](/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-040954/REPORT.md)
- [stronger standard layout sweep report](/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_standard_runs3_layout_sweep/20260719-041243/REPORT.md)
- [maxfit endpoint preflight report](/home/deepsaint/work/kv-tiered/tmh/artifacts/sock_endpoint_pressure/20260719-040147/REPORT.md)
- [maxfit layout sweep report](/home/deepsaint/work/kv-tiered/tmh/artifacts/tmh_30b_maxfit_preflight_layout_sweep/20260719-040423/REPORT.md)
- [standard sweep Fozzy trace](/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_layout_sweep.trace.fozzy)
- [stronger standard sweep Fozzy trace](/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_standard_runs3_layout_sweep.trace.fozzy)
- [maxfit sweep Fozzy trace](/home/deepsaint/work/kv-tiered/tmh/artifacts/fozzy/tmh_30b_maxfit_preflight_layout_sweep.trace.fozzy)

Observed on the frozen Qwen baseline:

- `recent_only` collapses completely as a memory policy
- `quantized_old_kv` is a strong simple baseline
- `fidelity_paged_kv` uses about `16.1%` less warm memory than `quantized_old_kv`
- `fidelity_paged_kv` improves exact and contains metrics at every tested budget, but modestly rather than dramatically
- the evidence reads as a transformer memory hierarchy result, not a new attention result
- a second model shows the same qualitative pattern, but at smaller scale than the frozen Qwen baseline
- a larger ungated 2B-class model also shows the same qualitative pattern, with FPA improving exact while matching contains and reducing latency versus `quantized_old_kv`
- the 30B ROCm layout sweeps preserve a `16.667%` old/warm KV pressure reduction across page sizes `8`, `16`, `32`, and `64`, and hot budgets from `75` down to `0`
- the stronger 30B live standard endpoint run adds repeated serving measurements at concurrency `1`, `2`, and `4`, with the regenerated layout sweep preserving `100%` plan validation and the same `16.667%` warm old-KV reduction

High-signal numbers from the baseline:

- at budget `50`, `quantized_old_kv` reached `46.4` exact and `64.4` contains, while `fidelity_paged_kv` reached `47.6` exact and `66.0` contains
- at budget `25`, `quantized_old_kv` reached `46.0` exact and `64.0` contains, while `fidelity_paged_kv` reached `48.0` exact and `66.4` contains
- at budget `0`, `quantized_old_kv` reached `46.0` exact and `64.4` contains, while `fidelity_paged_kv` reached `46.4` exact and `64.8` contains
- `recent_only` reached `0.0` exact and `0.0` contains at every tested compressed budget
- in the 30B maxfit preflight sweep, total effective KV reduction at `0%` hot reached `15.106-16.463%`, depending on page size, while plan validation stayed at `100%`

## What Has Not Been Proven

We have not yet proven:

- a new attention mechanism
- a model-general law of transformer memory
- cross-model and cross-workload generality
- that the current `fidelity_paged_kv` heuristic is the best TMH policy family
- that Python/MPS latency reflects the final native-kernel efficiency ceiling
- that the first `TMHMemoryPlan` prototype improves the overall quality/memory trade-off
- that the 30B layout-pressure result is already equivalent to live vLLM executing TMH-managed KV internally

Important measurement caveat:

- the real-model path currently has more trustworthy quality and residency metrics than true end-to-end native kernel timing
- top-1 imitation is informative but is not the main research target
- task behavior under memory pressure is the current primary north star

## Known Runtime Truths

The project currently has several important operational truths:

- the real benchmark authority is the explicit Python real-model harness, not the historical tiny-model path
- deterministic shardability is now a first-class production capability through sample offsets and manifest combining
- the native runtime now emits a precision census for K and V residency, so mixed-fidelity structure is directly observable in runtime artifacts
- the current Qwen-250 run is strong enough to freeze as a baseline, but not strong enough to claim generality
- the current SmolLM2-60 run is strong enough to count as real supportive cross-model evidence, but not strong enough to replace Qwen-250 as the flagship baseline
- the current Granite-60 run is strong enough to count as real supportive larger-model evidence, but still not enough to claim workload or model-family generality

## Non-Goals

TMH is not currently trying to prove:

- that one first-generation heuristic is the globally best KV policy
- that tiny-model wins automatically generalize to stronger models
- that a uniform cache can be repaired by one isolated trick
- that all gains should be described as changes to attention itself

## Research-Aligned Design Requirements

The implementation should continue moving toward these requirements:

1. One canonical production path from runtime execution to artifacts.
2. One canonical way to interpret policies through TMH rather than ad hoc naming.
3. Explicit support for shard-based, reproducible, host-backed benchmark runs.
4. Metrics that separate latency, throughput, bytes moved, tier hits, prefetch effectiveness, and recompute cost.
5. Support for future policies that differ along K/V, head, layer, role, and tier axes.
6. Runtime artifacts that directly expose mixed-fidelity K/V structure rather than forcing report-time inference from policy names.
7. A first-class prefill planning surface that can express compiled memory intent separately from runtime adaptation.
8. Benchmark outputs that can compare task quality against warm-byte cost directly.

## Benchmark Redesign Requirements

The next benchmark system should be built to prove or falsify the TMH abstraction, not merely to score one policy.

It must eventually cover:

- multiple model families
- multiple model scales
- multiple context lengths
- multiple memory budgets
- multiple workload types
- asymmetric K-only and V-only degradations
- layer- and head-sensitive policies
- routing-heavy and payload-heavy prompts
- long-context recall
- instruction persistence
- multi-hop state retention
- code-like dependencies
- explicit failure cases
- plan-versus-heuristic ablations
- anchor-policy ablations
- K-protected versus V-protected plan variants
- quality-per-byte reporting

The next focused matrix should compare at least:

- `quantized_old_kv`
- `fpa_no_plan`
- `plan_v0_prompt_anchor_raw`
- `plan_v1_anchor_k_protected`
- `plan_v1_structured_protect`

The benchmark surface should also emit:

- `task_score_pct`
- `task_score_delta_vs_quantized`
- `warm_bytes_delta_vs_quantized`
- `task_gain_per_extra_warm_byte`

## Contribution Hierarchy

If this project succeeds, the contribution order should be:

1. The abstraction: transformer memory hierarchy.
2. The runtime architecture that makes it testable.
3. The benchmark and falsification framework.
4. The family of policies explored inside that framework.
5. Any specific first-generation heuristic, only last.

This is important because the current `fidelity_paged_kv` heuristic may not survive, and that would still be a successful research outcome.

## TMHMemoryPlan Direction

The next runtime primitive is `TMHMemoryPlan`.

The intended architecture is:

Prefill
  ↓
TMH Prefill Compiler
  ↓
TMHMemoryPlan
  ↓
BlockManager
  ↓
Decode Runtime

The current small prototype has already validated that this boundary is implementable.

What it has not yet validated is the best plan policy.

The v0 lesson is clear:

- unconditional `raw/raw` prompt anchoring buys some quality
- it can also overpay in warm bytes
- the next plan family should protect selectively rather than bluntly

The first serious plan-v1 target should likely be:

- anchor K protected first
- anchor V only moderately protected
- prompt-body protection reduced relative to v0

## Documentation Split

This file is the canonical TMH system document.

It owns:

- project identity
- thesis
- scope
- current evidence boundary
- runtime truths
- architectural direction

The separate research baseline document owns:

- literature map
- claim boundaries relative to prior work
- paper positioning
- benchmark matrix for the research program
- arXiv readiness criteria

See [RESEARCH_BASELINE.md](/Users/deepsaint/Desktop/kv-tiered/tmh/RESEARCH_BASELINE.md).

## North Star

> Do not try to prove that `fidelity_paged_kv` is the best KV trick.
>
> Try to prove that transformers want a better memory model.
