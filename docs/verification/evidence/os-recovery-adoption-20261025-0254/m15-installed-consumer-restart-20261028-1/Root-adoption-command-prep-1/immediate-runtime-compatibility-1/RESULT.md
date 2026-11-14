Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The immediate libelf wait4 transport now consumes the single shared converter
owned by bfd_route: `wait_status_compat.py`, SHA c895898a,552B. The private source
uses its existing authenticated loader and replaces one API call. No converter
implementation was copied. The wait4 PID/status/usage accounting, group census,
stream closure, ownership, uncertainty and failure behavior remain unchanged.

The private transport retains its original readonly frozen metadata directory.
The first private relocation incorrectly found the adjacent libelf BINDINGS;
the read-only failing check and candidate hash are retained in
`INITIAL-PRIVATE-BINDING-FAILURE.json`. One correction pinned the original
metadata directory. The private libelf BINDINGS changes only capture_transport;
its adapter changes only the binding hash. Accepted originals remain unchanged.

Five focused groups pass under the actual declared `/usr/bin/python3`, resolving
to Python3.8.10 with `os.waitstatus_to_exitcode` absent. Tests cover exit0/37/255,
signal/core statuses, stopped/continued rejection, wrong PID/no-result/wait
failure, repeated-reap accounting, minimal source/data deltas, exact accepted
h990/cwd namespace loading, serial result predicates and explicit/omitted cwd.
Final run:0.165s wall,0.157s CPU,25556KiB peakRSS, CPU6/jobs1. No actual wait4,
workload Popen, signal, SDK/Git/guard/compiler/Docker/native operation occurred.

The installed-consumer cwd capture and serial driver do not use the missing API;
their accepted601f/b63a sources and9c22/4f12 packets need no change. The new test
uses a Python3.8-compatible AST comparison; the old test's `ast.unparse` call is
test-only and the original remains preserved.

`EXACT-COMPATIBILITY-BINDING.json` supplies all exact source/helper/binding refs
and the existing libelf owner interface. Only Root may select this private
transport under a fresh exact owner/execution review. No old retirement main,
SDK driver or probe is an entry. The separate prepared HOSTcompiler driver was
left unchanged; it still needs its exact source path/hash rebound if selected.

Root current frontier/currentfree, source quiescence, grants, owner/output/nonce
and execution release remain null pending genuine118 retirement/postjoin. This
is source/HOST-pure compatibility evidence only; no native, default-artifact,
collector-compile or file-closure credit is claimed.
