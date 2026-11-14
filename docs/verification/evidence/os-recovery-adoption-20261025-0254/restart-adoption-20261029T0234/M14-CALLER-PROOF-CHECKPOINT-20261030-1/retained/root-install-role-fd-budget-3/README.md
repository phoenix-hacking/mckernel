# Installer FD exercise: bounded fixture permission correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This unrun source successor preserves role-fd-budget-2 and all earlier results.
It changes only the synthetic `fstat` view: the actual staged operation root is
captured by device and inode before patching, and that exact directory retains
its real mode. Other fixture directories continue to receive the already used
test-only traversal view. The synthetic UID view remains zero. No actual mode,
production guard, ownership, admission or privilege is changed.

The focused fixture test checks the unchanged source-bound installer's actual
`dir_identity` function against root modes 0700 and 0701, both device and inode
mismatches, and an ordinary file. Both source files compiled to code objects
with system Python 3.8.10; neither test nor installer exercise ran here.
After Root's reviewed light-test admission, run the four mock-only fixture cases:

```
/usr/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-role-fd-budget-3/test_permission_view.py
```

Then rerun only the affected installer role with a new Root result and an
existing private fixture parent, under the same separately reviewed CPU 6,
256-FD and resource limits as installer-0001:

```
/usr/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-role-fd-budget-3/role_fd_budget.py --role installer --fixture-parent FIXTURE_PARENT
```

The original parent-0002 and keeper-0001 results remain scoped to source2;
they are not rerun or reattributed to this source. The result is a partial
mocked descriptor exercise, not a production peak, native acceptance, actual
root ownership, source exclusion or execution release. FD observer limitations,
unmodelled role paths and the temporary fixture behavior remain as documented in
role-fd-budget-1/README.md. No root call, actual installer mutation, native work,
fork, pidfd or real signal is authorized by this source packet.
