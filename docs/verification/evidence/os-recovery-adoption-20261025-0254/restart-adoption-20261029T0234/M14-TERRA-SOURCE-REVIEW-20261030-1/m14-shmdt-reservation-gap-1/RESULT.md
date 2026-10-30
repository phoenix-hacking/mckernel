# M14 shmdt reservation coverage: actual-source fixture

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The source-bound FULL28 candidate has a concrete reservation-coverage gap in `shmdt_body_result`. Its selected `sys_shmdt` obtains the current thread's VM, passes that VM and its `memory_range_lock`, and passes `munmap_do_bridge` as the actual removal callback (`syscall_policy.rs:26890`–`26916`). The actual body (`4404`) acquires the writer, looks up the matching range, checks the start and `MF_SHMDT_OK`, then invokes that callback with `holding_lock=1`; it makes no registry query. In the same combined source, `sys_munmap`, `mprotect`, and `mremap` use reservation-aware lock helpers before their mutation, whereas this shmdt path does not. A live mmap reservation pins its VM but relies on all mutations protecting its exact range; the shmdt code does not enforce that predicate itself.

`extract.py` hash-verifies the combined source d1151a64f122d75816f039481dfe19540825a0cc2f4b5bf69123f182241b60b4 and extracts five byte-identical bodies: field access, two range accessors, shmdt logger, and the shmdt body. `test.rs` supplies C-layout model structs and mocked lock, lookup and removal callbacks. The synthetic reserved-range flag is a fixture observation, not the real registry. Commands:

```
python3 extract.py > source-bindings.txt
rustc +1.85.1 --edition=2021 --test test.rs -o test-bin 2>compiler.stderr
./test-bin --test-threads=1 > test-output.txt
```

Three tests pass: ordinary allowed shmdt calls removal once, missing `MF_SHMDT_OK` returns -EINVAL without removal, and an active synthetic reservation with flags `MF_XPMEM | MF_SHMDT_OK` still calls removal exactly once while the synthetic reservation remains active. This is an actual-body host fixture, not a real kernel registry/concurrent run, real header/ABI check or proof that this state is reachable on the supported runtime. The XPMEM and SHMDT bits are distinct (`kernel/include/memobj.h`); `shmobj_create_indexed` sets SHMDT on an existing memobj and `process_add_range_mark_xpmem_bridge` ORs XPMEM into a non-null memobj, but no complete real call chain establishing that both flags and an active reservation coexist has been established.

Source-side caller trace: selected `memlock_split_range_bridge` and `memlock_join_range_bridge` feed mprotect's reservation-guarded interval transaction; selected `process_remove_range_split_bridge` is invoked during low-level removal, whose outer owner must provide protection. The XPMEM detach candidate checks its exact returned range under its reader and attachment lock, releases both and retries on conflict; its clear-PTE helper similarly checks a span. `process_add_range_remove_bridge` directly invokes the removal provider during add-range failure under the caller's original writer, with no intrinsic token check. Call graph/alias/lock and same-owner coverage for all providers remain open. Range and memobj lifetime are not guaranteed by the VM reference alone.

Do not insert a simple spin/retry into shmdt as a claimed fix: the shared token registry does not distinguish same-owner from other-owner, and waiting on a synchronous reservation owned by the current operation can prevent its own release. Next executable step is to source-bind the SHM/XPMEM construction and actual selected provider/caller sequence to decide real coexistence, then implement an owner-aware conflict decision before mutation which releases all blocking locks, relooks up after retry, and explicitly handles same-owner recursion. Review actual lock order, lifetime and ABI; the fixture can then become a negative regression with a genuine registry stub plus an ordinary no-conflict control. No kernel source or existing evidence was changed, and no native operation was performed.

SHA256: extracted bodies 3cb53b8e1cb9584a5bbb271c09c4f55182f4beeb8ba9ad7d15f2c3bd541beacf; fixture c36058036a9313fccd5c0b1b0726eaff345f33c6b54ea9c9bbd293bf521df32b; fixture result de42a6fea0aa637238e5a5ccd2a22d7ba27521c0d99e66f9054284d40c6fe518.
