# Linux collector watchdog/report-fsync source audit — 2026-09-15

Status: **SOURCE_FINDINGS_ONLY**. No packet or execution is released.

Reviewed adverse root owner SHA256 is
`be77a3585f94e159b8dd5222bd7cc894c083879cd82495fccf6e408749f18b2b`;
host supervisor SHA256 is
`cba4b4d50d68f9afd5aa8a4c2d830ec0b800f7fd7dfd07774911d5fd1b99c7e7`;
the accepted build archive SHA256 is
`eaf0665189b49d80359b44109d7f015e19700112cc1d07d68b2d1ccd405e8675`.

Watchdog recovery is source-bound today: withholding private `DISARM` or reaching
its bounded deadline enters identity-checked `recover_cleanup()` and writes the
watchdog result plus recovery journals. The accepted adverse packet exercises only
clean disarm, so triggered recovery is absent.

No deterministic post-reap/report-fsync injection seam exists. The supervisor
reaps the owned leader, fsyncs retained stream artifacts in `finally`, then writes
and fsyncs the final report. Current signals are latched rather than injected at
that precise boundary. The smallest future packet needs one test-only hook after
owned `waitpid()` and a distinct targeted final-report-fsync hook. It must retain
raw waits, partial/full report identities, stream-fsync status, reap/cleanup
journal and the original failure archive. These two injection points and
watchdog-triggered container recovery require separate reviewed cases. No runtime
or production credit follows.
