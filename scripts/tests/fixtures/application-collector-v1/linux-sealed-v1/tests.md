# Pinned Linux collector infrastructure checks

These are new ordinary Linux infrastructure fixtures. No compilation, execution,
catalog acceptance or native provenance is claimed by these source files. Root
owns the exact compiler/dependency/binary capture, isolated container identity,
four-CPU/12-GiB limit and independent whole-run deadline. Never execute the
stimulus directly: its interruption mode signals its actual collector parent.

Compile the unchanged parent `request.c`, new `sha256.c` and `collector.c` as
separate objects and link them into `linux-collector`. Compile/link `fixture.c`
and `sha256_harness.c` separately; the SHA harness links the actual SHA object.
Use the existing pinned C11 / `_GNU_SOURCE` / `-Wall -Wextra -Werror` profile,
retaining complete commands, logs, compiler dependencies, objects, final ELFs,
loader traces and disassembly. No linker wrappers, decoder/SHA mocks or altered
expected values are permitted. Ordinary builder compilation is sufficient.

Run the actual SHA harness first with ten seconds plus fifteen seconds of owned
cleanup. Its exact stdout is the nine lines below and stderr is empty; actual
raw wait must be zero. All original failed outputs must be retained.

```
PASS empty
PASS abc
PASS multi-56
PASS boundary-55
PASS boundary-56
PASS boundary-63
PASS boundary-64
PASS boundary-65
PASS rejected-update-preserves-state
```

The first three digests are literal standard known answers. The five boundary
vectors are the byte sequences `bytes(range(n))`, for n=55,56,63,64,65, with
independently calculated Python `hashlib` digests retained in the author source
capture. The actual C SHA object processes them in thirteen-byte chunks. The
harness also checks finalization leaves the original state intact and rejected
NULL/nonzero/bit-count-overflow updates leave every state byte unchanged. This
does not claim robustness for arbitrary corrupted SHA state structs.

`run_collector_tests.py` has two explicit, mutually exclusive profiles:

```
python3 run_collector_tests.py --collector /absolute/linux-collector \
  --fixture /absolute/fixture --supervisor /absolute/supervisor.py \
  --attempt-root /absolute/fresh-attempt --builder-only

python3 run_collector_tests.py --collector /absolute/linux-collector \
  --fixture /absolute/fixture --supervisor /absolute/supervisor.py \
  --attempt-root /absolute/fresh-attempt --root-infrastructure
```

The builder run requires actual nonroot uid/euid and checks one independently
well-formed request is BLOCKED before child creation because profile1 requires
root. The positive profile requires actual root in the separately isolated
pinned container. It does not drop credentials, use sudo or select a container.
The driver is not a mechanism for gaining root. The caller must also capture
that actual container/user configuration rather than accepting the CLI label.

The root profile runs exactly 25 cases in the fixed `CASES` order, stopping at
the first failure. Each call has an independent outer supervisor allowance of
40 seconds plus 15 seconds cleanup; keep an additional 300-second whole-driver
watchdog. A slow preparation can therefore fail the stronger outer bound even
though the collector's own preparation ceiling is 120 seconds. A fresh attempt
retains every invocation/request/manifest, expected stream, actual stream/raw
wait, source/sealed bytes, setup/events/report, assertion result and traceback.
There is no temporary-directory auto-removal. Full root attempts remain the
parent's archival responsibility.

| Cases | Independent expectation |
| --- | --- |
| literal | argv0 `literal-app`, then `literal`, empty, `A=B`; exactly three literal environment entries; exact cwd; six binary stdin bytes and EOF; actual memfd/descriptor exec semantics; stdout `LITERAL_OK\n`, stderr `LITERAL_ERR\n`, normal exit37 |
| empty-env, stdin-devnull | Complete empty environment / actual stdin EOF; exact single line; normal exit0 |
| pressure | Two real related processes write separate stdout/stderr concurrently; parent joins child; exactly 65536 `O` and 65536 `E`; normal exit0 |
| signal-term, exit143 | Actual WIFSIGNALED(SIGTERM) and actual WIFEXITED(143) respectively; never equate them |
| stdout-over, stderr-over | Observe65537, retain65536, explicit truncation/OUTPUT_LIMIT; actual child raw wait retained without inventing one exit outcome |
| pipe-holder, escaped-holder | Parent exits0 with one real live child inheriting pipes; ORPHANED_DESCENDANTS; exact actual adopted PID/startticks, SIGKILL raw reap and complete EOF/ECHILD; escaped child has its own session |
| timeout | Actual ten-second deadline, SIGKILL cleanup, TIMED_OUT |
| interrupt-collector | Subject signals its actual collector parent then waits; interruption remains first failure, actual SIGKILL cleanup |
| replace-source | Subject changes only its temporary requested source pathname after sealing; retained original executable bytes and actual continued sealed-image execution; normal exit0 |
| three bad hashes | Independent executable/stdin/manifest digest mismatch; no child |
| role-two, unknown-mode, malformed-request | Explicit rejection; no child |
| request-fifo, executable-symlink, stdin-fifo, missing-executable | Bounded type/path failures with no child; no producer or symlink-target fallback |
| script-executable | Unsupported executable format BLOCKED before child |
| existing-attempt | Outer exit125 and exact error bytes; original directory contents unchanged |

The driver constructs the request from literal public wire offsets and compares
actual artifact sizes/SHA256 independently with Python hashlib. It never imports
the subject decoder/collector. The reused outer supervisor is imported only when
the parent actually runs the tests; its exact file identity is retained/rechecked.
An inner collection status does not substitute for the outer actual raw exit,
complete outer streams and successful owned cleanup. Root must inspect those
outer results for the driver itself too.
The collector begins in the case parent directory, distinct from the requested
child cwd, and receives a harmless parent-only environment sentinel. The subject
must actually change cwd and replace its environment; an already matching
inherited setup cannot satisfy these fixture assertions.

These cases are an initial bounded batch, not complete collector qualification.
Further adversarial checks remain: stopped collector/external rescue, interruption
at completed-wait and report-fsync boundaries, missing/partial setup records,
read/write/fsync failures with retained prefixes, exact deadline observations,
file capability and seal-unavailability blocks, additional file/cwd component
mutations, hostile unowned pipe holders, owned-record overflow and source-bound
loader closure. Pathname-sensitive application predicates, real native payload
observations and application backend release remain separate unsatisfied gates.
