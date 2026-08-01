# 8. Conclusion

KV pages acquire different jobs as a request evolves. The first page anchors a shared history, the newest page absorbs writes, and the older body mainly consumes resident memory. TMH represents those jobs directly. Logical block numbers remain stable while page descriptors select BF16, INT8, or packed-INT4 storage beneath them.

The evaluated direct-placement prototype turns that idea into measurable capacity. At a 25% raw reserve, the 48-layer profile admits 73.82% more logical KV blocks than an all-BF16 cache. Retention experiments also show the danger of treating age as permission to discard: compressed old state preserves facts that a recent-only window loses.

Execution remains the harder half. The final evaluated TMH path is 18.33% slower than standard KV across the production suite. Live migration and prefix-overlay materialization are absent, and the early INT4 writer mishandles sign-definite vectors. Those are not minor qualifications; they define the present boundary of the system.

The work nevertheless points to a concrete architecture. Keep logical identity above representation, publish a page only after its payload is materialized, account for liveness directly, and dispatch kernels according to the page mix already known by the scheduler. With those pieces in place, tiered KV storage can become more than a capacity calculation. The next implementation must show that the added capacity can admit useful work faster than a homogeneous cache at the same memory limit.
