# Stopped-rescue source/context review — 2026-09-15

Status: **FAIL_SOURCE** remains appropriate after attempt 2 made no file change.
The parent-rescuer design is viable with one clarification: the rescuer observes
the collector's direct children, never waits/reaps fixture PIDs, and the collector
retains both fixture waits.

Correction dependency order:

1. Define READY/STOP_ARMED and rescue-journal schemas in packet/tests first. READY
   binds request nonce plus full collector/leader/child identities. Adoption is the
   child's PPID transition to the stopped collector; ECHILD is only the rescuer's
   final collector-ownership check. Preserve raw collector 256, fixture 9/9,
   EINTR/signal 15, absolute five-second stop and two-second descendant deadlines.
2. The fixture forks one child, uses a private initialized-child handshake, emits
   one bounded READY on stderr, then both block without forks or waits. It never
   emits STOP_ARMED or stops itself.
3. Generate the collector hook definition before exact `int main(...)` and invoke
   it after the unique pump/exec/leader-observation sequence. Read bounded retained
   stderr, verify nonce/identities, sealed exec, live unreaped/nonwaitable leader,
   no failure, and exact 384-byte setup plus EOF. Validate setup once, fsync the
   prerequisite artifacts/events/directory, emit STOP_ARMED, then raise SIGSTOP.
   Remove the earlier setup-packet injection. `validate_setup()` is stateful, so
   final validation must skip an already successful early validation. Regenerate
   the patch from exact source; do not guess contexts.
4. Replace rescuer C entirely. Its main forks/execs the collector with default
   SIGCHLD and no competing waiter; observes collector raw stop 4991; verifies
   actual direct children/startticks; kills leader, observes zombie and grandchild
   adoption, kills the now-direct child, never waits for either; then TERM/CONT,
   reaps collector raw 256 and observes ECHILD. Journal and fsync every identity,
   action, deadline, wait and recovery transition.
5. Build/profile wiring must compile and bind the local fixture and rescuer, update
   every file/dependency/output/command matrix and constrain selectors. Implement
   one consistent `run_case(case,collector,fixture,root,supervisor,rescuer)` API;
   supervise the rescuer, whose outer wait is zero, while the journal supplies the
   collector wait. Bind literal invocation/environment and every binary.
6. The oracle independently parses strict duplicate-rejecting request/setup,
   retained streams/events, collector report, rescue journal and outer report. It
   enforces identities, order, fsync durability, adoption, waits, EOFs, omissions,
   deadlines and cleanup. Handwritten summaries are never acceptance inputs.

Only after exact source pins and substantive negatives pass may independent review
consider a build packet. No build/root execution or application/production credit
is released.
