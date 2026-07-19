# TMH 30B Layout Sweep

This report sweeps one KV layout only: `tmh_fidelity_paged_kv`.
It reuses the real 30B sock endpoint traffic corpus and varies page size plus hot-window budget.

- model: `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- endpoint_result: `artifacts/sock_endpoint_pressure/20260719-023427/result.json`
- kv_layout: `tmh_fidelity_paged_kv`
- page_tokens: `8, 16, 32, 64`
- budgets: `75.0, 50.0, 25.0, 12.5, 6.25, 3.125, 0.0`
- generated_at: `2026-07-19T03:56:09Z`

## Sweep Summary

| page tokens | hot budget | cases | effective bytes/token | compression vs raw | warm reduction vs int8 old KV | total reduction vs same-hot int8 old KV | plan pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 75.0 | 10 | 84552.891 | 13.988% | 16.667% | 2.271% | 100.0% |
| 8 | 50.0 | 10 | 70116.331 | 28.674% | 16.667% | 5.431% | 100.0% |
| 8 | 25.0 | 10 | 55810.476 | 43.227% | 16.667% | 9.81% | 100.0% |
| 8 | 12.5 | 10 | 48655.583 | 50.505% | 16.667% | 12.723% | 100.0% |
| 8 | 6.25 | 10 | 45124.132 | 54.097% | 16.667% | 14.41% | 100.0% |
| 8 | 3.125 | 10 | 43358.997 | 55.893% | 16.667% | 15.328% | 100.0% |
| 8 | 0.0 | 10 | 41456.529 | 57.828% | 16.667% | 16.381% | 100.0% |
| 16 | 75.0 | 10 | 85293.995 | 13.235% | 16.667% | 2.133% | 100.0% |
| 16 | 50.0 | 10 | 70685.347 | 28.095% | 16.667% | 5.287% | 100.0% |
| 16 | 25.0 | 10 | 56375.563 | 42.652% | 16.667% | 9.605% | 100.0% |
| 16 | 12.5 | 10 | 49312.66 | 49.836% | 16.667% | 12.43% | 100.0% |
| 16 | 6.25 | 10 | 45782.39 | 53.428% | 16.667% | 14.082% | 100.0% |
| 16 | 3.125 | 10 | 43846.382 | 55.397% | 16.667% | 15.071% | 100.0% |
| 16 | 0.0 | 10 | 41953.058 | 57.323% | 16.667% | 16.1% | 100.0% |
| 32 | 75.0 | 10 | 86553.568 | 11.953% | 16.667% | 1.903% | 100.0% |
| 32 | 50.0 | 10 | 71670.548 | 27.093% | 16.667% | 5.043% | 100.0% |
| 32 | 25.0 | 10 | 57544.743 | 41.462% | 16.667% | 9.192% | 100.0% |
| 32 | 12.5 | 10 | 50484.202 | 48.645% | 16.667% | 11.926% | 100.0% |
| 32 | 6.25 | 10 | 46612.186 | 52.584% | 16.667% | 13.681% | 100.0% |
| 32 | 3.125 | 10 | 44626.069 | 54.604% | 16.667% | 14.667% | 100.0% |
| 32 | 0.0 | 10 | 42946.117 | 56.313% | 16.667% | 15.553% | 100.0% |
| 64 | 75.0 | 10 | 88413.786 | 10.061% | 16.667% | 1.574% | 100.0% |
| 64 | 50.0 | 10 | 74024.624 | 24.698% | 16.667% | 4.481% | 100.0% |
| 64 | 25.0 | 10 | 59903.541 | 39.063% | 16.667% | 8.405% | 100.0% |
| 64 | 12.5 | 10 | 52159.509 | 46.941% | 16.667% | 11.236% | 100.0% |
| 64 | 6.25 | 10 | 48187.275 | 50.981% | 16.667% | 12.947% | 100.0% |
| 64 | 3.125 | 10 | 47044.808 | 52.143% | 16.667% | 13.491% | 100.0% |
| 64 | 0.0 | 10 | 44932.234 | 54.292% | 16.667% | 14.515% | 100.0% |

## Readout

- The old/warm KV reduction remains `16.667%` wherever old KV exists, because the layout keeps old K int8, early/middle old V int4, and late old V int8.
- Total effective KV pressure reduction depends on how much of the context is still hot raw KV.
- Smaller hot windows move total effective reduction closer to the old/warm KV reduction ceiling.
- Page size changes can slightly move totals because prompt-anchor and tail pages round differently, but the no-eviction invariant stays fixed.
- This is still a layout-pressure sweep, not live runtime execution with TMH fused inside vLLM.
