# Source-only request decoder test inputs

The 84 cases call the real `acrq_decode` in `request.c`. No collector or payload
is launched. `decoder_harness.c` links the decoder as its separate translation
unit and compares fixed expected error tokens and decoded values. It has no
alternative parser and does not call decoder-private functions. The literal
400-byte baseline, including its declared hashes, is separately retained in
`literal-vector.json` and `literal_vector.h`. The fixture encoder must match
those exact 400 bytes before that case can pass.

`decoder-expectations.json` lists independently specified expected errors,
exact full-suite stdout, empty stderr and actual raw exit 0. These are proposed
infrastructure test expectations, not previously observed results. Source-only
authoring, hashing and review do not constitute a test run.

The harness supports one case or the complete ordered suite:

```
decoder-harness --all /absolute/new-attempt
decoder-harness maximum-wire /absolute/another-new-attempt
```

Root owns the exact pinned compiler and run wrapper. The intended C11 compile
arguments are `-std=c11 -O2 -g -Wall -Wextra -Werror -D_GNU_SOURCE`, followed
by the absolute retained `request.c` and `decoder_harness.c` paths and an output
ELF in a fresh build directory. Retain both headers and the wire/expectation
documents, compiler dependency identities, command/log/ELF and actual collector
report. No shell evaluation or application/vector source belongs in that run.
Use the existing pinned four-CPU/12-GiB wrapper, a ten-second infrastructure
process limit, fifteen-second owned cleanup and separate 65536-byte stdout and
stderr limits. Stop at the first unexpected result and preserve it before any
correction. A compiler warning or timeout is a failed infrastructure attempt,
not permission to alter the expected decoder result.

The output root is created exclusively. Every attempted case has a new child
directory with original `request.bin` and `result.json`; no temporary tree is
deleted. The input-mutation test first persists the original wire, then changes
the caller buffer after decoding and requires the copied output to stay exact.
The struct-copy test clears the original decoded struct and checks the copy's
offset-based strings. Original request files for null-pointer API cases still
record their fixture bytes, while result fields explicitly record the actual
null argument passed.

The harness checks output canaries, complete zeroing on rejected input,
independent header fields/hashes and every literal string/terminator. Actual
guard-page tests place the final supplied byte immediately before a PROT_NONE
page; one request is valid and one lacks the last string byte. There is also
an unaligned buffer. The largest valid request is exactly 65536 bytes, built
from 17 arguments with a final 3722-byte argument; a separate request adds one
byte and must fail SIZE. Maximum lists, maximum individual argument size,
empty complete environment, empty nonzero arguments, an empty regular stdin
file and raw high bytes are positive boundaries. These tests do not pretend
the declared artifact hashes were checked against filesystem contents.

Malformed cases cover header identity/version/length/reserved fields, unknown
role/profile, credentials/group/umask, counts, all fd modes and fixed limit
families; zero, oversized and high-word sizes; missing declared hashes/attempt
ID; contradictory devnull metadata; partial prefixes/bodies, huge lengths and
embedded NUL; case/path/argv0 rules; invalid and duplicate environment names;
and declared-length-consistent trailing data. The literal payload role and the
launcher role both remain metadata with execution disabled. Unknown optional
semantics cannot be added through flags or trailing fields.

Parent validation must inspect actual raw wait, complete bounded stdout/stderr
and owned cleanup before considering per-case records. Late storage errors or
a process fault may prevent updating a previously written JSON report; those
remain failures even if a local record had reached PASS. Any missing case or
artifact, changed source, mismatched expected token or output, nonzero raw wait,
signal, timeout, truncation or cleanup error fails this suite. No passed case
supplies runtime capability evidence, filesystem verification, native payload
identity/exit, transport release or catalog credit. Backend execution remains
disabled after all 84 pass.
