# sock Endpoint Pressure Benchmark

This is a standalone TMH pressure harness result. It does not modify or import TMH production runtime code.

- label: `sock-qwen3-30b-a3b-gptq-int4`
- model: `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- endpoint: `http://127.0.0.1:8000`
- profile: `standard`
- generated_at: `2026-07-19T02:34:27Z`
- elapsed_s: `240.3774`

## Token Preflight

| case | prompt tokens | original max new | effective max new | max model len |
| --- | ---: | ---: | ---: | ---: |
| `early_anchor_long_tail` | 1231 | 96 | 96 | 2048 |
| `middle_anchor_detour` | 954 | 128 | 128 | 2048 |
| `late_anchor_control` | 623 | 96 | 96 | 2048 |
| `decoy_collision` | 675 | 128 | 128 | 2048 |
| `routing_table` | 660 | 128 | 128 | 2048 |
| `structured_records` | 671 | 160 | 160 | 2048 |
| `instruction_persistence` | 1241 | 128 | 128 | 2048 |
| `multi_hop_bridge` | 635 | 160 | 160 | 2048 |
| `payload_dense` | 1227 | 192 | 192 | 2048 |
| `long_generation_systems` | 360 | 384 | 384 | 2048 |

## Throughput

| case | category | concurrency | completion tok/s mean | wall s mean | contains target mean |
| --- | --- | ---: | ---: | ---: | ---: |
| `early_anchor_long_tail` | `anchor_recall` | 1 | 29.3345 | 3.2726 | 100.0 |
| `early_anchor_long_tail` | `anchor_recall` | 2 | 35.6871 | 5.3801 | 100.0 |
| `middle_anchor_detour` | `anchor_recall` | 1 | 29.4023 | 4.3534 | 100.0 |
| `middle_anchor_detour` | `anchor_recall` | 2 | 35.949 | 7.1212 | 100.0 |
| `late_anchor_control` | `late_control` | 1 | 30.2448 | 3.1741 | 100.0 |
| `late_anchor_control` | `late_control` | 2 | 36.8657 | 5.2081 | 100.0 |
| `decoy_collision` | `confusable_recall` | 1 | 30.1318 | 4.248 | 100.0 |
| `decoy_collision` | `confusable_recall` | 2 | 36.936 | 6.9309 | 100.0 |
| `routing_table` | `structured_lookup` | 1 | 30.1439 | 4.2463 | 0.0 |
| `routing_table` | `structured_lookup` | 2 | 36.5803 | 6.9983 | 0.0 |
| `structured_records` | `structured_lookup` | 1 | 29.694 | 5.3883 | 0.0 |
| `structured_records` | `structured_lookup` | 2 | 45.3907 | 7.0499 | 0.0 |
| `instruction_persistence` | `instruction_retention` | 1 | 29.5305 | 4.3345 | 100.0 |
| `instruction_persistence` | `instruction_retention` | 2 | 36.5824 | 6.9979 | 100.0 |
| `multi_hop_bridge` | `multi_hop` | 1 | 29.5628 | 5.4122 | 100.0 |
| `multi_hop_bridge` | `multi_hop` | 2 | 36.2052 | 8.8385 | 100.0 |
| `payload_dense` | `dense_noise` | 1 | 29.3058 | 6.5516 | 100.0 |
| `payload_dense` | `dense_noise` | 2 | 36.7109 | 10.4601 | 100.0 |
| `long_generation_systems` | `long_generation` | 1 | 29.6228 | 12.963 | 0.0 |
| `long_generation_systems` | `long_generation` | 2 | 35.4191 | 21.6832 | 0.0 |

## Streaming TTFT Probes

| case | ttft s | elapsed s | completion tok/s |
| --- | ---: | ---: | ---: |
| `early_anchor_long_tail` | 0.1778 | 3.3023 | 29.0709 |
| `middle_anchor_detour` | 0.1539 | 4.401 | 29.084 |
| `late_anchor_control` | 0.1472 | 3.3181 | 28.932 |
| `decoy_collision` | 0.0969 | 4.3682 | 29.3025 |
| `routing_table` | 0.1063 | 4.3407 | 29.4885 |
| `structured_records` | 0.1469 | 4.4039 | 29.0651 |
| `instruction_persistence` | 0.1432 | 4.4681 | 28.6477 |
| `multi_hop_bridge` | 0.1396 | 4.3041 | 29.7389 |
| `payload_dense` | 0.1506 | 4.25 | 30.1178 |
| `long_generation_systems` | 0.1244 | 4.3323 | 29.5457 |
