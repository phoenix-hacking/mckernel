# M14/M15 Stable Baselines and System Recovery

**Stabilization reference updated:** November 13, 2026.

**Historical evidence snapshot:** November 10, 2026, from published checkpoint
`e34b958d35d508d29fbfc9ee9b7efd868a331b80`.

This guide records the successful McKernel image baseline and the procedure for
building on it through small, verified Rust changes. The objective is to carry
passing work forward, shorten each repair/build cycle, and publish useful results
promptly.

[CAMPAIGN.md](../../CAMPAIGN.md) remains the sole active plan, status log, and
handoff. [AGENTS.md](../../AGENTS.md) supplies the current execution rules. This
document is a technical reference and a dated snapshot; current assignments,
resource availability, and milestone decisions belong in those existing records.

## Fast development workflow — November 13, 2026

This workflow uses the existing source checks, configured production cache and
retained c964/a2f/f133 cohort. It separates quick developer feedback, production
build/link evidence and native acceptance so a failed native operation does not
automatically become a ban on independent source work. On the workstation, real
shared ownership, account and resource restrictions still apply. The hosted CI
checks use their own isolated runner and perform no native-host action.

### Three levels of verification

| Level | Use it for | What the result establishes |
| --- | --- | --- |
| Focused source feedback | An edited behavior, ABI boundary, source selector or build rule | Only the named fixture/code-generation checks actually run; no full image, C retirement or native acceptance |
| Incremental production build | A changed compilation unit, selected provider, configuration or link input | Actual affected objects, selected definitions and link on the matching configured profile |
| Native integration | Changed deployed behavior and original M14/M15 runtime requirements | Only the actual matching application/device/lifecycle/restoration conditions observed |

Keep one compositor of each shared configured build tree. Prepare source in
isolated branches/worktrees, preserve unrelated edits, and avoid concurrent
writers to the same output directory. Promote passing artifacts only at the
level they actually proved; retain the last passing cohort during candidate work.

### Quick edit feedback with the existing runner

List the supported M14 modules without importing tests or probing compilers:

```sh
python3 -B scripts/run_m14_focused_checks.py --list
```

Run the relevant existing modules for a wait-result change:

```sh
python3 -B scripts/run_m14_focused_checks.py \
  --module scripts.tests.test_m14_f03_wait_results \
  --module scripts.tests.test_m14_f03_wait_c \
  --json-output /tmp/m14-wait-feedback.json
```

The selection is explicit and restricted to the existing allowlist. Duplicate
names are removed in its stable order. With no module option, the same complete
18-module suite runs. Results identify full versus subset selection and every
unselected module. A skip, missing input, expected failure, test/import error or
zero-test run is not a passing result. Result-write failure returns nonzero.

Use the matching test compiler/provider environment. The hosted workflows already
pin their tools; those focused HOST tools are distinct from the production
compute and Linux-module toolchains. Do not substitute a convenient installed
compiler for an operation's required production profile.

For M15, use the existing explicit component test modules appropriate to the
changed code, such as the create/cleanup, CLI, diagnostic or daemon fixtures.
They retain their own source/tool/provider requirements. The M14 allowlist is
not a universal M15 runner. An ordinary unittest exit of zero with skipped
checks is incomplete feedback and receives no qualification credit.

There is no automatic changed-path dependency selector or cached-pass inference.
Tests import helper modules and consume headers beyond their names. A selected
run is fast feedback; the unchanged full integration suite and original
qualification conditions remain available and required where applicable.
The source hashes in the runner are explicit result metadata, not a complete
transitive cache key or proof that every source stayed unchanged during a run.

### Preserve incremental outputs when configuration is unchanged

The two existing F06 metadata producers now compare each final generated output
with its current bytes before writing. Identical generation preserves the file
and its modification time. Changed output still updates normally, and all
existing source/profile validation remains in place.

This fixes a specific invalidation chain: CMake invokes origin generation during
reconfiguration; the generated origin header, CMake metadata and Rust metadata
are actual compile dependencies. Unconditionally rewriting identical bytes can
force a new whole-crate Rust object, an architecture C object and their image
link. Keeping unchanged generated files unchanged removes that avoidable
invalidation. It does not suppress a real source/header/compiler/provider change.

Retain the configured cache and let its genuine dependency graph choose work.
A changed Rust crate input can legitimately require the whole Rust object.
Do not clean the tree, copy old objects into a new input configuration, or rebuild
unchanged Linux modules merely because another Git commit was created.
Reconfigure only when the actual configuration or build-system inputs require it.

### Keep the CI foundation useful

The focused M14 workflow continues to run the full original allowlist and adds
small runner/metadata regression checks. The F06 workflow keeps its actual
C-ownership/debug-data qualification. Current-source fixture extraction follows
the source's real guards while preserving its semantic assertions.

Canonical-branch pushes and relevant source changes should reach the applicable
checks. Superseded isolated HOST runs may be cancelled without cancelling a
native or shared-workstation operation. Pure development Markdown changes should
not launch the unrelated frozen-host inventory suite; affected source, workflow,
tracker and verification-data changes retain their applicable validation.

The ordinary CI jobs already have 10- and 15-minute overall bounds and individual
compiler/test subprocess timeouts. The local test runner does not claim a hard
whole-suite/descendant deadline. A fast feedback failure should produce its
actual error and scope; it does not erase the passing production baseline.

### Rollout and measurement

Adopt these source/tooling changes through the normal compositor workflow without
modifying any in-flight frozen operation or restarting the saved campaign.
Keep current native custody recovery separate. A code review or hosted test pass
does not release its process, lease or resource ownership.

Check the actual pinned CI result before calling the integrated foundation
green. Measure subsequent selected-test elapsed time and a genuinely admitted
unchanged reconfigure/build before claiming a workstation speedup. The local
metadata regressions prove output reuse semantics; they are not a production
image-build timing receipt.

Implementation references: [focused runner](../../scripts/run_m14_focused_checks.py),
[runner regressions](../../scripts/tests/test_run_m14_focused_checks.py),
[metadata regressions](../../scripts/tests/test_m14_metadata_reuse.py),
[origin producer](../../scripts/derive_f06_origin.py),
[signal metadata producer](../../scripts/derive_f06_signal_metadata.py), and
[compute dependency rules](../../kernel/CMakeLists.txt).

## Current reusable baseline — November 12, 2026

**Evidence checkpoint:** `15788ef8281952baf261a789e9ee6c3583d36e87`.
Use the existing saved **c964/a2f image, f133 deployment manifest and successful
1f5f installed control package** at their proven scopes. The November 10 record
below remains a historical reference; its older image and C-symbol counts are
not the current baseline.

### The saved pieces and their exact scopes

| Layer | Current retained identity | What is established |
| --- | --- | --- |
| Compute source and image | Source `c964be3917c8f4c5031108aa927c84894584b667`; image `a2f00a6105f20642db8ef95fe12ade0873120594531f325ef363a4bb59f0ff8a`, 13,349,576 bytes | Qualified build/link and existing selected/emitted ownership evidence; current native acceptance remains open |
| Preserved build inputs | 25 separate read-only copies, including image/map and 13 qualified link constituents, configuration, recipes and dependencies | Independent saved copies match qualified inputs; original configured working cache remains intact |
| Matching module/deployment inputs | Manifest `f13363e5eb31efee749e6fc2c9f9ca83f8d2304318e1b31c63318c20411f49d7` | Existing exact module, archived-image and provider joins; use the matched cohort together |
| Successful installed control package | Generation `1f5f59d76bfeb43ce0f738ee07d7148fc5f7a69498273f0be498efcb4ea30cfd`; 30 files / 407,882 bytes | Full publisher completion, positive original waits/lease closure, and independently qualified physical readback |
| Changed reporting candidate | c309 attempt; 30-file / 420,488-byte candidate | Failed parent verification/acknowledgement stage; no promotion or current native acceptance |

Sources: [preserved cohort][current-preserved],
[independent preservation receipts][current-preserved-receipts],
[current ownership scope][current-ownership],
[module/deployment joins][current-modules],
[delivery manifest references][current-delivery], [successful publisher][current-publisher],
[physical package qualification][current-readback],
[current candidate result][current-candidate].

The successful publisher completed at **06:52:53 America/Boise / 13:52:53 UTC**
on November 12. Full Root, sudo, installer and keeper completion were positive,
and the lease was `VERIFIED_CLOSED`. The subsequent physical readback verified
the actual immutable 30-file package and catalogue
`cc6570624480a149fa5a8f448f09ac2f07f47d4057f15cf6696ff80576d5e479`.
These are installation facts, not a claim that the installed native helper has
passed every required application case.

### Where the baseline is retained

Current image and build-input snapshot:

```text
/home/holden/mckernel-work/m14-blocker-resolution-20261110/perf-core-integer-normal-image-p03-max-1/preserved-c964-a2f00a61-1/
```

Original configured working cache:

```text
/home/holden/mckernel-work/m14-blocker-resolution-20261110/compute-image-source-1/output/build
```

Matched deployment staging and its manifest:

```text
/home/holden/mckernel-work/scratch/m14-native-c964-a2f00a61-staging-parent/native-signal-c964-a2f00a61-stage-20261111-1/native-diagnostic-manifest.json
```

Successful installed control package:

```text
/var/lib/mckernel-code-1f5f59d76bfeb43ce0f738ee07d7148fc5f7a69498273f0be498efcb4ea30cfd/installed-source-1f5f59d76bfeb43ce0f738ee07d7148fc5f7a69498273f0be498efcb4ea30cfd
```

Retain the exact source/configuration/toolchain/provider bindings in the
[producer request][current-producer], [preserved manifest][current-preserved]
and [module/deployment joins][current-modules]. The compute and Linux-module
toolchains have distinct bindings; do not collapse them into one assumed compiler
profile. The 25-file snapshot preserves artifacts and required link inputs; it
does not replace the complete configured working tree at another location.

The staged archives and assets have recorded identities under the staging path
above. This guide does not establish a separate durable copy of every staging
asset. Workstation Root should preserve only assets not already covered by an
appropriate retained snapshot, using the existing preservation workflow after
current resource ownership permits it, and record that disposition. Reuse the
already-preserved image and receipts without another whole-tree copy or hash-only
qualification round.

### Reuse and promotion rules

1. **Retain build evidence when consumed build inputs are unchanged.** A change
   confined to the publisher, reporting code or documentation does not require
   rebuilding c964/a2f or its unchanged modules. Name the changed implementation,
   configuration, selector, compiler, ABI, provider or link input before scheduling
   a rebuild. Use the existing incremental target when one is actually required.
2. **Treat control-package changes at their own scope.** The reporting candidate
   changes two package modules while reusing 28 files. Its new installed generation
   needs its actual publication and matching readback; the old 407,882-byte
   readback cannot verify new 420,488-byte contents. Image and module evidence
   remains reusable where their inputs are unchanged.
3. **Keep successful and candidate generations separate.** Preserve the prior
   successful snapshot and configured cache. Promote only the affected baseline
   entry after its complete success, matching qualification and necessary cleanup.
   A candidate failure must not erase the previous saved artifacts or overwrite
   their success records.
4. **Reuse artifacts and proof, not live authority.** The consumed 1f5f nonce,
   historical grants, process identities and leases are evidence, not fresh
   issuance or execution permission. Current ownership/resource checks and native
   requirements still apply.
5. **Use exact failure locations to make repair finite.** The c309 parent groups
   result verification, proof-cap handling and ACK sending under one stage.
   Preserve a fixed first predicate/substage and exception class through the
   existing reporter, even when arbitrary text remains redacted. Keep original
   validation and custody behavior intact. The saved c309 fields have not
   established a schema/model/size mismatch; do not invent one or rerun an
   unchanged failing publication. [Source diagnosis][current-diagnosis]

Root remains the sole compositor and operator. The current repair and retention
instruction is [recorded in the mailbox][current-instruction]. The existing
[recovery guide](M14-M15-NATIVE-RECOVERY-20261112.md) supplies the scoped native
recovery details. This index introduces no new wrapper, retention service, test
quota, milestone criterion or accepted runtime result.

## System stabilization and host preservation — November 12, 2026

**Evidence cutoff:** checkpoint `2b0c30fa630a9a8ef9b3874e1bd52229596b4f3b`,
published at 14:40:51 America/Boise / 21:40:51 UTC. The procedures below preserve
completed work and define how to build on it. They do not certify unperformed
runtime tests. Current execution state and assignments remain in CAMPAIGN.md.

### New results to retain with the existing baseline

| Component | Reusable result | Boundary that remains open |
| --- | --- | --- |
| Failed c309 HOST attempt | Qualified cleanup released that attempt's HOST reservation. | This establishes no successful c309 publication. Raw UNKNOWN/error fields, the normal lease, held Root FD and historical keeper-wait records remain preserved. |
| Publisher failure reporting | Minimal reporting correction; six focused controls passed. Four failure stages are distinguished and secondary reporting errors retain the original failure. | Actual new publication, acknowledgement, complete waits/lease closure and matching physical readback remain required. |
| M15 F05 public `ihk_create_os` | Three cases passed: results 0, 7 and -5, exactly one close per case, owned descriptors closed and stdin restored. | Controlled lower-libc seams do not prove the real IHK device/backend or whole F05 behavior. |
| UTI production-crate metadata | Actual private production metadata compilation/typecheck passed; matching ABI35/C evidence reused. | No implementation-body, ACK/lifetime, final image or native acceptance is implied. |
| M14 TLS artifact prerequisites | Original C/assembly/payload steps retained; the missing static collector compile and three remaining passive checks passed. Collector: 1,064,312 bytes, static ELF64 x86_64, no interpreter or dynamic dependencies. | TLS runtime/restoration and whole functional acceptance remain open. |
| M15 F08 service context | Authenticated source member read and read-only context of the three real active udev units passed. | Package provenance, monitor visibility, processed events and provider lifetime still require their own evidence. |

Preserve each result's source, exact invocation, artifact identity, actual output,
qualification and cleanup together. The committed evidence is indexed by the
[21:04 execution report][stable-results-first] and the
[21:42 execution report][stable-results-second]. The [F05 actual output][stable-f05]
is a runtime result at its stated scope. The [TLS qualification][stable-tls],
[reporting qualification][stable-reporting] and [UTI qualification][stable-uti]
record their separate boundaries.

### Host preservation: keep what passed and close only the missing copy gap

The 25-file read-only c964/a2f snapshot and original configured cache above are
already preserved. The matched staging manifest and last successful 1f5f
installed package remain the anchors. Retention handoff `c85d` maps 54 paths to
existing protected artifacts and **six additional files totaling 67,930,797 bytes**.
At this evidence cutoff, those six new copies have **not** been performed.
A proposed destination or a GitHub commit alone is not a host-copy receipt.

The [exact f133 staging manifest][stable-stage] records the following six source
assets, whose total matches the pending retention tranche. Root must correlate
these with the existing c85d source/destination rows before copying; the published
manifest does not prove that any destination already exists. Paths below are
relative to the matched deployment staging directory listed above.

| Source asset | Bytes |
| --- | ---: |
| `base.cpio.gz` | 25,589,058 |
| `derived.cpio.gz` | 26,152,936 |
| `assets/bzImage` | 16,134,144 |
| `overlay-manifest.json` | 15,535 |
| `root-base.json` | 11,768 |
| `source/native_diagnostic_overlay.py` | 27,356 |
| **Total** | **67,930,797** |

Workstation Root completes the existing retention operation at the next compatible
HOST boundary, keeping the ready publication/native critical path moving:

1. Use the existing 54-path disposition and six-file copy list. Confirm exact
   current sources and the existing preservation operation against the saved
   review; resolve only missing entries. Reuse the 25-file snapshot and its
   receipts instead of making another whole-tree copy.
2. Preserve the six genuinely missing assets in a separate versioned directory
   under the existing workstation work area. Use the established copy workflow;
   do not overwrite the saved baseline, working cache, installed generation,
   dirty source edits or live operation state. Read-only snapshots must be
   independent copies rather than writable aliases or hard links to changing
   files.
3. Record actual source and destination paths, bytes, hashes and modes in the
   existing manifest/receipt format. Verify the newly copied bytes once against
   their already-qualified source identities and record completion/cleanup.
   A mismatch stays explicit and is repaired at that file's scope.
4. Save this guide in the canonical host checkout at
   `docs/development/M14-STABLE-BASELINE.md`. Place a reference copy beside
   the retained manifest, with its source commit and SHA-256. The adjacent copy
   must retain the absolute evidence links; repository-relative links resolve
   from the canonical checkout.
5. Preserve the recent F05, TLS, UTI, reporting and F08 source/results in their
   existing verified locations. Record the retained path and pinned evidence for
   each. Copy only any indispensable artifact that the disposition proves is
   otherwise temporary or missing; report that delta rather than starting an
   unbounded inventory.
6. Return a host receipt naming the resolved checkout/guide path, adjacent guide
   path, preservation manifest, copied file count/bytes, checks performed and any
   unresolved item. Commit and push the guide and compact evidence references.
   Keep the large binaries and private operational material in their established
   host locations.

The host preservation is complete only when its actual copy/readback receipt is
available. This is a finite retention task, not another image build, new daemon,
new proof framework or replacement acceptance checklist.

### Reuse, repair and promotion procedure

**Start from the saved cohort.** Identify the retained c964 source, a2f image,
f133 matched deployment inputs and successful 1f5f control package by their full
recorded identities. Preserve current source successors and dirty work; these
retained identities are reuse references. Keep their source/configuration, compute toolchain, Linux-module
toolchain, provider and ABI bindings separate and exact. A compatible cached
build can be reused; a compiler/container tag alone is not an immutable identity.

**Classify a change before running anything.**

| Changed input | Necessary work |
| --- | --- |
| Documentation or status text | Save/review the text and verify publication; no image or native rerun. |
| Publisher/reporting module | Check the changed reporting behavior, then publish and physically qualify the new control generation. Reuse unchanged image/modules and completed focused controls. |
| One application, collector or test artifact | Rebuild/check only its affected target and dependent observations; retain passing unchanged steps. |
| Kernel source, selected provider, configuration, ABI or link input | Incremental rebuild of affected targets and the required linked-image/ownership checks, followed by matching affected functional evidence. |
| Missing/corrupt saved file | Restore that exact artifact from a qualified retained copy; reassess only evidence whose identity or custody changed. |
| Runtime failure with unchanged artifacts | Preserve the first actual failure, process/lease/resource state and original captures. Repair and qualify that scope before another operation that depends on it or its retained resources. Independent eligible work can continue under its own actual admission. |

Keep candidate outputs separate from the last passing version. Promote only the
layer whose required execution, readback and cleanup have actually passed. A
reporting failure must not demote an unchanged image; a successful compile must
not promote a native runtime result. Before a repeat, name the changed input or
resolved failure that makes it useful. Repeated green suites and blind retries
do not improve stability.

For the current reporting correction, reuse the six passed focused controls and
the prior eight unchanged supervisor controls. The next useful proof is a normal
new publisher run with actual acknowledgement, original waits/lease completion
and physical qualification of its new 30-file package. Bind both CORE and provider
generation to that successful package before separate native admission. Keep
c964/a2f/f133 unchanged unless a real dependent input changes. The old successful
407,882-byte readback cannot validate the failed 420,488-byte candidate or a later
generation with different contents.

### Controller, guardian and mailbox recovery

Use the existing launcher/guardian/mailbox stack and saved campaign state. Record
the currently installed entry point, resolved state directory and real unit names
in the host receipt. Keep the original failure log, stop reason, last completed
action, outstanding owner/resource state and next repair visible.

A healthy controller continues work. Inspect status before any restart; an idle
worker, completed child turn or retained historical error is not by itself a
current controller failure. If a component fails, the existing supervisor/guardian
recovers only the affected eligible component and records the reason and result.
Independent ready M14/M15 work can continue within the actual shared resource
limits while a failed lane is repaired.

Recovery must retain the same saved campaign, dirty work, finite credit-run ID,
cumulative budget and unresolved ownership. Do not use an unqualified generic
start command that overwrites the saved engine configuration, creates a new
credit-run identity, launches a duplicate controller or treats an old lease as
fresh authority. Genuine service/account/resource holds remain visible and are
reported through the existing mailbox instead of being hidden by restart loops.

Keep the 10-minute mailbox check and the existing SENT, RECEIVED, ACCEPTED,
WORKING, BLOCKED and RESULT distinctions. A receipt confirms delivery; only an
actual host result confirms that the guide/copies or repair are complete. A block
report identifies the first concrete error, its owner, the smallest next repair
and the precise user input needed, if any. The status text records baseline
identities, current candidate, last successful action and remaining original
M14/M15 conditions. Use the installed supported status/recovery commands and their
saved arguments; current CAMPAIGN.md remains the active handoff.

#### Supported inspection and saved recovery inputs

From the existing workstation checkout:

```sh
cd /home/holden/mckernel
python3 -B scripts/start_os_overnight.py status
python3 -B scripts/run_os_goal.py --progress
python3 -B scripts/run_os_goal.py --status
```

These report the actual unit names, state directory, current supervision/activity
and saved stop evidence. Follow the returned `state_directory` and
`state.json`'s actual log paths. The usual state directory is
`/home/holden/mckernel/.git/os-autopilot`; a linked worktree may have a different
resolved Git common directory. [Status implementation][stable-service]
[Launcher status modes][stable-launcher]

| Evidence | Path relative to the resolved state directory |
| --- | --- |
| Saved campaign and current log references | `state.json` |
| Watcher state/history | `watcher.json`, `watcher.jsonl` |
| Guardian state/checkpoint/saved arguments | `guardian.json`, `guardian-checkpoint.json`, `guardian-engine-config.json` |
| Last stop and stop history | `latest-stop.json`, `stop-events.jsonl` |
| Human-readable status and publication receipts | `status.txt`, `status-text-state.json`, `status-publish.json` |
| Mailbox receipt/command history | `mailbox-state.json`, `instructions/` |
| Existing cumulative credit-run record | `credit-runs/7c6ef3604bfb4008a917bba8cfb6cfaa.json` |

`python3 -B scripts/start_os_overnight.py status-text` refreshes the derived local
status text without starting model work or publishing remotely. It does write
local telemetry. Inspect the real guardian/engine unit names returned by
`status` with `systemctl --user status` and `journalctl --user -u`; do not
guess the path-dependent unit suffix. Treat private logs/configuration as host
state and publish only the compact evidence needed for diagnosis.

For explicit continuation after a resolved stop, the existing mailbox supports a
new, unedited authorized-user comment in PR #3 with `/mckernel-resume` alone on
the first line. This goes through the guardian and its saved engine configuration.
It does not clear unresolved ownership or other real holds.
[Mailbox parser][stable-mailbox]

For a necessary local relaunch, the campaign records the reviewed command at:

```text
/home/holden/mckernel-work/relaunch-preparation-20261112T093247Z/launch-command.txt
```

Reconcile that saved command against the current engine configuration, original
Root/objective and finite credit-run record before using the normal front door.
The complete argv and numeric budget are host-only; do not reconstruct them from
defaults. Do not use `prepare` as a reason to stop a healthy owner: its default
launch inspection can legitimately report that ownership is occupied.
Do not restart the guardian as routine maintenance: its termination handler
requests a checkpoint/stop of model work.
[Start/config handling][stable-service] [Guardian handling][stable-guardian]

### Definition of a usable stable baseline

A reusable baseline has retained artifacts and build inputs, matching source and
toolchain/configuration identities, passing evidence at a stated scope, an intact
previous good version, and a written recovery route. Stability is maintained by
changing one dependent scope at a time, preserving failures, restoring only the
affected component and publishing completed results promptly.

This checkpoint remains **105/156** counted checks, **M14 70.00%** and
**M15 74.59%**. These are dated figures. Host preservation and documentation do
not create milestone credit; the remaining native functional and original whole
requirements still need their actual acceptance evidence.

## Historical baseline — November 10, 2026

The remaining sections retain the original snapshot and general iteration
procedure. For the current artifact identities, use the index above.

## 1. Verified baseline identity

The real named `mckernel.img` target built and linked successfully. Its generated
configuration and ABI inputs were produced by the matching configuration operation.
The image, linker map, constituent objects, recipes, and dependencies were then
preserved before the next source change. [Build result][image-result]
[Configuration qualification][configure-proof] [Preserved baseline][baseline-manifest]

| Property | Recorded value |
| --- | --- |
| Image build source | `20a7bd5e72afcbe639d3a55fa0d1eada6dce4777` |
| Published evidence checkpoint | `e34b958d35d508d29fbfc9ee9b7efd868a331b80` |
| Configuration completed | November 10, 2026, 11:15:14 a.m. America/Boise / 18:15:14 UTC |
| Image build and metadata completed | November 10, 2026, 11:42:58 a.m. America/Boise / 18:42:58 UTC |
| Artifact | `mckernel.img` |
| Image size | 10,295,032 bytes |
| SHA-256 | `a54197260991e86de0a1a9b37ebd29a42c087503d16d871beb6a1bd2781dc3a0` |
| ELF | ELF64 executable; two load segments plus a note segment |
| Entry | `arch_start` at `0xfffffffffe83cb10` |
| Named undefined symbols | None in this final image |
| Host interpreter | None |
| Recorded build outcome | Build and passive metadata phases passed; client waits/streams joined and owned containers closed |

The ELF and symbol records establish the entry, segments, and symbol state.
[ELF metadata][image-elf] [Symbol table][image-symbols]

The recorded build command was:

```sh
cmake --build /work/output/build --target mckernel.img --parallel 1 --verbose
```

This is the command from the matching container/environment in the saved execution
record. Its `/work/output/build` directory is environment-specific. Reuse the
recorded source/configuration/toolchain bindings when preparing the next operation;
this command alone is not a complete setup recipe for an arbitrary checkout.

The image build source, evidence publication, and this documentation change are
distinct. A later documentation commit does not establish that a new image was built.

## 2. What this baseline establishes

The baseline establishes a working physical configuration/build/link path for the
recorded source and profile. It provides a concrete reference image against which
the next Rust selection and provider changes can be checked.

The image contains **Rust, C, and assembly**. At this snapshot, the final symbol
table and linker map identify these remaining live C function-symbol rows:

| Source owner | Live C function-symbol rows |
| --- | ---: |
| `kernel/syscall.c` | 42 |
| `arch/x86_64/kernel/syscall.c` | 5 |
| **Total** | **47** |

These rows are emitted symbols, not a count of 47 missing algorithms or 47
independent tasks. Existing Rust implementations still require correct selection,
integration, and final ownership proof. The baseline configuration records
`ENABLE_RUST_F06_SYSCALL_WHOLE=OFF` and
`ENABLE_RUST_M14_SYSCALL_ADAPTERS=OFF`. Changing selectors requires the corresponding
complete implementations and matching ABI/provider checks. [Linker map][image-map]
[Symbol table][image-symbols] [Configuration qualification][configure-proof]

Complete Rust/assembly project ownership, matching behavior, deployment, native
boot/application/lifecycle evidence, and original M14/M15 acceptance remain open.
Full image ownership qualification and its independent review were also pending at
this evidence checkpoint. Here, **passing baseline** means the recorded build,
link, and passive metadata result; it does not imply native runtime acceptance.
[Pinned campaign][campaign-snapshot]

## 3. What to preserve and reuse

The workstation preservation root is:

```text
/home/holden/mckernel-work/m14-blocker-resolution-20261110/compute-image-source-1/stable-baseline20a7-1/
```

The [preservation manifest][baseline-manifest] is the authoritative list of exact
paths, sizes, and hashes. It includes:

- The image and its linker map.
- All eleven constituent image objects, including the whole Rust object.
- Generated configuration headers and linker script.
- `CMakeCache.txt`, `compile_commands.json`, the exact link recipe, and Rust
  dependency records.

The valid working cache was left intact. The preserved snapshot remains recoverable
while the next candidate is prepared. These binary artifacts are retained on the
workstation; the repository publishes their evidence and identities.

Reuse passing source, ABI, provider, and functional evidence when its actual inputs
remain applicable. Let the build system rebuild changed compilation units and their
dependencies. A previously passing object is not interchangeable with an object
from a different source/profile merely because both link.

## 4. The fast iteration procedure

Use the existing campaign workflow and one integrator for shared build outputs.
Independent implementation, focused test preparation, and review can proceed in
parallel within the currently available resource and credit limits.

1. **Choose a coherent change on the M14 critical path.** Identify the required
   behavior, current provider, proposed Rust owner, and affected callers. Group
   tightly coupled selectors and providers into a consistent candidate.
2. **Prepare against the preserved baseline.** Record the candidate source and
   changed inputs. Carry forward unchanged contracts and passing results. Preserve
   unrelated dirty work and the last passing artifact.
3. **Review the changed behavior and ownership.** Resolve concrete type, lifetime,
   ABI, selector, and dependency questions from the actual source and build profile.
   Reuse prior review where its inputs remain valid.
4. **Perform the normal incremental build.** Use the matching configured environment
   and genuine generated dependencies. Keep one owner of shared build outputs.
5. **Check the affected boundary and final image.** Verify the intended Rust entries
   are actually selected, replaced C definitions are absent, provider ownership is
   unique, affected ABI and behavior checks pass, and the image still links with its
   real dependencies. Preserve unchanged technical evidence.
6. **Promote the passing checkpoint at its demonstrated scope.** Record the source,
   configuration, artifact identity, result, and remaining conditions. Preserve the
   new passing baseline without erasing the earlier one or unfinished work.
7. **Publish and continue.** Commit and push the coherent, reviewed change and its
   essential evidence. Update the existing campaign/ledger as justified and start
   the next ready dependency.

This compounds work because each successful increment becomes a reusable starting
point. Measure the benefit through actual iteration times and completed original
conditions; the baseline alone does not establish a numerical speedup.

## 5. Reuse and invalidation

Use the real dependency graph to determine what must be rebuilt and rechecked.
This table guides the existing checks; it introduces no additional acceptance gate.

| Changed input | Work to refresh |
| --- | --- |
| Implementation or consumed behavior | Rebuild affected units; run relevant functional and error-path checks |
| Types, layout, headers, or generated ABI | Recheck affected layouts/calling contracts and dependent consumers |
| Compiler, target, options, feature flags, or selectors | Reconfigure/rebuild as required; refresh affected ABI/code-generation evidence and dependent joins |
| Provider identity, C/Rust exclusions, or link inputs | Verify actual unique ownership, replaced C removal, and the affected final link |
| Deployment artifacts, runtime dependencies, or platform | Refresh matching deployment/native evidence where required by the original conditions |
| Documentation or unrelated edits with unchanged build/behavior inputs | Retain unaffected technical qualification |

A changed Rust compilation unit may still require rebuilding as a whole. Selective
validation means preserving unrelated proof, not manually injecting stale objects,
ignoring dependencies, or assuming an old hash describes newly emitted code.

## 6. Failure recovery

A failed candidate leaves the last passing baseline available. Use the existing
repair record to capture the exact command, source/profile, timestamp, exit or
error, log/artifact path, responsible agent, and next action.

The assigned agent should diagnose and correct the specific failure, obtain review
where needed, and rerun the affected build/check. Repeated failure with no new
evidence should trigger a second diagnosis or a revised repair plan. Keep independent
ready work moving while that repair proceeds.

Preserve actual process/resource ownership, unknown outcomes, service/access limits,
the finite run budget, and any later user pause or stop. An unavailable external
input should be described precisely with the affected operation and supplying owner.
Routine source-derived contracts remain engineering work. Use current `AGENTS.md`
and `CAMPAIGN.md` for live limits rather than treating this snapshot as permission
to change them.

## 7. Publication and progress visibility

Publish completed, verified work once its own required review is complete. Keep
pending qualification explicitly marked instead of withholding completed build
results while unrelated review or later milestone work finishes.

The existing progress report should show:

- The last passing source and artifact identities.
- The latest command outcome, actual completion time, and useful log reference.
- The current candidate, owner, next action, and any specific delay.
- Successful iteration time, including review/integration/publication wait where
  it explains the pace.
- Actual C ownership removed or changed, with the affected symbols rather than a
  count alone.
- Newly verified original conditions and the conditions still open.

Preserve the mailbox's sent, received, accepted, and waiting distinctions. Receipt
and controller acceptance indicate delivery; execution results establish progress.
Agent activity alone does not close a requirement.

## 8. Immediate continuation from this snapshot

At the pinned checkpoint, the genuine Rust `do_syscall` and `interrupt_syscall`
changes had been independently reviewed and privately composed. They were not
selected in the successful baseline image. The next planned candidate combined
those changes with the reviewed eligible host-cleanup/shared-context selectors,
followed by an incremental image build and actual Rust-entry/C-exclusion/ABI/provider
qualification. [Pinned campaign][campaign-snapshot]

Use the current campaign for later assignments and results. Retain the original
behavior and acceptance criteria, with original M14 acceptance before final M15
acceptance. Documentation and partial links receive no unsupported milestone credit.

For orientation, the evidence checkpoint recorded:

| Measure | November 10, 2026 snapshot |
| --- | ---: |
| M14 verified checklist | 51.48% |
| M15 verified checklist | 57.01% |
| Counted checks verified | 77 / 156 |
| Accepted M14 files / integrations | 4 / 6; 0 / 3 |
| Accepted M15 files / integrations | 1 / 8; 0 / 4 |

These are dated checklist figures, not estimates of engineering time or an assertion
that either milestone is accepted. The current report and canonical ledger carry
subsequent changes. [Pinned ledger][ledger-snapshot]
[Live status][live-status]

## Evidence references

- [Published evidence checkpoint][evidence-commit]
- [Image execution result][image-result]
- [Configuration qualification][configure-proof]
- [Preserved baseline manifest][baseline-manifest]
- [ELF metadata][image-elf], [symbol table][image-symbols], and [linker map][image-map]
- [Campaign at the evidence checkpoint][campaign-snapshot]
- [Progress ledger at the evidence checkpoint][ledger-snapshot]
- [Live progress and agent status][live-status]

[evidence-commit]: https://github.com/phoenix-hacking/mckernel/commit/e34b958d35d508d29fbfc9ee9b7efd868a331b80
[image-result]: https://github.com/phoenix-hacking/mckernel/blob/e34b958d35d508d29fbfc9ee9b7efd868a331b80/docs/verification/m14-current-image-20261110/image/execution/RESULT.json
[configure-proof]: https://github.com/phoenix-hacking/mckernel/blob/e34b958d35d508d29fbfc9ee9b7efd868a331b80/docs/verification/m14-current-image-20261110/configure/qualification/QUALIFICATION.json
[baseline-manifest]: https://github.com/phoenix-hacking/mckernel/blob/e34b958d35d508d29fbfc9ee9b7efd868a331b80/docs/verification/m14-current-image-20261110/PRESERVED-GREEN-BASELINE.json
[image-elf]: https://github.com/phoenix-hacking/mckernel/blob/e34b958d35d508d29fbfc9ee9b7efd868a331b80/docs/verification/m14-current-image-20261110/image/metadata/image-elf.stdout
[image-symbols]: https://github.com/phoenix-hacking/mckernel/blob/e34b958d35d508d29fbfc9ee9b7efd868a331b80/docs/verification/m14-current-image-20261110/image/metadata/image-symbols-relocations.stdout
[image-map]: https://github.com/phoenix-hacking/mckernel/blob/e34b958d35d508d29fbfc9ee9b7efd868a331b80/docs/verification/m14-current-image-20261110/image/metadata/image-map.stdout
[campaign-snapshot]: https://github.com/phoenix-hacking/mckernel/blob/e34b958d35d508d29fbfc9ee9b7efd868a331b80/CAMPAIGN.md
[ledger-snapshot]: https://github.com/phoenix-hacking/mckernel/blob/e34b958d35d508d29fbfc9ee9b7efd868a331b80/docs/verification/m14-m15-closure-progress.json
[live-status]: https://github.com/phoenix-hacking/mckernel/blob/codex/mckernel-control-mailbox/status.txt

[current-preserved]: https://github.com/phoenix-hacking/mckernel/blob/15788ef8281952baf261a789e9ee6c3583d36e87/docs/verification/m14-current-image-20261111/perf-supported-default-1/preserved-cohort/PRESERVED-COHORT.json
[current-preserved-receipts]: https://github.com/phoenix-hacking/mckernel/blob/15788ef8281952baf261a789e9ee6c3583d36e87/docs/verification/m14-current-image-20261111/perf-supported-default-1/actual-image-qualification/PRESERVED-COHORT-AND-INDEPENDENT-RECEIPTS.json
[current-ownership]: https://github.com/phoenix-hacking/mckernel/blob/15788ef8281952baf261a789e9ee6c3583d36e87/docs/verification/m14-current-image-20261111/i01-ownership-manifest-e1-1/independent-review/REVIEW.json
[current-modules]: https://github.com/phoenix-hacking/mckernel/blob/15788ef8281952baf261a789e9ee6c3583d36e87/docs/verification/m15-i02-matched-artifacts-20261112/INDEPENDENT-EXACT-THREE-AND-COHORT-JOINS.json
[current-producer]: https://github.com/phoenix-hacking/mckernel/blob/15788ef8281952baf261a789e9ee6c3583d36e87/docs/verification/m14-current-image-20261111/perf-supported-default-1/actual-producer/REQUEST.json
[current-publisher]: https://github.com/phoenix-hacking/mckernel/blob/15788ef8281952baf261a789e9ee6c3583d36e87/docs/verification/native-code-publication-successor-20261112/ROOT-EXEC-COMPLETION.ACTUAL.json
[current-readback]: https://github.com/phoenix-hacking/mckernel/blob/15788ef8281952baf261a789e9ee6c3583d36e87/docs/verification/native-strict-code-readback-20261112/ACTUAL-PHYSICAL-30-QUALIFICATION.json
[current-candidate]: https://github.com/phoenix-hacking/mckernel/blob/15788ef8281952baf261a789e9ee6c3583d36e87/docs/verification/native-reporting-c309-saved-result-20261112/SAFE-SAVED-RESULT-PROJECTION.json
[current-diagnosis]: https://github.com/phoenix-hacking/mckernel/blob/15788ef8281952baf261a789e9ee6c3583d36e87/docs/verification/native-reporting-c309-failure-20261112/SOURCE-DIAGNOSIS.json
[current-instruction]: https://github.com/phoenix-hacking/mckernel/pull/3#issuecomment-6834295484
[current-delivery]: https://github.com/phoenix-hacking/mckernel/blob/15788ef8281952baf261a789e9ee6c3583d36e87/docs/verification/m15-i01-deployed-20261112/WHOLE-REVIEW.json

[stable-results-first]: https://github.com/phoenix-hacking/mckernel/pull/3#issuecomment-6835906353
[stable-results-second]: https://github.com/phoenix-hacking/mckernel/pull/3#issuecomment-6836731718
[stable-f05]: https://github.com/phoenix-hacking/mckernel/blob/2b0c30fa630a9a8ef9b3874e1bd52229596b4f3b/docs/verification/m15-f05-public-create-20261112/ACTUAL-OBSERVER.stdout
[stable-tls]: https://github.com/phoenix-hacking/mckernel/blob/2b0c30fa630a9a8ef9b3874e1bd52229596b4f3b/docs/verification/m14-tls-compiler-partial-20261112/missing-static-passive-correction-1/QUALIFICATION.json
[stable-reporting]: https://github.com/phoenix-hacking/mckernel/blob/2b0c30fa630a9a8ef9b3874e1bd52229596b4f3b/docs/verification/native-result-predicate-reporting-20261112/QUALIFICATION.json
[stable-uti]: https://github.com/phoenix-hacking/mckernel/blob/2b0c30fa630a9a8ef9b3874e1bd52229596b4f3b/docs/verification/uti-private-DATA-metadata-20261112/QUALIFICATION.json

[stable-stage]: https://github.com/phoenix-hacking/mckernel/blob/2b0c30fa630a9a8ef9b3874e1bd52229596b4f3b/docs/verification/native-admission-debug-20261111/a2f-actual-stage-and-new-generation-1/stage/actual-output/native-diagnostic-manifest.json
[stable-service]: https://github.com/phoenix-hacking/mckernel/blob/2b0c30fa630a9a8ef9b3874e1bd52229596b4f3b/scripts/os_goal_service.py
[stable-launcher]: https://github.com/phoenix-hacking/mckernel/blob/2b0c30fa630a9a8ef9b3874e1bd52229596b4f3b/scripts/run_os_goal.py
[stable-mailbox]: https://github.com/phoenix-hacking/mckernel/blob/2b0c30fa630a9a8ef9b3874e1bd52229596b4f3b/scripts/os_goal_mailbox.py
[stable-guardian]: https://github.com/phoenix-hacking/mckernel/blob/2b0c30fa630a9a8ef9b3874e1bd52229596b4f3b/scripts/os_goal_guardian.py



## Current host adoption receipt

Recorded by the canonical Root at 2026-11-12T23:03:24.111814+00:00. CAMPAIGN.md remains the sole active plan.

The reviewed PR8 guide (bd35ed0c; 39,532 bytes; SHA256 ccb1c3dd3e5bf51f2d1d5759a3b796946bc2c755c0a7b85e6a9e5558ae110a9f) was adopted without a branch reset or service restart. This appended receipt records newer completed outcomes; dated pending sections above remain historical.

The six missing f133 staging assets were copied once through the corrected, independently reviewed operation. All six copies, totaling 67,930,797 bytes, have independent inodes, matching recorded digests, read-only modes and positive source/FD/process/stream bookends. Existing25 snapshot payloads were neither rehashed nor recopied; their metadata and the original cache/stage stayed unchanged. Actual preservation manifest: `/home/holden/mckernel-work/resume-20261112T094452Z-c964-a2f-staging-retention-gap-1/preserved-stage-missing-f133-1/PRESERVED-COHORT.json` (16,549 bytes; SHA256 c903e207c0d13a4a6b15880b2b1aeef5e62bbdb9d4d468f8551b014aef1e426c). Qualification: fa66550258e62598d5c3f836522cb2df8b605a9e2c4bf6fe208bed1e13253c13. The earlier pre-copy reference-shape failure and its separate retirement remain preserved.

TLS0891 staging is also qualified at Q2b5b25e6/Root622b9e7c: derived CPIO 26,166,986 bytes/57a5ea56, raw overlay9d4417f4, native DATA9103ae49, with the qualified TLS83e5 and static collector04ddd. This is staging, not TLS runtime/restoration. F08 alias ownership is installed-database metadata only (Q02cb48b2/Rootd3dbe76a); monitor context/readiness/events remain separate.

The last successful normal publication remains1f5f. Failedc309 and issued/nonreplayable29ed were not promoted. The29ed newest-account refusal and unavailable failed tuple/reason remain intact; any future publication needs independently reviewed fresh current-owner input through every unchanged account/credit/ownership/source/lease/resource guard. Native12/source/global UNKNOWNs and the excluded collector remain binding. Original progress stays105/156, M14=70.00%, M15=74.59%; no acceptance credit comes from preservation.

Canonical host guide: `/home/holden/mckernel/docs/development/M14-STABLE-BASELINE.md`. An identical read-only reference is saved beside the retained manifest at `/home/holden/mckernel-work/resume-20261112T094452Z-c964-a2f-staging-retention-gap-1/preserved-stage-missing-f133-1/M14-STABLE-BASELINE.md`. The existing guardian, watcher, mailbox interval, saved Root/goal and finite credit run were preserved.

