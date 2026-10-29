Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The b09 successor cannot receive source approval. Its bounded restart discards
an already observed compiler publisher when a later, unrelated PID disappears.
The exact synthetic counterexample is retained alongside this design. No b09
operation ran. Its fetched source and all Root3 failure evidence remain frozen.

Immediate publisher refusal alone does not preserve the full original process
predicate. The existing normal validator also rejects any owner/waiter PID or
descendant, including PID reuse. The custom validator rejects forbidden process
group/session IDs. These negative observations must survive aborted attempts.

Use one source successor with monotone negative observations inside the same
root census command. Keep maximum3 whole attempts for each required snapshot,
the narrow ENOENT predicate, diagnostic stderr, exact stdout schema and two
complete accepted snapshots. Do not retry the external command or transport.

Exact implementable deltas:

1. Change `process_source(normal,p)` to receive the already authenticated `b`
   and the exact prior command PID list. Derive the same sets used by the
   existing validators: waiter seeds are PIDs from `b.prior_actors` plus
   `b.new_known_actors` plus previous command PIDs; related seeds additionally
   contain `b.holder_pid`; forbidden PID/group/session seeds additionally
   contain `b.runner_pid`. Serialize these sorted integer sets into the generated
   root source. Do not infer births or introduce broad name exemptions.
2. Update the three source-generation contexts coherently. `Actual.census`
   already computes `prior_pids`; pass those with `self.b`. The `Actual.call`
   exact-root-command comparison derives the same list from the existing
   command children before the next spawn. In `validate_result`, generate the
   expected source separately for each PROC receipt using all earlier receipt
   PIDs, instead of computing a single code string for all PROC receipts.
   Preserve the current10-element census argv, challenge/caller and every other
   receipt/role predicate. Current root census client itself is not a prior PID.
3. Allocate one monotone PID-to-observed-PPIDs map outside both snapshot loops.
   After each first stat has passed the existing prefix/field/numeric checks,
   and before racy cmdline/exe/recheck reads, record PID/PPID and inspect its
   parsed PGID/SID. Refuse immediately for a forbidden PID/PGID/SID. Recompute
   the existing owner/waiter descendant fixed point over all observed parent
   pairs from every attempt, and refuse if it intersects observed PIDs.
   This covers out-of-order rows and chains split across attempts. Recording
   facts before a later disappearance is conservative; it supplies no positive
   clearance. Bound the map by the existing maximum4096 entries times6 attempts.
   Optionally reject an enumerated forbidden PID before its first stat, since
   the unchanged validator deliberately rejects PID reuse without birth relief.
4. As soon as a noncaller row has readable argv and exe and satisfies the exact
   existing publisher condition (including the existing caller-parent-sudo
   exception), raise a distinct ValueError. Do this before the second stat read
   so the publisher's own disappearance cannot erase its observed executable.
   Keep the existing original publisher predicate and later stat/birth checks;
   do not add an exception for newly seen compiler/helper processes. Check a
   parsed caller birth mismatch immediately as a fatal negative fact too.
5. The wrapper catches only the existing narrow FileNotFoundError/ENOENT case;
   no ValueError, publisher/known-actor/descendant/group refusal, permission,
   malformed data or PID-birth race can trigger a retry. Successful snapshots
   still return their own complete rows/groups. Keep all final parent-side
   existing validators unchanged as the acceptance check. Partial/monotone
   facts never become snapshots or clearance evidence.

This adds explicit checks to the old scan, so stop claiming the scan-body AST
is wholly unchanged. Bind the precise additions and demonstrate that every
original check remains. The monotone map is a local functional census detail,
not a new persistent framework or runtime authority.

Focused tests using the existing fake-proc leaves:

- Existing ordinary stat/cmdline/exe/recheck disappearance cases must still
  yield exactly two fresh complete snapshots, bounded attempts and retained
  diagnostics. Exhaustion and all existing malformed/permission/wrong-path,
  caller/birth/boot cases remain fatal.
- The retained150-rustc then200-ENOENT counterexample refuses immediately, as
  does a publisher whose own second stat disappears. No clean stdout follows.
- A known historical PID, reused known PID, prior-command PID and forbidden
  PGID/SID observed before another missing path all refuse without retry.
- A descendant refuses even when rows arrive child before parent. A parent
  fact from an abandoned attempt plus its descendant from a later attempt
  also refuses; no negative fact can be lost across first/second phases.
- A genuinely unrelated disappearing process may be retried; unrelated rows
  are not rejected merely because they were observed in a discarded attempt.
- Check exact generated source against the expected prior-command prefix at
  all three PROC receipt positions and wrong PID lists refuse. Preserve all
  other executor function/transport/Docker/once-claim changes at minimal scope.

Root3 release/output remain consumed failures. The latest genuine Root boundary
is5dea, with all72 nonces, native history, recovery custody and originalUNKNOWN
unchanged. Any later operation still requires newly reviewed/fetched exact
source, fresh payload/output/admission/resources and parent joins. Current-free
and native acceptance remain false/open. No implementation is edited here.
