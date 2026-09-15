# Linux collector storage-fault-v2 source correction packet 13

Status: DRAFT FOR INDEPENDENT PACKET REVIEW ONLY

This replaces rejected packet 12 and changes only supervisor wait/signal birth
evidence. Packets 1 through 11 otherwise remain mandatory.

Before owner spawn, the single-threaded supervisor sets SIGCHLD disposition to
SIG_DFL, makes no later disposition change, forks one sentinel that exits 73, and
requires its exclusive direct `waitpid` to return that sentinel with exact raw
status `73 << 8`. It records `sigchld_default=true,sentinel_wait_passed=true` in
the supervisor result. It uses no `Popen`, other waiter, SIGCHLD handler or
`SA_NOCLDWAIT`. For the real owner, `owner_reaped` is monotonic false-to-true;
direct-PID TERM/KILL is permitted only while false. Thus a directly spawned PID
cannot be reused before a signal.

Supervisor cleanup maintains `last_matching_startticks` for the real owner and
for every adopted PID. A direct-owner signal or wait uses the latest positive
birth established by any two matching PID/PPID/startticks observations before
that event, including cleanup observations after an initially UNOBSERVED summary;
it uses null only if no such pair was ever established. The event retains packet
12's exact direct-child Boolean field for signals and packet 4's direct wait
shape. The summary classification remains the initial packet-11 classification
and is not retroactively promoted; raw later observations prove the event birth.

Adopted signaling still requires two immediately preceding matching observations
and always records their positive birth. An adopted wait records the latest
independently established matching birth when one exists, but may use null when
the child was reaped before any identity was ever observed, as packet 2 and the
packet-4 reap-before-scan loop require. Null adopted wait birth is never accepted
for a signal and never treated as identity evidence.

Source controls cover the SIGCHLD sentinel and wrong-status/auto-reap failures;
no signal after direct reap; initially missing then later matched direct birth;
never-observed direct null; adopted reap-before-scan null; later-observed adopted
positive wait; and rejection of every adopted signal lacking positive birth.

No source/build/root/native/application/production gate is released without
fresh independent review of this exact packet hash.
