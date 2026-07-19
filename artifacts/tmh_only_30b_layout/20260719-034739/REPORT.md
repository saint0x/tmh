# TMH-Only 30B Layout Benchmark

This standalone report benchmarks one KV layout only: `tmh_fidelity_paged_kv`.
It does not compare legacy layouts and does not mutate TMH production source.

- model: `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- sock endpoint result: `artifacts/sock_endpoint_pressure/20260719-023427/result.json`
- kv_layout: `tmh_fidelity_paged_kv`
- page_tokens: `16`
- generated_at: `2026-07-19T03:47:39Z`
- plan_ranges: `artifacts/tmh_only_30b_layout/20260719-034739/plan_ranges.csv`
- invariant_report: `artifacts/tmh_only_30b_layout/20260719-034739/invariants.json`

## Model Shape

| field | value |
| --- | ---: |
| `layer_count` | `48` |
| `attention_heads` | `32` |
| `kv_heads` | `4` |
| `head_dim` | `128` |
| `hidden_size` | `2048` |
| `context_tokens` | `40960` |
| `late_layer_start` | `32` |
| `raw_dtype_bytes` | `2.0` |

## Budget Summary

| budget | cases | mean effective bytes/token | mean compression vs raw | mean c1 tok/s | mean c2 tok/s | mean TTFT s | contains c1 | plan pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 50.0 | 10 | 70685.347 | 28.095% | 29.697 | 37.233 | 0.1387 | 70.0% | 100.0% |
| 25.0 | 10 | 56375.563 | 42.652% | 29.697 | 37.233 | 0.1387 | 70.0% | 100.0% |
| 12.5 | 10 | 49312.66 | 49.836% | 29.697 | 37.233 | 0.1387 | 70.0% | 100.0% |
| 6.25 | 10 | 45782.39 | 53.428% | 29.697 | 37.233 | 0.1387 | 70.0% | 100.0% |
| 0.0 | 10 | 41953.058 | 57.323% | 29.697 | 37.233 | 0.1387 | 70.0% | 100.0% |

## Plan Invariants

| invariant | value |
| --- | ---: |
| validation_pass_rate_pct | `100.0` |
| checked_layer_pages | `149040` |
| cases_with_failures | `0` |
| total_shadowed_layer_page_matches | `0` |
| cold_bytes_total | `0` |
| dropped_k_pages_total | `0` |
| dropped_v_pages_total | `0` |
| layout_count | `1` |

## Case Detail At 25% Hot Budget

| case | total tokens | pages | hot | pinned | warm | ranges | effective bytes/token | compression vs raw | c1 tok/s | c2 tok/s | contains c1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `early_anchor_long_tail` | 1327 | 83 | 21 | 1 | 61 | 4 | 56127.855 | 42.904% | 29.3345 | 35.6871 | 100.0% |
| `middle_anchor_detour` | 1082 | 68 | 17 | 1 | 50 | 4 | 55905.479 | 43.13% | 29.4023 | 35.949 | 100.0% |
| `late_anchor_control` | 719 | 45 | 12 | 1 | 32 | 4 | 57469.33 | 41.539% | 30.2448 | 36.8657 | 100.0% |
| `decoy_collision` | 803 | 51 | 13 | 1 | 37 | 4 | 56027.975 | 43.005% | 30.1318 | 36.936 | 100.0% |
| `routing_table` | 788 | 50 | 13 | 1 | 36 | 4 | 56387.574 | 42.64% | 30.1439 | 36.5803 | 0.0% |
| `structured_records` | 831 | 52 | 13 | 1 | 38 | 4 | 56348.342 | 42.68% | 29.694 | 45.3907 | 0.0% |
| `instruction_persistence` | 1369 | 86 | 22 | 1 | 63 | 4 | 56081.391 | 42.951% | 29.5305 | 36.5824 | 100.0% |
| `multi_hop_bridge` | 795 | 50 | 13 | 1 | 36 | 4 | 56756.649 | 42.264% | 29.5628 | 36.2052 | 100.0% |
| `payload_dense` | 1419 | 89 | 23 | 1 | 65 | 4 | 56275.98 | 42.753% | 29.3058 | 36.7109 | 100.0% |
| `long_generation_systems` | 744 | 47 | 12 | 1 | 34 | 4 | 56375.054 | 42.652% | 29.6228 | 35.4191 | 0.0% |

## Interpretation

- This is the TMH layout ledger for the real 30B sock traffic profile, not a legacy policy matrix.
- The harness compiles a page-native TMH plan before computing memory pressure, matching the source-level `TMHMemoryPlan` shape.
- Plan ranges are resolved in native order: prompt anchor first, recent tail second, old history after that.
- `cold_bytes` remains zero by design: TMH demotes old KV fidelity instead of evicting it.
- The prompt anchor is pinned raw with hard authority.
- Earlier and middle-layer old values use int4; late-layer old values stay int8; all old keys stay int8.
- Endpoint tok/s and TTFT are copied from the live sock 30B run so layout pressure and serving behavior stay tied to the same traffic corpus.
