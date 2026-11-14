# Private Rust launcher error-propagation candidate

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source-only; uncompiled, unexecuted, no integration/acceptance/activation credit.
CPU6 bounded preparation only. Root owns integration, compiler/release/Git.
No shared or frozen source, compute C, host module, sentinel or launcher artifact
was changed. Candidate is derived exactly from accepted da71f316 source in
SOURCE-PACKET.json. Original bodies are retained next to extracted candidate
bodies. The separate provider owner owns exec claim groups/phase completion.

## Two real propagation points

Original transfer_image3376-3469 logs failed page MCEXEC_UP_TRANSFER via perror,
breaks only that section's page loop, advances sections, then returns0. Candidate
returns-1 immediately after the same diagnostic. Phase/direction/size/address,
zeroing/read ordering, signatures, original sentinel and all unrelated code stay
byte-identical.

In actual caller act_execve_phase2:2378, nonzero transfer_image produces the
existing image-failed diagnostic then returns-1; no image-ok/CLOSE_EXEC/cloexec
or success RET occurs. act_execve2441 propagates to main_loop_ret and returns1.
But act_main_loop_body2980 converts to worker result; thread_func3011 stores it
in td.ret; join_all_threads3039 discards td.ret. finish_main_image2437 returns0,
and another worker can leave that join waiting. Bare break->return therefore
does not prove a failing launcher process status.

The candidate's existing nonzero phase2 branch in act_execve retains the
main_loop_ret write, then uses existing cmd-server cleanup and process-exit
bridges exactly as act_exit2180-2187 does, status1. Existing C bridge
executer/user/mcexec.c:3076 is exit(term); no C repair or new ABI is needed. This
is a fatal post-replacement exec failure, not a synthesized guest success/error
RET. Any pending guest response/publication retains its original ownership until
normal launcher-death/OS retirement; this source candidate does not invent ACK,
release, cleanup or native proof. Process-exit/cleanup behavior needs independent
source review. The initial load caller finish_main_image2407 already returns-1
through mcexec_main_body4037 and C main; its behavior improves automatically.

## Cheapest next actual-body observation, only after root grant

The proposed actual-body-harness.rs includes exact extracted candidate
transfer_image, act_execve_phase2 and act_execve bodies, with narrow ABI-shaped
bridge mocks. Compile once using pinned reviewed ordinary Rust profile,
CPU6 <=1GiB; run success/page1/page2 as three separately captured subprocesses
under existing supervisor/timeout. No compile/tests have run in this packet.

Success checks original descriptor FROM_REMOTE direction1/64bytes, four actual
page TO_REMOTE direction0/4096bytes with physical advancement and full data,
both sections, image-ok, close-exec, cloexec and success-ret; exit0. Failure at
first/second page must stop remaining page/section work, retain perror and
image-failed diagnostics, execute cmd-cleanup and real harness process-exit1;
no image-ok/CLOSE_EXEC/cloexec/successRET. Frozen expected streams are provided
beside the harness. Strict byte/stderr/exit matching uses existing capture
machinery; no new native execution harness is introduced.

One original-body mutant comparison can substitute the retained original
transfer_image only: its failed ioctl will continue later sections and eventually
emit success-ret/exit0, rejected by unchanged failure oracle. Never call that
historical known-bad behavior an acceptance result. Proposal is not permission.
Preserve first failure; allow one bounded correction per family then escalate.
Host provider activation/native exec remain independently blocked until matched
modules and reviewed execution release. No repeat host trace is needed here.

The prior self-exec case metadata message incorrectly said193 bytes. Its frozen
expected.stdout, Python EXPECTED and oracle hex agree on199 bytes/SHA c415fd7c;
the actual immutable expected bytes remain unchanged. That prose correction is
recorded additively here without editing the prior frozen case.
