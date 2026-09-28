# startup.argv-empty: Linux diagnostic execution packet

**Status: DRAFT — independent review required.** This packet authorizes no
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
canonical host paths (no shell, `LD_*` override, or unreviewed substitute) and
record hashes, modes, ownership, device/inode, size, mtime and ctime. The
captured interpreter/DSO hashes must match. A mismatch is a hard stop. The
collector’s documented limitations (pathname substitution, provenance, and
interpreter/DSO closure) are packet gates, not waived risks.

## Canonical request (to be created only after review)

Create strict JSON at `<root>/request.json` with exactly the collector schema:

```json
{"schema_version":1,"kind":"linux-diagnostic-request","case_id":"startup.argv-empty","source":{"path":"<root>/startup.argv-empty.c","size":777,"sha256":"1786835eccf68588b5def92a056c4bc83b10a6ce7163778b59dd4c5481b7b465"},"oracle":{"path":"<root>/oracle.json","size":687,"sha256":"0be4d0cbd276aa77e381de0734ccfcc77304b9f9fa5d00b576c69fb01326e6d8"},"payload":{"path":"<root>/payload","size":20528,"sha256":"ff227c83b2da598110768e13f5e042b437e049659706b56079cc73f7c818a836"},"argv":["app","A","","B"],"executable_path":"<root>/payload","cwd":"<root>","env":{"LC_ALL":"C","PATH":"/usr/bin:/bin"},"stdin":null,"timeout_seconds":30,"cleanup_timeout_seconds":15,"stdout_limit_bytes":4096,"stderr_limit_bytes":65536,"application_acceptance":false,"mckernel_application_executed":false,"attempt":"<root>/attempt-001"}
```

`argv[0]` is deliberately `app`; the empty argument is the third literal
element. `stdin:null` means collector-enforced `/dev/null`. `<root>/attempt-001`
must be absent before launch and its parent must remain the same 0700 controlled
directory. The collector invocation is exactly:

```text
python3 -B <collector-absolute-path> --request <root>/request.json
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

1. Read-only checks found current `/lib64/ld-linux-x86-64.so.2` and
   `/lib/x86_64-linux-gnu/libc.so.6` hashes different from the retained closure;
   a matching controlled execution root/closure is not presently identified.
2. Independent review must confirm the canonical request, closure, root
   ownership, limits, and publication/teardown plan before release.

Until both are cleared, do not restore, invoke, or execute this packet.
