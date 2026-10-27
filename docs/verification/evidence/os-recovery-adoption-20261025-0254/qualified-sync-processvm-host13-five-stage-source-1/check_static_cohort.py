"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite source/API/ELF-metadata checks only; no compiler, live capture or runtime.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel');B=E/'ROOT-NEXT10-DEFAULT-BUILD-ADMISSION-1'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def load(p):return json.loads(p.read_text())
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 plan=load(D/'COHERENT-COMBINED-SOURCE-PLAN.NOT-GRANTED.json');P=load(D/'PROFILE.SOURCE-ONLY.json');old=load(B/'PROFILE.SOURCE-ONLY.json');expected=load(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json');export=load(D/'INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json')
 for rel,row in plan['preimages'].items():assert ref(R/rel)==row,('preadoption-only check',rel)
 for rel,row in plan['postimages'].items():
  assert ref(Path(row['path']))==row
  if rel not in plan['preimages']:assert not (R/rel).exists()
 F3=Path(plan['qualified_F03_source']['path']).parent;F6=Path(plan['qualified_F06_source']['path']).parent;bindings=load(F6/'SOURCE-BINDINGS.json')
 for key in ['abi','lock_helpers','process_helpers','x86_memory_helpers','reused_fragment','reused_leaf']:assert ref(Path(bindings[key]['path']))==bindings[key]
 helper=Path(bindings['composition_helper']['path']);assert ref(helper)==bindings['composition_helper'];compose=module('qualified_existing_process_vm_composer',helper)
 selected_c,selected_rust,leaf,parts=compose.compose((R/'arch/x86_64/kernel/syscall.c').read_text(),(F3/'candidate/kernel/rust/syscall_policy.rs').read_text(),Path(bindings['reused_fragment']['path']).read_text())
 def source_check(c,r,l):
  assert c==selected_c and r==selected_rust and l==leaf
  assert c.replace(parts['adapter_wrapper'],parts['adapters'],1).replace(parts['entry_wrapper'],parts['entry'],1)==(R/'arch/x86_64/kernel/syscall.c').read_text()
  assert r.removesuffix(parts['selection'])==(F3/'candidate/kernel/rust/syscall_policy.rs').read_text()
  assert l.count('unsafe extern "C" fn f06_process_vm_rw_')==13
  assert r.count('pub static F06_PROCESS_VM_RW_OFFSETS:')==1 and r.count('pub unsafe extern "C" fn arch_process_vm_rw_log_bridge(')==1
  assert 'static F06_PROCESS_VM_RW_OFFSETS' not in l and 'fn f06_process_vm_rw_log' not in l
 source_check((D/'candidate/arch/x86_64/kernel/syscall.c').read_text(),(D/'candidate/kernel/rust/syscall_policy.rs').read_text(),(D/'candidate/kernel/rust/f06_process_vm_entry.rs').read_text())
 negatives=0
 for mutation in [(selected_c.replace('MCKERNEL_RUST_F06_PROCESS_VM_ENTRY','BROKEN',1),selected_rust,leaf),(selected_c,selected_rust.replace('f03_sync_child_event_candidate','BROKEN',1),leaf),(selected_c,selected_rust,leaf.replace('MaybeUninit::<McsRwlockNode>','MaybeUninit::<McsRwlockNodeIrqsave>',1))]:
  try:source_check(*mutation)
  except AssertionError:negatives+=1
  else:raise AssertionError('source mismatch escaped')
 assert (D/'candidate/kernel/syscall.c').read_bytes()==(F3/'candidate/kernel/syscall.c').read_bytes()
 # Every prior Rust file is unchanged except policy; exactly one leaf added.
 oldmap=load(Path(old['inputs']['source_directory_exports'][0]['manifest']['path']));newmap=load(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json');before={r['relative']:r for r in oldmap['files']};after={r['relative']:r for r in newmap['files']}
 assert set(after)-set(before)=={'f06_process_vm_entry.rs'} and not set(before)-set(after)
 assert [name for name in before if before[name]['snapshot']['sha256']!=after[name]['snapshot']['sha256']]==['process_helpers.rs','syscall_policy.rs']
 runnerpath=D/'run_build_only.py';assert ref(runnerpath)==plan['existing_fixed_five_tools']['run_build_only.py']['materialized'];runner=module('accepted_unchanged_four_command_API',runnerpath)
 rows=runner.source_directory_postimages(P);assert len(rows)==106
 refs=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[r['postimage'] for r in rows]
 assert export['qualified_readonly_files']==refs
 for row in refs:runner.auth(row)
 vector=copy.deepcopy(P);vector['request_sha256']='a'*64;assert len(runner.commands_for_plan(vector))==5
 mounts=runner.mounts(P,export,D/'FUTURE-OUTPUT-NOT-CREATED');assert len({r['target'] for r in mounts})==len(mounts)
 assert len([m for m in mounts if m['target']=='/src/kernel/rust'])==1
 argv=runner.docker_argv(P,'source-only-pure-argv',mounts,D/'FUTURE-OUTPUT-NOT-CREATED');assert argv[:4]==runner.SUDO_DOCKER_PREFIX
 assert P['exact_commands'][-1]==old['exact_commands'][-1]
 assert [r for r in P['inputs']['objects'] if not r['replace']]==[r for r in old['inputs']['objects'] if not r['replace'] and r['link_token']!='CMakeFiles/mckernel.img.dir/process.c.o']
 assert len([r for r in P['inputs']['objects'] if not r['replace']])==7
 assert P['request_sha256'] is None and P['native_custody_clearance'] is None and P['runtime_authority'] is None
 assert not any('USE_NOCACHE_MMAP' in a or a=='f06_use_nocache_mmap' for c in P['exact_commands'] for a in c['argv'])
 for cfg in plan['new_Rust_cfgs']:assert P['exact_commands'][0]['argv'].count(cfg)==1 and (D/'candidate/kernel/CMakeLists.txt').read_text().count('"'+cfg+'"')==1
 for idx,key in [(2,'kernel'),(3,'arch')]:
  for flag in plan['new_C_defines'][key]:assert P['exact_commands'][idx]['argv'].count('-D'+flag)==1 and flag in (D/'candidate/kernel/CMakeLists.txt').read_text()
 assert len(set(expected['all_Rust_exports']))==35 and len(expected['carried_forward_Rust_exports'])==33 and len(expected['new_unique_Rust_exports'])==2
 assert [len(v['expected_remaining_names']) for v in expected['expected_C_function_sets'].values()]==[75,31]
 assert len(expected['exact_undefined_delta']['removed'])==15 and expected['exact_undefined_delta']['added']==[]
 assert expected['cumulative_seed_undefined_added']==['f03_do_exit_debug_v2']
 for row in expected['baseline_C_objects'].values():assert ref(Path(row['object']['path']))==row['object']
 manifest=load(D/'VALIDATOR-TEMPLATE-SOURCES.json')
 for name,row in manifest['templates'].items():assert ref(D/'validator-templates'/name)['sha256']==row['template_sha256']
 for path in [D/'qualify_produced_cohort.py',D/'check_postbuild_current.py',*list((D/'validator-templates').glob('*.py'))]:ast.parse(path.read_text(),filename=str(path))
 provider=(D/'validator-templates/qualify_next_providers.py').read_text();assert "assert row['source']==baseline_ref" in provider and "assert ref(Path(baseline_ref['path']))==baseline_ref" in provider and "assert sorted(after)==EXPECTED['expected_C_function_sets'][token]['expected_remaining_names']" in provider
 clone=(D/'validator-templates/qualify_clone_pointer_and_warning_suffix.py').read_text();assert "new_process_object=ref(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o')" in clone and "process=Elf(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o')" in clone
 profile=(D/'validator-templates/qualify_actual_f02_profile.py').read_text();assert "NEXT_ADDED=set(EXPECTED['cumulative_seed_undefined_added'])" in profile
 witness=ast.parse((D/'validator-templates/profile_clone_witness.py').read_text());assignment=next(n for n in witness.body if isinstance(n,ast.Assign) and getattr(n.targets[0],'id','')=='EXPECTED_PROVIDERS')
 assert (set(ast.literal_eval(assignment.value))-set(expected['cumulative_seed_undefined_removed']))|set(expected['cumulative_seed_undefined_added'])==set(expected['expected_new_undefined'])
 # Reuse F01's exact source restoration/logical-line/fragment checks; no writes.
 F01=E/'f02-source38-next-current-integration-source-1';source_result=load(F01/'SOURCE-ONLY-RESULT.json');verifier=F01/'verify_private_source.py';assert ref(verifier)==source_result['checks'][0];module('unchanged_HOST13_source_verifier',verifier).main()
 manifest13=load(D/'SOURCE-IMPLEMENTATION-AND-ACTUAL13-ABI.json')
 for row in manifest13['postimages']:
  relative=str(Path(row['path']).relative_to(F01/'candidate'));assert (D/'candidate'/relative).read_bytes()==Path(row['path']).read_bytes()
 assert expected['process_baseline_OBJECT_count']==84 and expected['process_expected_OBJECT_count']==71
 assert len(expected['HOST13_production_consumer_map'])==13 and expected['HOST13_production_consumer_map']['process_free_range_pages_source_line']=='process_memory_range_free_bridge'
 profile_tree=ast.parse(clone);expression=next(k.value for n in ast.walk(profile_tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='dict' for k in n.keywords if k.arg=='new_process_object')
 fresh=eval(compile(ast.Expression(expression),'new process report binding','eval'),dict(B=Path('/actual-fresh-build'),ref=lambda p:str(p)));assert fresh=='/actual-fresh-build/kernel/CMakeFiles/mckernel.img.dir/process.c.o'
 assert not (D/'FUTURE-OUTPUT-NOT-CREATED').exists()
 report=dict(scope=__doc__.splitlines()[0],status='PASS_EXACT_COMBINED_HOST13_SOURCE_AND_EXISTING_FIVE_STAGE_API_106_FILE_CLOSURE',runtime_authority=None,source_plan=ref(D/'COHERENT-COMBINED-SOURCE-PLAN.NOT-GRANTED.json'),profile=ref(D/'PROFILE.SOURCE-ONLY.json'),acceptance=ref(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'),negative_source_controls=negatives,canonical_postimages=7,closed_Rust_files=106,prior_Rust_files_changed=['process_helpers.rs','syscall_policy.rs'],new_leaf_files=['f06_process_vm_entry.rs'],C_baseline_counts=[76,45],expected_C_remaining=[75,31],carried_Rust_exports=33,new_public_Rust_exports=2,total_expected_exports=35,expected_U_removed=15,expected_U_added=0,commands=5,retained_C_inputs=7,exact_existing_five_runner=ref(runnerpath),no_current_capture_compiler_container_guest_Git_Root_grant_actions=True,default_acceptance=False,native_acceptance=False,whole_file_retirement=False)
 (D/'RESULT.SOURCE-ONLY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
