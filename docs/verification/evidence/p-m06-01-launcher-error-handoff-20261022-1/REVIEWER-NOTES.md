Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private coherent launcher error handoff; no shared integration, heavy build,
module, guest, Git or frozen SDK68/cbb04 runtime mutation. Source counterpart is
executer/user/rust/mcexec_helpers.rs, exact current preimage da71f316. Preserve
any later shared edits by applying/reviewing this patch against that preimage.

The actual mailbox response-ledger, ExecDelivery phase completion and
EXEC_USERCOPY_DONE consumers are ALREADY in shared current Rust. Reimplementing
these accepted bodies would duplicate work. The remaining real launcher caller
still swallows page-transfer failures: transfer_image logs ioctl failure then
breaks its inner loop and eventually returns0. Reuse the accepted previous
page-failure propagation candidate and its three success/page1/page2 body results.
Its real fatal act_execve caller path uses existing command-server cleanup and
process-exit(1) bridges; no C implementation or ABI addition.

This packet additionally closes three same-boundary phase2 callers that attempted
a guest RET and returned0 after descriptor allocation, descriptor download, or
cloexec failure. Actual kernel/syscall.c do_execveat calls munmap_all before
request.args[0]=2; the old guest userspace is already destroyed. Returning to the
worker loop with a failed/pending replacement is incorrect. Every branch now
returns-1 to the existing fatal process path. No synthetic guest RET, ACK,
response release, child/VM/CPU credit free or ownership cleanup is introduced.
Actual backend pending DONE/claims and uncertain publication stay retained.

Validation: one pinned Rust1.92 compile and three NEW actual-body host cases
passed in0.627s combined. These compile exact extracted transfer_image,
act_execve_phase2 and act_execve postimage bodies, with ABI-shaped host fixtures.
alloc/descriptor/cloexec each exits1 through actual Rust process branch and
checks exact expected events; any guest RET panics/fails the oracle. Descriptor
failure stops before pages; cloexec failure follows all4page writes/close-exec,
then terminates without successRET. Compile emits2fixture-private-interface
warnings, preserved. No candidate failure/correction occurred in this family.
All4supervised commands COMPLETED with cleanup_complete=true and closed captures.
These functional host-body fixtures are NOT real app/native proof. Prior accepted
suite is reused, not rerun. No practical check/milestone/retirement credit.

Command executed once:
/usr/bin/timeout --signal=TERM --kill-after=2s 30s /usr/bin/taskset -c 0 /usr/bin/prlimit --as=1073741824:1073741824 --cpu=20:20 --fsize=33554432:33554432 --core=0:0 --nofile=256:256 -- python3 /home/holden/mckernel-work/host-preparation/p-m06-01-real-consumer-join-20261022-1/run-checks.py

Execution grant: root ordinary CPU0/1GiBAS/20CPU/30wall, output only this fresh
private root. Existing project scripts/application-tests/supervisor.py owns each
compile/test subprocess collection. Every child is joined; no live child remains.

Prior compiler33 authority:
docs/verification/evidence/exec-reset-production-four-object-accepted-20261021-1/ROOT-ACCEPTED-COMPILER33-RECORD-1.json
acceptance3d7dc040 / physical911d. This is compute exec-reset Rust/native+legacy
crate and selected/policy-off C object feedback, NOT this launcher or full module.
Previous launcher body evidence:
/home/holden/mckernel-work/host-preparation/native-exec-delivery-transfer-rust-repair-20261021-1/launcher-error-propagation-1/actual-body-comparison-1/result.json
Previous phase completion retains original failed/then corrected pending RET
family in phase-completion-postimage-1/pending-error-ret-correction-1; do not
reset that family or replay rejected source designs.

Next executable prerequisites after independent source review/root integration:
1. Pin this new source in a fresh selected existing launcher build; use actual
   executer/user/CMakeLists.txt default ENABLE_RUST_USER_TOOLS=ON, ARCH=x86_64,
   pinned Rust; cmake --build <reviewed-build> --target mcexec -j2. Require a
   linked ELF with unique transfer_image/act_execve/act_execve_phase2 definitions
   supplied by selected Rust object and resolved existing exit bridges.
2. Independently released current matched SDK module compile/link must include
   ExecClaimGroup/ExecDelivery/application ABI20/21 real consumers. Existing SDK68
   frozen tuple is not silently updated and compiler33 is not module proof.
3. Fresh independent runtime release for199B real static Rust self-exec case,
   exact stdout/emptyerr/37, actual bytes/status/kernel log/retirement. Then real
   selected process exec/wait app235B/twochild37+42/EOF/positivewait/ECHILD/owned0
   with authentic CREATE_PPD/alias revoke/finalACK prerequisites. No replay of
   held/rejected requests, no mock fixture as replacement for this app gate.

Known remaining boundary: do_syscall_return is an existing void ABI that logs
RET ioctl errors and caller cannot observe its status. This patch does not claim
successful final RET/publication from source/body tests; actual matched runtime
publication and backend uncertain ownership remain required. No child-credit
storage, cpu.c/process.c fixes, or compute C functionality was modified.
