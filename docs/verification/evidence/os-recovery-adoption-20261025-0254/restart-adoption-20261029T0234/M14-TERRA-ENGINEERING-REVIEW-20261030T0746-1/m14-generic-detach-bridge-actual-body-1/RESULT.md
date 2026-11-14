# M14 generic ptrace detach signal bridge: actual-source host fixture

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The selected 23-generic inventory has Rust source for all 23 names already; this reuses the retained `ptrace_detach_do_kill_bridge` candidate and its existing Rust `f06_ptrace_report_signal_kill` adapter, rather than creating a competing port. `generate.py` copies the byte-exact bridge and extracts the real adapter body from the retained candidate policy source. The included C mock is the provider and also calls the actual Rust export with the original six-argument C ABI. Four cases verify argument and raw pointer preservation, exactly one provider call, null info, integer extremes, and 64-bit return conversion including -1 and LONG_MIN. Null thread in one fixture tests forwarding only; it is not a claim that a real null thread is valid.

Commands in this directory:

```
python3 generate.py > source-hashes.txt
rustc +1.85.1 --edition 2021 --crate-type lib --emit=obj -C panic=abort -O harness.rs -o harness.o 2>rustc.stderr
cc -std=c11 -Wall -Wextra -Werror oracle.c harness.o -o oracle 2>cc.stderr
./oracle > result.txt
```

PASS: four cases, one provider call each. `source-hashes.txt` binds input and extracted bytes; SHA256 bridge 6e6659fc62a3a2df73a4c40aeaaa57e77aaf30415eded759c9640128f6e67b54; adapter 09ce29c175a6bd3fca1f618fde7684a72d6f873938038d22c6ad9e0b688c31ea; harness object 423f5bd35e21dafa7ca90d83a71551311378a5eeaaeafaf92ce65f3e40ab2091; result 20ead862068d257c7f58005d6dd6db54ea07ebae62cff126a275d5078260cec8.

One initial harness build failed because an inline module resolved `#[path]` under nonexistent policy/; `failed-harness.rs`, `failed-rustc.stderr`, and `failed-cc.stderr` preserve that failure. A single bounded correction uses `include!` to include the unchanged body; no source-under-test or oracle changed. The Rust 1.85.1 and host C compiler fixture uses explicitly defined opaque types and an external mock; it is not the pinned SDK, real-header layout verification, whole crate, default link, caller lifetime proof, actual `do_kill`, native, or retirement evidence.

The missing `f03_stack_grow_borrowed_reservation_v1` provider is not implemented: its existing contract explicitly requires owner-specific borrowed writer handoff, revalidation, other-lock preservation and progress. The current `is_memory_range_lock_taken` convention exists to let remote fault processing skip locking while the offloading writer remains held, so merely dropping the lock in the callback is not established safe. Next: integrate/review the actual retained detach source and run genuine SDK profile/provider and caller ownership checks; separately trace the actual remote fault, offload and reservation ownership before attempting stack-provider implementation. No held generic_c/direct-TID/terminate_host or execve transfer/ACK path was exercised.
