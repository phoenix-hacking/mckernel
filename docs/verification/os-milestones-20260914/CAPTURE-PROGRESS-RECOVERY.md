# Capture progress and recovery visibility

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The October 21 cleanup completed both ownership-record releases, then its final process census hit a disappearing `/proc` entry. It entered an intentional quarantine hold. The capture had already saved the quarantine marker and traceback, but its terminal-only output hid them while waiting for child exit. The original failed attempt, journal and quarantine remain evidence.

The launcher now supports bounded, nonterminal progress for future operations. The running campaign uses its already admitted reader; changing the Python source does not reload the resident launcher. The old frozen capture is unchanged. The new `scripts/capture_os_critical_operation.py` is an opt-in template requiring its own exact source/operation binding and normal admission before use. It retains its qualified local base dependency and does not authorize a workload by itself.

After a compatible launcher starts, the coordinator can register each explicitly named fresh capture directory through the existing instruction queue:

```bash
python3 -B scripts/run_os_goal.py --instruct 'Register visibility for the prepared capture; execute only after the existing release and registration acknowledgment.' --capture-progress-directory /ABSOLUTE/FRESH/CAPTURE_DIRECTORY
```

Wait for the saved acknowledgment matching the current thread, worker and run before invoking that capture. A resident launcher without the advertised capability rejects registration. Ordinary instructions retain their existing behavior. Definite registration rejection preserves its original item and receipt without blocking later valid instructions; uncertain RPC delivery and service-policy, authentication or billing stops retain their existing behavior.

The capture emits at most two progress records: child join pending, and an observed quarantine marker. Terminal stdout remains a single final JSON result. Progress is neither completion nor physical clearance. It never releases resources, kills a child or grants execution authority. Heartbeats read only the two registered files. A new launcher archives old-instance hints before clearing its current view.

Before a critical wait, bind exact capture paths into the admitted reader. On a quarantine marker, classify recovery as required and use the qualified bounded diagnostic route immediately; do not wait for child exit to discover the hold. Report the last known stage and elapsed time for prolonged unknown-stage waits. Preserve locks, owners and original evidence, and use exact-state reconciliation. Do not infer a hang from healthy long execution, replay cleanup, synthesize completion, or clear locks speculatively. Carry the accepted process-census repair into future source construction and verify that current binding.

Focused regression command (one controlled child at a time; coordinate with exclusive workload admission):

```bash
taskset -c 0 prlimit --as=268435456:268435456 --cpu=10:10 --fsize=1048576:1048576 --core=0:0 -- python3 -I -B -m unittest discover -s scripts/tests -p 'test_os*capture_progress.py' -v
```

The tests exercise actual extracted methods, controlled child joining, queued registration and fake RPC. They do not run a campaign, privileged cleanup, guest, or full production capture admission. Their scope does not replace future exact source/release review.
