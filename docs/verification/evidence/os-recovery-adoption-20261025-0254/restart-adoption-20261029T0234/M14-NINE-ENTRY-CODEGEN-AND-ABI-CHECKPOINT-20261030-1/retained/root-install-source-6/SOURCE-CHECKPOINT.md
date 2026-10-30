# Functional M14 bounded installer watchdog successor

SOURCE ONLY; UNREVIEWED; NOT RELEASED. No test, sudo, signal, fork, root mutation,
installation, mount, SDK, native operation or cleanup occurred. v5 and prior
failures remain preserved. V2 unknown 2 GiB, native12, scratch21 and mutex27:4
remain held; host-install custody is not native current-free proof.

The child watchdog latches stop attempts in memory, signals its verified owned
pidfd and observes direct-child wait before attempting durable event writes. With
insufficient remaining grace it attempts immediate pidfd KILL, including when a
late sample has passed the cap; it does not start new work or extend the join
window. Failure to observe join becomes UNKNOWN. The remaining TERM/KILL/join
allowances stay inside admitted BOOT/MONO/UTC limits; no numeric-PID signal occurs.
The issuer completes a durable BEFORE_GO record before sending GO, then rechecks
controls, runtime, host receipt, timeout group and launch grace. A blocked pre-GO
journal therefore cannot release installer work.

The exact `INSTALL-PROFILE.SOURCE-ONLY.json` argv is `/usr/bin/sudo -A`, followed
by CPU6 `taskset`, `prlimit` with 1 GiB address space per operation process and
bounded CPU/files/FD/core limits, then root-owned GNU `timeout --signal=TERM
--kill-after=5s 60s` with its default private process group, then system Python and
the pinned literal bootstrap. There is no `--foreground`, setsid, escaped child,
sudo `-C` or inherited pre-sudo FD assumption. Issuer verifies actual root-owned
sudo/taskset/prlimit/timeout bytes, the exact timeout argv digest, timeout process
group/lineage, CPU affinity and limits, and that all six campaign actors and the
known outer owner remain outside the timeout group before GO. Root must supply
actual pinned hashes and confirm the process tree and fresh controls. Three
operation processes with the stated ceilings are planned at at most 3 GiB within
the 4 GiB operation allowance; timeout and capture overhead, native4+operation3
job count, native12, retained unknown 2 GiB and host reserve must fit actual
22.5447 GiB aggregate headroom. These are planning bounds, not measurements.

An external GNU timeout process ending is not positive installer join or retirement
proof. In particular, if all processes holding the shared lease OFD die, Linux
closes it and releases flock; a retained UNKNOWN journal does not hold that lock.
Root must separately establish and review an outside-group same-OFD owner or an
independently reviewed equivalent exclusion before claiming the lease survives
group-wide death. Any uncertain D-state/join retains its ownership and resource
hold record; no physical lease, cleanup or native retirement is inferred.

The v5 typed `HOST_INSTALL_RESOURCE_CUSTODY_V1` remains ROOT_CODE_INSTALL_ONLY,
native current-free null and no-unlisted interval UNKNOWN. Real start intent,
nonce, controller/receipt hashes, known outer caller, timeout argv/tool hashes,
BOOT/MONO/UTC caps, operation paths, source/lease ownership, independent timeout
capture, host resource and direct retirement evidence remain Root inputs. Existing
collector/profile/source/effective-view and native/current-free gates remain shut.

A first `/usr/bin/python3` 3.8.10 AST parse found a missing line continuation in
one synthetic test. Its exact failed source and error are retained as
`test_watchdog_ofd.syntax-failure.py.txt` and `AST-PARSE-FAILURE.json`; that one
bounded correction was applied. The subsequent AST parse passed 28 Python files
and 3 inline programs. Tests remain UNRUN. After independent review and Root
admission, a proposed separate-interpreter synthetic command is:

```
cd /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-source-6
/usr/bin/python3 -B -m unittest -v test_ready_go test_install_v2 test_watchdog_ofd test_host_runtime_deadline
```

This does not execute the installer or prove real pidfd stop, timeout, custody or
native behavior. Independent review and separate actual operation admission remain.
