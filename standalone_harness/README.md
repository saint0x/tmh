# Standalone sock Endpoint Pressure Harness

This harness is intentionally outside the TMH source-of-truth runtime. It does not import or modify `src/` or `python/kv_tiered_real/`.

Its job is to pressure-test a live sock OpenAI-compatible endpoint with TMH-shaped prompts on larger served models, then write standalone JSON, CSV, and Markdown artifacts.

## Current sock Launch Used

```bash
cd /home/deepsaint/work/sock
. /home/deepsaint/.cargo/env
source vllm/.venv/bin/activate
sockK_RUNTIME_PROFILE=rocm PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false \
  target/debug/sock serve Qwen/Qwen3-30B-A3B-GPTQ-Int4 \
  --host 127.0.0.1 \
  --port 8000 \
  --max-model-len 2048 \
  --max-num-seqs 8 \
  --max-num-batched-tokens 2048 \
  --gpu-memory-utilization 0.35 \
  --enforce-eager \
  --disable-log-stats
```

## Harness Commands

Smoke, 512-compatible shape:

```bash
cd /home/deepsaint/work/kv-tiered/tmh
standalone_harness/sock_endpoint_pressure_bench.py \
  --profile smoke \
  --runs 1 \
  --warmup-runs 1 \
  --concurrency-levels 1,2 \
  --stream-probe \
  --timeout-s 900
```

Standard, 2048-compatible shape:

```bash
cd /home/deepsaint/work/kv-tiered/tmh
standalone_harness/sock_endpoint_pressure_bench.py \
  --profile standard \
  --runs 1 \
  --warmup-runs 1 \
  --concurrency-levels 1,2 \
  --stream-probe \
  --timeout-s 1200
```

Near-context-limit, 2048-compatible shape:

```bash
cd /home/deepsaint/work/kv-tiered/tmh
standalone_harness/sock_endpoint_pressure_bench.py \
  --profile maxfit \
  --runs 1 \
  --warmup-runs 1 \
  --concurrency-levels 1,2 \
  --stream-probe \
  --timeout-s 1200
```

Preflight only:

```bash
standalone_harness/sock_endpoint_pressure_bench.py --profile standard --dry-run --timeout-s 120
standalone_harness/sock_endpoint_pressure_bench.py --profile maxfit --dry-run --timeout-s 300
```

## Current Artifacts

- 512-token smoke: `artifacts/sock_endpoint_pressure/20260719-022821/REPORT.md`
- 2048-token standard: `artifacts/sock_endpoint_pressure/20260719-023427/REPORT.md`
- 2048-token standard CSV: `artifacts/sock_endpoint_pressure/20260719-023427/summary.csv`
- 2048-token standard raw JSON: `artifacts/sock_endpoint_pressure/20260719-023427/result.json`
- 2048-token stronger standard, runs 3, concurrency 1/2/4: `artifacts/sock_endpoint_pressure/20260719-040954/REPORT.md`
- 2048-token maxfit preflight: `artifacts/sock_endpoint_pressure/20260719-040147/REPORT.md`

## Interpretation Boundary

This harness measures black-box sock endpoint behavior under TMH-shaped prompt pressure. It is not yet a TMH-policy A/B test because sock/vLLM is not exposing alternate KV residency/fidelity policies through the endpoint.

Use this as the served-model baseline and pressure corpus. The next implementation step is to wire real TMH policy control into the runtime path, then reuse this same harness to compare policies under identical traffic.

## TMH-Only 30B Layout Benchmark

The endpoint pressure harness measures live sock serving behavior. The TMH-only layout harness turns that same traffic corpus into a single-layout KV ledger for `tmh_fidelity_paged_kv`.

The layout harness now compiles a page-native TMH plan before calculating memory pressure. It mirrors the source-level `TMHMemoryPlan` contract:

- prompt anchor resolves first and is pinned `raw/raw`
- recent tail resolves second and stays hot `raw/raw`
- old early/middle-layer pages use `int8` keys and `int4` values
- old late-layer pages use `int8` keys and `int8` values
- no page is evicted or represented as cold storage in this layout

```bash
cd /home/deepsaint/work/kv-tiered/tmh
standalone_harness/tmh_only_30b_layout_bench.py \
  --endpoint-result artifacts/sock_endpoint_pressure/20260719-023427/result.json \
  --page-tokens 16 \
  --budgets 50,25,12.5,6.25,0
```

Current artifact:

- `artifacts/tmh_only_30b_layout/20260719-023922/REPORT.md`

Each run emits:

- `REPORT.md`: human-readable benchmark report
- `result.json`: full benchmark result with endpoint metrics, rows, and invariant summary
- `summary.csv`: case/budget summary rows
- `plan_ranges.json`: compiled TMH plan ranges for every case and budget
- `plan_ranges.csv`: spreadsheet-friendly version of the same plan ranges
- `invariants.json`: validation summary for coverage, authority, precision, and no-eviction guarantees

This report intentionally has one KV layout only: `tmh_fidelity_paged_kv`. It is the layout ledger to compare against the earlier 30B sock serving run.

## TMH 30B Layout Sweep

The sweep harness pushes the same one-layout contract across page sizes and more aggressive hot budgets.

```bash
cd /home/deepsaint/work/kv-tiered/tmh
standalone_harness/tmh_30b_layout_sweep.py \
  --endpoint-result artifacts/sock_endpoint_pressure/20260719-023427/result.json \
  --page-tokens 8,16,32,64 \
  --budgets 75,50,25,12.5,6.25,3.125,0
```

Current artifact:

- `artifacts/tmh_30b_layout_sweep/20260719-035609/REPORT.md`
- `artifacts/tmh_30b_standard_runs3_layout_sweep/20260719-041243/REPORT.md`
- `artifacts/tmh_30b_maxfit_preflight_layout_sweep/20260719-040423/REPORT.md`

Current validation:

```bash
cd /home/deepsaint/work/kv-tiered/tmh
standalone_harness/validate_tmh_30b_layout_sweep.py
/home/deepsaint/work/fozzy/target/release/fozzy doctor --deep \
  --scenario standalone_harness/tmh_30b_layout_sweep.fozzy.json \
  --runs 5 \
  --seed 1337 \
  --json \
  --proc-backend host \
  --fs-backend host \
  --http-backend host
/home/deepsaint/work/fozzy/target/release/fozzy ci \
  artifacts/fozzy/tmh_30b_layout_sweep.trace.fozzy \
  --strict \
  --json \
  --proc-backend host \
  --fs-backend host \
  --http-backend host
```

The current sweep contains 280 case/page/budget rows and 1,080 compiled plan ranges. The warm old-KV reduction is `16.667%` across all swept page sizes and budgets, with 100% plan validation and no cold or dropped KV pages.

The stronger standard sweep is regenerated from the runs-3 endpoint corpus. It preserves the same `16.667%` warm old-KV reduction and 100% plan validation while tying the layout-pressure result to repeated live measurements at concurrency `1`, `2`, and `4`.

The maxfit preflight sweep uses the `effective_max_tokens` from the near-context-limit profile as the completion pressure source. This gives a conservative layout-pressure read before running the expensive live generation pass.

Paper-facing read:

- The `16.667%` old/warm KV pressure reduction is stable across the standard measured 30B corpus and the maxfit near-context preflight corpus.
- Total effective KV pressure depends on the hot raw window; this is expected and should be reported separately from warm old-KV pressure.
- These standalone harnesses prove compiled layout accounting against real sock endpoint traffic. They do not yet prove live vLLM execution with TMH-managed KV internals.

## TMH Adversarial Layout Stress

The adversarial stress harness attacks the TMH memory-plan contract with synthetic model shapes and sequence geometry rather than another endpoint replay.

```bash
cd /home/deepsaint/work/kv-tiered/tmh
standalone_harness/tmh_adversarial_layout_stress.py --run-id robust-stress-v1
standalone_harness/validate_tmh_adversarial_layout_stress.py \
  artifacts/tmh_adversarial_layout_stress/robust-stress-v1
```

Current artifact:

- `artifacts/tmh_adversarial_layout_stress/robust-stress-v1/REPORT.md`
- `artifacts/fozzy/tmh_adversarial_layout_stress.trace.fozzy`

Current validation:

```bash
cd /home/deepsaint/work/kv-tiered/tmh
/home/deepsaint/.local/bin/fozzy validate \
  standalone_harness/tmh_adversarial_layout_stress.fozzy.json \
  --json
/home/deepsaint/.local/bin/fozzy --json run \
  standalone_harness/tmh_adversarial_layout_stress.fozzy.json \
  --det \
  --strict \
  --seed 20260719 \
  --proc-backend host \
  --record artifacts/fozzy/tmh_adversarial_layout_stress.trace.fozzy \
  --record-collision overwrite
/home/deepsaint/.local/bin/fozzy trace verify \
  artifacts/fozzy/tmh_adversarial_layout_stress.trace.fozzy \
  --strict \
  --json
/home/deepsaint/.local/bin/fozzy replay \
  artifacts/fozzy/tmh_adversarial_layout_stress.trace.fozzy \
  --json
/home/deepsaint/.local/bin/fozzy ci \
  artifacts/fozzy/tmh_adversarial_layout_stress.trace.fozzy \
  --json
```

Stress result:

- `16,632` total rows
- `9,255` old-KV rows
- `356,890,836` checked layer-pages
- `100%` plan validation
- `100%` invariant pass rate
- `0` cold/dropped KV violations
- `0` negative total-reduction rows with old KV
- Qwen-30B old/warm reduction remains `16.667%`

Boundary:

- the TMH hierarchy contract held across the adversarial matrix
- the exact `16.667%` warm old-KV reduction is Qwen-30B-shape specific
- arbitrary layer splits produce different warm-reduction percentages, and the one-layer all-late boundary shape intentionally has `0%` reduction versus uniform-int8 old KV

## TMH Model-Family Memory Baseline

The model-family baseline runs the production TMH planner against every locally cached Hugging Face config. This is the baseline to use for production memory-pressure language because it promotes the cross-model floor rather than a single-model value.

```bash
cd /home/deepsaint/work/kv-tiered/tmh
standalone_harness/tmh_model_family_memory_baseline.py --run-id model-family-v1
standalone_harness/validate_tmh_model_family_memory_baseline.py \
  artifacts/tmh_model_family_memory_baseline/model-family-v1
```

Current artifact:

- `artifacts/tmh_model_family_memory_baseline/model-family-v1/REPORT.md`
- `artifacts/fozzy/tmh_model_family_memory_baseline.trace.fozzy`

Current validation:

```bash
cd /home/deepsaint/work/kv-tiered/tmh
/home/deepsaint/.local/bin/fozzy validate \
  standalone_harness/tmh_model_family_memory_baseline.fozzy.json \
  --json
/home/deepsaint/.local/bin/fozzy --json run \
  standalone_harness/tmh_model_family_memory_baseline.fozzy.json \
  --det \
  --strict \
  --seed 20260719 \
  --proc-backend host \
  --record artifacts/fozzy/tmh_model_family_memory_baseline.trace.fozzy \
  --record-collision overwrite
/home/deepsaint/.local/bin/fozzy trace verify \
  artifacts/fozzy/tmh_model_family_memory_baseline.trace.fozzy \
  --strict \
  --json
/home/deepsaint/.local/bin/fozzy replay \
  artifacts/fozzy/tmh_model_family_memory_baseline.trace.fozzy \
  --json
/home/deepsaint/.local/bin/fozzy ci \
  artifacts/fozzy/tmh_model_family_memory_baseline.trace.fozzy \
  --json
```

Baseline result:

- `15` actual cached model configs
- `31` pressure cases
- `18,600` total rows
- `14,145` old-KV rows
- `100%` plan validation
- `100%` invariant pass rate
- conservative old/warm KV reduction floor: `16.071%`
- production claim number: `at least 16.0% old/warm KV memory-pressure reduction across the tested production model-family baseline`

Boundary:

- the Qwen-30B production shape still has `16.667%` old/warm KV reduction
- the production-wide number should be the cross-model floor, not the Qwen-30B-only value
- total effective KV pressure reduction remains workload-dependent because hot raw KV and prompt-anchor pages are intentionally preserved

## TMH Paper Claim Stress

The paper-claim stress harness is the larger pre-paper confidence pass. It evaluates many deterministic pressure variants over the full local model-config set and keeps only aggregate artifacts so the repo remains usable.

```bash
cd /home/deepsaint/work/kv-tiered/tmh
standalone_harness/tmh_paper_claim_stress.py \
  --run-id paper-claim-stress-v1 \
  --run-count 40 \
  --exhaustive-layer-page-limit 0
standalone_harness/validate_tmh_paper_claim_stress.py \
  artifacts/tmh_paper_claim_stress/paper-claim-stress-v1
```

Current artifact:

- `artifacts/tmh_paper_claim_stress/paper-claim-stress-v1/REPORT.md`
- `artifacts/fozzy/tmh_paper_claim_stress.trace.fozzy`

Current validation:

```bash
cd /home/deepsaint/work/kv-tiered/tmh
/home/deepsaint/.local/bin/fozzy validate \
  standalone_harness/tmh_paper_claim_stress.fozzy.json \
  --json
/home/deepsaint/.local/bin/fozzy --json run \
  standalone_harness/tmh_paper_claim_stress.fozzy.json \
  --det \
  --strict \
  --seed 20260719 \
  --proc-backend host \
  --record artifacts/fozzy/tmh_paper_claim_stress.trace.fozzy \
  --record-collision overwrite
/home/deepsaint/.local/bin/fozzy trace verify \
  artifacts/fozzy/tmh_paper_claim_stress.trace.fozzy \
  --strict \
  --json
/home/deepsaint/.local/bin/fozzy replay \
  artifacts/fozzy/tmh_paper_claim_stress.trace.fozzy \
  --json
/home/deepsaint/.local/bin/fozzy ci \
  artifacts/fozzy/tmh_paper_claim_stress.trace.fozzy \
  --json
```

Stress result:

- `40` deterministic traffic runs
- `15` actual cached model configs
- `31` base pressure cases
- `732,000` evaluated rows
- `682,050` old-KV rows
- `100%` invariant pass rate
- conservative old/warm KV pressure floor: `16.071%`
- production/paper claim number: `at least 16.0% old/warm KV memory-pressure reduction across the tested production model-family stress baseline`

Claim boundary:

- comfortable: TMH supports a production memory-hierarchy / memory-pressure reduction claim
- comfortable: the promoted number should be the conservative `16.0%+` floor
- not yet claimed: live vLLM-internal TMH KV management produces end-to-end runtime speedup
