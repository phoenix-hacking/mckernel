# Private perf descriptor initialization candidate

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Status: UNSELECTED, UNCOMPILED, UNTESTED, NOT ACCEPTED. The paired private Rust and C witness patches are based respectively on the already prepared standalone negative-return postimage `7b13e1975636f0c496394e4fb6b0243ae926837a03099a498a69b9c3ab04b8b1` and the selected `f06-debug-constants-align32-host-1/src/kernel/syscall.c` SHA256 `4af4524be701ecdbaae09fba906c99bd065364c4caefdcf007820f463773eaf4`. The selected `abi.rs` SHA256 is `ff48bc2e7c8fe00abf19572a3fe75661dd464a7a475fec91a0ac7d870f6fdd3e`. The C preimage and its actual header mount require fresh verification in any later composition.

The private specialization rejects a descriptor size mismatch before event allocation or host offload. After a successful tracked descriptor allocation, it stores null into the exact Rust `Mckfd.opt` and `Mckfd.dup_cb` fields before calling the unchanged real publication body. The x86 Rust size/alignment/offset assertions and guarded C size/alignment/offset/type assertions are paired; these have not been compiled. The C `sig_no` slot remains unchanged and carries no reference count.

The test source is included only for `cfg(test)` and must be placed adjacent to the candidate Rust module for a future independently admitted profile. The fixture calls the actual specialized entry body and its actual nested group/counter/offload/publication helpers, with small mocked event allocation, counter, host syscall, descriptor allocation and locking boundaries. It supplies a fully poisoned descriptor, checks the omitted fields are initialized by the time the real publisher takes its lock, checks head insertion and the other published fields, and checks size rejection before event allocation. Its implementation and expected behavior have not been verified by compilation or execution.

This is an initialization correction only. A null duplicate callback does not establish the ownership of a raw perf event shared across copied descriptors. Parent-list clone exclusion, in-flight descriptor pinning, fork/close and VM/process teardown, group leader/member lifetime, partial-allocation unwind, and the opening thread's counter-map ownership remain unresolved. It is not safe to select this candidate independently or treat this fixture as native, default, link or lifecycle acceptance.

Artifacts and SHA256:

- `f03_perf_group_cleanup.rs`: `cc0fc2d3fd5ded4898a56dbb82ec8def8b9d25819d63377b4efcac00d281bb54`
- `f03_perf_group_cleanup.patch`: `ad7bba955da793e7af6d926bc0a47a47a5a714a5950879d6cb42b59b222a9094`
- `syscall-witness.patch`: `e3387da61c7d80453d68cbbbc0c56efd4ffd7a502e9d067e5995247a7e73ad3d`
- `f03_perf_descriptor_init_tests.rs`: `27a8b3e056f1cae4319f68f6ec4c9b02e128f9607c6fa2ba72aee47c55c25a14`

Commands: source reads with `rg` and `sed`, creation of private successor and patch with Python `difflib`, creation of fixture with a shell heredoc, and `sha256sum` of those four private artifacts. No patch application, compile, test, live operation or native execution was performed. Next: independent source review, resolve lifecycle contract, bind the paired exact source/header preimages, and run the unchanged test only after an applicable reviewed light profile and fresh admission.
