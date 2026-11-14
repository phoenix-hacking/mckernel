Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
SOURCE ONLY batch2: full installed eclair-dump-backtrace.exp.in successor.
No compiler, fixture, subprocess-under-test, PTY process, native or canonical action.

Runtime state machine directly ports all seven expect alternatives, thread
selection/backtrace/skip/pagination, nested `not known.` quit dialogue, Unknown
thread quit and Quit-anyway acknowledgement. Arbitrary byte chunk boundaries,
first matching input position and original rule precedence are preserved. A
bounded incomplete-pattern suffix replaces expect's implicit input buffer.
EOF and child exit preserve original success disposition, including child nonzero
status; spawn/read/write errors return1. Original helper ignores argv; same here.

eclair_native.rs uses only upstream Linux libc openpty/libutil, setsid,
TIOCSCTTY ioctl, close and std::process Command. PTY child gets controlling
terminal and shared stdin/stdout/stderr, retaining interactive behavior; master
is closed in child before exec. It launches the already-existing Rust eclair
with exact `-k @prefix@/smp-@ARCH@/kernel/mckernel.img -i -l`. No project Tcl,
shell, C implementations or expect executable are invoked. Existing eclair's
BFD adapters remain separate M15 debt owned elsewhere, not closed by this port.

Exact next root-owned fixture (all source-only here): copy fixture.rs and
eclair_backtrace.rs to a fresh owned directory. Compile only state-machine
fixture: rustc --edition=2021 --test --crate-name m15_eclair_fixture fixture.rs -o fixture
Run only the owned fake byte-stream tests; no native transport is imported.
Then copy eclair_native.rs, eclair_main.rs, and render config.rs.in -> config.rs
with @prefix@=/owned and @ARCH@=x86_64. Link only, no native program execution:
rustc --edition=2021 --crate-name eclair_dump_backtrace -C panic=abort eclair_main.rs -o eclair-dump-backtrace.exp
Root owns independent fixture execution, original-reference dialogue comparison,
link evidence, canonical/default selector integration and any separate later PTY
fake-executable run. CMake fragment preserves installed executable basename.
No root/host permission or native campaign release is conferred by this source.
Preserve scratch21/evidence/permanent27:4 and ownership/resource release controls.

Differences explicitly not claimed equivalent: Rust-native IO error wording,
checked u64 thread counter overflow versus Tcl arbitrary integer, bounded suffix
retention instead of expect's implicit matching buffer. No error rollback or
signal cleanup is added: child lifetime follows terminal close/process exit as
in the original expectation helper. Existing project helper remains canonical
until matching selection/build/functional proof; no source/file/native credit.
