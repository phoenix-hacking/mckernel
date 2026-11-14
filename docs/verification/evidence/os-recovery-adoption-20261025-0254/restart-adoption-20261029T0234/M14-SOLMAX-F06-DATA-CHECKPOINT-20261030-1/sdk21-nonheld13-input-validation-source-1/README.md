# SDK13 input validation: private source only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This module never launches a process, creates a container, grants a lease, decides
root authority, proves live controls, verifies Docker image bytes, establishes
CPU6 exclusivity or infers global current-free. The old Root70 UNKNOWNs and held
request exclusions remain. The owner must independently check current root-sealed
request/review/module/driver bindings, source-map review, resource and daemon
continuity at pre-create and pre-start. Image-internal SDK tools require their
own genuine image/tool observation; manifest or image digest is not that proof.

Public interface (errors are ValueError or filesystem/JSON errors, all denial):

* `validate(request, *, profile_path, request_path, source_map_path) -> bound`.
  `profile_path` is exact 3e6d2491 profile; `request_path` is exact 6cce26d0
  source-only proposal, not root release. Actual `request` supplies `profile_sha256`,
  `proposal_sha256`, `image_id`, `source_map_path`, `source_map_sha256`, `mounts`
  (JSON lists `[host, target, readonly_bool]` in exact proposed order), `commands`
  (the exact profile list), `work_root`, `owner_evidence_root`, `attempt_root`,
  `lease_path`, and other owner/release fields. The core hash excludes only
  `compile_only_release`, matching old `_request_core_hash`. Work and evidence,
  attempt and lease must all be fresh; work must be the profile's fixed scratch
  path. Attempt and lease are direct children of evidence; evidence parent must
  already be a private user-1000 directory. Work and evidence must be disjoint
  from each other and mounted source paths. Other private path relationships and
  required ownership of newly created objects remain owner obligations.
* After exclusive work-root mkdir and before populating it, call
  `bind_work(bound, request, created_identity)` using the exact lstat tuple
  `(st_dev, st_ino, st_mode, st_uid, st_gid, st_nlink, st_size, st_mtime_ns,
  st_ctime_ns)`. It binds dev/inode/mode/uid/gid; outputs can subsequently change.
* `revalidate(bound, request)` repeats all byte/inventory checks and request core
  binding and checks the original directory identity. Before bind it requires
  work to remain absent; afterwards it requires the bound identity. Use immediately
  before Docker create/start and after the run; these checks do not cover daemon,
  mount effect, races after check, process ownership or root release.

Returned keys include `profile_sha256`, `proposal_sha256`, `request_sha256`,
`source_map`, `source_identities`, `commands`, `outputs` (four container paths),
`mounts` (30 proposed triples including `/work` rw), `readonly_mounts` (29 triples),
`source`, `work`, `owner_evidence`, `attempt`, `lease`, `snapshot`, source paths,
and `work_identity`. These are actual input observations only. Additional driver
and profile mounts must be independently checked by the integrating owner; do not
mistake the 30 proposed mounts for the owner's complete Docker specification.

The source map is a separately reviewed, root-release-bound JSON, absent today:
`schema` = `mckernel.sdk13.source-map.v1`, `profile_sha256` and `proposal_sha256`
are exact, `toolchain_lock` = `{path, sha256}` refers to actual bytes having the
profile's full lock digest, and `trees` has exactly `/src`, `/src/kernel/rust`,
`/nightly`, each `{root, entries}` with exact profile root and complete entries.
Each entry is `{relative, kind: "dir"}`, `{relative, kind: "symlink", target}`
(which must resolve within that tree), or `{relative, kind: "file", bytes,
sha256}`. Every file, directory and symlink must appear exactly once. The Rust
subtree has 156 total regular files (145 `.rs` currently), not 156 `.rs` files.
All source tree bytes, identities, generated config/header/origin, eight object
mounts and toolchain metadata are re-read and compared; unsupported special files,
escaping links, duplicates, changed paths or mismatches deny. Exact selector and
link argv use the untouched profile, preserving whole-signal pairing and five
absent overlapping cfgs. The independently reviewed map must also establish
source6153 ancestry and the authoritative 156-file closure, lock semantics and
header/tool origin; a self-reported map digest cannot establish those facts.
The profile's lock digest has no located direct-file receipt in this bounded task:
if the reviewed lock is not a file hash, the explicit `toolchain_lock` requirement
must be corrected against actual evidence, not manufactured. Likewise, unsupported
real source symlink or file forms need reviewed correction, never silent omission.

`test_sdk13_input_validation.py` contains small deterministic positive/negative
source fixtures. It is prepared but unrun; no source-only output indicates actual
validation, SDK build, ABI/native proof or production acceptance.
