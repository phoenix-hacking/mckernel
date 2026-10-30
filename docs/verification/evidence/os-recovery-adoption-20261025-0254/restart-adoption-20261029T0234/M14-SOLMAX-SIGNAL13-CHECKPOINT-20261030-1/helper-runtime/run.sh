#!/bin/bash
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
set -u
umask 077
cd -- "$1" || exit 99
printf '%s\n' "$$" > RUNNER.pid
cat "/proc/$$/stat" > RUNNER.proc-stat
ps -o pid=,ppid=,pgid=,sid=,stat= -p "$$" > RUNNER.identity
/usr/bin/time -v -o compiler.time /home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc --edition=2021 --test postformat_cases.rs -o postformat.test > compiler.stdout 2> compiler.stderr
compiler_status=$?
printf '%s\n' "$compiler_status" > compiler.exit
if [ "$compiler_status" -ne 0 ]; then exit "$compiler_status"; fi
/usr/bin/time -v -o fixture.time ./postformat.test --test-threads=1 > fixture.stdout 2> fixture.stderr
fixture_status=$?
printf '%s\n' "$fixture_status" > fixture.exit
exit "$fixture_status"
