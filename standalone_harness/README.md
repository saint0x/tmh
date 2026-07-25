# Standalone Harness

This directory contains the reproducible validation surface for the standalone TMH POC.

The harnesses do not implement the production vLLM runtime. They validate the layout contract and replay frozen benchmark artifacts.

## Core Scenarios

```bash
fozzy --json run standalone_harness/tmh_only_30b_layout.fozzy.json --det --strict --seed 1337
fozzy --json run standalone_harness/tmh_30b_standard_runs3_layout_sweep.fozzy.json --det --strict --seed 1337 --proc-backend host --fs-backend host
fozzy --json run standalone_harness/tmh_adversarial_layout_stress.fozzy.json --det --strict --seed 20260719 --proc-backend host --fs-backend host
fozzy --json run standalone_harness/tmh_model_family_memory_baseline.fozzy.json --det --strict --seed 1337 --proc-backend host --fs-backend host
fozzy --json run standalone_harness/tmh_paper_claim_stress.fozzy.json --det --strict --seed 1337 --proc-backend host --fs-backend host
```

## Validators

Each Fozzy scenario wraps one validator:

```text
validate_tmh_only_30b_layout.py
validate_tmh_30b_layout_sweep.py
validate_tmh_adversarial_layout_stress.py
validate_tmh_model_family_memory_baseline.py
validate_tmh_paper_claim_stress.py
```

The validators assert:

- layout identity is `tmh_fidelity_paged_kv`
- plan coverage is complete
- no old KV page is dropped
- prompt anchor pages stay raw/pinned
- recent tail pages stay raw/hot
- older pages demote to the expected warm precision
- published reduction numbers match frozen artifacts

## Artifact Families

```text
artifacts/tmh_only_30b_layout/
artifacts/tmh_30b_standard_runs3_layout_sweep/
artifacts/tmh_adversarial_layout_stress/
artifacts/tmh_model_family_memory_baseline/
artifacts/tmh_paper_claim_stress/
artifacts/fozzy/
```

The production SOCK/vLLM performance artifacts are not duplicated here. See `RESULTS.md` and the SOCK repo for that runtime evidence.
