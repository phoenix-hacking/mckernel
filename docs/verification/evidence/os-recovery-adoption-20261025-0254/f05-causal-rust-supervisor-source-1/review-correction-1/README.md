# Additive source review correction1

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This private successor fixes the four finite review findings described in
`REVIEW-CORRECTION.json`. The original12 files and READY1867 remain byte-exact.
The planned public interface f38f remains byte-exact; actual artifacts and
qualifications remain null. `REVIEW-CORRECTION.patch` is the exact source diff.
All36 controls are prepared and unrun. No compiler, executable, actual signal,
guest, guard or canonical operation ran.

# Private F05 Rust causal supervisor successor

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is one fixed F05 PID1 collector successor. It translates the selected
`ND_PROCESS_EXEC_WAIT` path of retained collector source `b3fc4f` into Rust,
including its existing supervisor, helper, frame and teardown operations. It
adds the agreed causal observer inside those loops. The retained C source and
`c020a8` executable stay unchanged. It has no configuration framework, wrapper
launcher, second observer process or kernel callback/refcount change.

`PREDECESSORS.json` records the exact proposal/addendum/Root protocol,
diagnosis, failed serial/result, frozen manifest, original evaluator and
owner139+4 source-pin provenance. The frozen image `60e62f`, old app `bfdda7`,
working C launcher `dca025`, collector and three modules were read and rehashed.
These joins preserve history; they do not renew runtime admission or establish
the still-required selected launcher source/object/config join. The canonical
default Rust executor is not used as proof for the retained launcher.

`main.rs` retains the120s collector bound, original module/native-boot sequence,
10s real `/bin/mcexec` child, exact argv/cwd/two environment entries, raw wait
status/timestamps,1024B streams, TERM/KILL/reap reserve,5s absolute post-reap
retirement window, single4096B `ND_PAYLOAD` publication, printk restoration and
poweroff-return failure. The outer native operation's existing300s limit is
owned by Root and unchanged. No helper/module/guest command was executed here.

`supervisor.rs` creates an exclusive empty mode0600 regular gate at
`/case/work/.f05-gate-31770ebb739fea402ded939617921dda` before actual launch.
`lifecycle.rs` requires the actual spawned launcher PID as the one SCHEDULE
parent, its positive clone56 RET-linked child, genuine publication, child
write1 RET0, child terminal231, parent wait61 RET naming the child, actual child
DELETE, real cleanup ACK and fresh bounded retirement tokens ending0. Interim
-11 remains pending. Only then does the observer write one ASCII `G` at offset0
and record that actual write. It rechecks pathname/descriptor identity and
initial emptiness. Duplicate tokens, unknown causal-row kinds, malformed rows,
wrong OS/generation/PID, unexpected errors, excess original12 attempts or a
parent terminal before the gate fail. The parent must then reach actual DELETE
and final retirement0, and procfs must be readable and empty, inside the same
original post-reap deadline. Namespace absence cannot release the gate.

The independently owned foreground Rust app uses the relative gate basename
under the original cwd, explicit DETACH while the child is stopped after all
memory checks, successful wait/reap and bounded genuine syscall entries while
the gate is empty. Missing/empty/EOF pending and bad bytes/errors/deadline are
the app owner's interface obligations. No extra environment entry is added.
Case identity is `M14-05-05-owned-processvm-v3-causal-204B`; no v3 app hash,
native nonce consumption, or future artifact identity is fabricated here.

The observer opens non-destructive `/dev/kmsg` and seeks to the prelaunch end.
It saves complete genuine records, with their native sequence/time metadata,
to a separate exclusive `lifecycle.kmsg` file. It fails on read errors/EPIPE,
gaps, duplicate/reversed sequences/times, continued/unrecognized headers or
262144B overflow. It catches up to EAGAIN before releasing the gate. Every
observed nonempty message and its multiplicity must still be present in the
single final raw `klogctl(3)` snapshot. The actual native snapshot bytes are
saved and written to console unchanged, followed by the original report.
Incremental records are never reconstructed into serial, appended, filtered,
reordered, normalized or deduplicated. Final full evaluator unknown-row and
235/227 contracts remain mandatory. The coverage check can reject formatting
differences; actual Linux raw-format qualification is still open.

The only executed source check is `rustfmt --edition 2021 main.rs` (which walks
its modules). Its first attempt exposed the installed formatter's unsupported
C-string literal; replacing that literal with a static NUL-terminated byte
string fixed parsing. No Rust compile/link or test executable ran. The20 pure
mocked Rust tests,10 mocked observer transport/file tests and6 ordinary HOST
tests are prepared but unrun. See
`HOST-QUALIFICATION.json` for a single proportional proposal for Root.

The selected host consumer `8bf30cd8` samples64 ordinary delivered calls per
HostProcess and always traces terminal231. That mechanism is separate from the
LWK128-entry debug logs. The observer requires positive clone56 RET, child
write1 RET0 and parent wait61 RET before the gate. During gate polling it needs
independent real lifecycle rows and the always-traced parent terminal, without
requiring every gate syscall to remain sampled. Foreground deadline clocks may
use local native_vdso time or delegated clock_gettime fallback; actual pre-gate
required row visibility remains a qualification predicate, never inferred.

Unsafe code is confined to the existing Linux process/descriptor/clock/signal
operations and documented x86_64 libc layouts. The candidate deliberately
rejects other targets. ABI/link/host lifecycle qualification, independent
ownership/ABI review, foreground source/oracle cross-binding, actual artifact
and runtime adoption, fresh source/account/native ownership admission and an
independent Root execution release remain required. No source-only record
grants compiler/staging/guest/cleanup authority or port retirement credit.

Only this private directory is owned by this lane. Root owns canonical
integration and all execution. Fixed stop2026-10-28T05:36:09Z, original credit
run/ceiling and observed debits, real holds, permanent27:4/scratch21 exclusions,
one-heavy4CPU/12GiB/512tasks/no network,7 aggregate jobs and HOST16GiB/scratch12GiB
free floors remain unchanged.
