# TMH Paper Claim Stress

This is the larger pre-paper stress run for the production TMH memory-pressure claim.
It evaluates many deterministic traffic variants across every locally cached model config and promotes only the conservative floor.

- generated_at: `2026-07-19T07:34:46Z`
- kv_layout: `tmh_fidelity_paged_kv`
- model_config_count: `15`
- base_pressure_case_count: `31`
- run_count: `40`
- evaluated_row_count: `732000`
- old_kv_row_count: `682050`
- invariant_pass_rate_pct: `100.0`
- conservative_old_warm_reduction_floor_pct: `16.071`
- promoted_public_number_pct: `16.0`

## Claim Readout

- The pre-paper conservative floor is `16.071%` old/warm KV pressure reduction versus same-hot uniform-int8 old KV.
- Public/product wording should stay at `at least 16.0% old/warm KV memory-pressure reduction across the tested production model-family stress baseline`.
- This remains a memory-pressure/layout claim, not yet a live vLLM-internal KV-manager speedup claim.

## Run Summary

| run | rows | old rows | pass % | min warm reduction | mean warm reduction | min total reduction |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 18600 | 18600 | 100.0 | 16.071% | 16.455% | 2.046% |
| 1 | 18600 | 17205 | 100.0 | 16.071% | 16.455% | 0.786% |
| 2 | 18600 | 16830 | 100.0 | 16.071% | 16.455% | 0.785% |
| 3 | 18360 | 16395 | 100.0 | 16.071% | 16.456% | 0.487% |
| 4 | 17800 | 16015 | 100.0 | 16.071% | 16.457% | 0.125% |
| 5 | 18360 | 17610 | 100.0 | 16.071% | 16.456% | 0.765% |
| 6 | 18600 | 17085 | 100.0 | 16.071% | 16.455% | 0.766% |
| 7 | 18040 | 16930 | 100.0 | 16.071% | 16.456% | 0.806% |
| 8 | 18360 | 16485 | 100.0 | 16.071% | 16.456% | 0.766% |
| 9 | 18360 | 16830 | 100.0 | 16.071% | 16.456% | 0.487% |
| 10 | 18040 | 18040 | 100.0 | 16.071% | 16.456% | 1.709% |
| 11 | 18040 | 16660 | 100.0 | 16.071% | 16.456% | 0.308% |
| 12 | 18040 | 15880 | 100.0 | 16.071% | 16.456% | 0.786% |
| 13 | 18360 | 18255 | 100.0 | 16.071% | 16.456% | 0.777% |
| 14 | 18600 | 17445 | 100.0 | 16.071% | 16.455% | 0.788% |
| 15 | 18120 | 16140 | 100.0 | 16.071% | 16.458% | 0.814% |
| 16 | 18600 | 17235 | 100.0 | 16.071% | 16.455% | 0.765% |
| 17 | 18040 | 18040 | 100.0 | 16.071% | 16.456% | 2.044% |
| 18 | 18360 | 16995 | 100.0 | 16.071% | 16.456% | 0.125% |
| 19 | 18120 | 16965 | 100.0 | 16.071% | 16.457% | 0.487% |
| 20 | 18040 | 18040 | 100.0 | 16.071% | 16.456% | 1.697% |
| 21 | 18600 | 16710 | 100.0 | 16.071% | 16.455% | 0.78% |
| 22 | 18360 | 16545 | 100.0 | 16.071% | 16.456% | 0.186% |
| 23 | 18600 | 17340 | 100.0 | 16.071% | 16.455% | 0.063% |
| 24 | 18040 | 16150 | 100.0 | 16.071% | 16.456% | 0.308% |
| 25 | 18040 | 16525 | 100.0 | 16.071% | 16.456% | 0.308% |
| 26 | 18040 | 17920 | 100.0 | 16.071% | 16.456% | 0.849% |
| 27 | 18360 | 16665 | 100.0 | 16.071% | 16.456% | 0.768% |
| 28 | 18600 | 16575 | 100.0 | 16.071% | 16.455% | 0.247% |
| 29 | 18040 | 16465 | 100.0 | 16.071% | 16.456% | 0.125% |
| 30 | 18040 | 18040 | 100.0 | 16.071% | 16.456% | 1.735% |
| 31 | 18600 | 17655 | 100.0 | 16.071% | 16.455% | 0.785% |
| 32 | 18600 | 17475 | 100.0 | 16.071% | 16.455% | 0.779% |
| 33 | 18600 | 16560 | 100.0 | 16.071% | 16.455% | 0.368% |
| 34 | 18360 | 18360 | 100.0 | 16.071% | 16.456% | 2.045% |
| 35 | 18360 | 15885 | 100.0 | 16.071% | 16.456% | 0.765% |
| 36 | 18600 | 17130 | 100.0 | 16.071% | 16.455% | 0.794% |
| 37 | 18040 | 16705 | 100.0 | 16.071% | 16.456% | 0.428% |
| 38 | 18040 | 15760 | 100.0 | 16.071% | 16.456% | 0.487% |
| 39 | 18040 | 17905 | 100.0 | 16.071% | 16.456% | 0.769% |

## Model Summary

| model | rows | old rows | pass % | min warm reduction | mean warm reduction | min total reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `JunHowie/Qwen3-32B-GPTQ-Int4` | 49000 | 45670 | 100.0 | 16.406% | 16.406% | 0.064% |
| `Qwen/Qwen2.5-0.5B-Instruct` | 48400 | 45070 | 100.0 | 16.667% | 16.667% | 0.065% |
| `Qwen/Qwen2.5-1.5B-Instruct` | 48400 | 45070 | 100.0 | 16.071% | 16.071% | 0.063% |
| `Qwen/Qwen2.5-32B-Instruct-AWQ` | 48400 | 45070 | 100.0 | 16.406% | 16.406% | 0.064% |
| `Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4` | 48400 | 45070 | 100.0 | 16.406% | 16.406% | 0.064% |
| `Qwen/Qwen2.5-3B-Instruct` | 48400 | 45070 | 100.0 | 16.667% | 16.667% | 0.065% |
| `Qwen/Qwen2.5-7B-Instruct` | 48400 | 45070 | 100.0 | 16.071% | 16.071% | 0.063% |
| `Qwen/Qwen3-14B` | 49000 | 45670 | 100.0 | 16.25% | 16.25% | 0.063% |
| `Qwen/Qwen3-30B-A3B-GPTQ-Int4` | 49000 | 45670 | 100.0 | 16.667% | 16.667% | 0.065% |
| `Qwen/Qwen3-32B` | 49000 | 45670 | 100.0 | 16.406% | 16.406% | 0.064% |
| `Qwen/Qwen3-4B` | 49000 | 45670 | 100.0 | 16.667% | 16.667% | 0.065% |
| `Qwen/Qwen3-4B-Instruct-2507` | 49600 | 46270 | 100.0 | 16.667% | 16.667% | 0.065% |
| `Qwen/Qwen3-8B` | 49000 | 45670 | 100.0 | 16.667% | 16.667% | 0.065% |
| `kaitchup/Qwen3-32B-autoround-2bit-gptq` | 49000 | 45670 | 100.0 | 16.406% | 16.406% | 0.064% |
| `kaitchup/Qwen3-32B-autoround-4bit-gptq` | 49000 | 45670 | 100.0 | 16.406% | 16.406% | 0.064% |

## Interpretation

- The larger stress run preserves the same conservative production number as the model-family baseline.
- The number to stand behind for paper/product language is the floor, not the average.
- The result is comfortable for a memory hierarchy and pressure-accounting claim.
- The remaining claim boundary is runtime integration: live vLLM/sock KV internals still need direct TMH-managed execution before claiming end-to-end runtime speedup from TMH itself.
