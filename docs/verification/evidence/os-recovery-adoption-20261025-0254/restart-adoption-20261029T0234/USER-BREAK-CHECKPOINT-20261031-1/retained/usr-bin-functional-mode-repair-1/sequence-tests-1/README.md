# Functional mode-repair sequence regression — source only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This separate fixture loads the exact frozen `mode_repair.py` and mocks all root,
filesystem mutation and signal operations. It exercises its real guarded repair
function: durable BEFORE_FCHMOD publication precedes one exact target-FD chmod,
separate readback is performed, a failed precheck makes no chmod call, and both
fchmod failure and postmutation output failure produce UNKNOWN without retry or
success. Tests have not run in this worker; system Python 3.8.10 compiled the file.

After Root's existing ordinary light-test admission, the new cases are:

```
/usr/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/usr-bin-functional-mode-repair-1/sequence-tests-1/test_repair_sequence.py
```

The three frozen basic tests may also be run as a separate interpreter invocation:

```
/usr/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/usr-bin-functional-mode-repair-1/test_mode_repair.py
```

Neither source nor test success grants a privileged release. The mode remains
0777 until an independently reviewed actual one-shot operation is completed.
