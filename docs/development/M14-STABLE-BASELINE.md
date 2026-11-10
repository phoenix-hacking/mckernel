# M14 Stable Image Baseline and Fast Iteration

**Evidence snapshot:** November 10, 2026, from published checkpoint
`e34b958d35d508d29fbfc9ee9b7efd868a331b80`.

This guide records the successful McKernel image baseline and the procedure for
building on it through small, verified Rust changes. The objective is to carry
passing work forward, shorten each repair/build cycle, and publish useful results
promptly.

[CAMPAIGN.md](../../CAMPAIGN.md) remains the sole active plan, status log, and
handoff. [AGENTS.md](../../AGENTS.md) supplies the current execution rules. This
document is a technical reference and a dated snapshot; current assignments,
resource availability, and milestone decisions belong in those existing records.

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
