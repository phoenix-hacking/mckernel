Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The source-only candidate is `coupled/bound-terminal-proc-v2-source-3/`.
`REVIEW-READY.json` binds its exact files, generator, source amendment, preimages,
patch, test commands, results and original preparation failures. Source1 and
source2 remain retained preliminary generations. Source3 has no root release,
physical clearance, native acceptance or application acceptance.

Acquisition now has one cumulative lifetime: at most eight entire sweeps inside
a five-second monotonic window, with bounded 10–50ms backoff and exactly two
completed sweeps required. Every listed PID must complete initial stat, command,
executable classification when applicable, and confirmation stat. Missing files
invalidate the entire sweep. The per-attempt ledger records all listed PIDs,
available identities, confirmed PIDs and the exact failure phase/path/PID and
available identity. Initial-stat disappearance records null identity; it never
fabricates or classifies an unknown process. Malformed data, permissions,
identity/parent conflicts, deadline, exhaustion and incomplete evidence refuse.
The same identity map and publisher list persist through both completed sweeps
and every unsuccessful sweep. An earlier publisher remains a refusal. The
consumer checks exact ledger/snapshot equality, all successful and failed sweep
relationships, cumulative identity consistency and original caller/boot/root
bindings. Original ownership closure uses every observed parent edge; owner,
waiter or discovered descendant PID appearing in any listed sweep refuses,
including an initial-stat disappearance of that already-known PID.

The report protocol is explicitly `fp-save-image.proc.v2`; old v1 evidence is
not relabelled. The producer prints one structured COMPLETE/REFUSED report.
The unchanged root-command wrapper requires a clean child stderr and caps its
stdout at the new 4MiB process-report bound. `process_absent` appends the report
before validation. At most eight reports are allowed, and a 4MiB reservation
plus 1024 bytes must fit below the 16MiB cumulative serialized budget before
starting another acquisition. Thus a cap refusal retains prior complete
reports without starting an acquisition whose report cannot fit. Preflight
includes reports in its existing result JSON and keeps successful stderr empty.
Cleanup includes them in terminal, validate-only and refusal JSON. Observer
stores the actual process artifact before validation. Postjoin includes them in
its existing success stderr JSON and emits a bounded structured report on a
census refusal, restoring the original AS limits in `finally`. Tar stdout and
all strict application stdout/stderr oracles are unchanged.

The exact generator applies the producer, validator, engine retention and all
coupled consumer amendments together before computing new pins. The existing
body checker recognizes only the explicit report-retention field added to the
validate-only return while retaining original Transaction/census/recovery
control-flow comparisons. No root/container/mutation gate was relaxed.

Verification completed under CPU7, 1GiB AS, 20 CPU seconds and 30 wall seconds:
14 tests execute the actual embedded producer, actual validator, actual
process_absent/census and actual Transaction.preflight_fresh refusal control
flow. They cover both complete sweeps, initial and late disappearance,
publisher/owner/descendant evidence surviving failed attempts, PID reuse across
retries and snapshots, exhaustion, deadline, malformed/permission failures,
schema/ledger omissions, aggregate-cap refusal before acquisition, mutation
remaining disabled, and actual postjoin census refusal retention/AS restoration.
The actual generated observer main, summary and finite postjoin consumer pass
one positive fixture; the publisher negative retains its v2 process artifact,
refuses success output and releases the fixture mutex. The generated body check
passes its genuine-shape check and 49 existing targeted refusals. The mocks are
explicit proc/time/root/filesystem/subprocess boundaries; no physical root,
Docker, guest or cleanup operation was run.

Two preparation failures are preserved. The first source-transform comparison
found the validate-only report-retention field missing from the generator
amendment; its one bounded correction passes. A later new checker-normalization
source string had a quoting SyntaxError; its one bounded correction passes.
No unchanged failing runtime candidate was replayed. The original closed root
preflight failure and its capture remain unchanged at the accepted predecessor
source directory.

Minimal publication/execution prerequisites: independently review source3 and
its exact patch, publish the whole coupled source set and generator/helper pins
through the dispatcher checkpoint/fetched-blob process, then bind a fresh
observer release to the new hashes and nonce
`m07-sigill-pass-image-observation-proc-acquisition-1`. Its source-only pending
operations are not releases. A fresh observer/readback is necessary because the
old observation authenticates v1 process artifacts and old source hashes. The
straightforward reviewed chain is fresh observer, summary, original-five
metadata and raw-five export, followed by a newly reviewed read-only preflight
and then separately released cleanup/postjoin. Old raw original-five bytes may
only be reused under a concrete independent decision authenticating unchanged
original FD descriptors/hashes and binding them explicitly to the new census
and release; this packet makes no such reuse or mutation decision. Root boot,
permanent 27:4 mutex, leases, exact target, original dirty inputs, Scratch21
exclusions and reserve576 pending approval remain unchanged.
