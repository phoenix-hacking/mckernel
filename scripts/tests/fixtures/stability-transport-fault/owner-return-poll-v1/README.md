# Return-poll classification correction

Source candidate only; root owns pinned compilation and execution. This does
not modify the frozen owner-phase-v2 controller or any original report.

The actual permanent-backpressure guest2 reported RET exit at35.746492106s
after reading `running` from the original worker's procfs syscall file. Native
RET remained active until40.004174297s. A running task can still be executing
that ioctl. The original `ret_left_observed` flag is therefore wrong; the
independent mode4 review preserves this defect and uses native RET plus actual
launcher WNOWAIT/EOF for its required terminal and deadline evidence.

This candidate factors the existing bounded-record sscanf expression into a
shared parser and adds an explicit classification. A read error, incomplete
record or negative syscall number is UNKNOWN. A complete selected RET record
is RET; another complete nonnegative syscall record is OTHER. The return poll
can mark a sampled exit only after previously observing RET and then OTHER.
The independent existing worker-stat disappearance path and all deadlines,
native phase operations, terminal WNOWAIT boundary and cleanup remain intact.
Polling still cannot provide accepted return value, errno or exact native
timing. The required native observer remains authoritative for those fields.

`poll-expectations.json` preserves all fourteen actual worker-syscall samples
from the original event stream: two reads, eleven RET samples and the final
running sample. Its last UNKNOWN expectation is established by the separately
observed later native RET leave, not by the classifier being tested. Seven
additional malformed/error boundaries cover empty input, negative syscall,
partial ioctl, trailing token, read error, syscall-file disappearance and an
explicitly synthetic complete nine-field negative syscall record.
The original complete event stream and controller report are retained beside
the vectors. The original/native event provenance remains in the full guest
and independent review; these copied inputs do not claim a new guest run.

`poll_harness.c` includes the exact candidate controller with its CLI main
renamed and never invoked. It calls the shared actual parser/classifier and
retains every raw input and classification in a fresh absolute directory.
No clock, procfs, wait, ioctl or process function is substituted. This is
retained-sample infrastructure regression evidence, with no payload or
transport acceptance. The root wrapper must require all twenty-one exact stdout
lines, empty stderr, raw wait0, complete owned cleanup and every case record.

Compile with the established controller C flags, actual phase_client.h and
public uprotocol.h dependencies. Invoke `poll-harness /ABSOLUTE/FRESH/ATTEMPT`
with a ten-second process limit, fifteen-second cleanup, and independent
65536-byte stream limits. A source review, successful compile or this replay
does not accept a new controller guest profile; composition with the separate
published-mode capture handshake still requires review and fresh validation.

The sequence expectations in the JSON remain metadata only. This harness tests
parser/classifier inputs pointwise; it does not execute the observe_return
loop or prove a full controller state-machine replay. Source review separately
checks that the corrected loop uses the classifier. Full controller/handshake
composition requires its own actual process and guest evidence.
