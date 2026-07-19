# TMH 30B Layout Sweep

This report sweeps one KV layout only: `tmh_fidelity_paged_kv`.
It reuses the real 30B sock endpoint traffic corpus and varies page size plus hot-window budget.

- model: `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- endpoint_result: `artifacts/sock_endpoint_pressure/20260719-040147/result.json`
- kv_layout: `tmh_fidelity_paged_kv`
- completion_source: `effective-max`
- page_tokens: `8, 16, 32, 64`
- budgets: `75.0, 50.0, 25.0, 12.5, 6.25, 3.125, 0.0`
- generated_at: `2026-07-19T04:04:23Z`

## Sweep Summary

| page tokens | hot budget | cases | effective bytes/token | compression vs raw | warm reduction vs int8 old KV | total reduction vs same-hot int8 old KV | plan pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 75.0 | 10 | 84424.298 | 14.119% | 16.667% | 2.295% | 100.0% |
| 8 | 50.0 | 10 | 70027.87 | 28.764% | 16.667% | 5.454% | 100.0% |
| 8 | 25.0 | 10 | 55682.021 | 43.357% | 16.667% | 9.857% | 100.0% |
| 8 | 12.5 | 10 | 48519.821 | 50.643% | 16.667% | 12.784% | 100.0% |
| 8 | 6.25 | 10 | 44944.172 | 54.28% | 16.667% | 14.502% | 100.0% |
| 8 | 3.125 | 10 | 43160.753 | 56.095% | 16.667% | 15.435% | 100.0% |
| 8 | 0.0 | 10 | 41313.266 | 57.974% | 16.667% | 16.463% | 100.0% |
| 16 | 75.0 | 10 | 84813.164 | 13.724% | 16.667% | 2.222% | 100.0% |
| 16 | 50.0 | 10 | 70318.834 | 28.468% | 16.667% | 5.38% | 100.0% |
| 16 | 25.0 | 10 | 55994.434 | 43.039% | 16.667% | 9.744% | 100.0% |
| 16 | 12.5 | 10 | 48843.137 | 50.314% | 16.667% | 12.639% | 100.0% |
| 16 | 6.25 | 10 | 45276.298 | 53.942% | 16.667% | 14.334% | 100.0% |
| 16 | 3.125 | 10 | 43532.46 | 55.716% | 16.667% | 15.237% | 100.0% |
| 16 | 0.0 | 10 | 41666.533 | 57.614% | 16.667% | 16.261% | 100.0% |
| 32 | 75.0 | 10 | 85578.898 | 12.945% | 16.667% | 2.081% | 100.0% |
| 32 | 50.0 | 10 | 71068.264 | 27.706% | 16.667% | 5.192% | 100.0% |
| 32 | 25.0 | 10 | 56765.669 | 42.255% | 16.667% | 9.467% | 100.0% |
| 32 | 12.5 | 10 | 49631.992 | 49.512% | 16.667% | 12.292% | 100.0% |
| 32 | 6.25 | 10 | 46144.317 | 53.06% | 16.667% | 13.908% | 100.0% |
| 32 | 3.125 | 10 | 44342.774 | 54.892% | 16.667% | 14.817% | 100.0% |
| 32 | 0.0 | 10 | 42373.065 | 56.896% | 16.667% | 15.866% | 100.0% |
| 64 | 75.0 | 10 | 87769.322 | 10.716% | 16.667% | 1.689% | 100.0% |
| 64 | 50.0 | 10 | 72524.941 | 26.224% | 16.667% | 4.835% | 100.0% |
| 64 | 25.0 | 10 | 58257.586 | 40.737% | 16.667% | 8.947% | 100.0% |
| 64 | 12.5 | 10 | 51282.236 | 47.833% | 16.667% | 11.594% | 100.0% |
| 64 | 6.25 | 10 | 47679.151 | 51.498% | 16.667% | 13.188% | 100.0% |
| 64 | 3.125 | 10 | 45257.654 | 53.962% | 16.667% | 14.349% | 100.0% |
| 64 | 0.0 | 10 | 43786.13 | 55.458% | 16.667% | 15.106% | 100.0% |

## Readout

- The old/warm KV reduction remains `16.667%` wherever old KV exists, because the layout keeps old K int8, early/middle old V int4, and late old V int8.
- Total effective KV pressure reduction depends on how much of the context is still hot raw KV.
- Smaller hot windows move total effective reduction closer to the old/warm KV reduction ceiling.
- Page size changes can slightly move totals because prompt-anchor and tail pages round differently, but the no-eviction invariant stays fixed.
- This is still a layout-pressure sweep, not live runtime execution with TMH fused inside vLLM.
