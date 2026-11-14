# Linux collector stopped-rescue design — 2026-09-15

Status: **PASS_DESIGN_ONLY** for a future separately named `stopped-rescue-v1`
packet. No source packet, build or execution is released by this record.

Pin the released collector
`09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f`,
root owner
`b794fc74a668f9f41caceb99e299381652fe02caa002c06d8b43c287b75599a3`
and host supervisor
`cba4b4d50d68f9afd5aa8a4c2d830ec0b800f7fd7dfd07774911d5fd1b99c7e7`.
Use a guarded collector hook immediately after pump/exec/leader observation; an
unknown or missing selector must fail compilation. The blocking fixture leader
forks one initialized child, then emits one nonce- and identity-bound `READY` and
both processes block without further forks or waits.

The hook may arm only after retained READY, sealed executable observation, complete
384-byte setup plus EOF, live unreaped leader and no earlier failure. It durably
records and fsyncs `STOP_ARMED`, then calls real `raise(SIGSTOP)`. The dedicated
single-threaded actual parent rescuer uses `SIGCHLD=SIG_DFL`, has no concurrent
waiter, and acknowledges the stop through `waitpid(WUNTRACED|WNOHANG)` with raw
status 4991. Markers or procfs state cannot substitute.

While the collector remains stopped and unreaped, the rescuer enumerates actual
direct children, kills the leader, observes its zombie and the grandchild's
adoption, then kills that now-direct child. It records each full identity, signal
and adoption transition, never signaling a cached PGID or marker-only PID. With
both zombies it sends the still-fork-owned collector SIGTERM then SIGCONT so the
existing collector can reap and publish. Expected collector raw exit is 256 with
`INTERRUPTED/collector-interrupted/EINTR`, signal 15, both fixture raw waits 9,
validated setup, complete EOFs/cleanup and zero omitted owner records. The rescuer
must observe ECHILD after collector reap.

Deadlines are five seconds to ready/stop, two seconds for descendant termination,
the existing 15-second post-continuation cleanup, 40 seconds per case and 300
seconds per container, all as absolute monotonic records. Preserve raw stop/exit
waits, identities/startticks, readiness/setup/streams/events, reports and fsync
outcomes, literal invocation/environment, exact CID cleanup, watchdog disarm and
independent post-owner lock reacquisition. Wrong/duplicate readiness, identity or
waits; extra descendants; missing adoption/EOF; premature exit; storage failure;
or misleading completion must fail.

Write allowlist: a new
`scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/stopped-rescue-v1/`
packet containing packet/tests/prepare/patch/inject/fixture/rescuer/oracle/run/build
and root owner files, plus one new focused test module. Independent source review,
negative protocol tests, separately reviewed build, artifact audit and separately
reviewed root execution remain mandatory. Watchdog-triggered recovery is separate.
No McKernel/application/production credit follows.
