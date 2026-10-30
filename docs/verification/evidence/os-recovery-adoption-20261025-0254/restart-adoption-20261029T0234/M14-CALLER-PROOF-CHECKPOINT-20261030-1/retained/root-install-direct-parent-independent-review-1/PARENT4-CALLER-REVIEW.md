# Parent4 and resident caller focused source review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. Source review only: no root, installation, native execution, nonce
consumption, operation admission, or gate release.

Reviewed Parent4 FROZEN-SOURCE.json
d02ec0a8e0a6550afdb31d655068a07f213f387f42ad97d2a920ccfc39edcfdf
and resident caller FROZEN-SOURCE.json
39e7f062cdaa56a3b2bdefd2b15795cc646a9a3fe77cd0d10d39d00112da3018.
Parent bootstrap 7e2e05b2c19881ae4348b273e5eae7d734f199c93263219a2d0b49e2c763180c,
parent body ffdad75a89dd433fa459968a3758e28d24809119698ba0afb2fd7ffbc02eeba3,
profile af535cf3031e0aa7f955f72c0ffde7813eccd44b042bee1346f1b97970405eb9;
caller driver 1e6baa7f88f4d371c272312b8a159d5391913b8d572015257d90b9d5b1e13d4d.

Scoped source/profile review: no remaining blocking defect identified in the
requested capture, handoff and owner paths. Before source loading, bootstrap
checks writable, regular mode-0600 UID1000 fd1 against the actual capture
device/inode supplied by the caller. The parent checks the same identity
around publication. It journals and emits the complete bounded DATA and fsyncs
before the one lease-close attempt, then emits a distinct disposition; short
writes, close uncertainty and missing final output remain UNKNOWN.

The resident caller reserves before its guarded fork, retains its actual sudo
pidfd and directly waits its child. It scans only that child's observed subtree,
records actual root-parent, keeper and installer PID/birth, checks separate
producer DATA against the observations and its capture, and keeps UNKNOWN when
the required identities, output or positive join are unavailable. Observations
are points in time; they are not global-descendant or native-current-free
proof. Parent's exact 22-element argv binds the actual capture identity and the
selected bootstrap; the separate caller entry binds the selected driver bytes.

R2 retains native12, V2-birth UNKNOWN with 2 GiB, scratch21 and mutex27:4.
The 18 GiB planning amount is native12 + unknown2 + joint operation4, with
other actual reservations separately included under 22.5447 GiB. Three 1-GiB
operation role limits plus the host-control share fit that 4-GiB plan only
when the real caller/sudo/frontend/monitor overhead stays within its reserved
share. The caller is CPU6-narrowed before sudo. RSS observation of the sudo
subtree is sampled only until the three roles have been observed; it is not
continuous measurement. The 256-FD per-role plan includes partial mocked peaks
plus source-based headroom and is not a measured production maximum.

Separate conditions remain: actual current operation/source review and one-shot
admission, fresh controls and usage, actual resource and broker overhead,
inherited clock caps, the live direct Root-session PID/birth and session join,
and a real capture/reservation path. A lost observation or uninterruptible
operation retains UNKNOWN and its reservation. Existing native, current-free,
source binding, effective-view and other physical gates remain unchanged.

Retained actual source-test-runs/parent4-caller-0001/RESULT.json reports 15
integrated mock cases PASS, exit 0, positive tool terminal and empty owned group;
0.11 seconds wall and 21748 KiB maximum RSS. These cover early capture, output
order, no-retry disposition, parser and fixture role observations, not real
root, sudo, fork, signal, pidfd, installation or production peak behavior.
Prior caller-data-0001 nine helper/order mocks are distinct predecessor evidence.
