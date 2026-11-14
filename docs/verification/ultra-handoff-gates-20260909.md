# Ultra handoff gates and remaining technical work

The requested next phase is bounded fixture/oracle drafting by Codex Spark
(or Luna if the user chooses). It is not blanket authorization to execute all
catalog cases on an unverified feature. Root will explicitly announce readiness
after the current-source build/regression gates below pass and the reviewed
initial context is saved to verified GitHub. Until then the handoff is pending.

## Required before the drafting handoff

- Preserve the exact original Max baseline and every new failed attempt.
- Complete native module build and all four image profiles with source/compiler
  bindings, actual selected-call/ELF checks and unchanged original controls.
- Pass the focused signal, XSAVE, fault-dispatch and futex/clone checks on their
  final sources. A source change invalidates the affected previous binding.
- Replay memory/files/threads/signals and both original control ABI regressions
  on one exact new module/image pair. Run the new independent ordinary signal
  and futex fixtures; retain a precise reason for each unavailable feature.
- Validate the catalog and small context packets, including the requested
  machine-aware vector coverage. Supply only the active packet's cases.
- Save the implementation, all results/failures, restricted starting context
  and explicit residual goals, push GitHub and compare fetched exact blobs.

The existing plan's runner, accounting and runtime transport-injection gates
apply before execution-enabled packets are released. They do not require the
faster model to finish a runner before it can draft that runner's tests or
ordinary application fixtures. No gate is silently converted into a PASS.
A draft-only handoff must say so plainly and retain execution_enabled=false.

## Concrete remaining capability goals

| Area | Required technical result | Evidence that closes the goal |
| --- | --- | --- |
| Host committed return failures | Distinguish send failure before publication from notify failure after publication; bound queued completion; retain/quarantine every owner that cannot safely be released. | Existing44 exact-method tests plus real staged injected-failure guests and complete owner/response observers. Injected EAGAIN is not physical ring saturation. |
| Native return integrity | Validate complete copied frame before state commit; preserve trusted flag bits; canonical user handler/restorer/RIP/RSP; no private recursive restart dispatch. | Exact ABI/policy tests, selected image code and ordinary real signal return/FP tests. Pure dispatcher vectors do not establish actual #GP/#PF delivery. |
| FP/SIMD state | Actual CPU MXCSR mask and selected xfeatures govern complete aligned private-copy restore; checked instruction failures remain process-local. | XSAVE buffer tests, actual bridge selection and guest register/state cases. Kernel no-SIMD assertions remain. |
| Futex timeout arithmetic | Checked single timespec copy, signed normalization, saturating deadline/tick arithmetic without absent freestanding compiler helpers, charge scheduler yields/retries. |240 pinned-Linux time vectors per compiler plus boundary conversion vectors and actual runnable-peer timeout tests. Realtime clock-step tracking remains separate. |
| Futex user word | Authorize complete aligned user span, prefault outside hash locks, exact nonblocking reread with contained failure under lock. | Source/ELF/instruction binding and actual guarded-pointer tests. Race with unmap needs a separate deterministic observer. WAKE_OP/PI/UTI remain closed. |
| Clone TID stores | Use complete target-VM writable copy/COW path; preserve Linux failure semantics; no raw child address write. | Exact producer/copy tests, selected do_fork route, actual pthread creation/join and the focused valid shared-VM CHILD_SETTID/CLEARTID fixture. Invalid child stores and fork/COW still need separate runtime evidence. Linux controller forks are not McKernel fork/COW verification. |
| External signal forwarding | Implement both SIG_THREAD and SEND_SIGNAL ioctl ownership/validation, correct guest PID/TID/generation delivery, ACK/error propagation, duplicate/death races and cleanup. | Block a real delegated read, deliver SIGUSR1 to its actual application, observe handler ACK before input, exact restarted return/FP state; repeat after target death. Current native handlers return EINVAL for these ioctls. |
| Extended signal xstate ABI | Supply/reconcile Linux software magic, feature bitmap, size/trailer and UC_FP_XSTATE semantics for each enabled extension, preserving ordinary legacy region. | CPUID0xD geometry and actual handler context inspection/restoration at each feature level. Raw XSAVE restore alone does not prove Linux extended-frame compatibility. |
| Robust futexes | Replace or explicitly reject the current successful head-discarding registration; own head lifetime, pending operation, list limits, owner-death marking and wakeups. | Real pthread robust mutex EOWNERDEAD/consistent/ENOTRECOVERABLE sequences and bounded owner-exit races. Current registration success is not capability proof. |
| Guest fork/exec | Implement non-null CREATE_PPD/adoption, stable process/MM ownership, COW, parent/child rollback, wait/exec and delegated routing. | Every application child has McKernel SCHEDULE/procfs/TID provenance and independent results/cleanup. Current host adoption rejects the fork path. |
| VM invalidation failures | Retain guest range/backing ownership until host invalidation outcome is safely resolved; propagate failed clear_host_pte/invalidation and forbid unsafe reuse. | Deterministic failure placement before/after invalidation, exact stale-mapping/owner/counter observations and fresh-guest retirement/quarantine outcomes. |
| Runner and oracles | Exact argv/environment/fds/identity and same-binary pinned-Linux guest reference; drain both streams, raw wait status, independent fixed oracles, timeout/cleanup and retained artifacts. | Deliberate supervisor failures, pipe pressure, malformed result/status and watchdog/QMP pause-resume tests; manifest hash/stale-source rejection. Container host Linux is not the reference guest. |
| Feature-gated vectors | Probe each execution engine's CPUID1/7/0xD, OSXSAVE and XCR0; require emitted target instructions and independent arithmetic/state oracles. | SSE/XMM, AVX/AVX2/YMM and available extension cases; AVX-512/opmask/ZMM only when its specific CPUID and XCR0 requirements pass. Host flags alone never enable guest instructions. |
| Accounting and campaigns | Expose exact per-owner allocations/claims/pagers/publications/quarantine and trace loss; freeze small campaign membership and resource limits. | Quiet-baseline comparisons, fresh failure guests, bounded repeated runs and explicit observed coverage. No-PID/procfs nodes alone is not all-resource leak proof. |

The physical host CPU feature record is
`ultra-host-cpu-features-20260909.json`. It is read-only metadata, not an
instruction test. The current TCG guest profile and any later KVM profile need
separate feature/state observations. Never expand host resources or issue a
model switch to satisfy an unsupported instruction case.

## Executor failure and repair discipline

Preserve the first unexpected failure with exact command, environment, original
and executed sources and full evidence. Stop that batch, then use a fresh guest
for an independent case after classification. A production candidate fix may be
attempted only under an execution-enabled packet's reviewed scope: one attempt,15minutes,two files,
80changed lines. Preserve its before/after evidence and send it to Max; do not
accept changed kernel code automatically. ABI, unsafe memory, scheduler,
transport/lifetime and unclear semantic changes require Max's narrow review.
Missing/unsupported/blocked capability never becomes PASS by skipping a check.
