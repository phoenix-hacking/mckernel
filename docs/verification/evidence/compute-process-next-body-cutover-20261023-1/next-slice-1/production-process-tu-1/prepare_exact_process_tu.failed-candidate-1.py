# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Source/read-only preparation only. No root/Docker/compiler/build/new TU launcher.
from pathlib import Path
import ast,hashlib,json,difflib,shutil
P=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');E=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1/next-slice-1/production-process-tu-1'
C9=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-9/default-image-preparation-1')
OLD=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-5/actual-owner-consumer-correction-1/next-build-preparation-1/pinned-full-image-attempt-2/owner-work')
LAY=P.parent/'production-abi-layout-1';S=P/'source-overlay';S.mkdir(exist_ok=False)
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(name,d):(P/name).write_text(json.dumps(d,indent=2)+'\n')
manifest=C9/'source-materialization-attempt-1/source-inputs.json';m=json.loads(manifest.read_text());assert pin(manifest)['sha256']=='fbd125807193835f88905d0c89d985dd9a0a066265598b09accd69d6fe25f3ea'
canonical_record=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1/next-slice-1/CANONICAL-INTEGRATION.json';assert pin(canonical_record)['sha256']=='e8290a189f27384e3ceed24a2d8f9385df56bc9640813f00d432e57b2f03a7c9';cr=json.loads(canonical_record.read_text());overlay={}
for rel,row in cr['postimages'].items():
 assert m['materialized_repository_files'][rel]==cr['preimages'][rel]['sha256'] and pin(R/rel)['sha256']==row['sha256']
 dst=S/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/rel,dst)
 overlay[rel]=dict(frozen_candidate9_sha256=m['materialized_repository_files'][rel],canonical=pin(R/rel),private=pin(dst),preserve_kind=m['materialized_kinds'][rel],preserve_materialized_mode=m['materialized_modes'][rel])
compile_db=OLD/'evidence/artifacts/compile_commands.json';rows=json.loads(compile_db.read_text());row=next(x for x in rows if x['file']=='/src/kernel/process.c')
abi_checks=OLD/'evidence/production-abi-checks.json';prior=json.loads(abi_checks.read_text());phase=next(x for x in prior['checks'] if x['phase']=='production-abi-process');assert phase['exit_code']==0
assert pin(OLD/'output/build/production-abi-process.c')['sha256']==phase['fixture_sha256']
driver=C9/'native_rust_exact_mckernel_image_offline.py';raw=driver.read_text();tree=ast.parse(raw);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_validate_reset_production_abi');proofs=next(ast.literal_eval(n.value) for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='proofs' for t in n.targets));suffix=proofs['kernel/process.c']
layout_recipe=json.loads((LAY/'EXACT-LAYOUT-WITNESS-RECIPE.GRANTED.json').read_text());values=json.loads((LAY/'ACTUAL-LAYOUT-VALUES.json').read_text());assert not values['differences'];assert len(values['values'])==130
assertions='\n/* Actual timer/spin Rust shared-type witness: sourcebound, no compute-C behavior. */\n'
for r,v in zip(layout_recipe['witness_rows'],values['values']):
 assert r['label']==v['label'] and v['C']==v['Rust']
 assertions+='_Static_assert(('+r['C']+') == '+str(v['Rust'])+'UL, '+json.dumps('M14 actual Rust '+r['label'])+');\n'
# Reuse the actual declaration/type checks from the approved real-header witness.
for line in (LAY/'source/actual_header_layout.c').read_text().splitlines():
 if line.startswith('_Static_assert('):assertions+=line+'\n'
(P/'ACTUAL-RUST-EXPECTED-ABI-ASSERTIONS.h').write_text(assertions)
fixture=(R/'kernel/process.c').read_bytes()+suffix.encode()+assertions.encode();(P/'production-abi-process.c').write_bytes(fixture)
# Finite derivative of the EXISTING consumer, no new execution mode/wrapper.
new=raw
for rel in ['kernel/process.c','kernel/rust/sched_helpers.rs']:
 before=m['materialized_repository_files'][rel];after=overlay[rel]['private']['sha256'];assert new.count(before)==1;new=new.replace(before,after,1)
anchor='M14_RUST_EXPORTS = ';i=new.index(anchor);new=new[:i]+"M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS = "+repr(assertions)+'\n\n'+new[i:]
new=new.replace("M14_RUST_EXPORTS = (", "M14_RUST_EXPORTS = ('spin_sleep_or_schedule', 'sched_spin_sleep_or_schedule_body_result', ",1)
anchor='    abi_rows = []\n';assert new.count(anchor)==1;new=new.replace(anchor,"    proofs['kernel/process.c'] += M14_TIMER_SPIN_PRODUCTION_ABI_ASSERTIONS\n"+anchor,1)
needle="    for symbol in ('set_timer','get_this_cpu_local_var','timer_set_timer_body_result','process_sched_set_timer_bridge'):"
assert new.count(needle)==1
new=new.replace(needle,"    _fail(not any(row[-2] in ('T','t') for row in rows(process_symbols, 'spin_sleep_or_schedule')),\n          'M14 original C spin_sleep_or_schedule body selected')\n    for symbol in ('spin_sleep_or_schedule','sched_spin_sleep_or_schedule_body_result',\n                   'set_timer','get_this_cpu_local_var','timer_set_timer_body_result','process_sched_set_timer_bridge'):",1)
needle="    unique(process_symbols, 'process_timer_runtime_offsets', 'R', 120)";assert new.count(needle)==1
new=new.replace(needle,"    for symbol in ('spin_sleep_or_schedule', 'process_sched_runqueue_offsets'):\n        _fail(not any(row[-2] == 'U' for row in rows(rust_symbols, symbol)),\n              'M14 spin wrapper/descriptor unresolved in production Rust: '+symbol)\n"+needle,1)
needle="    fields = ('thread_status_offset','thread_sched_list_offset','thread_spin_sleep_lock_offset',";assert new.count(needle)==1
new=new.replace(needle,"    _fail(re.search(r'\\bvoid\\s+spin_sleep_or_schedule\\s*\\([^;{}]*\\)\\s*\\{',pp,re.S) is None and\n          re.search(r'\\bvoid\\s+spin_sleep_or_schedule\\s*\\([^;{}]*\\)\\s*;',pp,re.S) is not None,\n          'M14 selected spin_sleep_or_schedule declaration/body exclusion')\n"+needle,1)
ast.parse(new);(P/'native_rust_exact_mckernel_image_offline.py.PREPARED').write_text(new)
(P/'EXISTING-CONSUMER-DELTA.patch').write_text(''.join(difflib.unified_diff(raw.splitlines(True),new.splitlines(True),fromfile='candidate9/native_rust_exact_mckernel_image_offline.py',tofile='private/native_rust_exact_mckernel_image_offline.py',n=3)))
# Ensure old source-independent behaviors/control/profile bodies are unchanged.
oldtree=ast.parse(raw);newtree=ast.parse(new);allowed={'_validate_reset_production_abi','_m14_check_set_timer_symbols','_validate_m14_set_timer_contract'}
oldfn={n.name:ast.dump(n,include_attributes=False) for n in oldtree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};newfn={n.name:ast.dump(n,include_attributes=False) for n in newtree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};assert oldfn.keys()==newfn.keys();assert all(oldfn[n]==newfn[n] for n in oldfn if n not in allowed)
operation= json.loads((C9/'next-build-preparation-1/NEXT-BUILD-OPERATION.READY-FOR-REVIEW.json').read_text());handoff=json.loads((C9/'next-build-preparation-1/WHOLE-CANDIDATE9-HANDOFF.json').read_text())
write('EXACT-NEXT-PRODUCTION-PROCESS-TU.OPERATION.NOT-RELEASED.json',dict(scope=cr['scope'],status='SOURCE_BOUND_EXISTING_GCC14_WHOLE_TU_PHASE_PREPARED_NO_EXECUTION',execution_authority=False,one_next_operation='Existing production-abi-process frontend phase after existing configure stage; full current process source + unchanged existing ABI suffix +130actual Rust layout assertions.',inner_argv=phase['argv'],inner_cwd=phase['cwd'],compiler=dict(path='/usr/bin/cc',expected_sha256='2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2',version='GCC14.3.1-4.4.el10',builtin_headers='/usr/lib/gcc/x86_64-redhat-linux/14/include',availability='accepted immutable image only; HOSTGCC9 is not a substitute'),compile_db=pin(compile_db),actual_selected_full_C_object_row=row,prior_same_phase_PASS=phase,prior_phase_receipt=pin(abi_checks),fixture=pin(P/'production-abi-process.c'),fixture_container_path='/work/output/build/production-abi-process.c',fixture_producer='Existing _validate_reset_production_abi; raw full currentprocess.c + existing proofs[kernel/process.c] + sourcebound130assertions. No TU-only rootlauncher/mode.',private_existing_consumer=pin(P/'native_rust_exact_mckernel_image_offline.py.PREPARED'),consumer_delta=pin(P/'EXISTING-CONSUMER-DELTA.patch'),expected_current_CpuLocalVar_current=7848,actual_layout_evidence=pin(LAY/'ACTUAL-LAYOUT-RECEIPT.json'),source_candidate=dict(frozen_candidate9_manifest=pin(manifest),frozen_candidate9_source_derivative=m['source_derivative_sha256'],frozen_candidate9_materialization=m['materialization_sha256'],preserve_other_entries=6959-len(overlay),preserve_symlinks=49,only_three_source_overlays=overlay,new_materialized_source_root=None,new_source_manifest=None,new_source_manifest_sha256=None,new_source_derivative_sha256=None,new_materialization_sha256=None),existing_container_profile=operation['profile'],existing_full_operation_lineage=pin(C9/'next-build-preparation-1/NEXT-BUILD-OPERATION.READY-FOR-REVIEW.json'),existing_owner=handoff['owner'],new_full_owner_request=None,new_outer_argv=None,source_producer_successor=None,root_aggregate_reservation=None,fresh_admission=None,independent_source_profile_review=None,independent_execution_release=None,precise_execution_dependency='GCC14 tool/header closure is image-only. Existing admitted owner/driver runs the full normal configure->ABI->Rustobject->kernel pipeline; it has no separately admitted TU-only selector. Root must first bind a coherent new source/producer/provenance/owner/request successor over the frozen candidate9+three overlays, publish/review it, and release the existing container profile at an eligible heavy boundary. This packet adds no standalone launcher.',C_frontend_qualifier='Successful -fsyntax-only wholeTU proves actual GCC14 selected source/layout/C callback declarations, not object ownership/final link/native.',later_object_link_obligations='Keep existing selectedprocess object compile, all timer/idle/memory/pageunmap guards; add spin Cbody exclusion, unique Rust/final spin/body T, no RustUspin/Cdescriptor. Do not require fictional Cspin import.',canonical_candidate9_P12_mutation=False,actual_compiler_runs=0,whole_TU_default_link_native='OPEN'))
report=dict(scope=cr['scope'],status='PASS_SOURCE_PREPARATION_ONLY',inner_argv_exactly_prior_accepted_GCC14_phase=True,all_old_driver_function_bodies_unchanged_except=sorted(allowed),new_functions_or_execution_modes=0,Python_AST_valid=True,source_overlay_count=3,new_source_identities_uninvented=True,canonical_candidate9_changed=False,compiler_Docker_root_heavy_runs=0,operation=pin(P/'EXACT-NEXT-PRODUCTION-PROCESS-TU.OPERATION.NOT-RELEASED.json'),CPU6_held=False)
write('PREPARATION-RECEIPT.json',report)
E.mkdir(exist_ok=False)
for path in P.rglob('*'):
 if path.is_file():
  dst=E/path.relative_to(P);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dst)
print(json.dumps(dict(operation=pin(P/'EXACT-NEXT-PRODUCTION-PROCESS-TU.OPERATION.NOT-RELEASED.json'),receipt=pin(P/'PREPARATION-RECEIPT.json'),consumer=pin(P/'native_rust_exact_mckernel_image_offline.py.PREPARED'),CPU6_held=False)))
