# Disabled perf host-light owner successor

Status: source-only, disabled, no operation release. Functional McKernel OS/Rust migration; no security testing. The predecessor retains the reviewed host retirement producer prefix. This successor requires literal True from authority and watchdog gates, claims its owner before callbacks, binds phase commands through a canonical JSON SHA256, validates finite positive inherited clock caps and deadline, and checks stop immediately before each spawn. Unknown and failed ownership stay sticky.

The actual binding, digest, authority and watchdog remain null. External interruptible watchdog and authenticated process/descriptor custody, real exact commands and oracle, immutable source/toolchain/staging, positive quiescence, live admission and release remain separate prerequisites. Callback deadline checks do not interrupt blocking operations. Signal delivery can still occur between the final check and spawn; post-spawn stop is quarantined. No launch is enabled by this artifact.

Fresh mock-only command, executed here:

```
timeout --signal=TERM 30s taskset -c 0 bash -c 'ulimit -v 524288; ulimit -t 20; ulimit -n 128; ulimit -f 16384; ulimit -c 0; exec python3 -B test_successor_final.py' > final.stdout 2> final.stderr
```

Exit 0; seven synthetic tests passed. They cover disabled source, strict negative gates, binding mutation, changed command digest, reentry, invalid or widened deadlines, stop before and during spawn assignment, and successful two-phase mocked ordering. They do not execute real subprocesses, the perf fixture, a compiler, Kbuild, configure, Docker or guest/native workloads. This test is not a reviewed execution admission or evidence of real process custody.

Evidence packaging initially failed with FileNotFoundError because Path('.') had a relative parent; no source or output was changed by that packaging attempt. Absolute cwd corrected this one bookkeeping error.
