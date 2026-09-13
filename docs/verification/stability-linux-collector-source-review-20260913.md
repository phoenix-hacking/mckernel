# Linux sealed collector source checkpoint

This checkpoint implements and independently reviews a new standalone Linux
collection component. It records no compiler execution, actual collector test,
guest run, application acceptance or backend release. The earlier decoder's
84 actual C checks remain a separate infrastructure result, retained in
`stability-application-request-decoder-tests-review-20260913-1.json`.

The implementation is under
`scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/`. Its explicit
`--linux-sealed-infrastructure-v1` command consumes the unchanged ACRQ0001 decoder
request, a source-selected manifest byte file and an exclusive attempt path.
Only Linux role1 is supported. The manifest is hashed but semantically opaque;
it grants no image, dependency, capability, packet or oracle authorization.
Original decoder/profile files, catalog packets, fault controllers and `run.py`
remain unchanged.

The source pathname selects bytes to copy, verify and seal. Actual execution uses
execveat with an immutable memfd and preserves independent argv0 and complete
literal argv/environment. This is an explicit infrastructure profile with
descriptor/memfd AT_EXECFN and proc-exe semantics. Existing pathname predicates
remain unsupported, and source-path release still requires immutable pathname
execution. Interpreter/DSO closure and native payload provenance are not supplied.

The collector checks source/stdin size and SHA256, canonical nonsymlink file
paths, source stability, sealed backing identity, actual child credentials,
group/umask/cwd and standard descriptors. It concurrently drains bounded streams,
records actual Linux waitpid status and keeps signaled termination distinct from
exit128+signal. The ten-second child deadline begins before fork; observed
completion must precede it. Fifteen-second cleanup pins the unreaped owned leader
through group handling and records direct/adopted child reaps. Completion requires
ECHILD and all pipe EOFs. An independent external watchdog remains mandatory.

The SHA implementation is adapted from retained pinned Linux sources. Three
standard literal answers, five independently calculated boundary vectors and an
update-state guard form a nine-line C harness. The separate actual-C stimulus and
driver specify25 bounded root cases plus one actual builder-identity rejection.
They exercise literal argv0/empty arguments/environment/cwd/stdin, concurrent
pipe pressure, limits, real signals versus exit143, timeout, interruption,
inherited/escaped pipe holders, post-sealing source replacement and malformed
input boundaries. All requests and expectations are retained independently.
No source helper was imported and no C fixture was executed during this review.

Independent source review covered SHA, child/setup/process ownership/waits,
file/seal/artifact/report handling, actual-C stimuli/driver and the dedicated
root profile. The source versions and findings are preserved in the linked
retention manifest. Corrections include interruption/deadline races, independent
proc-exe sample labeling, unavailable artifact creation versus an actual empty
file, preserved mismatching second-stat observations, independent copied-input
comparisons, and exclusive entry-point evidence writes. The driver now begins
with a different parent cwd and an environment sentinel, so child setup must
actually change them.

`root_profile.py` only prepares a fresh dedicated tree and an exact Docker command
plan. The parent owns its execution, development lock, full inspect validation,
raw command capture, first-failure logging and verified container cleanup. The
same pinned image, four CPUs/12GiB/no added swap/512PIDs, no network, dropped
capabilities and read-only root/repository remain required. Only the new dedicated
work tree is a writable host bind. UID0/group0 are explicitly configured and
observed without unnecessary privileged group mutation. The original builder
wrapper remains byte-identical. The collector uses original memfd creation flags
for the actual Linux5.15 host and fails closed on a no-exec/seal restriction.

Next, the parent can perform a source-bound pinned build, the nine-line SHA
check, the actual builder block and the separately reviewed isolated root25
batch. Complete original failures, compiler dependencies/ELFs, actual process
records and every archive member must be retained. Additional adverse storage,
late-interruption, setup-channel, stalled-collector and ownership-overflow tests
remain explicitly listed in `tests.md`. None of those checks can release a
catalog case, enable `run.py`, stand in for guest native provenance or establish
whole-OS readiness.

The additive source/retention index is
`stability-linux-collector-source-review-20260913-1.json`.
