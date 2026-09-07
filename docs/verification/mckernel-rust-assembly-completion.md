# McKernel completion requirement: Rust and assembly

User clarification, 2026-09-07: the entire McKernel kernel implementation must
be Rust or assembly. This is a required part of the active standalone HPC OS
goal, alongside native Linux 6.12 integration. It supersedes earlier wording
that excluded McKernel's remaining C implementation from the current goal.

## Required final implementation

The final McKernel image and the code implementing its kernel behavior must
originate entirely from Rust or reviewed assembly. This includes boot/init,
memory management, scheduling, exceptions/interrupts, syscalls, communication,
drivers, ABI entry points, and linked support/runtime code. A C wrapper,
fallback, helper, embedded library, or out-of-image project C service cannot
supply a missing part of that implementation. Compiling C to assembly or
renaming its object file does not satisfy the requirement.

Rocky/Linux remains the separate Linux control kernel. Its existing C/Rust
implementation and ordinary Linux services remain part of that boundary. The
project's native IHK/SMP/mcctrl modules retain their existing Rust implementation
requirement and reviewed assembly/ordinary-Linux-FFI rules in `final-push.txt`.
Public ABI declarations, linker scripts, generated non-executable metadata,
build/verification tools, and application code are not kernel implementation
language conversions. Supported applications can continue using C or other
languages through the preserved ABI.

Assembly is an allowed implementation language and is accounted for separately
from Rust. Every executable contribution must have a known source/build origin;
unknown provenance blocks completion. Linker padding and non-executable data
must be identified explicitly rather than used to inflate a language score.

## Preserve and integrate the existing Rust

Start with the repository-wide [reuse map](rust-reuse-plan.md): the McKernel
core, existing mcctrl Rust bodies, user tools, and native policy/runtime modules
have different consumers and execution contexts. Retain useful bodies and
current consumers; adapt the missing interfaces and ownership boundaries.
Replacing a C body requires an active replacement symbol/build path and the
relevant equivalence and runtime evidence. Reference C can remain during
migration for comparison, but cannot participate in the final production
McKernel implementation or its runtime dispatch paths.

## Required acceptance checks

These checks are additional to the native host-module tracker. They do not
change its 10,000-point denominator or turn its percentage into whole-OS
completion. The active goal is incomplete until both sets of requirements pass.

| Check | Acceptance condition | Current state |
| --- | --- | --- |
| MK-LANG-001 | Inventory every linked executable contribution and remaining C implementation/bridge; bind image, map, objects, source, configuration, and compiler inputs. | IN_PROGRESS: matching source-24a151fe compatibility image/map/report retained. |
| MK-LANG-002 | Preserve existing Rust bodies and consumers; record a verified Rust/assembly replacement for every retired C implementation path. | IN_PROGRESS: baseline and additive CPU reuse verified; remaining C replacements open. |
| MK-LANG-003 | Build the production McKernel with all kernel implementation paths supplied by Rust/assembly, including selected library/runtime support. | TODO |
| MK-LANG-004 | Inspect the final image and dependency/dispatch closure; reject C-origin executable contributions, hidden C fallbacks, and unknown source origins. | TODO |
| MK-LANG-005 | Pass ABI/equivalence checks and boot/workload/rollback/shutdown tests through the native Rocky/Linux 6.12 host modules. | TODO |
| MK-LANG-006 | Package and reproduce the exact tested Rust/assembly McKernel and native host artifacts; retain source-to-binary evidence. | TODO |

The retained [source-24a151fe linked report](compat-24a151fe-linked-rust.json)
records 614,183 Rust-owned executable bytes out of 783,847 (78.354960%). The
remaining 169,664 bytes combine C, assembly, other origins, and padding; that
remainder is not a measured C-only debt. This existing image does not yet meet
the clarified Rust/assembly-only completion requirement.
