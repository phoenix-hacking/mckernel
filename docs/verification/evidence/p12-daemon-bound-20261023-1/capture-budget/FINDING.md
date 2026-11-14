Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: final external capture storage remains unbound; do not release runtime from this result. No native, application, milestone or Rust-retirement credit.

The exact nine-file cohort is COUPLED-SOURCE-COHORT.json in the retained sibling p12-coupled-resource-review-20261023-1 directory. Its long_transport.py pin is 2964902b8b2465c40c4ee5c37fa161507426cc6695757cc46177dbea1b4b2075; owner pin is c342d1492e957c3ebdfc142b7fce7d10fbadcae8b64565f4d7ad0e336f1219ec. No pinned source changed.

Source chain and copies:

- long_transport.py:25-31 reserves seven attempt slots at384MiB,512MiB retained owner queue,32MiB metadata and96MiB Docker logs:3489660928 bytes total.
- native_diagnostic_container_owner.py:661-668 bounds the entire pending evidence queue to512MiB and4096 entries. _call:742-745 queues command stdout/stderr; _inner_result:1013-1024 queues inner-result and five retained capture copies. Those retained copies are already covered by512MiB and must not be counted again as an independent external serial copy.
- _flush:683-710 writes queued bytes after retirement plus a result record outside the queue. The32MiB metadata term remains for block/directory slack, attempt metadata, lock/status and control records; this review does not prove an exhaustive physical filesystem metadata bound.
- The owner main:1215-1239 emits no success capture and permits Python's ordinary traceback on failure. It does not bound external stdout/stderr storage or bind a capture wrapper.
- COUPLED-HOST-FILEBOUND-HANDOFF.json explicitly makes final external captures conditional. Its accepted_capture reference identifies the ordinary check helper, not a released final root wrapper. The actual LONG stage/manifest remain NULL. Neither a final external path/volume, independent stream limit, command count nor retained-copy count is bound.
- Accepted run_two_commands_source_bound_corrected.py:76-87 opens direct regular stdout/stderr files, then delegates limits to the caller. :139 hashes with32MiB maximum only after join; this is a post-capture assertion, not an independent write limit. Its ordinary main's32MiB FSIZE (:184) supplies its enforcement. LONG requires384MiB FSIZE and cannot inherit this lower hard limit.

Concrete arithmetic, retaining current96MiB logging provision provisionally:

| External design | Additional external payload per retained set | Total logical HOST growth |
| --- | ---: | ---: |
| One command, direct-file accepted helper, child FSIZE384MiB |805306368|4294967296|
| One command, independently enforced32MiB per stdout/stderr |67108864|3556769792|
| Same independently limited pair with two simultaneous retained copies |134217728|3623878656|

These additions preserve the entire existing32MiB metadata allowance. They do not take undocumented unused space from it. The first row assumes no separately retained duplicate. For N commands and C simultaneously retained complete copies, reserve N*C*2*stream_cap, plus separately bounded control files and filesystem allocation slack. A recursive archive or repository evidence copy is a new retained allocation unless proven a non-copy and accounted on its actual filesystem. Admission must use this full term before any producer begins; subtract only already measured allocation when calculating remaining growth. On HOST these bytes add directly to host_required_bytes; scratch copies also increase scratch_input_growth_bytes and the relevant backing-growth accounting. No historical free-space value proves current admission.

Actual-body check:

`taskset -c 7 python3 -I -B docs/verification/evidence/p12-daemon-bound-20261023-1/capture-budget/check_capture.py`

PASS: exact accepted helper body spawned an ordinary Python child with8KiB FSIZE. Both streams attempted16KiB writes; actual retained files were8KiB each,16KiB combined, and the helper's32MiB post-check accepted them. Direct child joined, process group absent, streams closed. The real long_transport.growth_requirements body confirmed that current admission adds only the existing logical_growth_bytes. The test scales enforcement down; it neither creates32/384MiB files nor proves the final privileged wrapper. See receipt.json and actual-helper-check-1/. One candidate passed; zero failed candidates and zero bounded corrections. Previous64 modeled observations/Docker96MiB review finding remain unchanged.

Repair specification:

1. Bind final wrapper source/argv, output paths and filesystems, one-command count, one retained capture set, per-stream independent bound and control/metadata bounds in a new typed source/release cohort. Add an explicit external_capture_bytes term to transport/profile/admission instead of folding it into metadata. Preserve child384MiB hard FSIZE and strict workload oracles.
2. A pipe drainer may preserve at most32MiB per stream, record overflow as failure, and continue draining/discarding excess until the owner completes its own retirement. Never accept truncated output. Record bytes received/discarded, overflow stream, direct-child join, stream closure and owner retirement evidence. Any cancellation path needs the owner's existing handled-signal and persistent-lease semantics.
3. Existing bounded_command is not a drop-in root wrapper: :478-519 handles output overflow through CommandLedger.retire/CommandChild.retire, whose :367-382 uses group SIGKILL. That can bypass a live DiagnosticOwner's container retirement. Introducing a wrapper with suitable lifecycle semantics needs focused independent review; this lane stops before adding that new lifecycle machinery.
4. Test positive output, stdout overflow, stderr overflow, simultaneous streams and nonzero exit with ordinary children first. Then review the exact owner-aware cancellation/retirement path before any root/guest release. Existing source-only passing check supplies no such release.

Separate unresolved conditions remain: daemon/log physical bound, exhaustive metadata/physical allocation bound, first matched V3 complete restoration, actual LONG stage/manifest and fresh aggregate identity/capacity/lease/retirement release. No Docker, root, QEMU, compiler, network or archive-hash operation was performed here.

Dispatcher-requested private accounting correction:

`long_transport.accounting-proposal.py` and `accounting-proposal.diff` preserve the original source and propose a separate typed external capture description: one command, two stream slots,384MiB each, one retained copy. This adds805306368 bytes to3489660928, giving4294967296 bytes (4GiB). Child FSIZE384MiB and32MiB metadata remain unchanged. The final wrapper is not instantiated in the supplied cohort; therefore EXTERNAL_CAPTURE_BINDING remains NULL and validate_release refuses immediately, before any filesystem admission or launch-related access. The proposal must not be installed as an execution release. No source pins/cohort or accepted evidence were changed.

`taskset -c 7 python3 -I -B docs/verification/evidence/p12-daemon-bound-20261023-1/capture-budget/check_accounting.py`

PASS: actual private growth_requirements adds the full4GiB; external slots/copies/size and metadata are exact; file_limit(True) stays384MiB; unbound validate_release fails before filesystem access. See accounting-receipt.json. This accounting candidate has zero failures and zero corrections. It does not supersede the separate daemon finding.

Finite physical allocation premise, still requiring final profile validation: both384MiB streams align to4096-byte allocation units, so their payloads require no tail-rounding beyond805306368 bytes when the actual output filesystem uses4096-byte units. More generally reserve2*(allocation_unit-1) bytes of stream tail slack, and separately bound directory entries, inode/extent/allocation metadata and control-record blocks within the retained32MiB allowance or enlarge that allowance. A fresh f_frsize observation alone does not prove filesystem internal metadata bounds. Arbitrary copy-on-write, snapshots, compression, delayed allocation, other writers or an unbounded retained-copy count invalidate this premise. The final root release must identify the actual output filesystem and applicable finite allocation premise; this source-only proposal does not claim an unconditional physical bound. No cleanup credit is assumed.

User-authorized142GiB preparation successor:

Read AGENTS.md's2026-10-23 growth instruction and USER-AUTHORIZED-GROWTH-PROPOSAL.json. Retained the110GiB accounting proposal byte-for-byte. New `long_transport.accounting-142GiB-proposal.py` changes only the exact backing geometry to152471339008 bytes and its diagnostic string. `accounting-142GiB-proposal.diff` contains that delta; `142GiB-SOURCE-SUCCESSOR.json` pins authorization, original and successor bytes and records downstream pending pins.

`taskset -c 7 python3 -I -B docs/verification/evidence/p12-daemon-bound-20261023-1/capture-budget/check_142.py`

PASS8 actual live_growth reader-body observations using substituted external path/stat/open/statvfs observations: accepts142GiB with correct UUID/mounted device/loop backing/output filesystem and42GiB full sparse gap; refuses110GiB,143GiB, wrong UUID device, wrong loop backing, wrong output geometry, nonregular backing and the obsolete10GiB gap for a fixture allocated100GiB. Opened fixture descriptors are closed on all applicable paths. `142GiB-reader-receipt.json` records every observation. This tests the actual reader with fixtures, not fresh live identity or capacity and not real root admission. Geometry successor candidate0failures/0corrections. No resize/root/Docker/guest/canonical mutation.

The private successor retains the earlier96MiB daemon-log provision; the dispatcher must merge its142GiB geometry into the independently repaired daemon/profile successor rather than overwrite that newer work. Regenerate coherent nine-file source/install pins, actual source copies/stage/manifest, LONG profile/release source_sha256 and execution templates after the merge. Final external capture binding remainsNULL, so no runtime authority is created. Only dispatcher-owned independently reviewed maintenance may grow scratch; all original110GiB sources/evidence remain retained.
