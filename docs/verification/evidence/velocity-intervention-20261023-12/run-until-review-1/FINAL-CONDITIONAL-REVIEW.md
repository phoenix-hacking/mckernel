# Delivery-window bridge: final narrow source review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
**Accept the final frozen source for one root-granted offline regression run.**
Production arming remains conditional on the actual test result, the tiny real
host capability observation described below, and root's owned installation/
current identity review. No live action was performed by this reviewer.

The external frozen packet SHA is
`696567f33cb232cdb77c184290138d4b256b6113c129c3c078bf930c6b811026`.
All five private source/config/startup-note pins and all three existing launcher,
watcher and CreditBudget pins match actual bytes. The bridge requires this
externally provided packet hash at arm, delayed launch and adapter entry. The
startup instruction uses its frozen digest. The first freezes and bounded
correction history remain preserved. No journal, bridge-start record,
replacement-launcher log or bridge lock exists at review time.

The existing watcher remains responsible for its supervised worker recoveries;
the existing CreditBudget retains the fixed run ID and cumulative account-wide
debit ceiling. There is no purchase, top-up, API-key billing, new session reset
or separate model engine. Actual available balance is checked again by the
existing launcher before inference. The current invocation explicitly resumes
the authorized window and does not convert an old pause banner into a new stop.
It preserves later user/service/authentication/billing holds.

The transition waits for the exact old watcher/worker/server identities to be
positively gone and for both existing model leases to be free. Automatic
transition is restricted to the local included-usage guard with actual weekly
exhaustion. A coordinated early transition requires a current exact-final-state
permit, explicit resume authorization and expiry. Unknown or held stops are not
authority to replay. The initial resumed model may reconcile retained owners
and prepare sources; this does not claim native physical clearance or authorize
a new guest/build outside existing controls. The healthy workload is not stopped
merely to change billing.

The corrected cutoff now takes the minimum of the retained BOOTTIME deadline
and each newly observed UTC-derived future cutoff. It persists that tighter
future limit across rollback and rearm. The launched watcher's fixed MONOTONIC
cutoff remains separate, so an earlier UTC/suspend cutoff cannot be mistaken
for its old relative expiry. Ordinary finite-watcher draining is delegated;
earlier expiry outside that drain window permits one exact-worker normal drain.
Already-draining and sent-intent state suppress another bridge signal. Only a
PIDfd-bound worker with checked birth/parent identity is signaled; watcher,
server, process group and native guest are not bridge signal targets.

Clock/source/transition holds suppress new admission while retaining an
existing guardian. Rearm reads the authenticated retained journal before drift
handling. A changed watcher PID/birth is held rather than adopted as owned
lineage. The replacement watcher child is polled/reaped so its zombie cannot
masquerade as a live owned process. Generic negative exits with stale retryable
metadata no longer create a restart; the existing authenticated watchdog
exception remains explicitly distinguished.

The final source declares24 offline mock cases, including the pre-expiry
forward/backward/rearm cutoff counterexample, guardian continuation on source
drift, foreign watcher refusal, one replacement child spawn/reap/no relaunch,
source/startup drift checks, stop/permit classification and adapter cutoff
consumption. This reviewer read those sources but did not import or run them.
Use the exact fresh ordinary command from SOURCE-READY: CPU0,2GiB address space,
60 CPU seconds,90-second wall plus6-second grace,32MiB file limit,256 descriptors,
no core. Preserve command, source pins, outputs, direct join and absence result.

Before production arm, root must additionally capture real target-Python3.9
support for CLOCK_BOOTTIME and pidfd APIs: open a pidfd for the observation
process itself, perform signal0 on that own pidfd, close it and retain the
interpreter/kernel capability receipt. This is not a campaign/native signal and
was not executed here. A mock attribute alone does not qualify the deadline
path. Root then retains its normal source/identity/unique-controller and managed
handoff checks; later new workloads still require actual normal physical and
resource admission. Keep pinned control sources unchanged while armed and
reconcile any necessary source change rather than silently replacing the packet.

There is no actual mock PASS, real capability PASS, armed controller, prepaid
transition, new model inference or runtime acceptance from this source review.
The original functional goal, M14 and M15 acceptance remain separate.
