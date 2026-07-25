# TMH Results

This file is the evidence ledger. It deliberately separates production SOCK results from standalone POC validation.

## Production SOCK Results

Environment:

```text
Host: GMKtec EVO-X2
GPU: AMD Strix Halo / Radeon 8060S, gfx1151
Runtime: ROCm 7.2.4
Model: Qwen/Qwen3-30B-A3B-GPTQ-Int4
Production repo: https://github.com/ariacomputecompany/sock
```

Best validated throughput points:

| Run | Wall | p50 | p90 | Total tok/s | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Standard c4 | `27.3267s` | `18.1438s` | `27.3235s` | `1022.0045` | baseline |
| TMH c4 after refcount | `23.5851s` | `21.2238s` | `23.5809s` | `1184.1359` | `+15.86%` tok/s |
| Standard c12 | `81.8280s` | `50.4540s` | `77.8302s` | `1023.9407` | baseline |
| TMH c12 after refcount | `80.1571s` | `58.5576s` | `80.0961s` | `1045.2849` | `+2.08%` tok/s |

Frontier robustness:

| Run | Wall | p50 | p90 | Total tok/s | Success |
| --- | ---: | ---: | ---: | ---: | ---: |
| c14 before overlay fallback | n/a | n/a | n/a | n/a | `0/14` |
| c14 BT8192 after fallback | `97.0692s` | `62.4780s` | `97.0302s` | `1007.0447` | `14/14` |
| c14 BT16384 after canonical fallback | `108.3874s` | `68.4651s` | `108.3815s` | `901.8857` | `14/14` |

Allocator/capacity result:

```text
TMH logical KV capacity at util0.35: +73.51% vs standard
```

Interpretation:

- TMH is now throughput-positive at the best validated production operating point.
- TMH has a strong memory-capacity story.
- c14+ is robust but not yet a throughput win versus the best c12 point.
- The next production work is active-step efficiency under raw pressure.

## Standalone Layout Validation

The standalone harnesses validate the POC layout contract against frozen artifacts and synthetic stress matrices.

| Suite | Result |
| --- | ---: |
| Qwen-30B layout sweep rows | `280` |
| Qwen-30B compiled plan ranges | `1,080` |
| Qwen-30B old/warm reduction | `16.667%` |
| adversarial rows | `16,632` |
| adversarial checked layer-pages | `356,890,836` |
| model-family rows | `18,600` |
| model-family old/warm reduction floor | `16.071%` |
| paper-claim stress rows | `732,000` |
| paper-claim stress old-KV rows | `682,050` |

Artifact anchors:

```text
artifacts/tmh_30b_standard_runs3_layout_sweep/20260719-041243/REPORT.md
artifacts/tmh_adversarial_layout_stress/robust-stress-v1/REPORT.md
artifacts/tmh_model_family_memory_baseline/model-family-v1/REPORT.md
artifacts/tmh_paper_claim_stress/paper-claim-stress-v1/REPORT.md
```

## Honest Boundary

The standalone POC results prove deterministic layout accounting and invariants. They do not, by themselves, prove production speed.

The production speed and capacity results are from SOCK.
