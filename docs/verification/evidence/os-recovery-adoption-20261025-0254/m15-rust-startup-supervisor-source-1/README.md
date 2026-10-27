# Fixed original Rust startup collector successor

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is one private original `startup.argv-empty` collector. It reuses the
actually qualified F05 source81bb generic process supervisor and PID1/helper/
serializer operations. Existing F05 source, artifact908f and its36-control
qualification remain unchanged and retain their original scope. This new
startup source has not been compiled or executed.

The startup execution array is exactly
`/bin/mcexec -t 1 0 app A "" B`. `profile.rs` owns that fixed array; the actual
supervisor and report serialization both consume it. The qualified CString
conversion retains the zero-length element and adds a final NULL pointer.
The unchanged two environment entries and `/case/work` cwd remain selected.
There is no runtime argv parser, environment expansion or case-selection mode.

The original Cstartup `#else` boot invocation is **only `/bin/native-boot`**.
This source copies it verbatim as `profile::BOOT_ARGV`. The separate process
profile's `hidos allow_oversubscribe` invocation is not selected. This resolves
the concrete profile discrepancy using the original startup source contract;
no current-helper adaptation is silently claimed. Any later necessary helper
adaptation requires its own disclosed source-bound review.

The F05 observer implementation, lifecycle module, gate, incremental kmsg and
observer-completion requirements are absent from this startup build. Extracting
the qualified constant-None path also removes the unused observer parameter
and its no-op call sites. Actual process supervision, captured streams, raw
status, error stages, original10s deadline,100ms TERM-to-KILL delay,2s reap
reserve and irreversible leader/group signal custody remain reused. The
original startup post-reap check requires readable empty numeric procfs within
the same absolute5s window. It does not claim F05's separate lifecycle proof.

One final native raw `klogctl(3)` snapshot remains262144B, saved and published
without rewriting. There is one4096B `ND_PAYLOAD` frame with the original stream
fields,1024B retention per stream, helper evidence, printk restoration and
poweroff-return rejection. The collector120s and outer native300s bounds remain
unchanged. The original5298 full evaluator and exact startup oracle remain
unchanged. The be6e raw41/35B-stderr failure and owner1 are preserved; the
observed mismatch establishes a collector composition defect, not an executor
defect or a successful correct-argv startup run.

`PREDECESSORS.json` records24 rehashed source/proposal/evidence references.
`QUALIFIED-BASE-EXTRACTION.patch` makes the source extraction reviewable.
`COLLECTOR-CASEPROFILE.json` declares the exact startup contract, source closure
and currently unbound artifact/HOST/native qualification fields. Root must bind
the actual new artifact and qualification, then coherently bind staging.init,
overlay/finalmap, derived initramfs, manifest and source publication. Metadata
alone cannot prove the compiled collector profile.

`fakeexec.rs` is a small HOST-only Rust helper, never a replacement mcexec or
guest payload. It checks actual raw argc8, all eight argv values including the
empty element, argv8=NULL, the two actual environment values and env2=NULL.
Only exact input produces the original startup stdout. Wrong process-profile
argv or a dropped empty argument preserves raw41 and the original35B error.
Paired tests pass the same source-owned array to the real supervisor and check
its actual bytes/status together with the report. A separate real-child test
checks the requested fresh private HOST cwd. No payload environment variable
is added: the helper path is bound at test-harness compile time.

Six applicable real-child HOST tests, two leader-custody controls and five
stream/frame/deadline controls are retained; three focused startup controls
bring the prepared total to16. No controls have run in this source lane.
`HOST-QUALIFICATION.json` proposes one finite CPU6 ordinary sequence using the
already accepted compiler/profile, with serialized tests and one compiler job.
It grants no actual execution. Root owns independent source/unsafe review,
actual compiler/artifact/HOST qualification, current admission and native
release after positive retirement of the failed be6e owner.

Only this private directory was written. No compiler, test executable, actual
signal, module, guest, Docker/sudo, account/clock/resource query, cleanup,
canonical/Git operation or subagent was used. Formatting parsing is the only
executable source check. Fixed2026-10-28T05:36:09Z and inherited earlier actual
clock/account/credit/real-hold/resource controls remain unchanged.
