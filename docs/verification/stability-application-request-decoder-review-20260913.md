# Application request decoder source slice

This additive slice implements the request decoder proposed in
`stability-application-collector-proposal-20260913.md`. It does not implement
the proposed Linux collector, McKernel application observer, stream attribution
or application execution backend. `scripts/application-tests/run.py` remains
unchanged and metadata-only. Original catalogs, reviewed packets and fault
controllers are preserved.

The new sources are in `scripts/tests/fixtures/application-collector-v1/`.
`request-v1.md` freezes the complete ACRQ0001 byte layout and API preconditions.
`request.c` and `request.h` provide a C11 memory decoder. The format separately
records desired credentials, literal executable/argv/environment/cwd/stdin,
fixed capture modes and limits, plus declared selected-input/executable/stdin
hashes and an opaque attempt identifier. There is no field that can authorize
execution or supply an observed OS/application/worker/process identity.

The decoder checks every header value, byte/count bound, string and environment
name, rejects unknown or contradictory fields and trailing bytes, and clears
all partial output on failure. It copies strings into caller-owned output
storage; offset-based slices survive input mutation and copying the output
struct. It does not allocate, open, resolve, hash or execute anything. Source
review checked the documented nonoverlapping input/output precondition and the
cursor/storage bounds. These are source findings, not observed C runtime results.

`literal-vector.json` and `literal_vector.h` retain a separately encoded
400-byte positive request with explicit expected fields. `decoder_harness.c`
calls the actual decoder and uses fixed expectations from the wire contract.
The 84-case set includes literal/empty arguments, preserved high bytes, desired
identity and declared hashes, complete empty/max environments, exact request
and string limits, copied ownership, unaligned/guard-page inputs and malformed
header/string/environment boundaries. `decoder-expectations.json` independently
lists the expected tokens and exact full-suite stdout. `decoder-tests.md`
describes root's future pinned compile/run, retention and first-failure checks.

The wire was retained before implementation, and every implementation freeze,
original harness before explicit alignment, independent review and source-only
metadata check is preserved in the companion JSON's capture/archive references.
The harness review caught an off-by-one fixture length before execution: the
maximum request initially totaled 65537 bytes because the case ID has 18 bytes.
The retained correction reduces only its final argument from 3723 to 3722 bytes;
the decoder and independent 65536/65537-byte boundary expectations are unchanged.
No compiler, decoder, harness, application, container or guest was executed in
this author/reviewer lane. Any later actual run requires an additive result
record; this source record does not become runtime acceptance retroactively.

The next authorized implementation decision remains a separately reviewed
ordinary Linux process collector using this decoder. Before launch it still
needs actual bounded file/hash/root checks and observed credential/fd setup,
owned process tracking, independent deadlines, complete raw streams and real
Linux wait status. The McKernel launcher wait must remain a launcher fact;
native payload route/exit/lifetime and stream attribution require separate
source-bound producers and validators. All global/case capabilities, transport
gates and a reviewed execution packet remain required for new catalog work.
