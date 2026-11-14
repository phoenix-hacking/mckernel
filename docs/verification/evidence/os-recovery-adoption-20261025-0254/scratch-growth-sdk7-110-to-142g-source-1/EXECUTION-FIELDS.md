Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source-only finite growth candidate; no root execution or scratch mutation occurred.

Invocation (dispatcher fills all absolute paths and SHA256 values after independent review):

    python3 -B /absolute/grow_scratch.py --source-sha256 SHA --contract /absolute/contract.json --grant /absolute/grant.json --grant-sha256 SHA --review /absolute/review.json --review-sha256 SHA --output /absolute/fresh-output --execute-exact-growth

All references use {path:absolute,bytes:integer,sha256:hex}. Contract is byte-bound by grant.contract. Grant and review bindings are exactly {source,previous_serial_operation,nonce,before,after}; before/after use grow_scratch.expected(OLD/NEW). Grant.status GRANTED_SCRATCH_GROWTH_110_TO_142G; commands exactly grow_scratch.COMMANDS; lower_reserves false. Review.decision PASS_SCRATCH_GROWTH_EXECUTION, grant ref, same bindings, implementation_ownership false and independent reviewer name.

Contract fields required:

- previous_serial_operation: native2 projection reference, exact SHA f18a78021d4f801d54c556a60d8ae751c31c3681c4dafceb00e813efdebeb268; nonce: new unique operation nonce.
- native2_current_acceptance: CURRENT290-NATIVE2-INDEPENDENT-POSTJOIN-ACCEPTANCE.json reference.
- fixed_cutoff: reference to ROOT-NEW18H-20261026-FIXED-CUTOFF-BINDING.json, exact SHA256 2e1d3fa8338e51973cf0af5677e7e256259aff539adb164be0fb53240d834b35. Guard checks same boot 7bfc5687-6c04-4d15-84eb-b92ab9a55dcb and exact wall1793100290 / monotonic882395.5689528405 / boottime897734.6960034363 at entry, child launches and final release. Every clock must remain strictly before cutoff.
- boot_id: current Linux boot ID; issued_wall, expires_wall: Unix seconds; expiry <= 2026-10-27T11:24:50Z. Preflight needs >600 seconds remaining; every child launch >300 seconds remaining.
- source_only false; execution_authority true. No source-only template releases execution.
- account_guard: {status:PASS_CURRENT_ACCOUNT_GUARD,observed_wall:Unix seconds,allowed_until_wall:Unix seconds}. Must be <=120 seconds old and cover expiry. Helper separately reads current state.json and checks fixed current thread/budget ID and amount, positive remaining, no budget error/spend-control flag, running phase, heartbeat <180 seconds.
- quiescence: {status:PASS_EXCLUSIVE_SCRATCH_GROWTH,observed_wall:Unix seconds,no_native_owner:true,no_Docker_owner:true,no_other_heavy_owner:true,no_SDK_lease:true,paused_consumers_reconciled:true,scratch_exclusive:true}. <=120 seconds old at final preflight. Dispatcher supplies this independently reviewed actual fresh ownership observation; helper does not probe Docker or alter shared records/SDK leases. The permanent mutex remains held throughout actual commands.
- mutex: {path:/run/lock/mckernel-development.lock,identity:{device,inode,uid:0,gid:0,mode:420,nlink:1,size:0}}. Set exact freshly observed permanent node device/inode. Open NOFOLLOW|CLOEXEC, flock EX|NB; no creation and no LOCK_UN.
- critical_files_manifest: reference to CURRENT-CRITICAL-PRESERVE-FILES.STATIC.json (five byte/SHA/identity records); scratch21_manifest: reference to SCRATCH21-PRESERVE-NODES.STATIC.json (24 node records). Hash/identity checked before/after. Grant binds both through contract.
- root_directory: {path:/home/holden/mckernel-work/scratch,identity:{device,inode,uid,gid,mode,nlink,size}} with mode permission bits (not S_IFDIR). Checked before/after.
- output_path: fresh absolute host-filesystem output directory, never on scratch; dispatcher must bind this location to its capture reserve.
- cpu_affinity [2,3,4,5], jobs 1, address_space_limit 2147483648, aggregate_limit <=12884901888. Dispatcher accounts for all other owners in quiescence; helper sets its affinity/AS limit.
- capture_bytes and emergency_bytes: positive finite reservations in bytes. HOST available must cover 32GiB growth + entire new sparse gap (142GiB minus current allocated bytes) +16GiB floor +8GiB headroom + these reservations. Scratch floor 12GiB before/after.

Frozen geometry: backing 110->142GiB, same device66306/inode47468427/root0600/nlink1; loop36 major7/minor36, offset0/sizelimit0/autoclear1/ro0, exact loop capacity, ext4 mount device1828/options/UUID. Tools have frozen SHA256. Dumpe2fs read-only geometry captures are separate from the three approved mutating commands. Final ext4 block count37224448, blocksize4096; reserved ratio original288358/28835840 within one block. No tune2fs/reserve lowering/rollback/shrink/delete/cleanup.

Outputs: exclusive fresh output directory; fsynced JSONL journal, separate child stdout/stderr, direct wait/argv/PID/return code/elapsed/rusage records; actual-commands.json status PASS_ACTUAL_SCRATCH_GROWTH_COMMANDS and grant/review/binding refs. Preflight checks the existing soft RLIMIT_FSIZE is unlimited or at least152471339008; it never widens this limit. Before mutation errors close only the helper's own mutex FD if no child remains unjoined and no spawn acquisition is uncertain. Before Popen the helper marks acquisition pending and masks handled signals through child ownership/raw proc-stat birth assignment. Every child, including read-only dumpe2fs, requires a positive direct wait. Unknown spawn or unjoined read-only child retains the actual mutex FD in quarantine just like a mutating attempt; no kill or retry. Once any mutating command is attempted, any error or caught signal quarantines helper indefinitely with its actual FD retained and child untouched. Journal storage failure cannot release an uncertain owner. Dispatcher must reconcile actual PIDs/effects; no automatic retry or rollback.

Success masks handled signals across closing its own FD and updating closure state, then emits FD-CLOSED with holder PID and parent_must_prove_retirement true. It does NOT emit normal_fd_release or a closed growth closure, holder_retired or group_absent. Parent directly joins and proves current process/group/streams retirement, writes PASS_NORMAL_FD_RELEASE; an independent reviewer then supplies fresh current physical acceptance and the mckernel.scratch-growth-closure.v1 chain consumed by growth_successor.py. No automatic acceptance.

After successful mutex FD closure, a publication fault reports POST_CLOSE_EVIDENCE_FAULT with external_postjoin_required via stderr/nonzero exit. It never reacquires the FD or claims retained custody. Parent must obtain actual join and physical evidence independently.
