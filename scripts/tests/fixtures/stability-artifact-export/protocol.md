# Bounded guest artifact export, STAF version 1

This is a verification infrastructure source candidate. The C exporter has
not been compiled or executed in this lane. Synthetic Python socketpair
tests exercise the host parser only. A captured tree, successful ACK or test
result does not accept an application, transport fault or McKernel behavior.

The guest exports one exact, quiescent attempt root after its controller and
owned cleanup have finished, including unsuccessful attempts. The source tree
must contain at most 256 descendants (directories count; the root does not),
at most 16 MiB of total regular-file content, relative paths at most 1024 bytes
and at most 64 components. Unsupported entries, a changed tree, cap overflow,
deadline or incomplete frame fail the export. There is no silent omission,
truncation-as-success, compression, shell invocation or arbitrary archive
extraction. Separate controller, Linux-reference and after-HELLO trees use
separate nonces/connections and fresh host capture directories. If root chooses
a shared parent, these bounds apply to the entire selected combined tree.

The controller owner overlay caps its probe attempts at 48, retaining four
files per attempt, so its own selected attempt remains below the entry limit.
The exporter must never write its stdout/stderr or host receive logs inside
the tree it is reading. Root must retain those external streams separately.
The guest attempt's capped/truncated controller streams remain visible in
their original metadata; exporting those files cannot upgrade their content
to complete controller evidence.

## Connection and invocation

Root adds an isolated virtio-serial port named `stability.artifacts`, backed by
a QEMU Unix socket configured as `server=on,wait=off`. This channel is separate
from the console, controller UART and QMP. The guest requires the pinned
`virtio_console.ko` and its actual dependencies. The intended device is
`/dev/virtio-ports/stability.artifacts`; an explicitly verified
`/dev/vport0p1` node may be supplied instead. Do not infer a port number solely
from that fallback spelling. Root must bind the actual named port/device to
the chosen QEMU socket using its guest sysfs/device records. No network or
guest mount of a host filesystem is involved.

Guest CLI:

```text
exporter ABSOLUTE_ATTEMPT_ROOT VIRTIO_PORT NONCE32
```

The nonce is exactly 32 lowercase hexadecimal characters. The wire carries
the 16 bytes represented by that string, in its displayed order. This is
not the two little-endian u64-word encoding used by the separate owner phase
ioctl. A fresh nonce binds each export. The host must supply the same exact
absolute source path it authorized; ROOT is never used as a host destination.

Host CLI, connected before launching the exporter:

```text
python3 -B receiver.py --socket SOCKET --destination FRESH_HOST_CAPTURE \
  --source-root ABSOLUTE_GUEST_ATTEMPT_ROOT --nonce NONCE32 --timeout 60
```

For integration in the parent QMP runner, use
`receive(connection, destination, expected_root, nonce, timeout_seconds=60)`
with an already connected socket. It does not take socket ownership. It returns
`{"manifest": ..., "ack": ..., "ok": ...}`; local storage errors propagate
and must fail the parent attempt. The caller must preserve its own exception
and timeout record, close the connection and retain the partial destination.
Destinations must not exist; the helper never overwrites an earlier attempt.

The exporter uses one 60-second Linux `CLOCK_MONOTONIC` deadline for the entire
walk, transfer and ACK. Device I/O is nonblocking with at most 100-ms poll
steps. Receiver parsing and ACK use one host-monotonic deadline (default 60
seconds, allowed range greater than zero through 120 seconds). The CLI's
connection wait has a separate bound; the parent should connect before the
export phase starts. Local filesystem calls and fsync are not interruptible
by this socket deadline. The parent must keep its independent host supervisor
and QEMU emergency-capture watchdog around the entire export. A guest pause
does not pause the host deadline.

## Binary framing

Every integer below is unsigned little-endian unless specified. Header and
record sizes are fixed; no native C structures cross the connection.

The stream begins with exactly 48 bytes:

| Offset | Size | Value |
| --- | --- | --- |
| 0 | 8 | ASCII `STAF0001` |
| 8 | 4 | version 1 |
| 12 | 4 | header size 48 |
| 16 | 16 | raw nonce bytes |
| 32 | 4 | entry cap 256 |
| 36 | 4 | content cap 16777216 |
| 40 | 4 | path cap 1024 |
| 44 | 4 | reserved zero |

Every record has a 16-byte header: kind u32, path length u32, payload length
u64, followed immediately by those exact path bytes and payload bytes.

| Kind | Path | Payload |
| --- | --- | --- |
| 4 ROOT | exact selected absolute source root | metadata64; first and once |
| 1 DIR | safe relative descendant | metadata64 |
| 2 FILE | safe relative descendant | metadata64 then exactly source size bytes |
| 3 END | empty | four u64: entries, directories, files, total content bytes |
| 127 FAIL | empty | 1–256 printable ASCII bytes describing first failure |

Metadata consists of eight u64 values: Linux mode, device, inode, size,
mtime seconds, mtime nanoseconds, ctime seconds, ctime nanoseconds. The two
seconds fields use signed two's-complement encoding; the host converts them
to signed JSON integers. Nanoseconds must be less than one billion. ROOT and
DIR must have directory mode, FILE regular mode; all descendants share the
source root device. The host retains metadata as evidence and creates private
host directories/files with modes 0700/0600. It does not apply guest ownership,
timestamps or permission bits to its host filesystem.

Only printable ASCII path bytes 32–126 are accepted; backslash is forbidden.
Relative entries must have no leading/trailing slash, empty, `.` or `..`
components. A descendant's parent must already have appeared as DIR. Duplicate
paths and repeated ROOT fail. The exporter walks using directory descriptors,
`fstatat(..., AT_SYMLINK_NOFOLLOW)` and `openat(..., O_NOFOLLOW)`; it rejects
symlinks, devices, sockets, FIFOs and regular files with link count other than
one. It opens each absolute root component without following symlinks. The
selected port may be the documented device symlink, but must resolve to an
actual character device. Its exact QEMU provenance is an external gate.

Before/after fstat checks compare device, inode, mode, link count, size, mtime
and ctime; directory traversal is bound to the metadata already sent for that
directory, including ROOT. Atime is intentionally excluded because reads may
update it. These checks detect ordinary mutation and retain failures; they
do not create an atomic snapshot against a privileged concurrent writer.
Source quiescence after actual owned cleanup remains required. Same-device
bind mounts are not distinguished by st_dev; the selected attempt root must
be the fresh ordinary artifact directory created by the reviewed controller,
with no externally introduced mounts. The exporter does not create mounts.

END asserts that the complete source walk passed its stability checks and
that all counts are exact. The host validates them against parsed content.
FAIL is legal only at a complete record boundary. A failure midway through a
file cannot insert another record: the incomplete bytes remain the raw prefix
and the host fails on EOF or deadline. Both implementations preserve first
failure; neither treats a successful partial file as a successful tree.

The host retains at most 17 MiB of framed raw data, above the maximum valid
16-MiB tree plus bounded metadata/path framing. It reads exact requested
lengths with chunks at most 32 KiB, checking declared limits before variable
reads. Bytes returned from the socket are written to `wire.bin` before they
are interpreted; a partially received file chunk can be present only in raw
wire evidence while the extracted file contains its preceding complete chunks.
`bytes_stored` and per-file SHA-256 describe exactly the extracted prefix.
Queued bytes after END fail. Because the exporter waits for ACK after END,
the receiver cannot prove that no future byte will ever arrive; this protocol
permits precisely one tree per connection, with no reuse or subsequent frame.

## Durable acknowledgment and retained files

The receiver anchors fresh destination creation/open to one parent directory
descriptor and stores `wire.bin`, `files/` and canonical `manifest.json` using
exclusive creation. It computes SHA-256 with
Python's standard hashlib for the exact raw stream, every extracted file and
the exact canonical manifest bytes. Successful parsing yields manifest status
`CAPTURE_COMPLETE`; errors yield `FAIL` with exact captured-prefix counts and
reason. Hash/count progress updates after every successful local write,
including a short write before a later error. Socket bytes received are counted
separately, so a failed disk write cannot falsely claim all received raw bytes
were stored. All files, directories and the destination's parent entry are
fsynced before any success ACK. Storage
or fsync failure withholds success ACK and propagates to the parent.

ACK is exactly 112 bytes:

| Offset | Size | Value |
| --- | --- | --- |
| 0 | 8 | ASCII `STAA0001` |
| 8 | 16 | exact raw nonce |
| 24 | 4 | status 0 success, 1 failure |
| 28 | 4 | reserved zero |
| 32 | 8 | exact total content bytes |
| 40 | 8 | exact descendant count |
| 48 | 32 | SHA-256 bytes of `wire.bin` |
| 80 | 32 | SHA-256 bytes of `manifest.json` |

The host records intended `ack.bin` before transmitting and separate
`ack-result.json` with actual byte count and error; manifest bytes never change
after their digest is sent. ACK failure can coexist with a complete durable
capture; `result.ok` is still false. A transport deadline still permits bounded
local failure metadata retention, but never a late success ACK. A malformed
initial header/nonce is not acknowledged. For a parsed valid header, failure
ACK is best effort and cannot authorize shutdown.

The C exporter validates ACK magic, nonce, zero status/reserved and exact
counts. It logs the host-provided digests and exits zero only after the full
ACK arrives before its original deadline. It does not implement cryptography
or independently compute the wire digest: those logged values are the host's
durability assertion. Root must compare them to its actual retained SHA-256
values. The host's `ack_complete` proves bytes were sent, not that the guest
received them. Root must require both host `result.ok` and the actual exporter
zero wait status/exact `STAF EXPORT_ACK` log before authorizing guest poweroff.
Failure emits `STAF EXPORT_FAIL ... poweroff_authorized=false` and exit 1.
No helper powers off or kills the guest itself.

## Required independent validation

Run `python3 -B test_receiver.py` for synthetic framing tests only. They use
literal independent wire structures, raw binary data, socket fragmentation,
exact nonce/count/digest comparisons, unsafe paths, duplicate/missing parents,
type/device/time errors, entry/content/depth limits, premature EOF, explicit
failure, trailing data, deadlines, unavailable ACK and injected host fsync
failure, partial local write errors and destination-parent fsync ordering.
They do not run C, kernel code, payloads, a container or QEMU.

Before guest use, root must retain an independent source review and pinned
C compiler `-Wall -Wextra -Werror` build with exact compiler inputs/dependencies.
The exporter requires Linux openat/fstatat/poll APIs and no external library
beyond libc. Actual positive and negative C/virtio checks must cover a nested
binary attempt tree, exact host hashes, missing/incorrect ACK and deadline,
unsafe source symlink/hardlink/type/path, cap overflow, mutation and interrupted
transfer with partial raw retention. Verify real port identity and guest
cleanup-before-export, then poweroff-after-ACK ordering. These are infrastructure
checks and cannot substitute for the four real retained-owner fault gates.
