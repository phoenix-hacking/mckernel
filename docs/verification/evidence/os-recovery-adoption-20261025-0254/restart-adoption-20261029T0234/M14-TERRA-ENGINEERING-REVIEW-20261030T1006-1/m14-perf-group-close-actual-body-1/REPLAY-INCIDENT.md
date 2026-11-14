# Accidental retained perf fixture replay

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

While preparing the separate group-close fixture, I mistakenly executed the already consumed local fixture a second time. The exact unintended shell line was:

```text
python3 -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-perf-group-actual-body-rust-correction-1/run.py 2>/dev/null
```

The command followed preparation of this new directory; its tool call reported exit 0 and about 0.2 seconds, but did not retain exact start/end timestamps, its outer stderr, a new wait4 record, or process identities. The old script recompiled the small Rust host fixture on CPU0 and executed its synthetic mock, overwriting its own RUN.json, command stdout/stderr captures and fixture binary. It did not perform a kernel, Docker, guest, native-kernel, privileged, controller, or cleanup operation. This was an accidental replay, not newly authorized evidence.

Read-only stat after the replay found the fixture binary mtime 2026-10-30T09:50:20.214050Z, first command capture mtime 09:50:20.222050Z, second command capture mtime 09:50:20.226051Z, and RUN.json mtime 09:50:20.230051Z. These file timestamps bracket writes, not the exact process start or finish. The original RESULT.md and MANIFEST.json still have mtimes 09:47:37.040906Z and 09:47:37.044906Z respectively.

The original reviewer-bound result is `../m14-perf-group-actual-body-rust-correction-1/RESULT.md`, SHA256 `a5a0cd542a5c8f438b81490eb1f54cb4d873eee94e7b9c910b7215e95a440513`, and its original MANIFEST.json SHA256 `7ff3a809953f181470387eba1e1dcaee6ecadb4b8d620eb478d1e718bb6edaf0`. The independent reviewer had reported that the three mock cases support the C/Rust group-error and one-free observations while leaving real allocator, production ABI/provider and concurrent group lifetime open. This incident does not strengthen or replace that review.

Comparison to the pre-replay manifest established identical before/after SHA256 for every rewritten retained file:

| File | Before and after SHA256 |
| --- | --- |
| RUN.json | `ce733529eceeaf5908ed3988d05e762fd450cc87b2952e88e05280c6984f0dd6` |
| cmd-1.stdout, cmd-1.stderr, cmd-2.stderr | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| cmd-2.stdout | `00b3b48db9ee519335913d3dc3f67bb7b378270c9692a34343f7aaa270decb15` |
| fixture | `524b2f3eb9afaeb2450209af816dda0603ddfaecf4e33056e6aa731d82627a63` |

The original file *contents* are therefore still available and match their previously recorded hashes. The pre-replay metadata for the rewritten files, including their old mtimes/ctimes and prior fixture inode, was not recorded in the available manifest and cannot be reconstructed from these hashes. The exact replay start/finish, replay subprocess identities and discarded outer stderr were not captured. The original `run.stdout`, `run.stderr`, `run.exit`, result and manifest were not rewritten by the accidental line. No restore, delete, additional replay or further fixture execution was performed after the stop instruction. The newly prepared group-close source is unexecuted.
