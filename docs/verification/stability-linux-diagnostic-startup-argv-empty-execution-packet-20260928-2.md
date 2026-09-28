# startup.argv-empty: Linux diagnostic execution packet

**Status: READY_FOR_REVIEW — independent execution review required.** This packet authorizes no
execution by itself. It is a Linux control diagnostic only: it is not a guest
run, McKernel application execution, M04/M06 acceptance, production-gate
credit, or catalog acceptance.

## Frozen inputs and provenance

Selected case: `startup.argv-empty` (packet-001, queue position 1), selected by
`python3 -B docs/verification/os-milestones-20260914/dispatch.py case
startup.argv-empty`. The source-approved collector is
`scripts/application-tests/linux_diagnostic.py`, source SHA-256
`c9932ce4883b1c23c4fc5df0cdb6b4cbe855c140d38787b6abf960f1d75ee409`, with the
PASS_SOURCE review in `docs/verification/stability-linux-diagnostic-source-review-20260928-1.json`.
The archive Git object binding is
`c9d87b95901c1581057a5ee86b1e5ab6196d3edc`; it resolves in this checkout as a
4,435,832-byte blob and must be reauthenticated before release.

Restore, without transformation, only from
`docs/verification/evidence/stability-review-20260913-1-01.tar.gz`, SHA-256
`a4b9bb58afc9b435c95868ef70b4edc86bb73b6df140d1a0272be91ca08403ce`, whose
member root is `stability-packet001-compile-20260913-1/`. The exact payload
member is `startup.argv-empty/payload`, SHA-256
`ff227c83b2da598110768e13f5e042b437e049659706b56079cc73f7c818a836`, size
20528. Its source is `startup.argv-empty/startup.argv-empty.c`, SHA-256
`1786835eccf68588b5def92a056c4bc83b10a6ce7163778b59dd4c5481b7b465`, size
777. Its independent oracle is `startup.argv-empty/oracle.json`, SHA-256
`0be4d0cbd276aa77e381de0734ccfcc77304b9f9fa5d00b576c69fb01326e6d8`, size
687. The retained record identifies interpreter `/lib64/ld-linux-x86-64.so.2`
(captured SHA-256 `0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b`,
size 930600) and DSO `/lib64/libc.so.6` (captured SHA-256
`b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4`, size
2339896). The archive member paths are
`startup.argv-empty/runtime/lib64/ld-linux-x86-64.so.2` and
`startup.argv-empty/runtime/lib64/libc.so.6`.

## Controlled restoration and safety gate

An operator may proceed only after independent review and only into a new,
dedicated 0700 root, for example
`/work/stability-linux-diagnostic-startup-argv-empty-20260928-2/`; its parent
must already exist, be controlled, and have no same-named child. Verify archive
SHA-256, reject absolute/traversal/duplicate members, require regular files,
and compare every restored member’s size and SHA-256 to the retained record.
Do not overwrite an existing path. Preserve the archive and all original
evidence. The payload, source, oracle, interpreter and DSO are immutable
inputs; the request and attempt directories are disposable outputs only.

Before release, independently verify the dynamic-loader closure at the exact
canonical paths in the pinned image (not on the host, and not from a bind
mount), with no shell, `LD_*` override, or unreviewed substitute. Record each
file’s canonical path, hash, mode, ownership, device/inode, size, mtime and
ctime. The captured interpreter and DSO hashes above must match exactly. A
mismatch, a symlink, a changed image `Config`/`RootFS`, or an unaccounted
transitive loader dependency is a hard stop. The collector’s documented
limitations (pathname substitution, provenance, and interpreter/DSO closure)
are packet gates, not waived risks.

## Pinned-image release (review input; not yet released)

The proposed release is inside the already retained immutable image
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`,
with retained manifest SHA-256
`c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
Before any payload is started, independently reauthenticate the image ID,
architecture/OS, complete `Config`, and complete `RootFS` layer list against
`/home/holden/mckernel-work/logs/image-native.json`. In that same image and
the same execution profile, run only a read-only closure preflight against the
canonical `/lib64/ld-linux-x86-64.so.2` and `/lib/x86_64-linux-gnu/libc.so.6`
paths (and every loader-discovered regular DSO). The preflight must publish a
manifest whose canonical loader/libc hashes are respectively
`0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b` and
`b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4`, with
the retained sizes 930600 and 2339896, and whose complete closure hash is
bound to the same image/profile. This preflight is not payload execution; it
must fail closed if the canonical paths or closure differ. No host DSO or
bind-mounted runtime may satisfy the check.

After independent execution review clears that preflight, use a fresh nonce,
fresh container name, fresh controlled root and fresh attempt name. The exact
Docker create argv is the following (the nonce and root are substituted only
as shown; no extra arguments are permitted):

```text
/usr/bin/docker create --pull=never --init --name mckernel-linux-diagnostic-<nonce> --label mckernel.linux-diagnostic.owner=<nonce> --cpus=4 --cpuset-cpus=2-5 --cgroup-parent=/mckernel-dev --memory=12g --memory-swap=12g --pids-limit=512 --cap-drop=ALL --security-opt=no-new-privileges --read-only --network=none --user=1000:1000 --ulimit core=0 --ulimit nofile=4096:4096 --tmpfs /tmp:rw,nodev,nosuid,size=256m --mount type=bind,src=<root>/snapshot,dst=/snapshot,readonly --mount type=bind,src=<root>,dst=/work --env TMPDIR=/work/tmp --env HOME=/tmp --env PYTHONDONTWRITEBYTECODE=1 --workdir=/work --entrypoint=/usr/bin/python3 sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94 -B /snapshot/linux_diagnostic.py --request /work/request.json
```

`<root>/snapshot` is a private, hash-verified read-only source snapshot.
`<root>` is a new 0700 controlled root, owned and prepared before create, and
is the only writable application mount;
its `request.json` must name `/work/startup.argv-empty.c`, `/work/oracle.json`,
`/work/payload`, cwd `/work`, and a fresh `/work/attempt-<nonce>`. The exact
request remains the schema shown below, with those paths substituted and no
additional environment, writer, wrapper, shell, or entrypoint. The owner must
record the exact create argv, nonce/label, container ID, image inspect and
Config/RootFS reauthentication, closure-preflight manifest, and immutable
root/attempt identities before `start --attach <container-id>`.

The independent watchdog must record its own PID/process identity, owner lock,
deadline, and signal-safe state. Attach must retain stdout/stderr and raw wait
status. Release requires one owned container lookup by both label and exact
name, an inspected state of exited/non-running/not-paused/not-restarting,
`OOMKilled=false`, `Dead=false`, empty error, and exit code 0, followed by
owner-only removal, repeated absence verification, watchdog disarm/reap with
raw wait status 0, and a final inventory. Any lookup ambiguity, attach
timeout, owner mismatch, unexpected descendant, cleanup uncertainty, or
stale-name collision is a hard stop. These records must use fresh names and
be retained with the collector evidence; no wrapper may be introduced.

## Canonical request (collector PASS / supervisor COMPLETED)

Create strict JSON at `<root>/request.json` with exactly the collector schema:

```json
{"schema_version":1,"kind":"linux-diagnostic-request","case_id":"startup.argv-empty","source":{"path":"<root>/startup.argv-empty.c","size":777,"sha256":"1786835eccf68588b5def92a056c4bc83b10a6ce7163778b59dd4c5481b7b465"},"oracle":{"path":"<root>/oracle.json","size":687,"sha256":"0be4d0cbd276aa77e381de0734ccfcc77304b9f9fa5d00b576c69fb01326e6d8"},"payload":{"path":"<root>/payload","size":20528,"sha256":"ff227c83b2da598110768e13f5e042b437e049659706b56079cc73f7c818a836"},"argv":["app","A","","B"],"executable_path":"<root>/payload","cwd":"<root>","env":{"LC_ALL":"C","PATH":"/usr/bin:/bin"},"stdin":null,"timeout_seconds":30,"cleanup_timeout_seconds":15,"stdout_limit_bytes":4096,"stderr_limit_bytes":65536,"application_acceptance":false,"mckernel_application_executed":false,"attempt":"<root>/attempt-001"}
```

`argv[0]` is deliberately `app`; the empty argument is the third literal
element. `stdin:null` means collector-enforced `/dev/null`. `<root>/attempt-001`
must be absent before launch and its parent must remain the same 0700 controlled
directory. The collector invocation is exactly:

```text
python3 -B <root>/snapshot/linux_diagnostic.py --request <root>/request.json
```

No compiler, shell, sudo, guest, VM, systemd, network, or additional writer is
permitted. The outer operator must impose an independent wall deadline greater
than 45 seconds and retain the host’s bounded CPU/memory/task limits.

## Oracle, publication, and teardown

PASS requires collector status `COMPLETED`, cleanup complete, unchanged input
identity, exit 0, empty stderr, and stdout exactly the oracle bytes:
`{"case":"startup.argv-empty","argc":4,"argv":["app","A","","B"],"terminator_is_null":true}\n`.
The expected wait is `{"kind":"exited","code":0}`; any signal, timeout,
nonzero exit, truncation, byte/accounting mismatch, mutation, setup error, or
cleanup uncertainty is FAIL. The collector must publish its exclusive
`diagnostic-evaluation.json`; its append-only sibling
`attempt-001.diagnostic-failure.jsonl` is mandatory evidence even on failure.
Retain request, worker report/diagnostics, stdout.bin, stderr.bin, evaluation,
failure journal, and an input manifest with archive/member and closure hashes.
Never overwrite or reuse an attempt name. After evidence is fsynced and
independently hashed, remove only the disposable attempt/request staging tree;
retain the original archive and published evidence. No result may be promoted
to application acceptance.

## Blockers and release conditions

1. This packet is **READY_FOR_REVIEW**, not released. The existing reviewed profile authorizes only
   the separate rebuild helper; it does not authorize this diagnostic create,
   closure preflight, payload, or publication. Independent execution review
   must explicitly approve this packet and its exact argv before release.
2. The pinned image ID, manifest SHA, complete `Config`/`RootFS`, and the
   canonical loader/libc hashes and complete closure must reauthenticate in the
   same image/profile before payload setup. Any mismatch is a hard stop.
3. Independent review must confirm the canonical request, fresh controlled
   root, owner/watchdog/attach/exit/cleanup evidence, limits, and publication
   and teardown plan. Until all three conditions are cleared, do not restore,
   invoke, create, or execute this packet.

The controller under review is
`scripts/application-tests/linux_diagnostic_container_owner.py`, SHA-256
`3d29c04a0dc7a7474773827e3468566aa72bc380ed4a9a6725c88914ada3fc93`. Its private snapshot must contain the exact source
hashes: `linux_diagnostic.py`
`c9932ce4883b1c23c4fc5df0cdb6b4cbe855c140d38787b6abf960f1d75ee409`,
`runtime_contracts.py`
`6d25c35718c056e9ee67dc8c0f132a650d1020a67cb9d9503a36092bba58b13e`, and
`supervisor.py`
`8b8700175e6673c3a6b652d4a93bd18b56def83dfa3ac4ec821d4ae6c554e873`.
The strict oracle is retained at
`docs/verification/evidence/stability-linux-diagnostic-startup-argv-empty-oracle-20260928-1.json`;
its current strict file SHA-256 is
`128b5665885bbebfabc68e59796a753f399066ca5d863d39bc4598750818c43b`; the
expected result is collector `PASS`, supervisor `COMPLETED`.

## Owner escalation closure (2026-09-28)

The owner is now a fail-closed, single-job controller. Before `create` it
requires a private 0700 root, a complete nonempty closure with unique absolute
paths and 64-hex digests, a durable nonce lease, and an exact zero-result
name/label lookup. It accepts exactly one returned container ID, rechecks the
same name and label, and records a fsynced append-only owner journal. Stop,
kill, and force-remove are independent bounded calls; absence is checked after
all three and the lease is retained on any uncertainty. Collector completion
is accepted only with the strict state object in the oracle and the retained
evaluation evidence. No stale container, replacement image, shell, wrapper,
network, compiler, guest, or Docker execution is authorized by this packet.

Runtime prerequisites remain independent review of the pinned image and full
loader closure, a fresh controlled root/snapshot, and an external wall
watchdog whose raw wait and live owner identity are retained. The focused
unprivileged fake-backend tests cover incomplete/duplicate closure rejection,
unique create ownership, argv isolation, and continued kill/remove cleanup.
