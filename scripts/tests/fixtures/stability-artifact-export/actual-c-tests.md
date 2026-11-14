# Actual C exporter PTY integration tests

Source prepared only. The author did not compile or execute the C exporter or
run this driver. Root owns execution under the established pinned container
wrapper and retains the exact compiler/module/image evidence separately.
These are ordinary Linux infrastructure checks: no McKernel, QEMU guest,
application payload or production acceptance is involved.

The guarded C source is SHA-256
`af85d0c692a1df677c2df7c9cbb5ee85fcf8b7dc31d2b14527675a3dc903fb6c`.
The only change from the first source freeze `90e87cf5...` is an
`#ifndef _GNU_SOURCE` guard around the existing definition. Root's first pinned
build failed because its unchanged `-D_GNU_SOURCE -Werror` flags diagnosed the
duplicate definition. The original source, command and failed compiler output
remain in `/work/stability-guest-collection-build-20260913-1`. The fix changes
no runtime logic or build flags.

Invoke from the source fixture directory using the root's original container
wrapper; the exporter argument names the separately pinned compiled ELF:

```text
python3 -B run_exporter_tests.py \
  --exporter /work/BUILD/exporter --exporter-sha256 FULL_ELF_SHA256 \
  --attempt-root /work/FRESH_ATTEMPT \
  --supervisor /work/REVIEWED_SUPERVISOR.py
```

`--receiver` and `--exporter-source` default to this directory's reviewed
files; root may give explicit absolute staged paths. The driver validates
their full frozen hashes and the reviewed supervisor hash, reads and copies
exact bytes into `inputs/`, checks those copied byte hashes before continuing,
and executes only its captured ELF and Python sources. The ELF/source compiler
binding remains the root build record's obligation; providing an ELF digest
alone cannot prove how it was compiled. `/.dockerenv` is only an accidental
execution guard; the external pinned wrapper supplies isolation/provenance.

Each selected case (`--case NAME`, repeatable) runs one copied driver worker
under the reviewed process supervisor. Default order is:

1. Binary nested files, an empty regular file and empty directories.
2. An empty selected tree.
3. Source symlink rejection without reading an outside sentinel.
4. A regular hard link to an outside sentinel, rejected by actual link count.
5. FIFO rejection without opening or blocking on it.
6. 257 empty entries: the first 256 may be retained, then explicit entry-limit
   failure. No partial tree receives a success verdict.
7. One sparse 16-MiB-plus-one source file: explicit content-limit failure.
8. An actual complete ACK with a changed magic byte.
9. An actual complete ACK with a changed nonce byte.
10. An actual complete ACK with a changed content-count byte.
11. An actual complete ACK whose status is changed from zero to one.
12. Only 111 ACK bytes accepted by the PTY master, then physical disconnect.
13. Physical master disconnect after exactly 4096 exporter bytes are read,
    midway through a real 1-MiB source file.
14. All 112 intended ACK bytes deliberately withheld; actual exporter waits
    through its unchanged 60-second deadline and must exit with deadline error.

Each worker opens a real PTY, calls `tty.setraw` on its slave before forking,
records actual termios and device identity/path, and gives the slave pathname
to the unchanged C CLI. The C program opens a real character device with its
original flags. The parent retains its own slave descriptor only until first
data, preventing the startup fork/open EOF race; it then closes that descriptor
so the actual exporter's close produces a real master EOF (Linux PTY EIO).
No tty echo, canonical input processing or newline conversion is permitted.
The master adapter implements bounded socket-style reads and a one-read
lookahead for the receiver's MSG_PEEK. All actual physical reads and writes
are retained independently of the receiver's own raw framing capture.

The parent executes the actual reviewed `receiver.receive` against the PTY
adapter. Successful cases compare its exact tree with independent literal
content, exact paths/counts and the C-reported host wire/manifest SHA-256.
They require actual exporter raw wait 0, empty stdout, one exact ACK stderr
line, a 112-byte physical ACK, unchanged bytes and actual PTY EOF. Negative
cases require raw wait 256 (normal exit 1), one exact failure stderr line and
no ACK-success log. Actual signal termination cannot satisfy either oracle.
The unsafe/cap failures use fixed independently expected reason/errno pairs;
PTY disconnection permits only the bounded Linux EIO/EPIPE channel outcomes.

ACK faults are explicit adapter fault injection, not a claim that the normal
receiver sends incorrect bytes. Its intended ACK and actual physical bytes
are retained separately. For the missing/short ACK cases the adapter accepts
intent but intentionally omits bytes, so receiver `ack_complete` alone has no
physical-delivery meaning for that injected test. The worker requires the
actual exporter's independent failure result and the exact physical byte
count. Missing ACK additionally requires at least 60 real monotonic seconds
from child start through observed wait. Neither clocks nor C deadlines are
replaced. A post-END failure frame from a C exporter rejecting its ACK remains
in physical evidence; the earlier receiver manifest stays immutable.

The C exporter is one direct unreaped worker child with no concurrent waiter.
The parent records its actual wait status and retains stdout/stderr in separate
exclusive files outside the source tree. The PTY is nonblocking and bounded;
wire logs allow at most 17 MiB plus 1024 bytes and output streams at most
64 KiB. A worker has 70 seconds, with at most 10 seconds of direct child
cleanup after failure. Its enclosing supervisor has 75 seconds plus 15 seconds
of owned cleanup. The suite stops at first unexpected result, has a 300-second
budget and reserves a full 75 seconds before each next case. Root must wrap
the entire driver with a correspondingly larger outer bound (at least 320
seconds plus its own cleanup). Normal cases are expected to finish promptly;
the missing-ACK case deliberately takes about one minute.
The actual observed wait and completed EOF/disconnect collection must both
precede the worker's original 70-second deadline. A delayed read, local evidence
write or wait observation crossing that deadline fails even if exit/EOF are
available by the time the call returns; the outer 75-second limit never
substitutes for this inner completion bound.

Every source tree, outside sentinel, capture, wire direction, intended ACK,
actual raw wait, termios record, stream and supervisor report remains under a
fresh attempt directory. No `TemporaryDirectory`, automatic fixture deletion,
attempt reuse, unlogged retry or weakened oracle is used. On unexpected
infrastructure failure, keep the whole tree and original source/ELF before
preparing a fresh bounded correction. The sibling synthetic parser tests also
now retain each case under TMPDIR and print its full evidence path.

This PTY suite proves actual C/Python protocol agreement and selected failure
behavior under its ordinary Linux test conditions. It does not establish real
virtio port provenance, guest cleanup ordering, QMP continuation or the four
native retained-owner transport fault gates. Those remain independent gates.
