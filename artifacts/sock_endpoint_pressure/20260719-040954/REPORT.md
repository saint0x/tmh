# sock Endpoint Pressure Benchmark

This is a standalone TMH pressure harness result. It does not modify or import TMH production runtime code.

- label: `sock-qwen3-30b-a3b-gptq-int4`
- model: `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- endpoint: `http://127.0.0.1:8000`
- profile: `standard`
- generated_at: `2026-07-19T04:09:54Z`
- elapsed_s: `796.1613`

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
| `early_anchor_long_tail` | `anchor_recall` | 1 | 28.875 | 3.3255 | 100.0 |
| `early_anchor_long_tail` | `anchor_recall` | 2 | 35.5885 | 5.395 | 100.0 |
| `early_anchor_long_tail` | `anchor_recall` | 4 | 69.1259 | 5.5553 | 100.0 |
| `middle_anchor_detour` | `anchor_recall` | 1 | 29.0228 | 4.4104 | 100.0 |
| `middle_anchor_detour` | `anchor_recall` | 2 | 36.301 | 7.0522 | 100.0 |
| `middle_anchor_detour` | `anchor_recall` | 4 | 70.1652 | 7.2974 | 100.0 |
| `late_anchor_control` | `late_control` | 1 | 29.0732 | 3.3025 | 100.0 |
| `late_anchor_control` | `late_control` | 2 | 35.9386 | 5.3456 | 100.0 |
| `late_anchor_control` | `late_control` | 4 | 70.9253 | 5.4142 | 100.0 |
| `decoy_collision` | `confusable_recall` | 1 | 29.4567 | 4.3464 | 100.0 |
| `decoy_collision` | `confusable_recall` | 2 | 37.1228 | 6.8961 | 100.0 |
| `decoy_collision` | `confusable_recall` | 4 | 70.9414 | 7.2177 | 100.0 |
| `routing_table` | `structured_lookup` | 1 | 29.5537 | 4.3312 | 0.0 |
| `routing_table` | `structured_lookup` | 2 | 36.178 | 7.0763 | 0.0 |
| `routing_table` | `structured_lookup` | 4 | 70.3076 | 7.2824 | 0.0 |
| `structured_records` | `structured_lookup` | 1 | 29.2164 | 5.4766 | 0.0 |
| `structured_records` | `structured_lookup` | 2 | 36.0754 | 8.8706 | 0.0 |
| `structured_records` | `structured_lookup` | 4 | 70.363 | 9.0958 | 0.0 |
| `instruction_persistence` | `instruction_retention` | 1 | 29.0205 | 4.4108 | 100.0 |
| `instruction_persistence` | `instruction_retention` | 2 | 36.1559 | 7.0805 | 100.0 |
| `instruction_persistence` | `instruction_retention` | 4 | 70.178 | 7.2958 | 100.0 |
| `multi_hop_bridge` | `multi_hop` | 1 | 29.683 | 5.3913 | 100.0 |
| `multi_hop_bridge` | `multi_hop` | 2 | 36.3484 | 8.8037 | 100.0 |
| `multi_hop_bridge` | `multi_hop` | 4 | 70.7241 | 9.0494 | 100.0 |
| `payload_dense` | `dense_noise` | 1 | 29.4483 | 6.5199 | 100.0 |
| `payload_dense` | `dense_noise` | 2 | 36.8253 | 10.4278 | 100.0 |
| `payload_dense` | `dense_noise` | 4 | 71.2868 | 10.7734 | 100.0 |
| `long_generation_systems` | `long_generation` | 1 | 30.1862 | 12.7212 | 0.0 |
| `long_generation_systems` | `long_generation` | 2 | 36.1177 | 21.2643 | 0.0 |
| `long_generation_systems` | `long_generation` | 4 | 69.6011 | 22.0837 | 0.0 |

## Streaming TTFT Probes

| case | ttft s | elapsed s | completion tok/s |
| --- | ---: | ---: | ---: |
| `early_anchor_long_tail` | 0.1798 | 3.4178 | 28.0884 |
| `middle_anchor_detour` | 0.1564 | 4.3693 | 29.2955 |
| `late_anchor_control` | 0.1527 | 3.2941 | 29.1434 |
| `decoy_collision` | 0.1079 | 4.3783 | 29.2348 |
| `routing_table` | 0.106 | 4.3598 | 29.3592 |
| `structured_records` | 0.1475 | 4.2449 | 30.154 |
| `instruction_persistence` | 0.1472 | 4.3655 | 29.3207 |
| `multi_hop_bridge` | 0.1384 | 4.3175 | 29.6471 |
| `payload_dense` | 0.1506 | 4.3289 | 29.5685 |
| `long_generation_systems` | 0.1236 | 4.3481 | 29.438 |
