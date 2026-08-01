# 2. Background and Related Work

## 2.1 KV cache storage in serving systems

For decoder attention, each layer stores keys and values for every retained token. With $L$ layers, $N$ KV heads, head dimension $D$, scalar width $s$, and sequence length $T$, a homogeneous cache requires

$$
M_{KV}=2LNTDs
$$

bytes per sequence before allocator and metadata overhead. Grouped-query attention reduces $N$, but the dependence on context and concurrency remains linear.

PagedAttention separates a request's logical block sequence from physical allocation [@kwon2023pagedattention]. Blocks need not be contiguous, and multiple requests can refer to the same prefix blocks. vAttention preserves virtual contiguity through operating-system demand paging rather than explicit block tables [@prabhu2024vattention]. Both approaches solve placement and fragmentation. Neither requires pages in one request to have different element formats.

TMH retains the logical-block model because block identity is already used for prefix hashing, sharing, preemption, and cleanup. Heterogeneity appears one level below: the descriptor for a logical page selects a raw or warm pool. That separation is straightforward for pages written directly into their final representation. It becomes harder when a page changes format while other requests still refer to it.

## 2.2 Quantization and mixed precision

KV quantization exploits the fact that cached tensors need not use the same precision as the model's attention arithmetic. KIVI showed that keys and values have different outlier structure and benefit from asymmetric treatment [@liu2024kivi]. KVTuner searches hardware-friendly key/value precision pairs layer by layer using offline sensitivity analysis [@li2025kvtuner]. KVmix also assigns precision by layer, keeps recent pivotal tokens at full precision, and supplies low-bit CUDA kernels [@li2025kvmix]. These two systems are especially close to TMH's precision policy.

TMH is less ambitious as a quantizer. Its two-thirds layer boundary is fixed, keys remain INT8, and only early-layer old values use INT4. The intended contribution lies elsewhere: page roles are carried through the allocator, scheduler-facing identity, prefix ownership, and mixed physical execution. KVTuner and KVmix provide stronger methods for choosing precision; TMH asks what the serving system must do once different pages actually have different representations. A natural successor would replace the fixed split with a calibrated schedule while retaining the same lifecycle contract.

DiffKV, originally released as LeanKV, combines differentiated K/V treatment, parallel compaction, and an on-GPU memory manager [@zhang2025diffkv]. It is the closest prior example of quantization joined to runtime allocation. TMH differs by making page age and request ownership explicit in scheduler-visible roles, but it should not claim heterogeneous precision or runtime-managed compressed KV as new by themselves.

## 2.3 Eviction, sparsity, and retained history

Another family of methods reduces cache size by deciding which tokens remain addressable. Scissorhands and H2O use persistence or heavy-hitter behavior to retain influential state [@liu2023scissorhands; @zhang2023h2o]. SnapKV infers important prompt positions from an observation window [@li2024snapkv]. Quest uses query-aware page sparsity, while PyramidKV, Ada-KV, and RazorAttention allocate capacity nonuniformly across layers or heads [@tang2024quest; @cai2024pyramidkv; @feng2024adakv; @tang2024razorattention]. StreamingLLM preserves early attention sinks to stabilize bounded-window decoding [@xiao2023streamingllm].

TMH does not select tokens inside a page. Every retained logical page remains present, with the first page pinned and the old body compressed. This is conservative in quality and regular in memory access, but it cannot match a good sparse selector's byte efficiency. The fact-recall experiment later in the paper is not an argument against sparsity; it only shows that age alone is a poor eviction rule for the chosen prompts.

## 2.4 Storage hierarchies for reusable KV

Recent systems broaden the problem from device compression to placement across memory tiers. AdaptCache chooses a compression method, compression rate, and DRAM/SSD placement for reusable KV entries, optimizing load delay under a quality constraint [@feng2025adaptcache]. KVDrive coordinates GPU memory, host DRAM, and SSD while overlapping I/O and attention work for long-context inference [@lin2026kvdrive]. SeKV stores compact semantic summaries on GPU and low-rank span representations on CPU, reconstructing detail when a query needs it [@abaskohi2026sekv].

Those systems make the term *hierarchy* literal through hardware placement. TMH's evaluated pools occupy the same GPU memory and differ in precision, mutability, and access cost. Its claim is therefore narrower: a hierarchy can also be defined by representation and lifecycle, but the present implementation does not offer cross-device placement. AdaptCache is particularly important for positioning because it already treats compression choice and storage location as one optimization problem. TMH contributes a page-identity and mixed-kernel view within the serving engine, not the general idea of a KV-native hierarchy.

Infini-attention takes a different route by adding compressive recurrent memory to the attention mechanism [@munkhdalai2024infiniattention]. SeKV similarly introduces semantic reconstruction. TMH leaves the model architecture unchanged and preserves one addressable KV entry per retained token, paying a larger storage cost in exchange for a simpler semantic contract.

## 2.5 Accelerator co-design

Hummingbird and TeLLMe show how memory layout, precision, and execution must be designed together on embedded FPGAs [@li2025hummingbird; @qiao2025tellme]. HiKV applies hierarchical importance at both token and element granularity in a dedicated decoding accelerator [@fang2026hikv]. TMH runs on general-purpose GPUs, yet the same lesson applies: a smaller representation is useful only when the access path can consume it efficiently. The production results in Section 6 show the penalty when a custom mixed kernel competes with a highly optimized homogeneous backend.

## 2.6 Positioning

Table 1 locates TMH among its closest neighbors. The comparison avoids broad novelty claims; by 2026, layer-wise precision, full-precision recent windows, multi-tier placement, and custom low-bit attention have all appeared in prior work.

**Table 1. Comparison with closely related KV-cache systems.**

| System | Main decision | Storage domain | Runtime identity/lifecycle focus | TMH distinction |
|---|---|---|---|---|
| KVTuner | offline layer-wise K/V bit width | GPU | limited | richer precision search; TMH adds page roles and physical ownership |
| KVmix | layer importance and recent full-precision tokens | GPU | partial | closest precision pattern; TMH retains paged logical identity across pools |
| DiffKV | differentiated compaction and allocation | GPU | strong | closest systems neighbor; TMH makes anchor/tail/body and request overlays explicit |
| AdaptCache | compression type, rate, and DRAM/SSD placement | DRAM and SSD | cache-entry placement | broader storage hierarchy; TMH focuses on in-server page execution |
| KVDrive | cross-tier placement and pipeline scheduling | GPU, DRAM, SSD | tier coordination | hardware hierarchy rather than same-device representation tiers |
| SeKV | semantic span resolution and reconstruction | GPU and CPU | semantic span lifecycle | model-assisted reconstruction rather than dense page preservation |
| TMH | page role plus fixed layer-dependent value precision | GPU | logical block, canonical page, request view | direct placement joined to page identity and mixed execution |

The defensible thesis is not that TMH discovered heterogeneous KV caching. It is that representation, block identity, sharing, and kernel dispatch must be designed as one contract. The prototype makes much of that contract concrete and, just as importantly, reveals where the contract is still broken.
