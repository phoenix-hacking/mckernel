**Decision: CLOSE_FAILED_OBSERVER_CAPTURE_ONLY_NO_EXECUTION_RELEASE.**

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

- **Confirmed failure:** [`observe_current_pass_image_retirement.py:245`](/home/holden/mckernel-work/host-preparation/m07-sigill-successor-native-data-preparation-20261022-1/actual-terminal-preparation-1/bound-terminal-source-correction-1/observe_current_pass_image_retirement.py:245), `main`, subscripts `current_live_postjoin`, whose exact consumed case value is `null`. The preserved traceback reports `TypeError`. Correction requires a genuine hash-bound postjoin reference and explicit input validation, followed by independent review; this decision releases no retry.
- **Observer closure accepted:** PID/PGID `3035822`, start ticks `44972881`, directly joined with exit `1` after `0.140694955` seconds. The consumed capture tail performs `child.wait()`, stream flush/fsync/close, then `killpg(pid,0)` absence checking. [Raw terminal events](/home/holden/mckernel-work/host-preparation/m07-sigill-successor-native-data-preparation-20261022-1/actual-terminal-preparation-1/ACTUAL-FAILED-OBSERVER-TOOL-OWNED-TERMINAL-PAIR-1.raw.jsonl) match the paired JSON and identify one completed failed tool item. Status and stdout/stderr hashes match retained bytes.
- **Fresh corroboration:** At `2026-10-22T15:12:47Z`, on the recorded boot, read-only procfs inspection found `/proc/3035822` absent, no members of group `3035822`, and zero unreadable process-stat entries. The observer output directory was absent.
- **Effects before failure:** The capture wrapper changed its own affinity/umask and created capture evidence. The observer set its process limits, validated release/source inputs, and loaded definitions/constants. Failure preceded root mutex acquisition, observation commands, inventories, output creation, and cleanup.

This closes the failed observer child/group/streams only. It establishes no retained-build physical clearance, reserve mutation authority, cleanup authority, native acceptance, or service retry. Outer OS PID/start/group fields remain unspecified; tool process ID `6205` is not treated as a Linux PID.

No files were written: the reviewer instruction prohibits edits and assigns decision recording to the dispatcher.
