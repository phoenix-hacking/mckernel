# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import pathlib,json,hashlib,shutil
P=pathlib.Path(__file__).resolve().parent; R=pathlib.Path('/home/holden/mckernel'); E=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1'
def ident(p):
 b=p.read_bytes(); return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
source=(R/'kernel/process.c').read_text(); original=(P/'ORIGINAL-set_timer.c').read_text().rstrip(); expected=source.replace('static const struct timer_runtime_offsets process_timer_runtime_offsets','PROCESS_SCHED_PUBLIC_BRIDGE const struct timer_runtime_offsets process_timer_runtime_offsets',1)
for declaration in ['unsigned long process_timer_spin_lock_bridge','void process_timer_spin_unlock_bridge','void process_timer_lapic_enable_bridge','void process_timer_lapic_disable_bridge']:
 expected=expected.replace('static '+declaration,'PROCESS_SCHED_PUBLIC_BRIDGE '+declaration,1)
expected=expected.replace(original,'#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+original+'\n#endif',1)
assert expected==(P/'source/kernel/process.c').read_text(),'all other process.c bytes must be identical'
join=json.loads((P/'actual-leaf-owned-capture-1/whole-join.json').read_text()); fixture=json.loads((P/'leaf-output-1/receipt.json').read_text()); assert join['status']=='PASS_LEAF' and fixture['status']=='PASS'
assert (P/'leaf-output-1/02.stdout').read_text().splitlines()==['PASS original-C/actual-Rust wrapper pairs=25750; real existing Rust timer semantics plus callback/descriptor/ordering and ignored-return checks']
production=P/'NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json'; assert ident(production)['sha256']=='295d258e7c22789993770d6b155c21dfc16863179d992d92405aa6792b4790d3'
receipt=dict(scope=join['scope'],status='PASS_FOCUSED_LEAF_NOT_KERNEL',whole_join=ident(P/'actual-leaf-owned-capture-1/whole-join.json'),fixture_receipt=ident(P/'leaf-output-1/receipt.json'),source_bindings=ident(P/'SOURCE-BINDINGS.json'),patch=ident(P/'PRIVATE-PRODUCTION.patch'),source_selection=dict(all_accepted_process_fixes_and_other_bytes_unchanged=True,only_C_changes='existing PUBLIC linkage for immutable descriptor+4 unchanged callbacks; exact original set_timer body gated !PUBLIC',original_C_body=ident(P/'ORIGINAL-set_timer.c')),actual_artifacts={name:ident(P/'leaf-output-1'/name) for name in ['actual.o','abi.o','equivalence','02.stdout','03.stdout']},actual_header_closure={rel:ident(R/rel) for rel in ['kernel/include/sched_helpers.h','kernel/include/process.h','lib/include/types.h','arch/x86_64/kernel/include/ihk/types.h']},observation='25750 exact wrapper pairs; underlying existing Rust timer body; real15offset/120byte header ABI/64bit ulong/int32; leaf oneTset_timer/noUset_timer; captured CPU/descriptor/callback identities and ordering; signed return ignored',leaf_note='U timer_set_timer_body_result is intentional capture shim in focused fixture only; actual same-module production helper remains unchanged',CPU6_released=join['CPU6_released'],compiler_or_fixture_failures=0,corrections=0,next_production_recipe_NOT_EXECUTED=ident(production),whole_C_TU_default_kernel_native='OPEN',broad_harness_execution='NOT_EXECUTED',independent_source_ABI_review='REQUIRED_BEFORE_CANONICAL')
(P/'ACTUAL-LEAF-RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
for name in ['actual-leaf-owned-capture-1','leaf-output-1']:
 shutil.copytree(P/name,E/name)
for name in ['run_leaf_owned.py','export_leaf_receipt.py','ACTUAL-LEAF-RECEIPT.json']:
 shutil.copyfile(P/name,E/name)
print(json.dumps({'receipt':ident(P/'ACTUAL-LEAF-RECEIPT.json'),'whole_join':ident(P/'actual-leaf-owned-capture-1/whole-join.json'),'next_production':ident(production)}))
