# Ultra application-test inventory and Spark implementation contracts

This is a source/evidence review and a proposed implementation inventory,
dated 2026-09-09. No new application, compiler, guest or validation run was
performed for this document. The accepted baseline is
[the Ultra handoff](native-application-ultra-handoff-20260909.md),
[readiness audit](native-application-readiness-20260909.json) and
[final checkpoint](native-application-final-checkpoint-20260909.json).
New tests below have **not run**. “Required” describes a future acceptance
contract, not an already demonstrated capability.

## What can be reused, and what it actually proves

| Existing input | Reuse and limits |
| --- | --- |
| `scripts/tests/fixtures/native-application-core.c` | Preserve unchanged as four golden regressions. Its build uses ordinary dynamic libc/pthreads, x86_64 `ET_EXEC`, `-fno-pie -no-pie`. Success is exact `NATIVE_CORE PASS CASE\n` and exit 37. This does not cover PIE, static libc or `dlopen`. |
| Memory core mode | 256 KiB malloc plus 256 KiB anonymous mmap, data checks, successful RO/RW `mprotect`, unmap/free. It never writes while RO, accesses `PROT_NONE`, or reads unmapped memory. Actual protection faults are a missing test. |
| Files core mode | 8,209-byte regular-file data, EOF, positional I/O, fsync, close/reopen, unlink and `ENOENT`. It does not cover directories, symlinks, fd sharing, partial I/O, truncation races, persistence across power loss or filesystem durability. |
| Threads core mode | Two pthreads, barrier, mutex, 2,000 increments, distinct TLS and join values on **one** McKernel CPU with `allow_oversubscribe`. This is concurrency and local futex evidence, not multicore parallelism or robust/PI/process-shared futex acceptance. |
| Signals core mode | Self-generated SIGUSR1 with block/pending/unblock and two alternate-stack handler entries. It does not establish Linux-to-McKernel external signal forwarding, a fatal application signal, interrupted blocking I/O, nested runtime handlers or AUTODISARM support. |
| `scripts/tests/fixtures/native-application-failure.c` and `native-application-failure-control.c` | Preserve the accepted blocked-read/SIGKILL test. The Linux supervisor kills the real Linux launcher group after finding its actual blocked worker syscall; this is owner-loss evidence, not a McKernel application `fork` test. The 700 forks occur in Linux. |
| `/work/run-native-application-signals.py` | Passing complete app/boot/route/retirement/pager/procfs runner. It is hard-coded to four cases and dated scratch inputs. It AST-extracts capture functions from another retained scratch helper, builds a boot probe and extracts logs with case-specific regexes. Reuse the established mechanisms with complete original/executed copies; do not generate another indefinite chain of string-replacement runners. |
| `/work/run-native-application-owner-failure-2.py` | Accepted explicit QMP-resume correction. Preserve this behavior: the inherited `capture(..., validate=False, resume=True)` path alone did not resume the first failed attempt. Test the controller's pause/resume state handling before new fault phases. |
| `/work/run-native-application-final-batch.py` | Reuse its five exact child-command records and original full control tests. i386 control ABI acceptance does not mean 32-bit applications run in McKernel. |
| `/work/build-native-application-core.py` | Captures compiler command/version, `-MD` dependencies, ELF, disassembly, runtime libraries and same-binary Linux references. Existing references run in the native **container**, whose syscall kernel is the computer's host kernel. Add a Linux reference inside the isolated pinned-kernel guest for new differential cases. |
| `scripts/tests/fixtures/native-application-*.rs` and paired `.c` | Existing exact-source adapter/protocol/layout/equivalence coverage is valuable when behavior changes. Unit fixtures and C reference models do not establish actual runtime side effects. Preserve their pinned-source selection and original assertions. |
| `host-kernel/native-rust/mcctrl_process.rs` | `Registration.trace_budget` starts at 64; one trace decision covers an entire delivery, with up to three lines (delivered, optional route, returned). This samples the first 64 delegated deliveries per registration. It is not an exhaustive syscall trace. |
| `kernel/rust/clone3.rs`, `kernel/rust/native_signal.rs` | Explicit project capability restrictions can supply negative-case contracts after individual argument validation is reviewed. Correctly rejected unsupported features must remain separate from supported Linux-equivalent behavior. |

The passing native module/image identities are protected:

```text
/work/native-application-signals-module-20260909-1
/work/mckernel-native-signals-images-20260909-2/native-rust/kernel/mckernel.img
/work/native-application-launcher-20260908-2/rust/executer/user/mcexec
/work/native-application-core-build-20260908-1/native-application-core
/work/native-application-failure-build-20260909-1
```

`/work` is `/home/holden/mckernel-work/scratch` on the host. Native behavior is
bound to source commit `3453edd571152132b19d23b26dad32f4204612e6`; the final
manifests bind 57 native and 37 guest compiler inputs. Resolve exact hashes
from those manifests rather than treating these directory names as identity.
Some old helper `scope` strings still say core/owner checks are pending. Those
strings are historical; current readiness comes from the final audit. A new
result schema must not infer readiness from free-text `scope`.

## Infrastructure prerequisites before accepting new application results

These are implementation tasks, not reasons to rerun the unchanged baseline
while the plan is being written. Spark can implement the bounded harness
work after Ultra has resolved any separate native-code review findings.

1. **Put the runner contract in the repository.** Proposed location:
   `scripts/application-tests/` containing `README.md`, `manifest.json`,
   `run.py`, `guest-supervisor.c`, `cases/`, `fixtures/` and `oracles/`.
   Keep immutable baseline helpers/evidence as references. Use Python's
   standard library and the already installed native C compiler; no new
   framework, Python package, download or third-party library is needed for
   the first stage. The runner accepts an explicit input manifest, case IDs,
   execution profile and a new output directory; `mkdir(exist_ok=False)`
   prevents overwriting prior attempts. Arbitrary executable shell fragments
   do not belong in case metadata; argv is an array.
2. **Establish a same-guest Linux reference.** The Linux supervisor first
   executes the exact payload directly under pinned guest Linux, resets that
   case's scratch tree and descriptors, then launches those identical payload
   bytes through the unchanged `mcexec -t 1 0`. Dynamic interpreter, DSO bytes,
   argv, environment, cwd, uid/gid, supplementary groups, umask, inherited fds,
   input bytes and applicable limits must match. Capture both environments.
   Require the reference and McKernel payload hashes to match. Linux must not
   use the host filesystem as an implicit oracle. Container references remain
   useful build checks, but carry `reference_kernel=container-host`, not the
   pinned guest Linux version.
3. **Build an independent result oracle.** Capture stdout and stderr as raw
   files, including embedded NUL bytes, and `waitpid`/`waitid` exit-versus-signal
   status. Do not rely only on a PASS substring, printk line, exit zero or a
   shell's `128+signal` convention. The supervisor's pipe pumps must drain both
   streams concurrently to prevent the harness from deadlocking a real app.
   Record output lengths and SHA-256, bounded exact bytes or a canonical
   parsed result, plus produced-file sizes/content hashes. Timestamps, PIDs
   and pointer addresses use explicitly declared relations/ranges; do not
   silently normalize arbitrary differences. Library return values and
   `errno` must be captured immediately; pthread APIs return error numbers
   directly and cannot be checked through unrelated `errno`.
4. **Keep provenance independent of the payload.** A new application PASS
   marker is insufficient. Bind actual schedule registration, OS generation,
   PID/TIDs, image/launcher/app identities, and at least one real delegated
   operation with matched worker/delivery/guest CPU and return. A Linux
   reference must never produce a matching McKernel schedule registration.
   For app children, prove each child remains in McKernel; a Linux `fork` in
   the supervisor is not a replacement. The current one-CPU profile requires
   guest CPU zero. Never delegate `clone3` to the Linux worker and count its
   child as a McKernel child.
5. **Define trace coverage before stress.** Short route tests can retain the
   original complete-match assertions for the observed delivery set. Once a
   registration reaches the 64-delivery cap, set
   `trace.coverage="first_64_deliveries"`; do not claim all runtime returns
   were audited. For a stronger long-run transport claim, first add reviewed,
   monotonic counters or a bounded structured event mechanism at the real
   accept/deliver/publish/retire transitions. It must expose loss/overflow and
   correlate owner generation, worker and delivery; prove its noninterference
   with the old fixtures. Merely increasing printk volume is not sufficient.
   Small functional workloads may proceed without this new instrumentation
   if their evidence honestly retains sampled-route scope.
6. **Observe cleanup and bound the observer.** Each finished case requires
   zero matching application/procfs registrations, successful retirement and
   process release, no unexpected quarantined/retained owner, and closure of
   every observed created pager handle. Require completion within 15 seconds
   after observed application exit. Capture actual state before/after groups
   for claims about growing owners, claims or registrations; absence of a
   `/proc` node alone cannot prove every kernel resource was reclaimed.
   Global pending-zeroing pages are not yet guaranteed fully drained, so
   do not invent an exact global free-memory-return assertion. Strong leak
   acceptance needs per-owner accounting or an explicit quiescence contract.
7. **Prove timeout and capture behavior.** Use the Linux supervisor's monotonic
   watchdog, independent of the McKernel application's clock, and an outer
   300-second QEMU deadline for ordinary guests / 600 seconds for full control
   guests. Every preparation subprocess also needs a finite timeout. A case
   timeout captures state before terminating the exact owned launcher/VM;
   no broad process-name kill. QMP stop/capture/continue is an explicit state
   machine; retain the emergency capture if continuation fails. A frozen
   guest clock must not disable the host-side deadline. The current 3-hour
   container maximum is an outer emergency limit, not an application timeout.
8. **Use precise negative-result classification.** Status is one of `PASS`,
   `FAIL`, `BLOCKED`, `NOT_RUN`; a required missing dependency is `BLOCKED`,
   never PASS. Exploratory unsupported-feature probes record observed
   semantics without promoting support. A reference mismatch or unexpected
   `ENOSYS` in a required supported case is FAIL. On the first validation
   failure stop the batch, immediately append exact command/environment/error
   to `kernel.log`, preserve the entire attempt and only then diagnose it.
   Every rerun gets a new attempt identity; no automatic retries that hide
   intermittent failures and no broad allowed-errno sets.

The existing guest init runs as root. Permission-denied tests are invalid as
ordinary-user conformance checks until a matched nonroot uid/gid profile and
access to required McKernel devices are verified. Start both engines under
the accepted root profile and omit `EACCES` claims. Do not put a small
`RLIMIT_AS` around `mcexec`: its large mapping needs and guest limit propagation
have not been established. Bound fixture allocations and thread stack sizes
explicitly first. Resource-limit propagation becomes its own later test.

### Proposed case/result schema

The following is a concrete contract example, with illustrative new paths.
It is not an executable file currently in the repository. Each case has its
own version; changing assertions changes that version, never an old record.

```json
{
  "schema_version": 1,
  "case_id": "file.errno.closed-fd",
  "case_version": 1,
  "tier": "required-short",
  "requires": ["dynamic-et-exec", "regular-file-io"],
  "payload": {"path": "/apps/file-contract", "sha256": "<build-bound>"},
  "argv": ["/apps/file-contract", "closed-fd"],
  "environment": {"LANG": "C", "LC_ALL": "C", "TZ": "UTC"},
  "cwd": "/case",
  "identity_profile": "baseline-root",
  "input_fixture": "empty-case-tree-v1",
  "timeout_seconds": 10,
  "output_limit_bytes": 65536,
  "limits": {"payload_allocation_bytes": 1048576, "threads": 1},
  "oracle": {
    "kind": "exact-record",
    "stdout_utf8": "FILE_CLOSED_FD read=-1 errno=9 write=-1 errno=9 close=-1 errno=9\n",
    "stderr_bytes": 0,
    "exit_code": 0
  },
  "reference": "same-binary-pinned-linux-guest",
  "provenance": "schedule-and-delegated-return",
  "cleanup": "normal-retirement-v1"
}
```

The result must include `case_id/version`, attempt ID, source HEAD, input
manifest digest, exact executable/interpreter/DSO identities, both engines'
actual kernel versions, exact argv/environment/profile, start/end/deadlines,
raw wait status, output/file artifacts, observed values versus expected
values, all comparison outcomes, schedule/owner identity, trace coverage,
cleanup results and evidence hashes. `status=PASS` is derived only after all
required assertions have individual results. The suite summary lists required
PASS counts, FAIL/BLOCKED/NOT_RUN IDs and exploratory results separately.
Missing evidence cannot default to zero or an empty passing collection.

## Stage 1: deterministic application contracts

First implement isolated cases rather than expanding the four original modes.
Each row below is a future test group; split it into separately named cases
at the points specified. Unless overridden: 10-second application deadline,
64 KiB output cap, at most 8 MiB live application allocation, one thread,
exact empty stderr and exit zero. Core regressions retain exit 37. Run each
case directly under pinned guest Linux, reset inputs, then through `mcexec`.
Fixed assertions must also hold independently of equality to Linux output.

| ID / order | Concrete operations and independently checkable result | Additional limits or prerequisites |
| --- | --- | --- |
| `base.core.*` | Replay the four unchanged core modes and HELLO as a harness compatibility gate. Retain exact bytes, exit 37, native schedule/return/retirement/pager and thread/signal assertions. | Existing 300-second guest budget. No weakening to fit the new schema. |
| `abi.startup` | Validate argc/argv with empty and whitespace-bearing arguments, fixed environment values, absent variable, cwd, umask 022 and page size 4,096. Record known auxv keys and interpreter/ELF identity without comparing randomized addresses. | Add a second ET_DYN/PIE build as `abi.startup.pie`, initially exploratory until accepted. Static libc and interpreter scripts are separate later cases. |
| `memory.zero-and-reuse` | For sizes 1, 4,095, 4,096, 4,097, 65,553 and 1,048,576 bytes, verify every byte of new anonymous mappings is zero, fill a deterministic pattern, unmap and repeat 16 times. Exercise malloc/calloc/realloc growth/shrink separately; only calloc and new anonymous mapping have a zero-byte oracle. | No more than 4 MiB live allocation; 20 seconds. Newly allocated malloc is not required to be zero; successful realloc may change address. |
| `memory.guard.readonly`, `.none`, `.unmapped` | Separate payloads perform an actual volatile access after RO mprotect, PROT_NONE, or unmap. Require SIGSEGV, `si_addr` equal to the tested address, and `SEGV_ACCERR` for protection / `SEGV_MAPERR` for unmapped access, where confirmed by the pinned Linux reference. | Use a one-shot `SA_SIGINFO` handler to report the real fault address/code through async-signal-safe write then `_exit`; no signal-longjmp or app fork prerequisite. Also add a separate default-disposition fatal case to verify actual signal termination. |
| `memory.file-private` | Map a two-page deterministic file privately, modify one page, unmap, reopen; the file must retain original bytes. Faulting beyond file EOF is a separate SIGBUS case. | Review existing pager/private mapping support; mapping success alone is insufficient. |
| `file.boundaries` | Read/write exact byte patterns of lengths 0, 1, 4,095, 4,096, 4,097, 8,209 and 65,553. Check return counts, EOF, size, current offset and reopened bytes. Positional I/O must leave the fd offset unchanged. | 20 seconds; file total under 1 MiB. For regular writes, handle short writes correctly and record them; do not assume pipe/socket write semantics. |
| `file.errno.*` | Independent cases: read/write/close on an already closed known fd → `-1/EBADF`; open a missing parent/path → `ENOENT`; `O_CREAT|O_EXCL` on existing regular file → `EEXIST`; negative absolute seek on a regular file → `EINVAL`; close/reopen and read EOF → zero. Capture errno immediately. | Derive exact Linux reference first. No permission-denied case under root. Use raw syscall only where testing raw ABI explicitly, not to bypass libc behavior unexpectedly. |
| `file.shared-offset` | `dup` an open file, read from both fds and prove shared open-file offset; `pread` remains independent. Closing one fd must leave the duplicate usable. | 20 seconds; no fork needed. |
| `file.namespace` | Create directory, create file, rename it, create/read symlink, enumerate exact entries excluding `.`/`..`, unlink entries, remove directory; reopen old name → `ENOENT`, `rmdir` nonempty directory → `ENOTEMPTY`. | Newly covered operations are exploratory until their first accepted reference/application comparison. Do not assume fsync verifies power-loss durability. |
| `thread.local-2-4-8` | For 2, then 4, then 8 pthreads: set explicit 256 KiB stack sizes, TLS starts zero, assign unique IDs, barrier then 1,000 protected increments each; exact totals 2,000 / 4,000 / 8,000, unchanged parent TLS, exact join values, destroy success. | 30 seconds; one McKernel CPU with oversubscription. Capture every actual child TID and removal. Accept 2 before starting 4, then 8. No speedup requirement. |
| `thread.condvar` | Producer/consumer over a 16-slot ring sends integers 0..9,999 in order, consumer receives each exactly once, sum 49,995,000; wait loops check predicates and tolerate spurious wakes. | 2 workers; 30 seconds; sequence and sum are both required. No sleeps used as correctness synchronization. |
| `futex.basic-negative` | On a naturally aligned mapped word: WAIT with unequal expected value → `EAGAIN`; wake with no waiter → zero; malformed alignment → `EINVAL`. Use one distinct case per error and record libc versus raw-syscall error conventions. | Review actual syscall command/flag validation and confirm pinned Linux reference. Existing mutex success does not establish the negative cases. |
| `futex.timed-wake` | Handshake-controlled waiter/waker; require exactly one successful wake and completion. Separately use a short bounded relative wait with no waker, expecting `ETIMEDOUT`. | 2 workers; 10-second outer deadline. Do not assert microsecond timing equality under TCG. Robust, PI and process-shared futexes remain separate. |
| `signal.nested-altstack` | SIGUSR1 handler triggers a distinct SIGUSR2 handler, both SA_ONSTACK; record three bounded stack observations (outer before, inner, outer after), in-range addresses, nesting order, old mask restoration and return to normal stack. Repeat 16 times. | No malloc, printf or pthread calls inside handlers. Existing exact-source nested model is supporting evidence, not this runtime test. |
| `signal.external` | Linux supervisor sends one SIGUSR1 only after the McKernel app announces ready; require exactly one real handler entry and application acknowledgement before termination. | Separate from killing mcexec with SIGKILL. First establish supported signal forwarding and handler targeting. Preserve sender/target and live syscall evidence. |
| `signal.interrupted-read` | Block a delegated read, deliver external handled signal without SA_RESTART; require interrupted return `-1/EINTR` and unchanged untouched buffer. Separate SA_RESTART case supplies known bytes only after the handler acknowledges and requires full expected read content. | 20 seconds; depends on accepted external signal forwarding and supervisor handshake. Never release pipe writer early, which would produce EOF instead of interruption. |
| `time.monotonic` | Read CLOCK_MONOTONIC 1,024 times and require nondecreasing values, valid nanoseconds; use a separate relative sleep case with 10 ms requested and only a loose elapsed lower bound, not an exact duration. | Record vDSO versus forced syscall path as separate subcases. 10-second outer Linux-supervisor watchdog. Realtime is not required monotonically increasing. |
| `numerical.integer-reduction` | Sum integers 0..999,999 with a scalar implementation and 2/4 partitioned pthread workers. Exact unsigned 64-bit sum is 499,999,500,000; partition coverage and per-thread subtotals independently checked. | 30 seconds, fixed 256 KiB thread stacks, no SIMD/parallel-speedup claim. |
| `numerical.integer-matrix` | 64×64 int32 inputs `A[i,k]=(i+3*k)%17-8`, `B[k,j]=(5*k+j)%19-9`; scalar int64 accumulation. Compare every cell against an independent Python integer oracle and then compare scalar and 2-thread partitioned output. | 30 seconds, under 1 MiB working data. This is a deterministic numerical workload, not BLAS/MPI performance evidence. |

`memory.guard.*` must not be compiled into undefined-behavior constant folding:
use runtime-selected mapped addresses and explicit volatile accesses; retain
the emitted access instruction in disassembly. A null dereference compiled
from an old fixture alone is a weaker protection test.

### Explicit unsupported-feature cases

Keep these outside the Linux-equivalence success count. They test the current
documented McKernel capability contract and absence of partial side effects:

* For `sigaltstack`, a valid otherwise ordinary stack with `SS_AUTODISARM`
  currently returns `-1/EINVAL` in `kernel/rust/native_signal.rs`; the old
  configuration remains installed. Linux can support this flag, so comparing
  the two engines as if success were required would be the wrong oracle.
* In `kernel/rust/clone3.rs`, otherwise valid requests for a deliberately
  unsupported flag such as `CLONE_IO` produce `-EOPNOTSUPP` after argument
  validation. Require no new McKernel thread/process or Linux worker child.
  Malformed combinations may correctly fail earlier with `EINVAL`; use one
  reviewed exact argument vector, not “any unsupported flags → 95”.
* Size below 64 in clone3 is `EINVAL`; size above 4,096 is `E2BIG`, and nonzero
  unknown trailing bytes are `E2BIG` in the current decoder. Invalid pointers
  have ordering constraints. Reuse the exact vectors in
  `scripts/tests/fixtures/native-application-clone3.c` / `.rs` and their
  recorded Linux oracle; do not synthesize tests by calling the Rust decoder
  itself as both actual and expected result.

These are new runtime acceptance tests even though exact-source unit evidence
already exists. They cannot be marked passing from the source inspection.

## Stage 2: unchanged representative applications already close to hand

The retained Linux initramfs contains an actual
`/usr/bin/coreutils` multicall ELF, `/bin/bash`, and runtime DSOs including
`libc`, `libcrypto`, `libz`, `liblzma` and `libzstd`. Its `/bin/stat` and
`/bin/uname` are **shebang scripts**, not standalone native ELFs. The native
Dockerfile at `/home/holden/mckernel-work/setup/docker/Dockerfile.native`
installs `gzip`, `xz`, `zstd`, `gcc`, `gcc-c++`, Python and binutils. This is
installation-recipe evidence; first inventory exact versions/ELF types,
options and complete DSO closure from the pinned container image and bind
their bytes. Library presence does not prove the corresponding application
or development headers are available. No installation is needed for the
first coreutils stage.

Invoke the actual multicall ELF through mcexec, using the applet-selection
option after confirming it with the pinned binary's Linux inventory:

```text
/bin/mcexec -t 1 0 /usr/bin/coreutils --coreutils-prog=cat /case/input
```

Launching `bash -c 'cat ...'` now would combine shell startup, fork/exec,
redirection and cat coverage before each is established. The Linux supervisor
should arrange stdin/stdout/cwd and launch each ELF directly. Tests of the
shell's process behavior belong to Stage 3.

| Required order | Exact workload / oracle | Bound and status |
| --- | --- | --- |
| `app.coreutils.cat` | 1,048,576 deterministic bytes `((i*29)^(i>>8)) & 255`; stdout exactly equals the input, stderr empty, exit zero. Also test empty file and stdin modes as distinct cases. | 15 seconds, 2 MiB output cap. New app, not yet executed in McKernel. |
| `app.coreutils.wc` | `wc -c` from the same stdin: exactly `1048576\n`; `wc -l` on a separate 4,096-line fixed text: exactly `4096\n`. Verify pinned binary formatting during reference capture, without silently changing expected formatting afterward. | 15 seconds, 64 KiB output cap. No locale-dependent word classification initially. |
| `app.coreutils.sha256sum` | Hash the exact 1 MiB input; expected digest is independently computed by Python `hashlib` during input generation, and complete output has fixed `/case/input` name. Require identical reference/application digest, filename, newline and exit. | 20 seconds. Bind CPU-feature configuration and any crypto DSOs; this adds real user-space crypto computation coverage. |
| `app.coreutils.cp` | Plain copy of 1 MiB input to a new file; compare full bytes/size by independent supervisor oracle. No initial `-a`, reflink, sparse-file or ownership claims. | 20 seconds, under 4 MiB case files. Trace optional copy_file_range/reflink fallback as observed, not assumed. |
| `app.coreutils.sort` | 4,096 ASCII lines of descending zero-padded integer keys; `LC_ALL=C sort -n` yields exact ascending expected lines, no loss/duplication. | 20 seconds, 2 MiB output cap. Do not test parallel sort or external spill yet. |
| `app.gzip.roundtrip` | Pinned unchanged gzip `-n -c /case/input` on 1 MiB deterministic data; compare compressed bytes with same-binary guest Linux output. Decompress captured output independently with Python zlib/gzip and require the exact original data. Add a separate gzip `-d -c` execution under McKernel. | 30 seconds each, 4 MiB output cap. Copy exact pinned executable and transitive DSOs first; do not assume presence in initramfs. |
| `app.xz.roundtrip` | Pinned xz with explicit single-thread mode, low preset `-0`, fixed format and memory limit no greater than 32 MiB after option/reference inventory. Roundtrip and compressed-byte oracle as above, using independent Python `lzma` where available. | 30 seconds each. Defer if pinned options/decoder dependency are absent; record BLOCKED, not skipped PASS. |
| `app.zstd.roundtrip` | Pinned zstd low-level compression with an explicitly confirmed single-thread option, same-byte Linux comparison plus independent output validation with a separately identified decoder. | 30 seconds each. Python stdlib zstd support is not assumed in Python 3.12; gzip/xz are enough for the first compression milestone. |

A corrupted-stream test should follow successful roundtrips: truncate or alter
a specifically selected compressed stream, require the pinned utility's
documented nonzero exit and no falsely accepted full plaintext. Capture exact
reference stderr/version before fixing that case's expected output; do not
allow an arbitrary nonzero code to count as success. Application stderr from
`mcexec` and payload stderr must be separately attributable when possible.

## Stage 3: process families and broader APIs, explicitly unverified

Only start each group after its prerequisites pass. Initial per-case bounds
are 30 seconds, 8 MiB working memory and at most two live application child
processes / eight threads. A child-process test must retain per-child McKernel
provenance and cleanup. Linux has handled syscalls in the existing source
tables for fork/vfork/execve/wait4; presence in a table is not runtime evidence.

| Group | Required contract before a larger application depends on it |
| --- | --- |
| `process.fork-wait-cow` | Parent and child each write a distinct byte in formerly shared private memory; parent retains its own value, child exits 23, parent receives that child PID/status once, second wait yields `ECHILD`. Use an in-McKernel child, not a Linux supervisor fork. |
| `process.exec` | Child executes a second bound ELF with fixed argv/environment, inherited open fd and one CLOEXEC fd; exact surviving-fd behavior and exit 23. Failed exec of missing path yields `ENOENT` while old process remains runnable. ET_EXEC first, PIE second. |
| `process.pipe` | Guest application parent/child transfer 65,553 deterministic bytes using retry loops, close all writers and observe EOF. Broken-pipe case separates default SIGPIPE from ignored-SIGPIPE `EPIPE`. No Linux-created pipe can replace the in-app pipe construction test. |
| `process.wait-signal` | In-app child exits through default SIGTERM/SIGSEGV; parent checks `WIFSIGNALED` and exact signal. Add WNOHANG before child completion and proper reap after it. |
| `app.bash` | Unchanged shell performs arithmetic/expansion first, then a two-stage known pipeline only after process/pipe/exec gates pass. Exact output/status and every child location are required; shell success cannot mask child exit failure. |
| `loader.dlopen-cxx` | Shared object constructor/destructor and resolved function return, then a small C++ vector/string/RAII/exception workload. Capture linker/interpreter/libstdc++/libgcc_s/libm closure; do not label these accepted from C libc smoke. |
| `ipc.poll-eventfd-socketpair` | Deterministic readiness and byte-transfer tests, closed-fd/error semantics, no internet/network interface. Each API is exploratory until accepted. Network service applications require a later explicit socket/network plan. |
| `limits.exhaustion` | Begin with controlled small fd/allocator/thread capacities and actual state accounting. Prove exact exhaustion error, rollback and subsequent successful operation. Full 64-worker/64-mailbox saturation, permanent transport stall/quarantine, OS shutdown and resource restoration require a separate reviewed fault-injection design. |

Multicore McKernel, NUMA placement, MPI, XPMEM, UTI, GPU/device libraries,
performance claims and full LTP are later campaigns. Do not expand from one
McKernel CPU / 128 MiB merely because Linux has four vCPUs / 8 GiB. No MPI or
LTP/OSTEST install was established by this review.

## Historical test sources: reuse carefully

| Path | Concrete finding and disposition |
| --- | --- |
| `test/common.sh` | Defaults to `mcstop` and `mcreboot` and searches a user config / installed external LTP or OSTEST. Never source it on the development host for this plan. A guest-specific runner replaces orchestration while preserving any reused test body and declared expectations. |
| `test/user_space/README`, `go_syscall_test.sh`, `go_swapout_test.sh`, `patch_and_build.sh` | Historical “auto” workflow resets sources and applies diagnostic kernel patches. It is not a reusable current-baseline launcher. Retain source tests and specific expected cases only after review; do not run these wrappers. |
| `test/user_space/futex/futex_test.sh` | Reboots McKernel, kills process-name matches, depends on external LTP and diagnostic printk text. Use its case inventory as a later source of ideas; no current compatibility or passing claim. |
| `test/portability/futex_wake_op.c` | A real pthread/raw-futex test source exists, but it uses sleep for ordering, lacks robust return assertions and can wait without a bound. Its printed `[OK]` alone is insufficient; write a bounded adapted fixture with original source retained and an independent Linux result. |
| `test/issues/1422/filemap_sigbus.c` | Useful model for file-backed access beyond EOF, but invalid argc returns zero and it lacks a self-contained signal oracle. Reuse the access scenario with an external/handler signal contract and exact file setup. |
| `test/issues/1340/segv.c`, `raise_sig.c` | Useful historical fatal-signal seeds; inspect emitted access / validate argv and actual signal status. A raw null pointer C dereference is subject to compiler UB transformations. |
| `test/issues/1065/file_map.c` | Maps a file and calls `system("cat /proc/PID/maps")`; no byte-coherence oracle. It combines unverified process execution with mapping and is not a substitute for the proposed private/shared file-map cases. |
| `test/issues/1323/rwlock.c` | Depends on private test syscall 750; it is not an ordinary pthread rwlock application. Do not select it as representative userspace coverage. |
| `test/issues/1410+1420/C1410T01.c` | Contains unbounded busy-loop/fork/migration behavior. Its original orchestration and multicore assumptions do not fit the current short single-CPU stage. |
| `test/large_page`, `test/uti`, `test/xpmem`, `test/qlmpi`, architecture-specific `arm64` paths | Real historical investments to preserve. These require separate feature/configuration/dependency audits; they are not implied by the x86_64 baseline or suitable for bulk launch now. |

The repository's Python/configuration/equivalence suites remain regression
tools; their counts are separate from application executions and features
accepted. An existing binary checked into a historical test directory is not
a trusted current compiler-bound fixture until rebuilt and identified inside
the isolated toolchain.

## Repeatability and milestone definitions

After each newly supported **short** case first passes, run it three times in
one OS instance and once in a fresh guest using identical module/image/app
bytes. After all Stage 1/initial coreutils cases pass, run ten sequential
cycles of that accepted subset in one OS, then the same subset in a fresh
guest. Split into bounded guest batches before the 300-second deadline; the
batch definition is fixed before execution. Keep exact counts and IDs; do not
silently omit slower cases. Longer 1-hour stress is a separate stage with its
own observed resource-accounting and trace-coverage contract, not an inflated
QEMU timeout on a stalled short test.

The first useful milestone is **unchanged core regressions + Stage 1 short
contracts + cat/wc/hash/copy/sort + gzip roundtrip**, all under the same input
pair, with independently verified bytes and no unexpected owner retention.
This would justify broader process/application work; it would not establish
production readiness, multicore/MPI, shutdown correctness or full Rust/assembly
completion. Spark should implement and execute one coherent group at a time,
returning discovered native correctness problems for the separately reviewed
fix workflow instead of changing expected outcomes or silently inserting
compatibility fallbacks into applications.

This inventory is review background, **not Spark's unrestricted assignment**.
The root Ultra plan must issue small fixed work packets with an exact input
file list, writable file allowlist, selected case IDs, frozen expected results,
resource budget, permitted commands and a completion checklist. Give Spark
only the relevant packet and directly required helpers/sources, rather than
the entire historical AGENTS log or this full inventory. A packet
must say whether it only drafts fixtures or also runs them. Spark must stop
the affected batch and preserve/escalate unexpected kernel bugs, dependency
gaps, semantic ambiguity, timeout, unexpected errno or assertion failures;
it cannot broaden scope, weaken an oracle, reinterpret unsupported behavior
as PASS or self-authorize the next stage. The later user instruction permits
bounded test/harness repairs and isolated candidate product patches within
the root plan's explicit time, attempt and changed-file limits. Spark retains
the original failure plus the candidate patch and its results for Max review;
it cannot promote an unreviewed candidate kernel change into the accepted
baseline. After classification, independent cases may continue in fresh
guests; damaged guests and dependent cases remain stopped. The final root
Spark contract supersedes any earlier blanket no-fixes wording. Spark readiness
is explicitly announced by the root only after its prerequisite review and
blocking repairs are complete.

Retain the exact suite manifest, compiler dependencies, executable/runtime
closure, case inputs, both Linux/McKernel outputs, full serial/debugcon/QEMU
command, structured results, physical queue/memory/register captures, timeout
and failure captures, and final source/build bindings. Preserve all failures.
Use the existing validated archive/hash/fetched-Git-blob checkpoint process
after coherent work and about every 30 minutes of sustained work. Disk cleanup
only follows verified retention and current-dependency checks; no current
module, image, compiler, failed attempt or source input is expendable.
