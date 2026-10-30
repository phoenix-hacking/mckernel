# Functional M14 profile argv correction

SOURCE ONLY; UNREVIEWED; NOT RELEASED. Frozen source10 and all prior failures
remain unchanged. No test, sudo, fork, signal, pidfd operation, root operation,
installation, mount, native workload or cleanup ran.

The corrected profile changes only two argv elements: index 4 is taskset's CPU
operand `6`; the `-c` found only after the `-- /usr/bin/python3 -I -B` structural
prefix has its operand at index 16 set to the exact frozen
`BOOTSTRAP-CODE.py` bytes (SHA-256
`40d470de1538548a4c4a3075f867257dc550f89b7c1593a3e75c76eca0edc87a`). All other
arguments and profile fields are preserved from frozen source10. It does not alter
any source, timeout proof, controls, limits, owner receipt or native gate.

The prepared test checks the complete exact argv and frozen source bindings. In a
fresh interpreter it also imports the actual pinned source10 `monitor_owned` and
uses mocked poll/wait results for timer exit zero plus the bound installer pidfd
terminal and ECHILD, timer nonzero, timer signaled, adopted-installer nonzero and
pidfd poll error. These are synthetic control-flow checks; they do not prove live
PID identity, GNU timeout, process custody, install, native or root behavior.

Python 3.8.10 AST parsing of the test source passed. The test is UNRUN. After
independent review and Root admission, proposed exact local command is:

```
cd /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-source-10/profile-argv-correction-1
/usr/bin/python3 -B -m unittest -v test_profile_and_monitor
```

The Root-approved known-role/tool proof, immutable review artifact and live
operation/resource/lease/clock inputs remain separate. UID1000 access, source
exclusion, global descendants and native current-free remain unproven.
