# Published client metadata cases

81 independently declared literal request/reply/collection vectors exercise the
actual C op_validate function and compare its complete persistent identity and
consumed-sequence state. The C harness never calls ioctl, op_call, fork, exec,
the controller main, QMP, or a guest. These are synthetic metadata observations,
not actual owner, raw-wait, kernel, UART or transport evidence.

The source specification fixes OS2/PID123/generation9, independently encoded
nonce words, application11/worker12/delivery13/claim14/index3/physical4096..4136,
and requester456. It uses the explicit version2 native field offsets, snapshot
and operation sequences, independent monotonic intervals and timer35/deadline40s.
Valid zero timer/present1 and exact two-second recovery reserve are separate
boundaries. Results include unchanged versus consumed request state, complete
identity checks, all source-bound raw request/reply bytes and exact output.

The first 68-vector generator is retained as metadata-vector-generator.original.py.
Before any test execution, source inspection corrected the successful SELECT
expected key from its prior zero value to the independently specified selected
key. The current generator also supplies release digests in input identity and
adds 13 request-identity/proof negatives for the stronger request validator.
No first-generation test or compiler failure occurred or is claimed.

The per-case exclusive files are request.bin, reply.bin, identity.bin,
observation.bin and result.json. Both complete post-call structs are retained
using the exact pinned ELF/header layout; padding bytes are opaque and supply
no semantic predicate. Every actual field is available even on failure. Files are
fsynced before the exact PASS/FAIL line, with the first mismatch stopping the
suite. A pinned parent must bind compiler inputs, ELF, loader, all vector bytes,
raw zero wait, exact stdout/empty stderr, deadlines, EOF and owned cleanup.

Still separate: initialization/digest-conversion helper boundaries, actual C
client child/ioctl collection, controller polling/PTY integration, release ACK
ambiguity with the host, eight HELLO launches and all physical/native joins.
No complete client/controller or application acceptance follows this suite.
