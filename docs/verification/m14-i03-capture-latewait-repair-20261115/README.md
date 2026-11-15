# Late original-wait capture cleanup

Functional McKernel OS/apps and Rust/allowed assembly only; **NO SECURITY TESTING**.

This is a tested source repair for future capture instances serving
`M14-I03-E1`. It has not changed the current retained process or accepted an
original checklist condition.

The original capture owner can join its original child after a timeout, but its
query context still retains the selector, input and capture descriptors. The
final retention loop therefore continues even after the child is joined. The
patch finishes those original descriptors once after positive late-wait proof,
persists the actual capture receipt, and preserves the initial timeout and its
traceback. Live children, ambiguous closes and I/O or persistence failures retain
their actual owning context. Successful queries and the selected keeper bodies
are unchanged. Resource retirement still requires the owning Root's actual proof.

The patch is `capture-latewait.patch`, SHA256
`412dbdc7ae08d1e0837423287e10b7ad1209c8307bfc6a4570ff149a594c7212`.
`candidate_capture_root_once.py` is a frozen proposal, **not a launch command**;
its paths and request pins belong to the original failed operation. Apply the
small patch to the next fresh capture source and bind that actual operation.
Never run the frozen candidate or fixture keeper as a controller.

The three offline fixtures use a fake original Popen and real fixture-owned
pipes/files. They cover terminal late completion, live/ambiguous retention, and
one-shot close/persistence failure. The selected keeper fixture is an exact copy
of original source SHA256
`1f668620d63bf7ab4a4b86ee6c8d2128b96d59d4e19c4d0601ab2dc894870657`;
tests extract definitions rather than execute its controller entrypoint.

From the repository root:

```sh
taskset -c 7 python3 -B docs/verification/m14-i03-capture-latewait-repair-20261115/test_capture_latewait.py
```

The initial three fixtures passed in 0.070 seconds with 22.3 MiB peak RSS under
a 512 MiB address-space ceiling. This proves the offline lifecycle repair, not
module linkage, native behavior, or M14/M15 acceptance. Passing build artifacts
remain in the existing `m14-m15-build-reuse-20261115` manifest and local cache.
