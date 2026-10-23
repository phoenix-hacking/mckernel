# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import pathlib,json,hashlib,shutil
P=pathlib.Path(__file__).resolve().parent; R=pathlib.Path('/home/holden/mckernel'); E=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1'
def ident(p):
 b=p.read_bytes(); return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
prior=R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/next-memory-bridge-rust-20261023-1/NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json'
recipe=json.loads(prior.read_text()); closure=P/'fullcrate-preparation-1/source'; inputs={}
for rel in recipe['source_inputs']:
 canonical=R/rel; source=P/'source'/rel if (P/'source'/rel).exists() else canonical
 dst=closure/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,dst)
 inputs[rel]=dict(canonical=ident(canonical),private=ident(dst),modified_target=source!=canonical)
argv=recipe['argv'][:]
for i,a in enumerate(argv):
 if a.startswith('--emit=obj='): argv[i]='--emit=obj='+str(P/'fullcrate-preparation-1/mckernel_rust.o')
 if a.endswith('/source/kernel/rust/lib.rs'): argv[i]=str(closure/'kernel/rust/lib.rs')
plan=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='NOT_EXECUTED',execution_authority=False,argv=argv,compiler_sha256=recipe['compiler_sha256'],source_inputs=inputs,source_input_count=len(inputs),prior_exact_profile=ident(prior),profile=recipe['profile'],expected_symbols=dict(T=['set_timer','process_sched_set_timer_bridge'],not_U=['set_timer'],new_U=['process_timer_runtime_offsets','process_timer_spin_lock_bridge','process_timer_spin_unlock_bridge','process_timer_lapic_enable_bridge','process_timer_lapic_disable_bridge'],already_U=['time_sharing'],wholecrate_U_count=597),whole_C_TU_default_link_native='OPEN')
(P/'NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json').write_text(json.dumps(plan,indent=2)+'\n')
# Keep the ABI compile narrow: actual timer header, exact source-bound public process declaration.
(P/'fixture/abi.c').write_text('''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <sched_helpers.h>
/* Exact kernel/include/process.h declaration, hash bound in SOURCE-BINDINGS.json. */
void set_timer(int runq_locked);
_Static_assert(sizeof(unsigned long)==8,"ulong64");
_Static_assert(sizeof(int)==4,"int32");
_Static_assert(sizeof(struct timer_runtime_offsets)==120,"existing15offsets");
_Static_assert(__builtin_types_compatible_p(__typeof__(&set_timer),void (*)(int)),"set_timer ABI");
''')
leaf=dict(scope=plan['scope'],status='NOT_EXECUTED',execution_authority=False,argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(P/'fixture/run_fixture.py')],profile='CPU6 onejob/AS2147483648/CPU60/wall90+6/FSIZE33554432/NOFILE256/core0/RUST_MIN_STACK2097152; inherited affinity and rlimits via accepted990 owned_capture + signal handlers; Rust1.92/GCC9 CGU1',capture_helper=dict(path='/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py',sha256='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'),files={str(p.relative_to(P)):ident(p) for p in (P/'fixture').iterdir() if p.is_file()},expected_pairs=25750,source_parse_required=['PUBLIC selected set_timer declaration only; fallback original body exact','PUBLIC offset descriptor + four callback symbols global; fallback static','private production harness removes only obsolete weak set_timer, requires T set_timer and five new U, preserves existing U time_sharing, exact U ledger 593->597'],whole_C_TU_default_kernel_native='OPEN')
(P/'NEXT-LEAF-RECIPE.NOT-EXECUTED.json').write_text(json.dumps(leaf,indent=2)+'\n')
(P/'READINESS.md').write_text('''Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source candidate only; no compiler, app, root or target instruction was run.

Selected actual body: kernel/process.c set_timer(int), 12 lines including signature/braces.
Existing consumers: process_sched_set_timer_bridge in process_helpers.rs (used by Rust wakeup/schedule paths), cls.rs preemption path, and process.c scheduler calls. Public declaration kernel/include/process.h:909 is unchanged. Before: actual full Rust object needs U set_timer. After expected: one Rust T set_timer, no C PUBLIC definition/no U set_timer.

Rust preserves current-CPU lookup before the mutable time_sharing load, existing descriptor address, exact runq_locked signed int, four callback addresses and ignored signed return. It introduces no early return, lock, timer operation or struct layout. Existing Rust timer_set_timer_body_result remains unchanged. C offset table and four unchanged callback bodies become externally visible under existing PROCESS_SCHED_PUBLIC_BRIDGE; fallback remains static and original set_timer body is verbatim inside !MCKERNEL_RUST_PROCESS_HELPERS. C providers are retained ABI boundaries, not newly ported C implementations.

Focused fixture extracts the original C body and actual Rust wrapper and existing timer body. Both wrappers route through a capture-only C shim then the real existing Rust timer algorithm. Host models are explicitly fixture-only. 25,600 valid CPU cases plus25 NULL-CPU cases and125 arbitrary signed provider-return/mutable-global-order cases compare exact args, ordered callback events and final timer state. It models lock/runqueue state; it never executes lock ASM, APIC, root, guest or production state instructions. ABI compile uses actual sched_helpers.h and source-bound exact process.h declaration.

Private exact run_equivalence.sh delta removes obsolete weak set_timer, adds the five provider bindings, changes U set_timer to T set_timer, and updates expected total U593->597. Existing U time_sharing is retained. Broad harness execution has not occurred; these host bindings are not production providers.

Next executable observation: run NEXT-LEAF-RECIPE.NOT-EXECUTED.json once under dispatcher CPU6 grant/accepted990 capture and handlers. Then independently authorize pinned nightly exact78-input production Rust command; it remains NOT_EXECUTED. Whole process.c TU, default kernel link and native call path remain OPEN. No body/whole-file retirement credit.
''')
E.mkdir(exist_ok=False)
for rel in ['prepare_source.py','prepare_plan.py','SOURCE-BINDINGS.json','PRIVATE-PRODUCTION.patch','ORIGINAL-set_timer.c','READINESS.md','NEXT-LEAF-RECIPE.NOT-EXECUTED.json','NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json']:
 shutil.copyfile(P/rel,E/rel)
shutil.copytree(P/'source',E/'source'); shutil.copytree(P/'fixture',E/'fixture')
print(json.dumps({n:ident(P/n) for n in ['SOURCE-BINDINGS.json','PRIVATE-PRODUCTION.patch','NEXT-LEAF-RECIPE.NOT-EXECUTED.json','NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json']}))
