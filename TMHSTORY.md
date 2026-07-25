# TMH Story

TMH started as a question about KV compression and became a runtime tiered memory hierarchy.

## The Original Lamp

The early experiments showed that dropping old KV was not just a mild degradation. It changed behavior badly. Compressed retention, by contrast, preserved behavior much better.

That changed the frame:

```text
wrong frame: can we throw away old KV?
better frame: how should inference memory be tiered?
```

## The Research POC

The standalone TMH repo models the hierarchy:

```text
first page      -> pinned raw
recent tail     -> hot raw
old early pages -> int8 K / int4 V
old late pages  -> int8 K / int8 V
```

The POC is useful because it is small, deterministic, and Fozzy-validated. It gives a clean place to test layout claims without carrying all of vLLM.

## The Production Turn

The real implementation moved into SOCK because the meaningful test is live serving:

- vLLM scheduler integration
- physical raw/warm GPU pools
- descriptor events
- cache writers
- mixed attention kernels
- prefix-cache behavior
- raw-pressure fallback

That work made the thesis sharper. TMH is not just an accounting trick. It is a runtime policy that has to win against the exact costs of scheduling, cache updates, attention reads, and release bookkeeping.

## The Breakthrough

The largest performance bug was not the attention kernel. It was descriptor lifetime management. Canonical descriptor release scanned too much state at completion time, creating a quadratic CPU bottleneck.

Refcounts turned the bad c12 result into a positive one:

```text
old TMH c12: 171.3223 tok/s
new TMH c12: 1045.2849 tok/s
standard c12: 1023.9407 tok/s
```

That is the point where TMH became both a capacity win and a throughput-positive production path.

## Where It Stands

TMH is currently:

- positive at c4 and c12 in the production SOCK path
- much better in logical KV capacity than standard KV under the tested memory budget
- robust at c14 where earlier runs failed
- not yet a +20% throughput win at the saturation frontier

The honest ending today:

```text
TMH works. It is positive. The next frontier is turning the capacity lift into a larger throughput lift under c14+ pressure.
```
