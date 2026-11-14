# Rolling traversal and role FD driver review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. Source review only; no tests, root calls or physical operations.

Child4 direct_entry.py SHA256 7ac4718a01be185cc1d816bf5c91e84960b73ca51209d7c3b909cda354ccfcea
retains verified leaf descriptors, rechecks each named component, uses one
stop-deferred close per temporary predecessor, and leaves a sticky FAILED
state and no numeric retry on ambiguous close. Repeated successful loading
returns its cached object with no new traversal. Parent3 bootstrap SHA256
7b09acf2... likewise retains leaves while retiring temporary ancestors under
stop deferral. A pinned leaf does not prove a later named ancestry claim.

The parent2 recovery and child4 unhanded-stop changes address the reviewed
retained-pidfd failure: parent independently checks the child relationship,
pidfd type, flags, pidfd PID and stable identity, and excludes a
PidfdVerificationError; child requires a ChildRecord with an identified birth
before signaling. Any incomplete identity remains UNKNOWN. No physical stop,
retirement or native/current-free result is established by source review.

The source-bound role_fd_budget.py SHA256
296339c84292b7d4392c3ce853a4b9354c689f75b355cc35375f8082e944d4b6
is suitable for the requested ordinary unprivileged CPU6/512 MiB profile and
separate role runs at the selected existing 128/256 descriptor limits. It
creates and retains ordinary private fixtures; performs real source reads and
opens/closes; mocks UID, immutable flags and receipt/control gates; and stops
the installer before the first attempted O_CREAT. It does not perform real
root, fork, pidfd, signal, immutable ioctl or install mutation.

The driver measures its actual ambient starting FD count; it does not itself
allocate or enforce a fixed preoccupied baseline. The caller must supply and
record any fixed baseline or report the observed one. Its sampled peak is
partial: actual process creation, SCM_RIGHTS, receipt paths, installer output
writers/freeze, failures, and uninstrumented internal opens are excluded.
An observed pass therefore does not establish the full-operation 256-FD peak
or grant operation authority. Existing reservations, source/effective-view
gates and native-current-free UNKNOWN remain unchanged.
