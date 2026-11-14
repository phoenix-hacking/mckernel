Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Scope: functional OS 35-check work plus separate active M14 Rust/reviewed-assembly cutover. This change earns no native or whole-file retirement acceptance.

The failed consumer and producer disagree only at the owner schema admission surface: the source producer emits `mckernel.m14-combined-production-thin-inputs.v1`, while owner `_validate_request` only admits its four predecessor schemas. The authenticated provenance implementation already declares the M14 type as `THIN_SCHEMA`, requires the exact candidate/IHK identities and exact canonical manifest SHA256 b47cf0f2a65aa90f2e010d717bf381c85adf063b68951fd8e53682cb87f27be6, and validates all materialized source files/modes, tracked links and retained IHK metadata. Relabeling that producer would defeat its explicit lineage. The smallest coherent correction is three new type memberships in the owner: general schema admission, explicit derivative identity admission, and mandatory supplemental gitlink admission.

Finite `_validate_request` contract inspected in full before execution:

| Stage | Actual bound requirement retained |
| --- | --- |
| Request/resources | Exact request type; candidate/IHK/image identities; jobs <=4; timeout; aggregate memory; zero memory-backed allocation; disk floors and live device identities. |
| Namespace/identity | Existing empty mode-0700 work/evidence parents; absent output/evidence/attempt and receipt; exact source/disk inode identities; disjoint roots. Pure validation creates none. |
| Released programs/manifests | Exact driver/provenance/host-owner constants and file hashes; source/toolchain manifests hash-bound; source candidate/IHK identities. |
| Source type/derivative | Adds exact M14 type while preserving explicit source_derivative_sha256, materialization_sha256 and base_git_commit_only scope equality. Full-tree requests still reject thin fields. |
| Toolchain | v2 root inventory/translation; receipt/evidence/library closure; host Git hash; mounted tools; kernel closure; exact nightly; sealed environment and PATH. |
| Supplemental source | Exact libdwarf manifest/base cross-reference, Git commit/tree/index/worktree, file bytes and metadata; new M14 branch requires manifest and root. |
| Raw materialization | Existing authenticated provenance validates its pinned M14 canonical document and every materialized file/link/mode/metadata entry. |
| Backup/mount/exclusion | Original backup identity and full inventory; exact mount mapping; active non-retired common path; disjoint source/toolchain/backup/gitlink/evidence roots. |
| Final admission | Existing authenticated host owner read-only resource and mount/allocation measurement; expected aggregate/zero-memory-backed checks. |

Pure validation dependencies are regular-file reads and hashes, directory inventories, read-only Git observation through the authenticated executable, procfs/mount observation and host filesystem measurement. It imports authenticated shared-entry/host/provenance source but calls no acquisition, Docker, root helper, compiler, build, guest or probe. `ImageOwner.run` is deliberately never invoked: it acquires the shared heavy token before validation, and the failed old token remains parent/reviewer-owned.

The owner source still uses the preserved old common-exclusion binding solely to reproduce the exact request contract. It is a source candidate, not a released next build. The next real build must get a new parent-owned attempt/common/lease/work/evidence namespace, exact successor owner/request/source bindings, fresh identities/capacity, reviewed retirement of the old shared token, and independent execution release. Do not replay the consumed original attempt or source-profile-only acceptance. Existing image10972/SDK5 acceptance is unchanged; no compiler or guest has run this successor.

Interpreter binding is part of the consumer contract: the actual frozen build uses `/home/holden/anaconda3/bin/python3` (3.9.12). The first ordinary fixture mistakenly used `/usr/bin/python3` (3.8.10), progressed beyond the corrected admission and failed at unchanged provenance `Path.is_relative_to`. That fixture failure and all captures are retained. The single bounded correction changes only the ordinary fixture interpreter to the actual build interpreter; it does not alter provenance or raw-source validation.
