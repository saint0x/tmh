# TMH Research Note

## Working Title

Transformer Memory Hierarchy:
old KV should be demoted in fidelity, not evicted

## Status

This is a short research note draft anchored on the frozen `Qwen/Qwen2.5-1.5B-Instruct` 250-sample stress result in:

- [manifest_combined.json](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/manifest_combined.json)
- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress250_combined/summary_failures.csv)

It also includes supportive cross-model validation passes on:

- `HuggingFaceTB/SmolLM2-1.7B-Instruct`
- `ibm-granite/granite-3.3-2b-instruct`

It is not yet an arXiv draft.

It is the first frozen narrative for the empirical claim.

## Abstract

We investigate whether transformer inference should be managed as a fidelity-tiered memory hierarchy rather than as a flat KV cache. On a 250-sample stress benchmark using `Qwen/Qwen2.5-1.5B-Instruct`, naive eviction of old KV (`recent_only`) fails catastrophically at every tested compressed-memory budget. A simple compressed-retention baseline (`quantized_old_kv`) preserves behavior far better, showing that old KV is not optional even when it does not remain hot or raw. We then evaluate a mixed-fidelity policy (`fidelity_paged_kv`) that preserves hot pages in raw form while demoting older memory asymmetrically across K and V. Across all tested budgets, this policy reduces warm-memory footprint by about `16.1%` relative to `quantized_old_kv` and modestly improves task-level metrics such as exact-match and contains-target rates. These results support a transformer memory hierarchy framing: old memory should be demoted in fidelity rather than evicted, and task behavior under memory pressure is a more useful objective than top-1 imitation of a flat-KV baseline.

## Research Question

The core question is:

> Should transformer memory be managed as a heterogeneous hierarchy with differentiated fidelity, rather than as a uniform cache?

This is stronger than asking whether one more KV compression trick works.

It is also more honest than claiming a new attention primitive.

## Experimental Setup

Mainline model:

- `Qwen/Qwen2.5-1.5B-Instruct`

Harness:

- explicit real-model Python evaluation path
- deterministic stress suite
- 250 samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policies: `full_kv`, `recent_only`, `quantized_old_kv`, `fidelity_paged_kv`

The benchmark target is not top-token imitation alone.

It is task behavior under memory pressure.

## Frozen Result

### 1. Eviction fails

`recent_only` is invalid under this stress suite.

At every tested compressed budget:

- exact: `0.0`
- contains: `0.0`

Its failure modes are destructive:

- empty outputs
- degenerate repetition
- memory recall failures
- needle recall failures
- code mismatches
- reasoning mismatches

### 2. Compressed old KV is a strong baseline

`quantized_old_kv` preserves the overall baseline behavior shape:

- exact: `46.0-46.4`
- contains: `64.0-64.4`
- top-1 agreement: `98.91-99.07`

This is the first strong simple baseline for the TMH framing.

### 3. FPA still separates at 250

`fidelity_paged_kv` holds a modest but consistent task-level advantage over `quantized_old_kv` at every tested budget.

Exact:

- `50`: `46.4 -> 47.6`
- `25`: `46.0 -> 48.0`
- `12.5`: `46.0 -> 47.6`
- `6.25`: `46.0 -> 47.2`
- `0`: `46.0 -> 46.4`

Contains:

- `50`: `64.4 -> 66.0`
- `25`: `64.0 -> 66.4`
- `12.5`: `64.0 -> 66.0`
- `6.25`: `64.4 -> 65.2`
- `0`: `64.4 -> 64.8`

Warm memory:

- about `16.1%` lower than `quantized_old_kv` at every tested budget

Top-1 agreement:

- lower than `quantized_old_kv` at every tested budget

This is important.

It suggests that task preservation and top-1 imitation are not the same objective.

## Cross-Model Support

We also ran a supportive second-model validation pass on:

- `HuggingFaceTB/SmolLM2-1.7B-Instruct`
- `60` stress samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policies: `full_kv`, `recent_only`, `quantized_old_kv`, `fidelity_paged_kv`

The same shape held:

- `recent_only`: `0.0` exact and `0.0` contains at every tested compressed budget
- `quantized_old_kv`: `46.667` exact at every budget and `46.667-48.333` contains
- `fidelity_paged_kv`: `48.333` exact at every budget and `48.333-50.0` contains
- FPA warm-memory footprint: about `16.67%` lower than `quantized_old_kv` at every tested budget

This is still a smaller run than the frozen Qwen baseline, so it should be described as supportive validation rather than as the mainline benchmark result.

We then added a larger ungated third-model validation pass on:

- `ibm-granite/granite-3.3-2b-instruct`
- `60` stress samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`
- policies: `full_kv`, `recent_only`, `quantized_old_kv`, `fidelity_paged_kv`

The Granite result further strengthens the same story:

- `recent_only` remains invalid in practice:
  - `50`: `1.667` exact and `1.667` contains
  - `25`, `12.5`, `6.25`, `0`: `0.0` exact and `0.0` contains
- `quantized_old_kv`: `58.333` exact and `66.667` contains at every tested budget
- `fidelity_paged_kv`: `60.0` exact and `66.667` contains at every tested budget
- FPA warm-memory footprint: about `16.25%` lower than `quantized_old_kv`
- FPA top-1 agreement is lower, but task behavior remains better
- FPA latency is mostly better than `quantized_old_kv` on this model

This is the first larger ungated 2B-class validation in the current TMH evidence chain.

## Interpretation

The best current interpretation is:

- old KV is not optional
- old KV does not need to remain fully hot and raw
- fidelity-aware demotion can dominate eviction
- asymmetric treatment of K and V is a promising systems direction

This supports the framing:

> transformer memory hierarchy

not:

> new attention mechanism

## Honest Claim Boundary

The strongest honest claim today is:

- transformer inference benefits from treating KV as heterogeneous memory
- preserving old KV in compressed form is substantially better than dropping it
- a mixed-fidelity policy can reduce warm memory while modestly improving task behavior
- the same qualitative pattern now appears on Qwen2.5-1.5B-Instruct, SmolLM2-1.7B-Instruct, and Granite 3.3 2B

Claims we do not yet have license to make:

- universal model generality
- universal workload generality
- a finished native-kernel efficiency result
- a new attention primitive

## Why This Is Paper-Direction Evidence

This is no longer just plumbing.

The frozen result has:

- a real capable model
- multiple supportive cross-model confirmations
- a deterministic benchmark harness
- a clear losing baseline
- a strong simple compressed-retention baseline
- a differentiated mixed-fidelity result
- an honest, systems-aligned interpretation

That is enough to justify a short paper-direction note and a broader benchmark program.

## Immediate Next Steps

1. Expand the benchmark matrix across workloads and context shapes.
2. Add more workload coverage beyond the current stress-suite concentration.
3. Move mixed-fidelity observability further into the native runtime artifacts.
4. Build native mixed-fidelity kernels and re-evaluate latency once the Python/MPS overhead is no longer dominant.

## What Would Strengthen This Into A Real Paper

- one or more cross-model wins
- workload diversity beyond the current stress suite
- stronger native timing
- richer byte-movement accounting
- ablations across K-only, V-only, layer-aware, and semantic-role-aware policies

## Current Bottom Line

The current evidence does not support a "new attention" paper.

It does support a TMH paper direction:

> old KV should be demoted in fidelity, not evicted
