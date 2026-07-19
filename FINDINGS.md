# TMH Findings Log

## Purpose

This document is the running findings ledger for the TMH research program.

It is intentionally less formal than the spec and less polished than paper-facing notes.

Its job is to capture:

- findings worth preserving before they get normalized away
- negative results that changed our direction
- measurement caveats that matter for honest interpretation
- architectural lessons that emerged from implementation, not theory
- candidate hypotheses that should later become benchmark rows or paper text

## Current Status

The project is now beyond the stage of asking whether there is any signal at all.

The active question is:

> what is the strongest honest, repeatable claim the data supports, and what runtime abstraction explains it best?

The current answer is TMH:

- transformer memory is heterogeneous
- eviction and demotion are fundamentally different operations
- runtime memory policy changes task behavior materially
- the contribution is better framed as memory hierarchy than as new attention

## Empirical Findings

### 1. `recent_only` is not a valid production memory policy

This is the cleanest finding in the project so far.

Across the main real-model runs, dropping old KV does not merely degrade gracefully.

It changes model behavior catastrophically under stress.

Observed repeatedly on:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `HuggingFaceTB/SmolLM2-1.7B-Instruct`
- `ibm-granite/granite-3.3-2b-instruct`

Takeaway:

- old KV is not optional
- recency-only locality is too weak as a transformer memory policy

### 2. Compressed retention is qualitatively different from eviction

`quantized_old_kv` consistently preserves behavior far better than `recent_only`.

This means the important distinction is not:

- raw versus imperfect

It is:

- retained versus destroyed

Takeaway:

- old memory can be demoted aggressively
- old memory cannot simply be erased

### 3. Task behavior and top-1 imitation are not the same target

The runs repeatedly showed that higher top-1 agreement with the full-KV baseline does not necessarily imply better task outcomes.

This matters because it shifts the optimization target from:

- token-level imitation

to:

- preserved task behavior under memory pressure

Takeaway:

- exact/contains and failure shape are currently more meaningful than top-1 imitation
- top-1 is diagnostic, not the north-star metric

### 4. FPA is real, but the win is modest and believable

The strongest stable FPA result is not a huge quality jump.

It is:

- lower warm memory
- small, consistent task improvement
- non-catastrophic latency behavior

That is a good systems shape.

It is more credible than a noisy, dramatic gain that disappears on replication.

Takeaway:

- the value is in stable memory/behavior tradeoff improvement
- overselling the magnitude would weaken the work

### 5. Replication across model families is the strongest current evidence

The important story is no longer one model and one win.

The important story is that the same qualitative pattern survived across multiple capable decoder-only instruction models.

Takeaway:

- replication now matters more than chasing a larger single-number delta

### 5.1. The warm-memory reduction holds at 30B served-model layout scale

The GMK ROCm machine now provides a larger served-model validation surface through sock/vendored vLLM:

- `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- OpenAI-compatible sock endpoint
- real endpoint pressure corpus at `2048` context
- near-context maxfit preflight corpus with prompt lengths around `1.88k-1.90k`

The TMH-only layout harness compiled exactly one layout:

- `tmh_fidelity_paged_kv`
- prompt anchor pinned `raw/raw`
- recent tail hot `raw/raw`
- old early/middle-layer K/V as `int8/int4`
- old late-layer K/V as `int8/int8`
- no cold or dropped KV

Across the standard measured sweep and the maxfit preflight sweep:

- page sizes: `8`, `16`, `32`, `64`
- hot budgets: `75`, `50`, `25`, `12.5`, `6.25`, `3.125`, `0`
- rows per sweep: `280`
- compiled plan ranges per sweep: `1080`
- plan validation: `100%`
- warm old-KV reduction versus same-hot uniform-int8 old KV: `16.667%` everywhere

A stronger live standard endpoint run now also exists:

- runs: `3`
- warmup runs: `1`
- concurrency levels: `1`, `2`, `4`
- elapsed wall time: `796.1613s`
- concurrency `4` reached about `69-71` completion tok/s by case
- streaming TTFT stayed around `0.106-0.180s`
- the layout sweep regenerated from this stronger corpus preserved the same `16.667%` warm old-KV reduction and `100%` plan validation

Takeaway:

- the original `16-17%` memory-pressure result is not only a tiny-model artifact
- the precise stable claim is old/warm KV pressure reduction, not unconditional total serving memory reduction
- total effective KV reduction depends on the hot raw window and approaches the warm-KV reduction as the hot window shrinks
- the next falsification point is live execution of TMH-managed KV inside the vLLM runtime, not more report-time layout arithmetic alone

## Architectural Findings

### 6. The project’s true abstraction boundary moved upward

The project started as a search for better KV treatment inside an attention-runtime path.

The evidence kept forcing a reframing:

- not new attention first
- new memory abstraction first

Takeaway:

- TMH is the actual contribution boundary
- `fidelity_paged_kv` is one policy inside that boundary

### 7. `BlockManager` guessing after memory construction is too late

The original runtime shape relied on runtime heuristics after pages already existed.

That worked for first results, but it hid an important weakness:

- the runtime knew where a page was
- it did not know what the page meant

Takeaway:

- a prefill-time planning boundary is architecturally cleaner than purely reactive runtime heuristics

### 8. `TMHMemoryPlan` is a real primitive, not just renamed heuristics

The small prototype proved an important point:

- a compiled memory plan can be emitted
- the runtime can consume it
- the decode path remains intact
- behavior moves in measurable ways

Even though v0 is not the final policy, the boundary itself appears real.

Takeaway:

- compile/execute is now a justified architecture path, not just a concept note

### 9. Plan v0 taught the right negative lesson

The first prompt-anchor plan pinned too much raw/raw state.

Observed effect:

- better task behavior at some budgets
- larger warm-memory footprint
- advantage fading at tighter budgets

That is a good negative result because it tells us exactly what to fix next.

Takeaway:

- naive anchor protection overpays
- selective protection is the next serious direction

## Measurement Findings

### 10. The real-model Python harness is currently the authority for quality claims

The live real-model harness is now the benchmark truth surface for quality and residency claims.

The old tiny-model path was useful for plumbing, but it is not the evidence surface anymore.

Takeaway:

- quality claims should be anchored to the real-model harness artifacts
- tiny random GPT-2 style plumbing results should not be used to support paper claims

### 11. Deterministic shardability is not a convenience feature

Sharded large-run execution made the flagship evidence practical and reproducible.

Takeaway:

- shardability is part of production research infrastructure
- reproducible aggregation is a core benchmark capability, not an implementation footnote

### 12. Warm-memory accounting is becoming a first-class metric

The benchmark shape increasingly depends on understanding quality relative to residency cost, not only raw quality numbers.

Takeaway:

- bytes matter
- warm bytes should be treated as a primary axis of evaluation, not a side metric

## Research Findings

### 13. The strongest honest claim is about memory hierarchy, not attention novelty

The current evidence supports:

- heterogeneous transformer memory management is useful

It does not yet support:

- a new universal attention mechanism claim

Takeaway:

- the paper should lead with memory hierarchy
- any attention framing should be secondary and careful

### 14. The runtime may matter more than the first scheduler

There is a real chance the most durable contribution is:

- the TMH abstraction
- the runtime architecture
- the evaluation framework

and not the exact first-generation FPA heuristic.

Takeaway:

- the project should optimize for clean abstractions and falsifiable evaluation, not attachment to v1 heuristics

### 15. Prefill likely has richer information than decode for memory planning

Decode is local and reactive.

Prefill has access to:

- the full prompt
- prompt structure
- early segment boundaries
- repeated text
- instruction context

Takeaway:

- the best planner probably starts in prefill
- decode should execute and adapt, not invent the whole layout from scratch

## Negative Findings Worth Keeping

### 16. Tiny random models were good plumbing and bad evidence

They helped harden the path.

They did not support the actual research claim.

Takeaway:

- plumbing success is not paper evidence
- model capability matters for memory-policy evaluation

### 17. More heuristics is not automatically more science

A growing list of hand-tuned policy rules can make the runtime look more sophisticated while making the claim less clear.

Takeaway:

- every new heuristic should justify itself against a cleaner abstraction story

### 18. Native latency conclusions are still softer than quality conclusions

The Python/MPS path has been good enough to reveal strong behavioral signal, but it is not the final word on kernel-level timing efficiency.

Takeaway:

- memory/quality claims are currently stronger than final latency claims

## Immediate Hypotheses To Test

### 19. Prompt anchors should be selective, not unconditional

Candidate next plan:

- protect anchor K more than V
- keep only a narrow system/instruction subset pinned
- lower prompt-body fidelity instead of preserving it raw

### 20. Structured spans may deserve differentiated protection

Candidate categories:

- code
- numbers
- retrieved facts
- tabular records

Hypothesis:

- these spans may have higher key fragility than generic prose

### 21. Quality should be measured relative to residency cost

The next comparison should explicitly track something like:

- `task_gain_per_extra_warm_byte`

That will make selective-plan tradeoffs easier to read than raw exact/contains deltas alone.

This metric is now wired into the real-model harness summary surface alongside:

- `task_score_pct`
- `task_score_delta_vs_quantized`
- `warm_bytes_delta_vs_quantized`

### 22. Plan v1 removed most of the raw-anchor tax, but did not beat heuristic FPA on the first real matrix

The first explicit planner matrix now exists on:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `24` stress samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`

Artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v1/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v1/summary_failures.csv)

Observed shape:

- `recent_only` still fails decisively
- `quantized_old_kv` remains the strong uniform compressed baseline
- `fpa_no_plan` improves task score over `quantized_old_kv` at budgets `50`, `25`, `12.5`, and `6.25` while using less warm memory
- `plan_v0_prompt_anchor_raw` matches the higher-budget task gains, but overpays heavily in warm bytes and degrades at `6.25`
- `plan_v1_anchor_k_protected` removes most of the raw-anchor overpay
- `plan_v1_structured_protect` is very close to `plan_v1_anchor_k_protected` on this matrix

Important nuance:

- plan-v1 is architecturally healthier than v0
- but on this 24-sample Qwen matrix it does not beat `fpa_no_plan`
- it mostly converges toward the heuristic FPA quality shape while giving up some of the warm-byte advantage

Takeaway:

- the planner boundary remains justified
- the current planner heuristics are not yet better than the simpler mixed-fidelity heuristic
- the next planner revision has to win on quality per warm byte over `fpa_no_plan`, not merely over `plan_v0`

### 23. Query-anchor protection is the first planner variant that is actually competitive

The next focused planner revision now exists on:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `24` stress samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`

Artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress24_plan_matrix_v2/summary_per_sample.csv)

Observed shape:

- `plan_v2_query_anchor_k_protected` drops first-page anchoring and protects only the last prompt page as the query anchor
- at budgets `50`, `25`, and `12.5`, `plan_v2_query_anchor_k_protected` matches `fpa_no_plan` exactly on task score while preserving the same warm-memory footprint
- at budget `6.25`, `plan_v2_query_anchor_k_protected` still matches `fpa_no_plan` on task score, with only a small warm-byte increase
- at budget `0`, `plan_v2_query_anchor_k_protected` beats `fpa_no_plan`:
  - task score: `62.5` vs `60.417`
  - exact: `54.167` vs `50.0`
  - contains: both `70.833`
- `plan_v2_query_anchor_k_protected` remains below `quantized_old_kv` on warm bytes even at budget `0`

Important per-sample nuance:

- on the `suite_multihop_001` sample, `plan_v1_anchor_k_protected` failed where `fpa_no_plan` succeeded at budget `6.25`
- the v2 query-anchor plan recovers that failure
- at budget `0`, v2 also succeeds on a multihop case where `fpa_no_plan` fails

Takeaway:

- the planner boundary is now stronger than it looked after v1
- protecting the query anchor is materially better than protecting the first prompt page
- the right memory object for planning is not "prompt head" in the abstract
- it is the subset of prompt memory that decode is actually likely to route back through under pressure

### 24. The v2 query-anchor result survives a 60-sample confirmation sweep

The larger confirmation sweep now exists on:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `60` stress-suite samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`

Artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v2_confirm/summary_per_sample.csv)

Observed shape:

- `plan_v2_query_anchor_k_protected` matches `fpa_no_plan` exactly on task score, exact, contains, and warm bytes at budgets `50`, `25`, and `12.5`
- at budget `6.25`, `plan_v2_query_anchor_k_protected` still matches `fpa_no_plan` on task score, exact, and contains with only `6931` extra warm bytes
- at budget `0`, `plan_v2_query_anchor_k_protected` beats `fpa_no_plan`:
  - task score: `60.0` vs `59.167`
  - exact: `51.667` vs `50.0`
  - contains: both `68.333`
- at budget `0`, `plan_v2_query_anchor_k_protected` remains below `quantized_old_kv` on warm bytes:
  - `1488023` vs `1649536`

Failure-shape nuance:

- `plan_v2_query_anchor_k_protected` matches `fpa_no_plan` exactly through budgets `50`, `25`, `12.5`, and `6.25`
- at budget `0`, `plan_v2_query_anchor_k_protected` converts one `reasoning_mismatch` into one more `exact_or_prefix_match`
- relative to `quantized_old_kv`, both heuristic FPA and plan v2 remove one `reasoning_mismatch` at moderate budgets

Takeaway:

- the v2 result was not just a small-sample fluke
- query-anchor planning is now supported as a stable planner direction
- the current honest claim is still "competitive with heuristic FPA, with a small tight-budget edge," not "planner dominance"

### 25. Stress-suite scaling uses two knobs, not one

The real-model harness has an important benchmark-control nuance:

- `--max-samples` alone does not enlarge the synthetic stress suite
- the stress profile also requires raising `--stress-samples`

Takeaway:

- large stress confirmations should always set both `--max-samples` and `--stress-samples`
- otherwise a run can look larger by path name while actually evaluating only the six seed suite cases

### 26. Numeric-head protection widened the planner edge without losing the query-anchor win

The next planner revision now exists on:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `24` stress-suite samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`

Artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite24_plan_matrix_v3_probe/summary_per_sample.csv)

Observed shape:

- `plan_v3_query_anchor_numeric_head_k_protected` stays flat with `plan_v2_query_anchor_k_protected` at budgets `50`, `25`, and `12.5`
- at budget `6.25`, it beats both `fpa_no_plan` and `plan_v2_query_anchor_k_protected`:
  - task score: `64.583` vs `62.5`
  - contains: `75.0` vs `70.833`
- at budget `0`, it again beats both:
  - task score: `64.583` vs `60.417` for `fpa_no_plan`
  - task score: `64.583` vs `62.5` for `plan_v2_query_anchor_k_protected`
  - contains: `75.0` vs `70.833`

Failure-shape read:

- `plan_v2_query_anchor_k_protected` keeps the multihop rescue over `fpa_no_plan`
- `plan_v3_query_anchor_numeric_head_k_protected` preserves that rescue
- it additionally converts the `suite_numbers_015` numeric failure into a `contains_target` success at budgets `6.25` and `0`

Takeaway:

- query-anchor planning was not the endpoint
- adding selective numeric-head protection can widen the planner edge at the tightest budgets
- the important pattern is not broad prompt-head pinning
- it is selective recovery of structurally fragile head memory while preserving the query-anchor win

### 27. The larger 60-sample v3 control completed cleanly and froze the low-budget edge

The completed larger control now exists on:

- `Qwen/Qwen2.5-1.5B-Instruct`
- `60` stress-suite samples
- budgets: `50`, `25`, `12.5`, `6.25`, `0`

Artifacts:

- [summary.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary.csv)
- [summary_failures.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_failures.csv)
- [summary_per_sample.csv](/Users/deepsaint/Desktop/kv-tiered/results_real/Qwen_Qwen2.5-1.5B-Instruct_stress_suite60_plan_matrix_v3_control_full/summary_per_sample.csv)

Observed shape:

- `plan_v3_query_anchor_numeric_head_k_protected` stays flat with `fpa_no_plan` and `plan_v2_query_anchor_k_protected` at budgets `50`, `25`, and `12.5`
  - task `60.833`
  - contains `70.0`
- at budget `6.25`, `plan_v3_query_anchor_numeric_head_k_protected` keeps the edge:
  - task `60.833` vs `60.0` for both `fpa_no_plan` and `plan_v2_query_anchor_k_protected`
  - contains `70.0` vs `68.333`
- at budget `0`, it keeps the same edge:
  - task `60.833` vs `60.0` for `plan_v2_query_anchor_k_protected`
  - task `60.833` vs `59.167` for `fpa_no_plan`
  - contains `70.0` vs `68.333`

Failure-shape read:

- `plan_v3_query_anchor_numeric_head_k_protected` preserves the earlier multihop/query-anchor rescue
- it still converts `suite_numbers_015` from `numeric_mismatch` to `contains_target` at budgets `6.25` and `0`
- this is visible directly in the aggregate failure counts:
  - `plan_v2_query_anchor_k_protected` at `6.25` and `0`: `numeric_mismatch 2`, `contains_target 10`
  - `plan_v3_query_anchor_numeric_head_k_protected` at `6.25` and `0`: `numeric_mismatch 1`, `contains_target 11`

Takeaway:

- the larger control confirms the `v3` direction rather than merely supporting it
- the gain remains narrow, interpretable, and concentrated in numeric-head recovery at the tightest budgets
- the frozen benchmark artifact for `v3` is now the completed `60`-sample control, not the earlier interrupted partial

### 28. The adversarial layout stress held the hierarchy thesis but scoped the numeric claim

The standalone adversarial stress harness now exists at:

- `artifacts/tmh_adversarial_layout_stress/robust-stress-v1/REPORT.md`
- `artifacts/fozzy/tmh_adversarial_layout_stress.trace.fozzy`

Scope:

- `16,632` shape/page/budget/sequence rows
- `9,255` rows with old KV present
- `356,890,836` checked layer-pages
- page sizes from `1` through `512`
- hot budgets from `100` down to `0`
- five model shapes, including Qwen-30B GQA, dense/GQA boundaries, fp32 MHA, large-70B-style GQA, and a one-layer all-late boundary

Observed shape:

- plan validation: `100%`
- invariant validation: `100%`
- cold or dropped KV violations: `0`
- negative total-reduction rows with old KV: `0`
- Qwen-30B old/warm KV reduction: `16.667%`

Important boundary:

- the hierarchy thesis held under the adversarial matrix
- the exact `16.667%` warm old-KV reduction is not universal
- it is the Qwen-30B production-shape value induced by the current late-layer split
- other layer splits produce other old/warm reduction percentages
- the one-layer all-late boundary has `0%` reduction versus uniform-int8 old KV by construction, but still preserves the no-drop/no-cold TMH contract

Takeaway:

- the robust claim is stronger and cleaner now: TMH is a safe explicit hierarchy contract under extreme layout geometry
- the paper should avoid overselling `16.667%` as a universal constant
- `16.667%` is the production Qwen-30B result; the general contribution is the compiled memory hierarchy and its invariant-preserving pressure behavior

### 29. The production memory-pressure claim is now a cross-model floor

The model-family baseline now exists at:

- `artifacts/tmh_model_family_memory_baseline/model-family-v1/REPORT.md`
- `artifacts/fozzy/tmh_model_family_memory_baseline.trace.fozzy`

Scope:

- `15` actual cached Hugging Face model configs
- `31` pressure cases
- `18,600` total rows
- `14,145` rows with old KV present
- page sizes `8`, `16`, `32`, `64`, `128`
- hot budgets `75`, `50`, `25`, `12.5`, `6.25`, `3.125`, `1`, `0`

Observed shape:

- plan validation: `100%`
- invariant validation: `100%`
- conservative supported-model old/warm KV pressure floor: `16.071%`
- promoted public number: `at least 16.0% old/warm KV memory-pressure reduction across the tested production model-family baseline`

Important boundary:

- the earlier `16.667%` value remains true for Qwen-30B and other shapes with the same effective early-layer fraction
- it should no longer be promoted as the production-wide number
- the production-wide number should be the cross-model floor
- total effective KV pressure remains request/budget dependent because hot raw KV and prompt-anchor pages are preserved by design

Takeaway:

- we now have a baseline number that is conservative enough to stand behind across the actual tested model family
- use `16.0%+` for production memory-pressure language
- keep `16.667%` as the Qwen-30B-specific result in detailed benchmark tables

### 30. The 40-run paper stress keeps the production floor intact

The larger pre-paper stress run now exists at:

- `artifacts/tmh_paper_claim_stress/paper-claim-stress-v1/REPORT.md`
- `artifacts/fozzy/tmh_paper_claim_stress.trace.fozzy`

Scope:

- `40` deterministic traffic runs
- `15` actual cached model configs
- `31` base pressure cases
- `732,000` evaluated rows
- `682,050` old-KV rows
- `100%` invariant pass rate

Observed shape:

- every run passes
- every model passes
- conservative old/warm KV pressure floor remains `16.071%`
- promoted public number remains `at least 16.0% old/warm KV memory-pressure reduction across the tested production model-family stress baseline`

Takeaway:

- I am comfortable using `16.0%+` as the production memory-pressure number for the paper
- I am comfortable claiming that explicit TMH planning gives a robust old/warm KV pressure reduction across the tested model-family stress baseline
- I am not comfortable claiming live TMH KV-manager runtime speedup until TMH is wired into the vLLM/sock serving internals and rebenchmarked end-to-end

## Proposed Comparison Matrix

The next TMH plan study should compare:

- `quantized_old_kv`
- `fpa_no_plan`
- `plan_v0_prompt_anchor_raw`
- `plan_v1_anchor_k_protected`
- `plan_v1_structured_protect`
- `plan_v2_query_anchor_k_protected`
- `plan_v3_query_anchor_numeric_head_k_protected`

These policy labels are now explicit in the real-model harness rather than remaining implicit inside one overloaded `fidelity_paged_kv` bucket.

Primary readout:

- exact
- contains
- failure shape
- warm bytes
- task gain per extra warm byte

Secondary readout:

- top-1 agreement
- latency

## Bottom Line

The most important finding so far is not that one heuristic won.

It is that the project uncovered a better systems question:

> what is the right operating system for transformer memory?

That is the finding that now organizes the implementation, the benchmarks, and the paper path.
