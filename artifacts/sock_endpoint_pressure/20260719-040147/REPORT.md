# sock Endpoint Pressure Benchmark

This is a standalone TMH pressure harness result. It does not modify or import TMH production runtime code.

- label: `sock-qwen3-30b-a3b-gptq-int4`
- model: `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- endpoint: `http://127.0.0.1:8000`
- profile: `maxfit`
- generated_at: `2026-07-19T04:01:47Z`
- elapsed_s: `0.0011`

## Token Preflight

| case | prompt tokens | original max new | effective max new | max model len |
| --- | ---: | ---: | ---: | ---: |
| `early_anchor_long_tail` | 1885 | 96 | 96 | 2048 |
| `middle_anchor_detour` | 1462 | 128 | 128 | 2048 |
| `late_anchor_control` | 950 | 96 | 96 | 2048 |
| `decoy_collision` | 1014 | 128 | 128 | 2048 |
| `routing_table` | 988 | 128 | 128 | 2048 |
| `structured_records` | 999 | 160 | 160 | 2048 |
| `instruction_persistence` | 1896 | 128 | 128 | 2048 |
| `multi_hop_bridge` | 963 | 160 | 160 | 2048 |
| `payload_dense` | 1881 | 192 | 163 | 2048 |
| `long_generation_systems` | 523 | 384 | 384 | 2048 |

## Throughput

| case | category | concurrency | completion tok/s mean | wall s mean | contains target mean |
| --- | --- | ---: | ---: | ---: | ---: |
