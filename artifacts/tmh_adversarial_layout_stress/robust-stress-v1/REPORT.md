# TMH Adversarial Layout Stress

This stress run attacks the standalone TMH layout contract across synthetic model shapes, sequence geometries, page sizes, and hot-cache budgets.
It does not mutate sock or vLLM runtime code.

- generated_at: `2026-07-19T06:38:00Z`
- kv_layout: `tmh_fidelity_paged_kv`
- shapes: `qwen3_30b_a3b_gqa, dense_7b_gqa, large_70b_gqa, small_all_late_boundary, fp32_mha_boundary`
- page_tokens: `1, 2, 3, 4, 7, 8, 16, 31, 32, 64, 127, 128, 256, 512`
- budgets: `100.0, 99.0, 90.0, 75.0, 50.0, 33.333, 25.0, 12.5, 6.25, 3.125, 1.0, 0.0`
- synthetic_cases: `21`
- row_count: `16632`
- checked_layer_pages: `356890836`
- invariant_pass_rate_pct: `100.0`

## Thesis Readout

- Plan validation pass rate: `100.0%`.
- Invariant pass rate: `100.0%`.
- Cold/dropped KV violations: `0`.
- Negative total-reduction rows with old KV: `0`.
- Qwen-30B old/warm KV reduction: `16.667%` wherever old KV exists.

## Boundary Found

- The exact `16.667%` old/warm reduction is production-shape specific for Qwen-30B because its TMH late-layer split leaves two thirds of layers eligible for int4 old-value demotion.
- Other model shapes keep the same no-eviction/no-cold invariants, but their old/warm reduction varies with the early-vs-late layer split.
- A one-layer all-late boundary shape has `0%` reduction versus uniform-int8 old KV by construction, while still preserving the TMH no-drop/no-cold behavior.

## Shape/Budget Summary

| shape | budget | rows | old rows | pass % | exhaustive | sampled | min compression vs raw | min warm reduction vs int8 old KV | min total reduction vs same-hot int8 old KV | qwen warm reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `dense_7b_gqa` | 0.0 | 294 | 221 | 100.0 | 287 | 7 | 0.0% | 16.406% | 0.016% |  |
| `dense_7b_gqa` | 1.0 | 294 | 206 | 100.0 | 287 | 7 | 0.0% | 16.406% | 3.281% |  |
| `dense_7b_gqa` | 3.125 | 294 | 206 | 100.0 | 287 | 7 | 0.0% | 16.406% | 3.281% |  |
| `dense_7b_gqa` | 6.25 | 294 | 206 | 100.0 | 287 | 7 | 0.0% | 16.406% | 3.281% |  |
| `dense_7b_gqa` | 12.5 | 294 | 206 | 100.0 | 287 | 7 | 0.0% | 16.406% | 3.281% |  |
| `dense_7b_gqa` | 25.0 | 294 | 206 | 100.0 | 287 | 7 | 0.0% | 16.406% | 3.281% |  |
| `dense_7b_gqa` | 33.333 | 294 | 206 | 100.0 | 287 | 7 | 0.0% | 16.406% | 2.344% |  |
| `dense_7b_gqa` | 50.0 | 294 | 193 | 100.0 | 287 | 7 | 0.0% | 16.406% | 1.823% |  |
| `dense_7b_gqa` | 75.0 | 294 | 171 | 100.0 | 287 | 7 | 0.0% | 16.406% | 0.825% |  |
| `dense_7b_gqa` | 90.0 | 294 | 139 | 100.0 | 287 | 7 | 0.0% | 16.406% | 0.329% |  |
| `dense_7b_gqa` | 99.0 | 294 | 71 | 100.0 | 287 | 7 | 0.0% | 16.406% | 0.028% |  |
| `dense_7b_gqa` | 100.0 | 294 | 0 | 100.0 | 287 | 7 | 0.0% | 0.0% | 0.0% |  |
| `fp32_mha_boundary` | 0.0 | 252 | 179 | 100.0 | 252 | 0 | 0.0% | 16.667% | 0.008% |  |
| `fp32_mha_boundary` | 1.0 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 16.667% | 1.852% |  |
| `fp32_mha_boundary` | 3.125 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 16.667% | 1.852% |  |
| `fp32_mha_boundary` | 6.25 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 16.667% | 1.852% |  |
| `fp32_mha_boundary` | 12.5 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 16.667% | 1.852% |  |
| `fp32_mha_boundary` | 25.0 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 16.667% | 1.852% |  |
| `fp32_mha_boundary` | 33.333 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 16.667% | 1.282% |  |
| `fp32_mha_boundary` | 50.0 | 252 | 151 | 100.0 | 252 | 0 | 0.0% | 16.667% | 0.98% |  |
| `fp32_mha_boundary` | 75.0 | 252 | 129 | 100.0 | 252 | 0 | 0.0% | 16.667% | 0.43% |  |
| `fp32_mha_boundary` | 90.0 | 252 | 98 | 100.0 | 252 | 0 | 0.0% | 16.667% | 0.169% |  |
| `fp32_mha_boundary` | 99.0 | 252 | 40 | 100.0 | 252 | 0 | 0.0% | 16.667% | 0.014% |  |
| `fp32_mha_boundary` | 100.0 | 252 | 0 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `large_70b_gqa` | 0.0 | 294 | 221 | 100.0 | 279 | 15 | 0.0% | 16.563% | 0.016% |  |
| `large_70b_gqa` | 1.0 | 294 | 206 | 100.0 | 279 | 15 | 0.0% | 16.563% | 3.312% |  |
| `large_70b_gqa` | 3.125 | 294 | 206 | 100.0 | 279 | 15 | 0.0% | 16.563% | 3.312% |  |
| `large_70b_gqa` | 6.25 | 294 | 206 | 100.0 | 279 | 15 | 0.0% | 16.563% | 3.312% |  |
| `large_70b_gqa` | 12.5 | 294 | 206 | 100.0 | 279 | 15 | 0.0% | 16.563% | 3.312% |  |
| `large_70b_gqa` | 25.0 | 294 | 206 | 100.0 | 279 | 15 | 0.0% | 16.563% | 3.312% |  |
| `large_70b_gqa` | 33.333 | 294 | 206 | 100.0 | 279 | 15 | 0.0% | 16.563% | 2.366% |  |
| `large_70b_gqa` | 50.0 | 294 | 193 | 100.0 | 279 | 15 | 0.0% | 16.563% | 1.84% |  |
| `large_70b_gqa` | 75.0 | 294 | 171 | 100.0 | 279 | 15 | 0.0% | 16.563% | 0.832% |  |
| `large_70b_gqa` | 90.0 | 294 | 139 | 100.0 | 279 | 15 | 0.0% | 16.563% | 0.332% |  |
| `large_70b_gqa` | 99.0 | 294 | 71 | 100.0 | 279 | 15 | 0.0% | 16.563% | 0.028% |  |
| `large_70b_gqa` | 100.0 | 294 | 0 | 100.0 | 279 | 15 | 0.0% | 0.0% | 0.0% |  |
| `qwen3_30b_a3b_gqa` | 0.0 | 294 | 221 | 100.0 | 283 | 11 | 0.0% | 16.667% | 0.016% | 16.667 |
| `qwen3_30b_a3b_gqa` | 1.0 | 294 | 206 | 100.0 | 283 | 11 | 0.0% | 16.667% | 3.333% | 16.667 |
| `qwen3_30b_a3b_gqa` | 3.125 | 294 | 206 | 100.0 | 283 | 11 | 0.0% | 16.667% | 3.333% | 16.667 |
| `qwen3_30b_a3b_gqa` | 6.25 | 294 | 206 | 100.0 | 283 | 11 | 0.0% | 16.667% | 3.333% | 16.667 |
| `qwen3_30b_a3b_gqa` | 12.5 | 294 | 206 | 100.0 | 283 | 11 | 0.0% | 16.667% | 3.333% | 16.667 |
| `qwen3_30b_a3b_gqa` | 25.0 | 294 | 206 | 100.0 | 283 | 11 | 0.0% | 16.667% | 3.333% | 16.667 |
| `qwen3_30b_a3b_gqa` | 33.333 | 294 | 206 | 100.0 | 283 | 11 | 0.0% | 16.667% | 2.381% | 16.667 |
| `qwen3_30b_a3b_gqa` | 50.0 | 294 | 193 | 100.0 | 283 | 11 | 0.0% | 16.667% | 1.852% | 16.667 |
| `qwen3_30b_a3b_gqa` | 75.0 | 294 | 171 | 100.0 | 283 | 11 | 0.0% | 16.667% | 0.838% | 16.667 |
| `qwen3_30b_a3b_gqa` | 90.0 | 294 | 139 | 100.0 | 283 | 11 | 0.0% | 16.667% | 0.334% | 16.667 |
| `qwen3_30b_a3b_gqa` | 99.0 | 294 | 71 | 100.0 | 283 | 11 | 0.0% | 16.667% | 0.029% | 16.667 |
| `qwen3_30b_a3b_gqa` | 100.0 | 294 | 0 | 100.0 | 283 | 11 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 0.0 | 252 | 179 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 1.0 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 3.125 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 6.25 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 12.5 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 25.0 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 33.333 | 252 | 164 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 50.0 | 252 | 151 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 75.0 | 252 | 129 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 90.0 | 252 | 98 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 99.0 | 252 | 40 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |
| `small_all_late_boundary` | 100.0 | 252 | 0 | 100.0 | 252 | 0 | 0.0% | 0.0% | 0.0% |  |

## Interpretation

- The TMH plan contract survived the adversarial matrix: prompt anchors stay raw/pinned, recent tails stay raw/hot, and old pages are demoted rather than evicted.
- The thesis holds as a hierarchy thesis: explicit KV layout management continues to provide a safe memory-pressure path under extreme geometry.
- The numeric `16.667%` claim should remain tied to the Qwen-30B production shape, not stated as universal across arbitrary layer splits.
