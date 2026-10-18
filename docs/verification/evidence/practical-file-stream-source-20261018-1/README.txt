Task practical-file-stream-app-20261018-1
Functional working-OS/app prerequisite; broader qualification remains deferred.
Useful command: file-stream copy-check INPUT NEW_OUTPUT
Copies any stable binary input with 4096-byte bounded memory, computes FNV-1a64,
closes/reopens output, reads it back, and checks both byte count and checksum.
Successful output is retained. Existing destinations are refused using O_EXCL.
Incomplete owned output is unlinked on failure; unlink and close failures produce
nonzero status. The destination directory must be private/stable during copying.
Input must remain stable. No crash-persistence/fsync claim is made.

Read/write retry EINTR; writes handle short results. close is performed once per
descriptor under Linux semantics, with errors reported rather than retried after
a descriptor may already have been released. FNV-1a64 is a checksum, not crypto.
The application uses public libc file/stream calls; no process/pipe/network API.

Actual reference has an independent fixed stdout oracle for a 10247-byte payload
containing all byte values, embedded NULs and more than two 4096-byte boundaries.
It also checks exact output bytes externally. Empty file is a second positive.
Negatives perform real ENOENT input open, EEXIST output open (existing bytes
preserved), and EISDIR read after output creation (incomplete output removed).
No forced short-write/EINTR/close/unlink fault is claimed to have been injected.

Driver imports unchanged independently accepted cancellation harness ad74ec8;
all subprocesses have a 30-second wall bound. Serial CPU7/one job, AS1GiB per
process, CPU150, 256fds, file size64KiB, core0, total artifacts under1MiB.
Pinned host GCC9.4 and system libc2.31 are Linux reference only; this binary is
not a guest artifact until separately reviewed profile recompilation. No guest,
Docker, root, Git, shared manifest or application acceptance changes.
