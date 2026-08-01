# 7. Limitations and Discussion

## 7.1 A hierarchy in representation, not location

TMH's raw and warm pools normally occupy the same GPU memory. The word *hierarchy* refers to different obligations: raw pages are larger, mutable, and cheap to read; warm pages are smaller, stable, and more expensive to interpret. Placement, conversion, and access cost distinguish the tiers even when their physical device is the same.

AdaptCache and KVDrive use a broader meaning, spanning DRAM, SSD, or GPU memory [@feng2025adaptcache; @lin2026kvdrive]. Their existence narrows TMH's novelty. The useful question is not who first used the word hierarchy, but which interfaces survive when KV state moves. TMH's answer is a stable logical page above representation-specific slots. That idea remains relevant if warm pages later move to host memory, but the current data offer no evidence about cross-device transfer.

## 7.2 Direct placement is not dynamic tiering

Most of the evaluated mixed pages are prompt pages assigned to their final representation before prefill writes them. Nothing moves after those tokens are cached. Direct placement captures much of the capacity benefit for long prompts, and it is simpler than background demotion, but it does not respond to changing memory pressure or a growing decode tail.

A genuine dynamic hierarchy needs a materialization state between allocation and publication. The descriptor cannot become readable until conversion finishes, and the source cannot be reclaimed until earlier readers finish. Prefix overlays need the same discipline in the opposite direction. The prototype has roles, slots, and ownership for these transitions but no payload operation connecting them.

The safest short-term system would disable live role changes and keep a page in whichever initialized representation it already occupies. That restriction reduces adaptability without risking silent reads from empty storage. A complete implementation can later add bulk conversion and make publication contingent on its completion.

## 7.3 The precision policy is a baseline

The fixed two-thirds split was chosen for simplicity. KVTuner and KVmix demonstrate that layer sensitivity can be measured and used to assign precision more carefully [@li2025kvtuner; @li2025kvmix]. TMH's plan can carry a model-specific boundary or several layer ranges, so a calibrated schedule does not require a new ownership model. It may, however, require more physical pool classes and more kernel variants.

The early-value INT4 implementation must also be repaired. Expanding the observed range to include zero solves the sign-definite collapse while preserving the same four-bit payload. After correction, model activations should be measured directly. Random synthetic vectors are not enough: value distributions, outliers, and sensitivity vary by layer and head.

Keys remain INT8 throughout the warm body because key error perturbs the softmax weights. That conservative choice is consistent with KIVI and KVTuner, but it is not proven optimal for the evaluated Qwen model [@liu2024kivi; @li2025kvtuner].

## 7.4 Capacity needs a workload

The 73.82% capacity increase assumes a 25% raw reserve. Long prompts with stable bodies fit that mixture well. Many short requests do not. Every active sequence consumes an anchor, and a large hot window can make most pages raw. Separate free lists then create class fragmentation: free warm slots cannot satisfy a raw allocation.

Capacity should ultimately be reported as admitted work under a request distribution, not only as logical blocks. A convincing experiment would increase concurrency until the all-BF16 server begins to preempt or reject requests, then compare throughput, tail latency, and quality at the same device budget. The present endpoint study stops at concurrency four, far below the point at which the additional logical pages become the deciding resource.

Dynamic pool balance could be handled through conservative provisioning, class-aware admission, or migration. Static provisioning is simplest but leaves capacity unused. Admission can predict raw and warm demand from each request's block table. Migration offers the most flexibility and also carries the greatest correctness and bandwidth cost.

## 7.5 One general kernel is not enough

The unified attention kernel was a sensible first implementation because it provided one route through every supported page type. Its responsibilities are broad: descriptor resolution, raw loads, scale loads, INT8 conversion, nibble unpacking, causal masking, grouped-query mapping, and streaming-softmax updates. The standard backend does much less interpretation in its inner loop.

The natural endpoint is a small kernel family. Raw-only short sequences should use the existing homogeneous backend or a genuinely raw-specialized path. Mixed direct-prefill requests need page descriptors and dequantization. Long, low-concurrency decode may benefit from segmentation once the context is large enough. All-warm prompt regions may deserve a separate prefill kernel. The scheduler and metadata builder already know which regime is present; rediscovering it inside every tile wastes work.

Native handoff must be explicit. The failed ROCm bypass showed that a backend kernel cannot consume TMH storage merely because the active pages happen to be raw. Block tables, layouts, and softmax boundaries must match the backend's contract.

## 7.6 Lifecycle cost belongs in the algorithm

Descriptor scans are host work, yet they can dominate a cache feature at concurrency. Reclamation determines when a supposedly available slot can be reused. A hierarchy with slow liveness accounting does not possess its theoretical capacity in practice.

Canonical reference counts are the straightforward replacement for repeated scans. Prefix-cache ownership, active request references, and overlays should update separate counters because their lifetimes differ. Such accounting is not glamorous kernel work, but it is part of the memory algorithm. The later unversioned performance notes are consistent with that diagnosis, although they cannot serve as evidence until the implementation is recovered or reproduced.

## 7.7 Evidence limits

The production result comes from one AMD integrated GPU and one Qwen3-30B MoE/GPTQ model. CUDA diagnostics use a different model and device. Register pressure, memory bandwidth, compiler behavior, and backend quality differ enough that the 18.33% deficit should not be transferred numerically to another accelerator.

The retention study uses much smaller models and an emulated policy. Its prompts emphasize fact recall and use strict string matching. Long-form generation, code, multilingual work, retrieval at production context lengths, and the physical Qwen3-30B cache remain unevaluated.

Statistical power is also limited. Two timed batches expose large regressions but cannot resolve sub-percent changes. The per-cell table is more informative than the optimizer chronology: it shows a consistent deficit and identifies a workload where the gap approaches one half. Repeated runs with confidence intervals are needed before small tuning effects deserve interpretation.

Numerical error is the weakest evidence category. The available thresholds omit trial count and distribution, and the INT4 bug proves that a permissive aggregate comparison can miss structured failures. A corrected writer should be evaluated through tensor-error distributions, logit drift, and end-to-end deterministic generation before any quality claim is attached to physical TMH.

## 7.8 What TMH establishes

Despite those limits, three results survive.

First, page roles can be lowered into real physical pools without changing the scheduler's logical block interface. Directly placed raw and warm pages coexist in one request and pass through an integrated server.

Second, the capacity arithmetic is substantial and transparent. Scales, layer-dependent payloads, descriptors, anchor reserve, and integral allocation are included. The result is not inferred from nominal bit width alone.

Third, the negative performance result identifies the actual research problem. Heterogeneous storage is easy to justify with bytes and hard to make competitive in execution. The missing work is no longer vague: repair INT4, make migration transactional, replace descriptor scans with direct liveness accounting, and dispatch narrower kernels by page regime.

The prototype is valuable because it reaches the point where those costs become visible. Its strongest claim is not a finished hierarchy or a speedup. It is an empirical account of what a page-role-aware KV cache requires once it leaves an offline compression experiment and enters a serving runtime.
