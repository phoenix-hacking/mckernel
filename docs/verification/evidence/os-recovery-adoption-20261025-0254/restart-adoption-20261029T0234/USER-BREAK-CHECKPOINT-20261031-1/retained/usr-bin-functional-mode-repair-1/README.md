# One-directory functional interpreter-ancestry repair — source only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
R3's actual keeper reported `directory ancestry is not root controlled`. The
retained observation identifies `/usr/bin` as UID/GID 0, mode 0777, device
66306 and inode 1048578 on the stated ext4 root mount. The requested correction
is one `fchmod` on that exact held directory FD to mode 0755. This is a source
packet only: no metadata or filesystem permission was changed here.

The fixed source rechecks the actual Root session and current R3 caller/sudo/root
PID/birth chain; fresh included-only usage and guardian/capacity controls under
inherited UTC/BOOT/MONO caps; actual capture identity; the observed mount line
and namespace, no intervening `/usr` or `/usr/bin` mount, writable mount, exact
root/`usr`/`usr/bin` identities, ownership, mode, mtime/ctime, and absence of
both access and default POSIX ACLs. It opens every directory with
`O_DIRECTORY|O_NOFOLLOW`, durably emits BEFORE DATA, then repeats the relevant
checks immediately before its one `fchmod` call. It fsyncs, validates the exact
metadata and path, and checks a separately opened nofollow readback FD. It closes
each owned descriptor once with explicit close state and emits final DATA. A
failed or interrupted fchmod, verification, journal/capture, or close is UNKNOWN;
there is no retry, rollback, recursive chmod, chown or native/resource release.

`PROFILE.SOURCE-ONLY.json` contains the exact proposed sudo-A/taskset CPU6/
prlimit/Python argv: 64-MiB address space, 5 CPU seconds, 128 FDs, no network
and no fork in the helper. Root must independently review the actual source,
measure the available share inside the current R3 reservation, preserve the
existing four compute jobs and other native holds, and create a fresh private
caller-owned regular capture. It must bind the capture device/inode in the two
last arguments. The retained observation SHA and exact source hashes are frozen
in the source and manifest.

Before invocation Root supplies canonical JSON plus newline and its SHA-256
with the exact `repair` key set: status
`REVIEWED_ONE_SHOT_FUNCTIONAL_MODE_REPAIR`, scope `USR_BIN_0777_TO_0755`,
nonce `8c12bd228ca26f54732752129977b7310a74234a5d8812faaaa8658be5925bec`,
the actual observation and independent-review hashes, actual controls/capacity
hashes, fresh issued/expiry BOOTTIME ns (maximum 30 seconds), inherited-bounded
MONOTONIC expiry and UTC cap, actual included-only weekly usage and observation
UTC ns, `service_status=NO_NEW_REJECTION`, actual mount-namespace device/inode,
`native_release=false`, `native_currentfree=null` and `reservation_release=false`.
Root passes the release path/hash, actual independent review path and capture
device/inode as the final five profile arguments. Root is the authority; a JSON
status or hash alone does not authorize a mode change. The review and actual
one-shot consumption must be preserved before launch, with UNKNOWN retained if
dispatch or outcome is uncertain.

System Python 3.8.10 compiled the three source files. The three targeted mocked
identity/ACL/close tests remain unrun. No root operation, permission mutation,
SDK mount, native/guest work or cleanup occurred. The two failed operation
nonces, original UNKNOWN4 GiB and current R3 reservation, native12, V2 UNKNOWN2,
scratch21 and mutex27:4 remain retained.
