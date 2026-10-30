# Caller sudo/Python role correction — source only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This separate source successor preserves caller 1a42 and the live first operation.
It requires the actual process command line to start with exact
`/usr/bin/python3`, `-I`, `-B`, `-c`, and the pinned literal before using the
existing owned-tree parent chain to identify root parent, keeper and installer.
A sudo command line containing the same literal is no longer itself classified
as Python. All other driver behavior and custody gates remain unchanged.

The new case uses a realistic root-owned sudo argv carrying the full Python
command and a distinct Python root/keeper/installer PPID chain. It first checks
an early sudo-plus-root observation, then the complete tree. After Root's
existing light-test admission, run only this new mock case:

```
/usr/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-caller-role-correction-1/test_sudo_role.py
```

No test or operation was run here. The first operation remains LIVE/UNKNOWN;
its nonce and resource reservations are retained. This correction grants no
replay, fresh operation, native release or current-free proof. A reviewer must
bind the new driver and entry before any future separately admitted use.
