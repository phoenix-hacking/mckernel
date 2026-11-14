# Linux collector storage-fault v2 source packet 3

Date: 2026-09-15
Task: `M02-B-storage-fault-v2-source`
Disposition: `SOURCE_PACKET_INPUT_BINDING_DRAFT_ONLY`

This additive correction supersedes only the retained-input portion of packet 2
at SHA256
`0feaad14f408acf806fb391195e519a16de60cc41ffdb24cd9721ea432b90089`.
All other clauses and closed gates in packets 1 and 2 remain unchanged. It
authorizes no compiler, build, root, collector, payload, guest, application or
production execution.

The owner CLI requires canonical absolute, no-symlink regular-file arguments
`--source`, `--generated-source`, `--header` and `--elf`. Before socket creation
or fork it stable-reads each by a pinned fd, rejects size above 1 MiB for source/
generated/header or 16 MiB for ELF, verifies pre/post fstat identity, and checks
its SHA256 against the four reviewed hash values. A mismatch creates no child.
The canonical absolute `argv[0]` must equal the canonical `--elf` path exactly;
the owner verifies this equality before fork and execs that exact path. The
oracle independently requires `owner.argv[0] == owner.inputs.elf.path` and the
same canonical file identity. A distinct-file executable-path mismatch is a
mandatory negative.

Add exact top-level owner-result key `inputs`. Its exact keys are
`source,generated_source,header,elf`. Each record has exact keys
`path,present,size,sha256`: path is the canonical input path, present is true,
size is a nonnegative integer within its bound, and SHA256 is the stable-read
lowercase hash. These records are required and must equal the corresponding
hashes object values. Missing/unreadable/changed/symlinked/nonregular/oversized
inputs reject before fork and are preserved as owner preparation failure, never
as a storage-fault selector result.

The oracle independently repeats the bounded pinned-fd stable reads at validation
time and joins their current bytes to both `inputs` and `hashes`. It also checks
the source hash against the frozen collector identity. Hash strings without
these retained readable bytes cannot satisfy a positive fixture. Source tests
provide real bounded temporary bytes and cover, one mutation at a time, each
path/hash mismatch, missing input, symlink, nonregular input, oversize input and
pre/post identity change. Compiler and subprocess entry points remain mocked.
