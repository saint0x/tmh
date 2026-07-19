# TMH Model-Family Memory Baseline

This report measures the production TMH memory-plan logic across every locally cached Hugging Face model config.
It promotes the conservative floor across supported configs rather than a single-model number.

- generated_at: `2026-07-19T07:14:50Z`
- kv_layout: `tmh_fidelity_paged_kv`
- model_config_count: `15`
- pressure_case_count: `31`
- row_count: `18600`
- old_kv_row_count: `14145`
- invariant_pass_rate_pct: `100.0`
- promoted_old_warm_reduction_floor_pct: `16.071`
- promoted_public_number_pct: `16.0`

## Production Number

The supported-model floor is `16.071%` old/warm KV pressure reduction versus same-hot uniform-int8 old KV.

For external/product language, use `at least 16.0% old/warm KV memory-pressure reduction across the tested production model-family baseline`.

This is intentionally a floor, not an average. Total effective KV pressure reduction still depends on hot-window size, page rounding, and how much old KV exists in a request.

## Model Summary

| model | layers | kv heads | late start | rows | old rows | pass % | min warm reduction | mean warm reduction | min total reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `JunHowie/Qwen3-32B-GPTQ-Int4` | 64 | 8 | 42 | 1240 | 943 | 100.0 | 16.406% | 16.406% | 0.497% |
| `Qwen/Qwen2.5-0.5B-Instruct` | 24 | 2 | 16 | 1240 | 943 | 100.0 | 16.667% | 16.667% | 0.505% |
| `Qwen/Qwen2.5-1.5B-Instruct` | 28 | 2 | 18 | 1240 | 943 | 100.0 | 16.071% | 16.071% | 0.487% |
| `Qwen/Qwen2.5-32B-Instruct-AWQ` | 64 | 8 | 42 | 1240 | 943 | 100.0 | 16.406% | 16.406% | 0.497% |
| `Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4` | 64 | 8 | 42 | 1240 | 943 | 100.0 | 16.406% | 16.406% | 0.497% |
| `Qwen/Qwen2.5-3B-Instruct` | 36 | 2 | 24 | 1240 | 943 | 100.0 | 16.667% | 16.667% | 0.505% |
| `Qwen/Qwen2.5-7B-Instruct` | 28 | 4 | 18 | 1240 | 943 | 100.0 | 16.071% | 16.071% | 0.487% |
| `Qwen/Qwen3-14B` | 40 | 8 | 26 | 1240 | 943 | 100.0 | 16.25% | 16.25% | 0.492% |
| `Qwen/Qwen3-30B-A3B-GPTQ-Int4` | 48 | 4 | 32 | 1240 | 943 | 100.0 | 16.667% | 16.667% | 0.505% |
| `Qwen/Qwen3-32B` | 64 | 8 | 42 | 1240 | 943 | 100.0 | 16.406% | 16.406% | 0.497% |
| `Qwen/Qwen3-4B` | 36 | 8 | 24 | 1240 | 943 | 100.0 | 16.667% | 16.667% | 0.505% |
| `Qwen/Qwen3-4B-Instruct-2507` | 36 | 8 | 24 | 1240 | 943 | 100.0 | 16.667% | 16.667% | 0.505% |
| `Qwen/Qwen3-8B` | 36 | 8 | 24 | 1240 | 943 | 100.0 | 16.667% | 16.667% | 0.505% |
| `kaitchup/Qwen3-32B-autoround-2bit-gptq` | 64 | 8 | 42 | 1240 | 943 | 100.0 | 16.406% | 16.406% | 0.497% |
| `kaitchup/Qwen3-32B-autoround-4bit-gptq` | 64 | 8 | 42 | 1240 | 943 | 100.0 | 16.406% | 16.406% | 0.497% |

## Budget Summary

| budget | rows | old rows | pass % | min warm reduction | mean warm reduction | min total reduction | mean total reduction |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0 | 2325 | 1860 | 100.0 | 16.071% | 16.455% | 0.487% | 14.44% |
| 1.0 | 2325 | 1785 | 100.0 | 16.071% | 16.455% | 4.945% | 14.094% |
| 3.125 | 2325 | 1785 | 100.0 | 16.071% | 16.455% | 4.945% | 13.73% |
| 6.25 | 2325 | 1785 | 100.0 | 16.071% | 16.455% | 4.945% | 13.046% |
| 12.5 | 2325 | 1785 | 100.0 | 16.071% | 16.455% | 4.945% | 11.565% |
| 25.0 | 2325 | 1785 | 100.0 | 16.071% | 16.455% | 4.945% | 8.874% |
| 50.0 | 2325 | 1770 | 100.0 | 16.071% | 16.455% | 2.291% | 4.785% |
| 75.0 | 2325 | 1590 | 100.0 | 16.071% | 16.455% | 0.788% | 1.951% |

## Boundary

- The production memory-pressure number should be the conservative old/warm KV floor across supported model configs, not the Qwen-30B-only value.
- The exact per-model reduction is determined by the model's layer count and TMH late-layer split.
- The current supported-model floor is set by Qwen2.5 models with `28` layers and `late_layer_start=18`.
- Total effective KV pressure reduction is workload-dependent because hot raw KV and prompt-anchor pages are intentionally preserved.
