Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is a second diagnostic source delta for the e49 dead_caller_absent full-proc
observer. The observed legacy PROC_CODE failure was a different collector path;
34 completed dead_caller checks passed in the actual run. This packet does not
claim that dead_caller_absent caused the actual failure.

The baseline fixture extracts the actual e49 functions and models an ordinary
PID exiting on the second stat read. All proc reads, UID and observer facts are
mocked. Source tests never import or invoke the live cleanup controller.

The focused functions permit at most three fresh pair attempts, retaining each
failed partial and discarding every partial from success. A retry needs exact
second-stat ENOENT after complete bounded stat, cmdline and executable capture,
PID/birth/group/operation argv checks and publisher classification. Only ordinary
root-level processes (parent0/1), excluding PID1 and the pinned observer, qualify.
First-stat/cmdline/executable ENOENT and unknown parent chains remain hard refusals.
This conservative boundary cannot classify an unseen command as nonpublisher.

Parsed caller/owner/waiter IDs, descendants and original groups are hard refusals
before followup reads. The same frozen legacy publisher predicate is reused;
known publisher discovery and operation namespace argv are hard before a later
exit. Seen births are retained across retries, so PID reuse is refused. The root
observer's full birth/credentials identity is pinned before/after each pair and
after retryable churn. Malformed data, permission errors, wrong error paths,
unknowns and persistent churn remain hard. The original complete two-snapshot
absence validator and full-EOF/16MiB total capture ceiling remain unchanged.

Only focused function replacements and a delta manifest are supplied. No full
cleanup controller is cloned, no current root process/FD is changed, no workload
or admission is run, and no source acceptance or execution release is implied.
Actual root keeper adoption requires the independent reviewer and Root to bind
these exact source hashes to its existing phase and ownership controls.
