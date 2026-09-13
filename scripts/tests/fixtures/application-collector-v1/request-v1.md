# ACRQ0001 request decoder, version 1

This directory implements only a memory decoder. It contains no collector,
executable launcher, file verifier, native application observer or execution
authorization. A successfully decoded request remains `execution_enabled = 0`.
The caller must not interpret syntactic validity as capability or provenance.
The historical collector proposal remains unchanged.

All integers below are unsigned little-endian. The decoder reads individual
bytes; the wire does not depend on C structure layout or pointer alignment.
There is exactly one 256-byte header followed by the string table. An input
buffer contains exactly one request, between 256 and 65536 bytes inclusive.
Unknown versions, flags, values, reserved bytes and trailing bytes fail.

| Offset | Bytes | Field and permitted value |
| --- | --- | --- |
| 0 | 8 | Literal ASCII `ACRQ0001` |
| 8 | 4 | Schema version, exactly 1 |
| 12 | 4 | Header length, exactly 256 |
| 16 | 4 | Total request length, exactly the supplied buffer size |
| 20 | 4 | Flags, exactly 0 |
| 24 | 4 | Declared role: 1 Linux reference payload, 2 McKernel launcher |
| 28 | 4 | Identity/limit profile, exactly 1 |
| 32 | 4 | Desired uid, exactly 0 |
| 36 | 4 | Desired gid, exactly 0 |
| 40 | 4 | Desired supplementary group count, exactly 1 |
| 44 | 4 | Desired supplementary group, exactly 0 |
| 48 | 4 | Desired umask, exactly 18 decimal (`0022` octal) |
| 52 | 4 | argv count, 1 through 64 |
| 56 | 4 | Complete environment entry count, 0 through 64 |
| 60 | 4 | stdin mode: 0 `/dev/null`, 1 immutable regular file |
| 64 | 4 | stdout mode, exactly 1 (separate capture pipe) |
| 68 | 4 | stderr mode, exactly 1 (separate capture pipe) |
| 72 | 4 | Process timeout, exactly 10000 milliseconds |
| 76 | 4 | Cleanup timeout, exactly 15000 milliseconds |
| 80 | 4 | stdout retention bound, exactly 65536 bytes |
| 84 | 4 | stderr retention bound, exactly 65536 bytes |
| 88 | 8 | Declared executable size, 1 through 99614719 bytes |
| 96 | 8 | Declared stdin size, 0 through 99614719 bytes |
| 104 | 32 | Selected-input manifest SHA256, raw bytes, not all zero |
| 136 | 32 | Executable SHA256, raw bytes, not all zero |
| 168 | 32 | stdin SHA256: all zero for mode 0; not all zero for mode 1 |
| 200 | 16 | Attempt identifier, opaque raw bytes, not all zero |
| 216 | 40 | Reserved, all zero |

Mode 0 additionally requires stdin size 0 and the exact string `/dev/null`.
Mode 1 permits an empty regular file but requires a declared nonzero hash and
an absolute stdin path. The maximum artifact size equals the existing
runtime-contract bound (95 MiB minus one byte). These are declared identities,
not verified contents. SHA bytes are neither calculated nor authenticated by
this decoder. The attempt identifier is an opaque join key, not an OS identity.

The string table has this exact order: case ID, executable path, cwd, stdin
path, every argv entry in order, every environment entry in order. Each string
is encoded as a four-byte length followed by exactly that many bytes, with no
wire terminator. Every string is at most 4095 bytes and contains no NUL.
The case ID is 1 through 96 ASCII letters, digits, dots, hyphens or underscores.
Its first character must be a letter or digit. There is no Unicode decoding,
escaping, shell substitution, sorting, whitespace trimming or normalization.

Paths must be absolute and lexically canonical: no empty, `.` or `..`
components, repeated slash or trailing slash. `/` is permitted only for cwd.
This lexical check does not resolve symlinks or prove filesystem existence.
Executable path and argv0 remain independent. argv0 must be nonempty but can
be a bare name; every subsequent argument may be empty. Argument bytes other
than NUL are literal, including high bytes, newlines and shell metacharacters.

Each environment entry is the literal `NAME=VALUE` string. NAME must match
ASCII `[A-Za-z_][A-Za-z0-9_]*`; VALUE may be empty and may contain further
equals signs, high bytes or newlines. Names cannot repeat, even with identical
values. Entry order is preserved. An empty table means an explicitly empty
environment, not inheritance. This deliberately supports a smaller reviewed
subset than every environment name accepted by Linux execve.

`acrq_decode(bytes, length, output)` returns an error enum or `ACRQ_OK`.
The caller supplies a valid output object and readable input of the stated
length. Those memory ranges must not overlap. A null input is rejected; a
null output returns `ACRQ_ARGUMENT` and cannot be cleared. On every other
failure the entire output object is zero. On success every string is copied
into the output's own storage with an extra NUL; slices use offsets/lengths,
not pointers into the input. Mutating or releasing the input after decoding
does not alter the decoded values. Copying the output struct preserves slices.
The decoder performs bounded reads, copies and comparisons only; no allocation
or operating-system call is needed. The approximately 68 KiB output belongs
in caller-owned static/heap storage, not a small kernel stack.

`acrq_error_name` supplies fixed diagnostic tokens. Error categories describe
the first invalid field in the documented header/table validation order; they
are decoder results, not application outcomes. The caller must retain original
wire bytes and request SHA256 independently. No wire field can enable execution,
set actual IDs or populate a Linux wait or McKernel terminal observation.

Before a future collector may execute, a separately reviewed caller must bind
this request to the strict JSON/runtime packet, rehash actual input/executable/
loader/root bytes, establish and observe credentials/cwd/fds, enforce process
and cleanup deadlines, and prove every global/case capability. Container and
guest topology, the independent QEMU watchdog, native payload route/exit/lifetime
and stream attribution remain outside this decoder. `run.py` stays unchanged
and metadata-only. This version creates no catalog or transport acceptance.
