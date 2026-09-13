# Real Linux terminal-boundary harness

Status: **SOURCE ONLY; NOT COMPILED OR RUN BY THE AUTHOR.** Root owns the
pinned compilation and execution lane. Successful checks grant no guest,
payload, transport or production acceptance.

`terminal_waitable_harness.c` includes the exact local `controller.c`, renaming
only its CLI `main`. It directly calls `owner_terminal_launcher_waitable` once
per scenario. There are no substitutions for `clock_gettime`, `waitid`, `read`,
`poll`, procfs, `pump`, or the method under test. The original controller CLI
and every ioctl/guest path are uninvoked. The compiler must retain the actual
controller/header/public ABI include dependencies; bind them to the reviewed
bytes before compiling this additive harness.

CLI, one fresh process and directory per scenario:

```text
terminal_waitable_harness CASE /ABSOLUTE/FRESH/ATTEMPT
```

| CASE | Independent expected result |
| --- | --- |
| exit-eof | Actual exit0 and both pipe EOFs pass. The method's own pump observes exit/EOF; two later WNOWAIT observations still identify the unreaped child. |
| alive-eof | Both real writers close but the launcher remains alive. The original effective deadline fails with ETIMEDOUT. |
| descendant-stdout | Launcher is waitable; a real child descendant retains only stdout's writer. Stderr reaches EOF, stdout does not; deadline fails. |
| descendant-stderr | Launcher is waitable; a real descendant retains only stderr's writer. Stdout reaches EOF, stderr does not; deadline fails. |
| ticks-mismatch | Actual waitable child and EOFs are ready; expected original start ticks differ by exactly1. Method fails ESTALE. |
| nonzero-exit | Actual exit23 and EOFs pass this boundary observation. Raw wait5888 is retained; it is explicitly not payload acceptance. |
| expired-ready | Actual waitable child and both EOFs are established first. An already-expired input deadline rejects them, including the method's post-loop deadline check. |
| overall-deadline | Alive launcher with both EOFs; the original90-second overall origin leaves200ms while input allows15seconds. The minimum overall deadline must fail. |

The clocks are real. For short checks, `seed.json` records origin-field
arithmetic preserving the exact method expression
`min(input_ns + 15000000000, started_ns + 90000000000)`. Ordinary negative
cases leave200ms; positive/identity cases leave1second; expired-ready places
the input deadline1ms before the sampled clock. The overall case seeds only
the original started_ns origin. A host uptime below91seconds cannot satisfy
this fixture's unsigned arithmetic and causes a recorded setup failure.
No production timeout constant or loop is shortened/replaced. Immediately
before invoking the method, with no intervening log or filesystem action,
nonexpired cases require at least20ms of actual remaining entry budget.
Late entry skips the method and fails the harness case; it cannot qualify as
an expected timeout. The original entry clock/budget and whether the method
was called are retained before cleanup. Expired-ready instead requires the
captured entry time to be at or after its deliberate expired deadline.

The fixture is an actual direct child, creates its own session/process group,
and reports PID/descendant identity over a separate pipe. The harness becomes
a child subreaper. A held descendant closes the unused stream writer and
retains exactly the writer being tested until owned cleanup. Stream contents
are independent literal bytes, not outputs generated from the tested method.

Each scenario exclusively creates `argv.nul`, real stdout/stderr captures,
`events.jsonl`, the raw fixture readiness message, `seed.json`, the complete
method observation and two actual WNOWAIT observations before cleanup, then
`harness-result.json`. Expected failure errno/reason/time and each assertion
are retained. The original observation and stream/event captures are synced
before any cleanup signal or reap. Nothing is deleted or overwritten.

Cleanup signals only the confirmed group created by the unreaped direct child
(or that direct child if group identity is unavailable), then records each
actual raw wait. Launcher identity remains unrecycled until the final reap;
subreaper ownership retains orphaned descendant identities. The harness checks
exactly one reaped child, or two for a held-writer case, and no remaining child.
Cleanup completion also requires both actual pipe EOFs observed before the
original2-second cleanup deadline; its completion timestamp is retained.
Alive launchers/held descendants expect owned-cleanup SIGKILL raw wait9;
already exited launchers retain their actual original exit status.

Setup waits are bounded at3seconds each, method observation uses the original
deadline expression, cleanup is bounded at2seconds, and a10-second alarm
interrupts the harness through the controller's existing interrupted flag.
Root must additionally use the original bounded supervisor/container wrapper
to enforce the whole process-tree limit and preserve any abnormal termination.
Expected ETIMEDOUT/ESTALE cases produce the controller's original failure
diagnostic; only an unexpected harness outcome is a test failure. Stop and
retain/log that original failing attempt before any correction/retry.

Required pinned evidence includes exact compiler invocation/dependencies,
diagnostics, object/ELF and harness/controller/header hashes, the eight separate
invocations and supervisor raw waits, each complete attempt tree, and the
independent source review. A harness PASS is Linux infrastructure evidence only.
