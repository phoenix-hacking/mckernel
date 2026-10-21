# Actual33-scenario getter snapshot result acceptance

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: ACCEPT_PASS_FINITE_ACTUAL_GET_MEMPOLICY_SNAPSHOT at the reviewed actual
Rust caller/controlled-callback boundary. All33 scenarios/66 actual-body calls
pass. Reuse source-union recorde26aeb31 and exact fixture reviewbe276c32; no
unchanged source inventory, production-body review or test replay was performed.

The actual34-line output contains all33 named scenario passes and the exact final
summary. Each pass follows the independently checked return/events/complete
guarded output-byte expectations for both original and candidate actual bodies.
Stable cases agree. The two deliberate still-live overwrite witnesses preserve
their expected differences: candidate mode/requested mask prefix use the snapshot
captured before simulated unlock; original bodies observe the documented later
policy payload. These are controlled ordering witnesses, not real free/race tests.

The passed oracle also checks five mask lengths0/1/9/32/32, default/zero-output
suppression, VM fallback, invalid-range and each missing callback, copy failures,
validation, NODE/MEMS_ALLOWED fast paths and wrapping lookup end0. Lookup/search
occur under the simulated read-lock state; usercopy occurs after unlock; normal
and error event traces balance unlocks. Full VM/range bytes remain unchanged;
full policy bytes differ only by the two explicit callback overwrites. Complete
mode/mask guard arrays match expected bytes. All three typed allocations use
the reviewed final-heap in-place initialization, closing the static padding
oracle defect without changing production bodies or expectations.

Compile/link PID2430910/start35600296 and actual33cases PID2430925/start35600346
both exit0 with empty stderr. Both records have direct child join, absent group,
closed streams and no timeout, unexpected member, capture or retirement error.
Outer PID2430907/start35600288 exits0 in0.6476230119587854s with agreeing
started/direct-wait/direct-join/whole records and the same positive closure.
Outer stdout158bytes and empty stderr match their records. All six inner/outer
raw stream sizes and SHA256 values were independently compared and match. The
actual outer argv equals the exact corrected proposal. Dispatcher reports CPU6
released after complete closure.

Root grant7e921849 binds reviewbe276c32, CPU6/1GiB per process,35s outer and the
exact proposal limits asserted by the runner before commands. It records a
4GiB aggregate ordinary envelope/maximum4jobs, split into CPU6 and independent
CPU7 envelopes, with no census/LAST window. MemAvailable28,397,637,632bytes
exceeds the minimum. Host42,135,465,984 exceeds18,001,952,768required; scratch
14,145,933,312 exceeds13,706,985,472. Those requirements preserve both floors
plus640MiB reserve and the additional144MiB aggregate growth for the concurrent
CPU7 terminal-body check. No heavy/profile expansion is inferred from overlap.

Exact accepted evidence:

- check-1/result.json: `afd21ef58ca573b1a30d7f77d12d6a11c0db75f7b98f8db72fe51221de9c1cb9`
- check-1/actual-33-cases/stdout: `0e419d0256935dc0bf0945543beb0039b6f0473d00e833002ab55ef2f820fabf`
- actual-outer-capture-1/grant.json: `7e921849c2c9e92dcb269d33b584e2e6fcbd8d93955ea2b12f9ab69670c71042`
- actual-outer-capture-1/whole.json: `13b61587b15fe770846f0df397273b250099e9233411ace2903c5f990da6efaf`

The first executed candidate passes; zero executed failure corrections were
used. The original statically blocked padding fixture remains preserved and is
not retroactively called tested. This closes the finite caller-fixture
prerequisite only. Coherent shared integration still belongs to root with the
accepted source union and exact current preimages; no integration occurred here.

No actual C getter equivalence, kernel lock implementation, writer/free/native
concurrency, allocation lifetime after true reclamation, VM-wide fallback
synchronization, full production crate/ABI, final link/default activation, native
mbind/get_mempolicy, current image or compute-C retirement is accepted. The
independent traversal22-case result remains distinct. Current image/retained
ownership gates are unaffected.

Reviewer actions were retained result/command/grant/birth/wait/join/stream reads
and hashes plus this private report. No execution, root/guest, lease, Git or
shared-source operation was performed.
