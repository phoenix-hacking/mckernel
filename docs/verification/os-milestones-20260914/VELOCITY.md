# Functional McKernel progress — review 166

Updated 2026-10-21T23:18:05.803098+00:00. Next review23:47:18.663UTC.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Canonical progress:24/35 practical checks; six whole milestones complete
(M00,M02,M03,M04,M10,M11). Native behaviors30; Rust paths21production/18native.
Leading accepted counts:97coherent source units(38OS/59infrastructure),
33production compiler batches and11native batches.

This interval added2sources,1native batch and1native behavior; no practical
check or whole-milestone gain. The current119B nonempty NUMA native acceptance
is genuine; owner37.482589779s. Root checkpoint564e58e3 is pushed/fetched.

Completed and pending work\n\nActual119B nonempty NUMA native case independently accepted and root-adopted; owner37.482589779s, all7steps/3readbacks. Genuine incremental source dedup/root adoption97(38OS/59infra). Checkpoint564e58e3 pushed/fetched selected ledger blobs. Exec pure plan/cursor11actual cases and response-ledger4host-body cases accepted; target/native not proven. Launcher propagation3bodycases pass, success0 and page1/page2failure1, cleanup/exit ordering; independent review scoped mocks/no target compile. M05 resource-v2 adapter correction and exact two-CPU67 collector/decoder correction pass with stale66/altered68 refusals; original machinery/failures retained. M07 current053d app+bootstrap stage accepted60members/58unchanged, no kernel rebuild/guest.

M06 mailbox completion/post-user-copy COMMIT/ABORT four-case candidate ready uncompiled/unwired; real mapping/claims/default/link/native remain gates. Corrected launcher target build not yet accepted. M05 changed full-static collector and exact runtime stage/bindings not yet accepted; no public-restoration cycle. M07 third-readonly-root/10-source normalization packet0118f2fb ready, normalization/runtime/native unrun. SDK66 storage fixed-capacity gate remains blocked; active no-resize prevails.

Velocity and next actions\n\nSince review165: +2 coherent source units,+1 accepted native batch,+1 native behavior; no practical/whole/Rust-path gains. Ready work moved from one dispatcher to disjoint CPU6/7 ordinary checks alongside checkpoint after a causal foreground steer; both completed. No overall4x engineering claim. Native119 compile-reference-to-raw79.2478min includes waits/bindings; owner37.48s only. Latest six-app regression8.09455/min informational2.97882x baseline; historical20-app6.332426x scope remains separate.

Prioritize completion-hook actual body gate and real linked/provider obligations; avoid another new framework or broad readiness audit. Run only changed M05 static collector and current-profile stage; reuse accepted v2 probe/model/lifecycle artifacts. Finish M07 normalizer with exact third readonly root once. Overlap disjoint ordinary work within grants; root alone serializes heavy/native releases. Count source once only after actual dedup/adoption; body/app compile not production batch.

Milestone limits\n\nSix complete M00/M02/M03/M04/M10/M11. M07 broader exit still open despite2/2. M12 profile buckets remain separate: eligible2CPU1boot/6launches, no public10cycles/100launches/60productive minutes. M09 integration estimate is not whole-kernel Rust conversion.

Resource controls remain: one heavy workload onCPU2-5/4jobs/12GiB/512tasks;
ordinaryCPU6/7 grants only, host16GiB/scratch12GiB floors, preserved scratch21
container/exclusions and permanent mutex27:4. No resize or capacity bypass.
Current resident was not restarted; future visibility fix5b66b7f2 has17tests.
