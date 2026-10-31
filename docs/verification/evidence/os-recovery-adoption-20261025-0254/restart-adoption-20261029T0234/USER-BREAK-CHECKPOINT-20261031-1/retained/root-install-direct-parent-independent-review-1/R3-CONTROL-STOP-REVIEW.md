# R3 current control stop review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. The companion JSON is a conditional source/operation review, not
the separately minted fresh stop release and not evidence of a signal or join.

The frozen source binds the actual R3 request, argv, reservation, capture
inodes and exact two failure notes. It rechecks the actual Root/caller/sudo
PID/birth chain, unchanged parent source and Python argv/interpreter, same PID
namespace, one target thread, no current children, selected held FDs and no
R3 output directories. It requires one retained pidfd with Pid and NSpid -1,
opens a fresh target-verified root-parent pidfd, emits and fsyncs
PRESTOP_METADATA, and rechecks before using that pidfd for TERM and, if needed,
KILL. It
reports terminal and its own single-close disposition separately from the
outside sudo direct wait and caller-session join. Errors retain UNKNOWN and do
not release either operation reservation.

The keeper pidfd-to-keeper association is an inference from the exact trusted
Parent5 single-ChildRecord-before-lease control path, the source-bound capture
and the actual selected FD evidence. It is not a separately recorded keeper
wait status; that status remains UNKNOWN. The emitted PRESTOP metadata may later
contribute to the separately reviewed failed-before-mutation process-memory
rule only if the actual target stop and outside joins are positively proved.
It does not by itself release R3 memory, the original dfd reservation, native
ownership, current-free or any source/effective-view gate.

The actual one-directory repair result records /usr/bin on device 66306 inode
1048578 at mode 0755, with separate readback and closed descriptors. The
unchanged original ancestry guard subsequently passed at that inode. One
focused failure-note mock also passed in r3-stop-and-mode-guard-0001; neither
is an install or native acceptance.

Root must supply the exact source's fresh one-shot release and actual current
controls, usage, role identities, resources, CPU6, exclusive capture and
positive helper/sudo/caller joins. Its eight-second post-signal observation is
not a guaranteed end-to-end wall bound; uncertain held-pidfd custody or an
unjoined helper remains charged. Keep original UNKNOWN four GiB, R3 four GiB,
native12, V2 UNKNOWN two GiB, scratch21, mutex27:4 and all native holds.
