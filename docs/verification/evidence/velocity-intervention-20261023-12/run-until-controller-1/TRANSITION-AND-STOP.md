# Fixed delivery window bridge — prepared, not armed

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The existing watcher already preserves its work window across worker recoveries and forwards a stable credit-run ID. Existing CreditBudget records cumulative observed account-wide balance decreases; increases do not restore allowance. Neither --hours nor --credit-budget can be retrofitted into the resident included-only process. No current watcher/worker/server/nativeowner was signalled, restarted or otherwise changed.

One detached private bridge watches the existingstate. It arms a fixed2026-10-25T00:00Z cutoff plus persisted CLOCK_BOOTTIME backstop and a retained credit-run ID. Its first arm freshly binds watcher/worker/server PIDs, birthticks and PPIDs, not PID arithmetic. Existinglauncher watch.lock/run.lock remain owned by their normal holders; no lock is unlinked or bypassed.

Preferred transition: after currentLONG natural completion, root coordinates one normal between-workloads worker checkpoint, then positively observes oldwatcher/worker/server retirement. The bridge passively waits; it does not initiate an early handoff. Root supplies handoff.json approving the exactFINAL stoppedstate SHA, deadline, explicitcurrentresume and shortexpiry, using HANDOFF-PERMIT.TEMPLATE.json. A signal/pausedstate alone never resumes work. A later realuserstop must revoke this permit/use --cancel; service/auth/billing/unknown stops never turn into genericrestart.

Automatic alternative is deliberately narrower: local included_usage_guard, included_only mode and100% of a10080-minute weeklywindow, after exactoldmodeltriplet disappearance and freeoriginalleases. quota_exhausted/credit_balance_decreased/unknownbilling/service/auth stops do not qualify. Missing/unknown ownerphysicalclearance is NOT a circular prerequisite for modelresume: startup is explicitly RECOVERY-ONLY source/evidence/retirementreconciliation, with NO newguest/build until existing physicalacceptance is actuallyclosed.

The one newlauncher uses the existing canonical launcher/watcher/creditguard and a tiny private entry adapter. The adapter recomputesremainingtime atwatcherboundary from the earlier of UTC/persistedBOOTTIME cutoffs, then existingmonotonic watcherhorizon remainsfixed acrossallitsrecoveries. A30-second checkpointreserve(+<=1secondschedulingmargin) replaces600-secondpredeadline quiescence. This lastinterval remainsproductive checkpoint/owneddrain; nearcutoffthecampaign mustnotadmit workthatcannotfinish/checkpoint. Normalunchangedbounds/rootowners remainauthoritative.

Atdeadline the original--hours0 process receives atmostONE exactpidfd-bound workerSIGTERM to request normalcheckpoint/drain. No watcher/group/server/guest signal is sent bythisbridge. Any alreadydrainingstate suppresses the signal. A finite replacementwatcher ordinarily owns relativeexpiry. If a forwardUTCstep reaches theabsolute deadline earlier than its scheduled31-second quiescencewindow, bridge requests one exactworkerdrain; it skips alreadydrainingworkers and records the signal before futurepolls. It never sends a competingnormal-expiryTERM. Each observation persists BOOTTIME cutoff=min(saved cutoff, current BOOTTIME+max(0,deadlineUTC-current UTC)). This latches an earlier future cutoff through rollback/rearm; the launched watcher relative MONOTONIC cutoff stays separate. Source drift keeps the retained guardian active and blocks new inference; a foreign watcher publication never replaces the trusted original identity. Existing watcher retainsitsnormal modeldrain handling; no directguestkillorownershipclearance is added.

Root-reviewed detached arm command (NOTRUN):

```sh
nohup /usr/bin/taskset -c 0 /home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-12/run-until-controller-1/bridge.py --run --packet-sha256 fd28d66e4d93e3154bbd3d89e09b909c6997a7a0925b0d88f094a46f7343ea54 > /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-12/run-until-controller-1/bridge.console.log 2>&1 < /dev/null &
```

Preserve the existing launcher's inherited hardlimits; do NOT armbridge under a tiny hardAS/CPU/FSIZE/NOFILE cap which its replacement launcherwouldinherit. The bridge's metadata stayssmall; its childexplicitlyrestores onlythe userapproved CPU pool0,2-7. Existing--quiet avoids duplicatingfullmodeloutput into replacement-launcher.log; canonicalconsole/protocol/creditruns remainretained.

Explicit cancel command (NOTRUN):

```sh
/home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-12/run-until-controller-1/bridge.py --cancel
```

It records a private USER-STOP marker; the armed bridge requests onlynormalworkerdrain and never resumes. The one transitioned launcherargv is derived by launcher_argv and retained in journal.launch_intent before Popen, with hashpinnedCURRENT-INVOCATION.txt and fixedcreditID. An uncertain launchintent is never automaticallyreplayed. A newwatcher owns all subsequent classifiedrecoveries, narrowed to positive knownclasses by the adapter; no genericunknownnegativeexit retry.

Exact modelhandoff signal, ifrootchooses it, must use the same stop_worker(bind(actualstate,actualwatcher)) pidfd helper under an independently accepted safeboundary command, never a bare numeric kill or signals towatcher/guest. This packet grants no earlysignal. No handoffpermit is fabricated bysourcepreparation.

SOURCE-READY.json binds source and exact proposed CPU0/2GiB/60CPU/90wall+6/32MiB/256FD/core0 offlinefixture command. Fixtures are supplied metadata/clock/process doubles; they do not spawnprocesses or signal/model/bill. None ran duringpreparation. Independentreview and one rootordinarytestgrant precede actualarm.

FROZEN-PACKET.json SHAfd28d66e4d93e3154bbd3d89e09b909c6997a7a0925b0d88f094a46f7343ea54 is externally supplied atarm and passed toprivateentry; both verify allprivatecode/config/startup and canonical launcher/watcher/creditguard bytes before use. The startupnote SHA is taken fromthat frozenpacket, never recomputed asnewauthorization from changedlaterbytes. Source/privateentry/clock-model tests remainNOTRUN in thispreparation.

Before actual arm, root must retain one tiny Python3.9 capability receipt for own-process pidfd_open, pidfd signal0, close, and CLOCK_BOOTTIME availability. This packet executes none of those operations.

Python3.9 here lacks pidfd builtins. Reviewed compatibility uses callable builtins when present, otherwise only Linux x86_64 typed libc pidfd syscalls434/424. The actual new wrapper must pass own-process signal0/CLOCK_BOOTTIME receipt before arm; SOURCE-READY supplies that exact command. No numeric PID signal fallback exists.
