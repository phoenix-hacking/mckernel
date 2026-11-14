# Owner phase metadata harness

`phase_metadata_harness.c` includes the actual frozen `phase_client.h`
validator and supplies independent literal 256-byte little-endian request and
response fixtures. It executes no ioctl, process creation, application payload,
guest, fake clock or owner observer. Compilation and tests are NOT_RUN in the
author's lane; root owns pinned compilation and execution.

The harness takes no arguments. Root should require actual raw exit zero and
the complete stdout JSON with `status: PASS`, `failures: 0`, scope
`synthetic-owner-phase-metadata-only`, `actual_ioctl_executed: false`, and both
acceptance flags false. Compile using the same pinned C11, `_GNU_SOURCE`,
`-Wall -Wextra -Werror` profile as the controller, retaining full header inputs,
diagnostics, object/ELF and invocation. A small independent process deadline
and the ordinary pinned resource limits still apply. Stop and retain the
complete first failure before changing anything.

The independent fixtures cover nonce word order and decimal bounds; initial
selection with distinct application, worker, delivery and ledger identities;
malformed immutable header and reserved bytes; missing required identities;
changed selected worker; inconsistent consumed sequences and errors; absent,
unreaped, nonzero or signalled synthetic probe status; and the explicit late
observation flag. Dispatched EAGAIN must advance the sequence, untouched-output
EAGAIN must not, and ambiguous EFAULT must fail without retry.

Terminal, Recovery, TerminalPlusFive and AfterEightHello examples exercise
metadata shape validation only. The synthetic raw-status integers do not prove
a process was signalled, and the late flag does not exercise actual clock
sampling. These checks do not prove native terminal semantics, five elapsed
seconds, eight HELLO launches, syscall copyout behavior or device/process
provenance. Actual pinned process/UART tests and source-bound guest phase
observations remain separate required evidence.
