# Signal actual-body host fixture execution record

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Work directory: `/home/holden/mckernel`. Source-only host fixture; no container, kernel build, module, guest, or native workload was started. The run applied the retained private patch to a temporary source copy and compiled host stubs plus an extracted Rust function. It did not alter the retained source or private patch.

The initial invocation was:

```sh
python3 docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-ARCH5-SIGNAL-ACTUAL-BODY-20261030-1/check.py
```

The initial temporary directory was `/tmp/m14-signal-body-umxo3itq`. The system default `rustc 1.60.0-nightly (777bb86bc 2022-01-20)` was invoked by `check.py` as follows after the `cc -c` step and patch application:

```sh
rustc --edition=2021 --test /tmp/m14-signal-body-umxo3itq/fixture.rs -C link-arg=/tmp/m14-signal-body-umxo3itq/mock.o -o /tmp/m14-signal-body-umxo3itq/fixture
```

It failed with E0599: raw pointer methods `cast_mut` at extracted `body.rs:42` and `cast_const` at `body.rs:67` were unavailable in that toolchain. Python reported `subprocess.CalledProcessError`, exit status 1; no tests executed on that first attempt. The earlier tool output contains the original diagnostics; this record preserves their substantive content, not a verbatim full compiler transcript.

The single bounded correction selected `/home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc` in the fixture, without modifying the candidate body. A subsequent pass initially produced fixture warnings; the fixture was adjusted to avoid shared references to mutable statics and suppress only private-interface fixture warnings. The final recorded check invocation was:

```sh
python3 docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-ARCH5-SIGNAL-ACTUAL-BODY-20261030-1/check.py > docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-ARCH5-SIGNAL-ACTUAL-BODY-20261030-1/RESULT.txt 2>&1
```

`check.py` creates a fresh Python temporary directory, invokes `patch --silent --output <temporary-policy> <retained-policy> <private-patch>`, `cc -c <temporary-mock.c> -o <temporary-mock.o>`, Rust 1.85.1 with `--edition=2021 --test <temporary-fixture.rs> -C link-arg=<temporary-mock.o> -o <temporary-fixture>`, and `<temporary-fixture> --test-threads=1`, each via `subprocess.run(..., check=True)`. The final temporary directory name was not retained. Temporary-directory cleanup is performed by Python on context exit.

[RESULT.txt](RESULT.txt) records six passing tests and source/script SHA-256 values; it contains no compiler warnings. The final shell command also displayed that output with `cat`. The tool returned a completed result; the script reached its post-test hash print, so each checked subprocess returned successfully and was waited for by `subprocess.run`. Exact PIDs, start times, per-process resource consumption, independent process-tree inspection and post-run lease observations were not recorded. This is join evidence for the fixture's direct subprocess calls, not evidence of native-owner cleanup or absence of unrelated processes. No native ownership was claimed or changed.

No explicit CPU affinity, cgroup, memory ceiling, job limit or timeout was set for these host fixture subprocesses; their inherited effective values and peak CPU/memory were not measured. The commands were sequential, and the test runner was explicitly limited to one test thread. The controller's physical workload limits remain applicable to future controlled work; this lightweight host fixture does not establish or grant an additional build or guest lease.

The host mock test does not prove kernel ABI, selected linkage, actual handler execution, real logging concurrency or native behavior. M14 acceptance remains open.
