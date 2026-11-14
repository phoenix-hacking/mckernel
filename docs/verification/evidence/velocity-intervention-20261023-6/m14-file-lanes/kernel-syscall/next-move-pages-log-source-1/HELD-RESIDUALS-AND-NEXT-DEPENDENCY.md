Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The private move_pages_log_bridge port preserves the five original messages, ignored error argument, unknown-event behavior, call count and byteexact C fallback. It reuses existing Rust kprintf. Source-only differential and real-TU ABI witnesses exist; actual results remain null. No second executable queue was created. The af2c signal production queue remains the one prepared production queue. Untested sys_move_pages source43a60 remains excluded from its proof.

Already-held residuals and rough difficulty (not a fresh inventory, completion estimate or numeric ETA):

| Named body/boundary | Existing Rust coverage and current proof | Rough remaining difficulty |
| --- | --- | --- |
| move_pages_log_bridge | New private Rust export uses existing Rust kprintf and existing five constants; not compiled/tested. Exact C fallback retained. | Low; typed variadic output parity and actual selected caller/link still need proof. |
| sys_move_pages plus five adapter bodies | Private source43a60 reuses unchanged existing Rust allocation/verify/node/lock/SMP/copy/free orchestration; no actual fixture yet. | Moderate with uncertainty in real provider/ABI closure; architecture SMP handler remains C. |
| syscall_forward_sigaction_update_bridge / existing forward_sigaction_update body | Existing C provider retained for passed Rust do_sigaction. Partial context initializes only arg0..2; existing real Rust getter exports deliberately read just those fields. | Moderate to high uncertainty; preserve Linux forwarding, returned-error handling and partial-context behavior before port. No new port here. |
| do_prlimit64 and syscall_do_prlimit64_bridge | Existing Rust validation/resource mapping and frontends; full resource copy/forwarding/process hash/IRQ/lock/rlimit lifetime orchestration still live C. | High, especially ownership and early-error ordering. |
| do_execveat and sys_execveat | Existing Rust execveat helper/frontends; full live exec lifetime and filename pre-read semantics not ported here. | High; lifecycle/provider closure and partial-context forwarding require focused evidence. |
| reset_cputime / set_cputime | Existing Rust time/timer primitives; live monitor/time conversion/counters/itimers/signal/timer orchestration not retired here. | Reset comparatively small; set_cputime high and uncertain. |
| arch move_pages_smp_handler (F06 boundary, outside this lane) | Untouched architecture C callback retained by source43a60; no new coverage inferred. | Cross-lane dependency; difficulty not established here. |

Accepted signalfd is canonical. Pending-mask/sigsuspend/do_sigaction have actual 5712 controlled equivalence pairs and 34 ABI/layout checks; full-current78 production consumption is queued af2c, not claimed completed. Existing F06 ptrace definitions in canonical policy3ef are preserved. None of these leaf/source results retires kernel/syscall.c as a whole. GCC14/default image, linked-current selection and native evidence remain open for new bodies; diagnostic and Linux control-plane callbacks remain explicit debt. engineering_percentage=null.

Next dependency: execute the already-frozen af2c production queue only on a fresh root grant, then root centrally merges independently accepted fragments. The formatter's future consumer must show exact C/Rust bytes and call count, selected real-TU ABI/allocated caller reference, unique Rust definition and eventual default/native proof. A future combined move-pages merge must replace the source43a60 selected C logger body with this Rust declaration; its f03_move_pages_log link_name alias can resolve the new export. Do not silently apply overlapping C region patches.
