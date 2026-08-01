# Appendix B. Additional Results

## B.1 Model-family layer rounding

Finite layer counts determine the old-body saving relative to uniform INT8. The lower bound in the evaluated model-family corpus is set by the fraction of layers assigned packed values.

| Layers | First late layer | Early layers | Old-body saving |
|---:|---:|---:|---:|
| 24 | 16 | 16 | 16.667% |
| 28 | 18 | 18 | 16.071% |
| 36 | 24 | 24 | 16.667% |
| 40 | 26 | 26 | 16.250% |
| 48 | 32 | 32 | 16.667% |
| 64 | 42 | 42 | 16.406% |

The extended corpus contains 732,000 layouts, including 682,050 with a nonempty old body. No sampled layout falls below 16.071% among the fifteen evaluated production configurations. Synthetic geometries outside that family can fall lower; a one-layer all-late model has zero saving against uniform INT8.

## B.2 Qwen2.5 fact-recall measurements

Values in each cell are exact-or-prefix match / target containment, in percent.

| Policy | 50% hot | 25% | 12.5% | 6.25% | 0% |
|---|---:|---:|---:|---:|---:|
| recent only | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| quantized old | 46.4 / 64.4 | 46.0 / 64.0 | 46.0 / 64.0 | 46.0 / 64.4 | 46.0 / 64.4 |
| fidelity paged | 47.6 / 66.0 | 48.0 / 66.4 | 47.6 / 66.0 | 47.2 / 65.2 | 46.4 / 64.8 |

Full KV records 46.4% exact-or-prefix match and 64.4% containment. The policy-level quantizer used here is not the production Triton writer.

## B.3 Smaller retention sets

On SmolLM2-1.7B, recent-only produces no exact matches across the five hot budgets. Uniformly quantized old KV stays at 46.667% exact match; fidelity paging stays at 48.333%. Containment ranges from 46.667% to 48.333% for uniform quantization and from 48.333% to 50.0% for fidelity paging.

On Granite-3.3-2B, recent-only reaches 1.667% exact match at the 50% budget and zero below it. Uniformly quantized old KV records 58.333% exact match and 66.667% containment. Fidelity paging records 60.0% exact match and 66.667% containment.

## B.4 Interpretation of optimization deltas

The physical implementation improved from 26.44 to 29.76 completion tokens/s after page-aligned kernel work, a 12.56% change relative to the first version. The subsequent page-descriptor result is 29.98 tokens/s, only 0.73% above the preceding measurement. With two timed batches per cell, the latter difference is not statistically resolved.

The 64-page raw-floor experiment raises the geometric mean to 30.33 tokens/s but remains 17.37% below standard. Segmented decode raises sampled utilization to 83% while lowering throughput by 4.53% near 1K context. Together, the results argue against using utilization or compressed-page fraction as a proxy for useful throughput.

## B.5 Evidence excluded from the main result

Research notes written after the main physical benchmark describe canonical reference counters, pool-exhaustion fallback, and positive throughput at selected concurrency points. The implementation that produced those measurements is unavailable. We therefore omit the numbers instead of using them to revise the principal comparison; reproducing the mechanisms from source is necessary before they can support a paper claim.
