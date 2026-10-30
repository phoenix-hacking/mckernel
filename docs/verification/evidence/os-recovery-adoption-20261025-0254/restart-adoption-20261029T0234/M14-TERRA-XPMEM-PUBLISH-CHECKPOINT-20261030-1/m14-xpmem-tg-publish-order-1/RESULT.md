# Private XPMEM TG publication-order correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Status: UNSELECTED, UNCOMPILED, UNTESTED, NOT ACCEPTED. This is a source-only correction for the existing `xpmem_open_tg_body_result` TG initialization order. It does not establish partition lifetime, open/close, group ownership, rollback, clone, host FD, or native behavior.

The exact preimage is `/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/f06-debug-constants-align32-host-1/src/kernel/rust/xpmem_helpers.rs`, SHA256 `e8c7970b672c724f14da2eb0a12fdbcd11df62f824422a5f8a98da4364328255`. The candidate moves the existing store of `current_thread` to `tg_group_leader` from after the hash bucket unlock to immediately after all other TG initialization and `tg_not_destroyable_fn`, before the bucket lock and list insertion. All other calls, return paths, locks and their order, argument/layout ABI and the C fallback remain unchanged. A hash-list reader can observe the new leader when insertion occurs; this statement does not assert that surrounding lifetime or other synchronization is correct.

`xpmem_tg_publication_tests.rs` is a separate actual-body fixture with mocked allocation, lookup and lock/list boundary providers. A separate test-only patch makes it a child module of the candidate for a future test build; the production patch contains no test graft. The fixture checks at the actual insertion callback that the leader, VM, IDs, prior ref initialization and bucket-lock callback are present; it checks the existing-TG path, current error-pointer-as-miss fallback, allocation failure and missing callback. It is not compiled or executed, so its own buildability and assertions remain to be reviewed. The error-pointer case records existing behavior, not an endorsement of that behavior.

Artifacts, SHA256:

- `xpmem_helpers.rs`: `8a88864073aec2d288297893da072bc26ba34773405bedb09f7c981a0c398892`
- `publish-order.patch`: `a8f4e33cff2cafac59acbbc28b125ad916840b8ae615714a56d78f55611935ab`
- `test-module.patch`: `5c5620bcd0dbb1e4c85c79c0fc604ce3003f5f8c30399ccfeb7a31202154adab`
- `xpmem_tg_publication_tests.rs`: `6f64df2e9374307d9fad50f4af3a7f2e192534ece619885ef160ae19721a27c8`

Commands: bounded `rg`/`sed` source reads, Python source move plus unified-diff generation in this private directory, fixture creation via heredoc, and `sha256sum` on the artifacts. No patch application, compiler, fixture, native, Docker, guest, privileged, controller or cleanup operation was run. Next: independent source/fixture review, exact combined overlay and selector binding, then admitted light-profile actual-body verification. Default/link/native acceptance requires separate proof.
