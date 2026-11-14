"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact source/API/config/expectation preflight; execute no compiler or artifact gate.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,runpy
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel');B=E/'ROOT-SYNC-PROCESSVM-HOST13-FIVE-BUILD-ADMISSION-1'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(p.read_text())
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 plan=read(D/'COHERENT-NEXT-DEFAULT-SOURCE-PLAN.NOT-GRANTED.json');P=read(D/'PROFILE.SOURCE-ONLY.json');X=read(D/'INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json');expected=read(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json');old=read(B/'PROFILE.SOURCE-ONLY.json')
 for rel,row in plan['preimages'].items():assert ref(R/rel)==row
 for rel,row in plan['postimages'].items():
  assert ref(Path(row['path']))==row
  if rel not in plan['preimages']:assert not (R/rel).exists()
 assert len(plan['postimages'])==9 and plan['timer_included'] is True
 f3=read(Path(plan['F03_source']['path']));assert (D/'candidate/kernel/syscall.c').read_bytes()==Path(f3['source_postimages']['kernel/syscall.c']['path']).read_bytes()
 arch=(D/'candidate/arch/x86_64/kernel/syscall.c').read_text()
 for row in plan['F06_exact_sources']:
  b=read(Path(row['source']['path']));assert row['qualified_guard_before_line_restoration']==b['C_wrapper'];assert row['selected_C']==b['C_wrapper']+'#line '+str(row['following_logical_line_preserved'])+'\n';assert arch.count(row['selected_C'])==1;arch=arch.replace(row['selected_C'],row['original_C'],1)
  assert (D/'candidate'/row['canonical_module']).read_bytes()==Path(row['qualified_module']['path']).read_bytes()
 assert arch==(R/'arch/x86_64/kernel/syscall.c').read_text()
 timer=E/'f02-timer-layout-storage-next-current-source-1';timer_impl=read(Path(plan['timer_implementation']['path']))
 for row in read(timer/'SOURCE-ONLY-RESULT.json')['postimages']:
  rel=Path(row['path']).relative_to(timer/'candidate');assert (D/'candidate'/rel).read_bytes()==Path(row['path']).read_bytes()
 oldmap=read(Path(old['inputs']['source_directory_exports'][0]['manifest']['path']));newmap=read(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.FIVE.json');before={r['relative']:r for r in oldmap['files']};after={r['relative']:r for r in newmap['files']};assert len(after)==109
 assert set(after)-set(before)=={'arch_copy_to_user_bridge.rs','arch_copy_from_user_bridge.rs','arch_syscall_forward_context_bridge.rs'} and not set(before)-set(after)
 assert {n for n in before if before[n]['snapshot']['sha256']!=after[n]['snapshot']['sha256']}=={'process_helpers.rs','syscall_policy.rs'}
 for cfg in plan['new_Rust_cfgs']:assert [n for n in after if cfg in Path(after[n]['snapshot']['path']).read_text()]==['syscall_policy.rs']
 for name in ['abi.rs','sched_helpers.rs','waitq.rs','lock_helpers.rs','spinlock_helpers.rs','x86_memory_helpers.rs','lib.rs']:assert before[name]['snapshot']['sha256']==after[name]['snapshot']['sha256']
 runner=module('actual_existing_fixed_five_source_API',D/'run_build_only.py');assert ref(D/'run_build_only.py')==dict(ref(B/'run_build_only.py'),path=str(D/'run_build_only.py'))
 for n in ['build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py','capture_and_bind_resource.py']:assert (D/n).read_bytes()==(B/n).read_bytes()
 vector=copy.deepcopy(P);vector['request_sha256']='a'*64;assert len(runner.commands_for_plan(vector))==5
 rows=runner.source_directory_postimages(P);assert len(rows)==109
 refs=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[r['postimage'] for r in rows];assert refs==X['qualified_readonly_files']
 for row in refs:runner.auth(row)
 assert [r for r in P['inputs']['objects'] if not r['replace']]==[r for r in old['inputs']['objects'] if not r['replace']]
 assert sum(not r['replace'] for r in P['inputs']['objects'])==7 and sum(r['replace'] for r in P['inputs']['objects'])==4
 assert P['exact_commands'][1]==old['exact_commands'][1] and P['exact_commands'][-1]==old['exact_commands'][-1]
 mounts=runner.mounts(P,X,D/'FUTURE-OUTPUT-NOT-CREATED');assert len({r['target'] for r in mounts})==len(mounts)
 assert P['request_sha256'] is None and P['native_custody_clearance'] is None and P['runtime_authority'] is None
 assert len(set(expected['all_Rust_exports']))==39 and len(expected['carried_forward_Rust_exports'])==35 and len(expected['new_unique_Rust_exports'])==4
 assert [len(v['expected_remaining_names']) for v in expected['expected_C_function_sets'].values()]==[72,28]
 assert expected['process_current_OBJECT_count']==71 and expected['process_expected_OBJECT_count']==70 and len(expected['new_timer120']['expected_words'])==15
 assert len(expected['exact_undefined_delta']['removed'])==4 and not expected['exact_undefined_delta']['added']
 tree=ast.parse((D/'validator-templates/profile_clone_witness.py').read_text());assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and getattr(n.targets[0],'id','')=='EXPECTED_PROVIDERS');assert (set(ast.literal_eval(assignment.value))-set(expected['cumulative_seed_undefined_removed']))|set(expected['cumulative_seed_undefined_added'])==set(expected['expected_new_undefined'])
 gates=read(D/'VALIDATOR-TEMPLATE-SOURCES.json')
 for name,row in gates['templates'].items():assert ref(D/'validator-templates'/name)['sha256']==row['template_sha256'];ast.parse((D/'validator-templates'/name).read_text())
 driver=module('literal_current_cohort_qualifier',D/'qualify_produced_cohort.py');helpers=driver.bind_validator_dependencies(gates);probe=runpy.run_path(str(D/'literal_import_probe.py'),run_name='__main__');assert Path(probe['profile_clone_witness'].__file__)==Path(helpers['profile_clone_witness.py']['path'])
 spec=importlib.util.spec_from_file_location('actual_cohort_narrow_alias',helpers['narrow_f02_alias_identity.py']['path']);alias=importlib.util.module_from_spec(spec);spec.loader.exec_module(alias);assert callable(alias.validate)
 assert not (D/'actual-qualification-1').exists() and not (D/'FUTURE-OUTPUT-NOT-CREATED').exists()
 result=dict(scope=__doc__.splitlines()[0],status='PASS_COHERENT_SIX_FUNCTION_TIMER120_SOURCE_REAL_FIVE_API_109_MAP_AND_PINNED_LITERAL_IMPORTS',runtime_authority=None,source_plan=ref(D/'COHERENT-NEXT-DEFAULT-SOURCE-PLAN.NOT-GRANTED.json'),profile=ref(D/'PROFILE.SOURCE-ONLY.json'),acceptance=ref(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'),postimages=9,Rust_files=109,commands=5,retained_C_inputs=7,new_objects=4,expected_C_FUNCs=[72,28],expected_process_OBJECTs=70,expected_Rust_function_exports=39,new_timer_data=1,timer_actual15word_ABI_and25750_oracle=plan['timer_actual_result'],source_body_rewrites=0,arch_original_tracked_file_line_origins_preserved=True,helper_imports_explicit_and_authenticated=True,unexecuted_four_history_preserved=True,actual_nonce=None,actual_Root_admission=None,actual_resource_authority=None,actual_execution_release=None,compiler_Docker_canonical_Git_native_actions=0)
 (D/'RESULT.SOURCE-ONLY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
