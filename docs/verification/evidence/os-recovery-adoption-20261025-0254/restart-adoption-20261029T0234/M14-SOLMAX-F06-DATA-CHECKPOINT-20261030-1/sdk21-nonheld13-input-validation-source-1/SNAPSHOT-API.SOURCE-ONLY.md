# SDK13 per-attempt source snapshot successor

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This source-only, unexecuted successor leaves c7df unchanged. It neither owns a
lease nor grants a release, rehashes source trees, starts Docker, proves native
custody, checks container-effective mounts, or asserts an SDK/ABI/native result.
The driver must still validate effective mounted input bytes before the compiler.

The owner first performs its independently reviewed prelease domain and root
release checks and exclusively acquires the compile lease. It then calls
`begin_snapshot(request, *, profile_path, request_path, source_map_path,
prehashed_trees, lease_check, admission_check, expires_monotonic_ns)`. It returns
the existing c7df bound keys plus private `_input_snapshot`. A local isolated
copy of c7df is used; only its `_tree` is replaced with `_adopt_tree`, without
modifying shared c7df module state or files. This validates the fixed profile,
proposal, request, exact mounts, selectors, config, overlays, eight objects,
toolchain manifest and literal lock. It scans tree membership and metadata but
never opens a tree file to recompute its digest. The separately reviewed prior
byte observation is accepted only if its per-file digest/size equals the frozen
map and its file/symlink identity exactly matches current stat; its root identity
must match as well. All mapped directories are scanned and their identities are
captured while lease and actual quiescence checks succeed. The complete directory
set must equal the source map; newly introduced masks and extra files are denied.

The three `prehashed_trees` keys `/src`, `/src/kernel/rust`, `/nightly` each
contain `{root, root_identity, entries}`. `root_identity` and every entry's
`identity` are lists ordered `(dev, ino, mode, uid, gid, nlink, size, mtime_ns,
ctime_ns)`. Entries cover every file and symlink in the mapped tree, but not
directories. Each retains map fields `relative`, `kind` and, for a file,
`bytes` and `sha256`; for a symlink, `target`. Independent source review must
bind every entry's historical digest AND identity to the actual completed file
read and the exact map; a made-up collection of values and a self-consistent
hash are not evidence. The retained SOURCE6153 JSONL 2c9eac14 is the point-in-time
6153 observation; its directory identities were not recorded. The separate
nightly identity ledger eeabd12d and Rust ledger are point-in-time observations.
A separately reviewed converter must preserve all rows, bind actual receipt
identities and ensure their hashes derive from the actual source reads. Do not
invent a matching ledger or reuse source-map values as an observation. Root
identity provenance and previously unrecorded directories need independent
review. This module accepts the specified normalized object, it does not claim an
unreviewed converter already exists.

`lease_check()` must call the actual owner's `lease.load_owned()` and return the
actual lease bytes; this module rereads the named regular file, compares exact
bytes, inode and owner PID/starttime, request core, profile and nonce. The owner
must keep the exclusive lease and protect its namespace throughout the attempt.
`admission_check()` MUST re-observe and validate independently reviewed actual
root release, control/service/account/time, daemon/socket and complete source
quiescence/noninterference under the operation. It returns exactly
`{request_sha256, profile_sha256, source_map_sha256, root_release_identity,
quiescence_identity, daemon_identity, lease_identity: [dev,ino],
expires_monotonic_ns, prehashed_sha256, snapshot_receipt_identity}`. The three
identity objects and receipt identity are nonempty, exact and stable across the
attempt; `prehashed_sha256` is SHA256 of canonical JSON (sorted keys, compact
separators, no NaN) of the normalized `prehashed_trees`. This shape is only an
API contract; no data structure, fact hash or boolean replaces review of the
callback's actual observations. A release/admission bound to this exact map and
snapshot is required before use. A reasonable expiry must be no later than the
actual root admission. Checks occur on both sides of initial adoption and each
metadata scan; an expiry or change permanently invalidates this in-process
session. On begin failure, the owner must retain ownership and end the attempt;
no automatic same-admission retry, rehash fallback or source mutation is allowed.

After exclusively creating work, owner calls `bind_work` exactly as with c7df.
Call `revalidate(bound, request)` before container create, before start, and at
post-run review. It checks initial bound request/profile/map/snapshot, owner
PID/birth, lease bytes and inode, all files/directories/symlinks and targets,
root directory membership, work identity and actual admission before and after
scan. It never calls a tree content hashing function or reuses data across
processes/invocations. A file whose bytes change after initial observation must
change its monitored identity (including ctime) under the supported filesystem
and admitted quiescence model; that model and absence of writers must be
independently established. Metadata observation cannot prove unchanged bytes
in the presence of uncontained writers or unsupported filesystem semantics.

`test_sdk13_input_snapshot.py` is unrun synthetic fixture source for changed
same-size contents, restored mtime, new masks, symlink retarget, root/profile,
lease/request/admission change, expiration, prehash mismatch, and no rehash.
No captured test or runtime outcome is represented by this preparation.
