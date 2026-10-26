Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Retained-input diagnostic PASS on CPU2, one process, 0.28 seconds. No compiler,
link, Docker, native operation, signal, cleanup or canonical mutation ran.

Actual defects remain the original three duplicate definitions of resource_set_list,
resource_set_lock and runq_reservation_lock, plus the two Rust division-panic imports.
The existing three-file correction already addresses all five: pair process.c with
MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE under linux-6.12 and use the prepared checked
signed division returning EINVAL for zero/MIN/-1. No replacement port was needed.

The new diagnostic cross-binds the exact retained link.txt with its 11 input rows,
confirms exactly nine reusable prefix objects and two required replacement objects,
confirms the original duplicate provider pairs from actual ELF symbols, confirms the
prepared process command differs by exactly one macro, and confirms both panic
imports are absent from the already accepted corrected default Rust object. Exact
process argv, Rust command, link argv and original correction paths are in RESULT.json.

Next executable build work after actual physical/admission clearance is the existing
incremental driver: compile only selected process.c and whole actual-default Rust,
then raw-link the exact eleven inputs. Preserve source6153, nine prefix objects and
SDK21. The HOST corrected Rust result does not remove the mandatory fresh default
object ownership/provenance gate. The source-ready Source38 later coherent graph
cannot replace current290 inputs without its separate source/default binding.

Source38 GNU_RETAIN loss stays OPEN. Its four 32-byte descriptors lose 0x200000
through HOST binutils2.34 partial linking. No retention/GC guard or flag was waived.
The exact selected-default link currently has no --gc-sections, which does not itself
prove Source38 retention semantics or qualify its final allocation/consumer proof.

Blocker: retained root1060806/parent1060803 native custody and positive physical
reconciliation; root alone owns recovery and actual new workload admission. No
additional dependency-ready production edit exists within this private write set.
New default/native/file closures: zero.
