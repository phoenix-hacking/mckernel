# Same-Ddebug atomic-view source successor

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source candidate and host fixture only. No production integration,
compiler/link image, default ownership, native/app/389 acceptance or race-free
claim. Independent NO-GO on registry traversal and complete access coverage is
unchanged. The earlier AtomicDdebug candidate and its artifacts remain untouched.

The selected WAKEUP_DEBUG is again the exact original `#[repr(C)] Ddebug`
allocation (the 32-bit packed field is ordinary `u32` in its definition).
Static initialization supplies the existing bit encoding; the logger and the
special selected-record path call `AtomicU32::from_ptr` on the raw address of
that static's `line_flags`. Compile-time assertions bind Ddebug alignment and
field offset to AtomicU32 alignment. Relaxed loads and CAS preserve line bits.
The selected path derives its word pointer directly from the actual static,
not the registry-walk pointer, and does not create references to the whole
Ddebug. This removes the added distinct `AtomicDdebug` aggregate-type issue for
the Rust-owned record, subject to review; it does not prove the entire program
satisfies the from_ptr safety contract.

The pinned toolchain's `lib/rustlib/src/rust/library/core/src/sync/atomic.rs`
lines 2598–2666 documents the API's atomic alignment, read/write lifetime and
non-mixing requirements. All accesses to this particular 32-bit word, including
line, flags, show/store and hidden byte/whole-record accesses, must be traced to
valid atomic accesses or proved nonconcurrent. Static initialization occurs
before runtime; no concurrent ordinary access or mismatched-width access is
allowed, and no C fallback or alternate registry provider may bypass the branch.
The 389 other records keep existing access behavior; they are not covered by
this narrow change. A source list, selector/linked-address audit, actual build
identity and independent ownership review are required.

The separate registry problem remains. Linker script `kernel/config/smp-x86.lds.in`
lines 20–23 concatenates independently emitted records between linker-defined
symbols; `debug.rs` uses `dbg.add(1)` and dereferences raw fields across those
records. Pinned core pointer docs require in-bounds allocation provenance for
`add`, and `wrapping_add` retains the originating provenance; replacing the
arithmetic or using equal C layout does not supply a proof. The two-record
fixture executes that same unresolved walk and cannot turn it into proof.

A genuinely single foreign array would need one real defined array allocation,
valid alignment/initialization for every element and per-consumer pointer
identity. A linker alias over separately compiled objects is not, by itself,
proof the compiler's memory model recognizes one array. A separately generated
array of actual per-record pointers may avoid cross-allocation arithmetic if
it is a real single table and each entry carries valid original pointer
provenance, but static/local C and Rust descriptors, section ordering, pointer
relocations, typing, life span, concurrency and no duplicates/omissions all need
source and linked-image evidence. Copying records into an array while original
loggers still read their old descriptors would change dynamic-debug behavior.
An assembly iterator is likewise not automatically a provenance proof; its
foreign pointers, accesses, ABI and mutation contract require independent
compiler/model and cross-language review. No such redesign is implemented.

Local checks: compiled two tests using the pinned nightly, --test, the two
paired cfgs, debug-default 0, existing reviewed HOST CPU0/512MiB profile; both
compiles exited 0. `atomic_access_test --test-threads=1` passed 2/2 (actual
logger and accessor; six threads interleave on CPU0). The actual Rust sysfs
show/store fixture passed 1/1 with a two-record linker section, host libc
format/string/strtol and mocked kernel dependencies. Its copied debug.rs is an
exact candidate prefix followed only by test wrappers. Results, warnings and
streams are retained beside binaries. CPU0 interleaving is not simultaneous
multicore execution; tests do not prove provenance, exact 389 layout or native
behavior. Commands are the same as the previous candidate's README and fixture
RESULT.md, with this directory as the working directory and output streams in
this directory; exact commands are retained below.

Compile accessor: `/usr/bin/env MCKERNEL_F03_PTRACE_WAKEUP_DDEBUG_FLAGS=0 /usr/bin/taskset -c 0 /usr/bin/prlimit --as=536870912 --cpu=30 --nofile=128 --fsize=8388608 --core=0 /usr/bin/timeout --signal=TERM --kill-after=5s 45s /home/holden/mckernel-work/toolchains/rustup/toolchains/nightly-2026-02-19-x86_64-unknown-linux-gnu/bin/rustc --edition=2021 --test --cfg f03_leaf_callbacks_candidate --cfg f03_ptrace_wakeup_log_candidate atomic_access_test.rs -o atomic_access_test 2>atomic_compile.stderr`
Compile sysfs: same command with `sysfs-body-tests-1/sysfs_test.rs -o sysfs-body-tests-1/sysfs_test 2>sysfs-body-tests-1/compile.stderr` in place of the final source/output arguments.
Run each binary using `/usr/bin/taskset -c 0 /usr/bin/prlimit --as=536870912 --cpu=30 --nofile=128 --fsize=8388608 --core=0 /usr/bin/timeout --signal=TERM --kill-after=5s 45s`, followed by the binary path and `--test-threads=1`; stdout and stderr were redirected to retained files.

Hashes:
- logger `0d727062a6faccfe3a1ca0213a29dbbb321301632474cd3bb27e2e04899ec49a`
- debug.rs `60da116d4a0f0fa9bd9a31c3dc5f48cfc337b166bbb2cb790108094aed65e83d`
- registry accessor `a2062798333ab7fab2f93a0bd9c3464284913b9ec22c6563dfd038c8dc6b07f0`
- atomic fixture source `3d90f3c7417ba761672a93c23e01faf8f56e6b096f6d1982c9272b4e508b01a2`, binary `3ce72d9a77783d1f1d768e8d9543d94a4bf11514421479fd2f0fb11c9338643b`
- sysfs fixture source `aa7d6898a3c67b96178669e85bf97672c8a48afdb7df4bb6b20e9b448c8ce475`, binary `b6666c96e6d533d193f40b7bd82bb80ee57269c3287427b45765672428881415`
