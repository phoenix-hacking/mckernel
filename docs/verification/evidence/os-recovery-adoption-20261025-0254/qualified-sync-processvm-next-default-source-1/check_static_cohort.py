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
 plan=load(D/'COHERENT-SOURCE-PLAN.NOT-GRANTED.json');P=load(D/'PROFILE.SOURCE-ONLY.json');old=load(B/'PROFILE.SOURCE-ONLY.json');expected=load(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json');export=load(D/'INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json')
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
 assert [name for name in before if before[name]['snapshot']['sha256']!=after[name]['snapshot']['sha256']]==['syscall_policy.rs']
 runnerpath=B/'run_build_only.py';assert ref(runnerpath)==load(B/'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json')['runner'];runner=module('accepted_unchanged_four_command_API',runnerpath)
 rows=runner.source_directory_postimages(P);assert len(rows)==106
 refs=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[r['postimage'] for r in rows]
 assert export['qualified_readonly_files']==refs
 for row in refs:runner.auth(row)
 vector=copy.deepcopy(P);vector['request_sha256']='a'*64;assert len(runner.commands_for_plan(vector))==4
 mounts=runner.mounts(P,export,D/'FUTURE-OUTPUT-NOT-CREATED');assert len({r['target'] for r in mounts})==len(mounts)
 assert len([m for m in mounts if m['target']=='/src/kernel/rust'])==1
 argv=runner.docker_argv(P,'source-only-pure-argv',mounts,D/'FUTURE-OUTPUT-NOT-CREATED');assert argv[:4]==runner.SUDO_DOCKER_PREFIX
 assert P['exact_commands'][-1]==old['exact_commands'][-1]
 assert [r for r in P['inputs']['objects'] if not r['replace']]==[r for r in old['inputs']['objects'] if not r['replace']]
 assert len([r for r in P['inputs']['objects'] if not r['replace']])==8
 assert P['request_sha256'] is None and P['native_custody_clearance'] is None and P['runtime_authority'] is None
 assert not any('USE_NOCACHE_MMAP' in a or a=='f06_use_nocache_mmap' for c in P['exact_commands'] for a in c['argv'])
 for cfg in plan['new_Rust_cfgs']:assert P['exact_commands'][0]['argv'].count(cfg)==1 and (D/'candidate/kernel/CMakeLists.txt').read_text().count('"'+cfg+'"')==1
 for idx,key in [(1,'kernel'),(2,'arch')]:
  for flag in plan['new_C_defines'][key]:assert P['exact_commands'][idx]['argv'].count('-D'+flag)==1 and flag in (D/'candidate/kernel/CMakeLists.txt').read_text()
 assert len(set(expected['all_Rust_exports']))==35 and len(expected['carried_forward_Rust_exports'])==33 and len(expected['new_unique_Rust_exports'])==2
 assert [len(v['expected_remaining_names']) for v in expected['expected_C_function_sets'].values()]==[75,31]
 assert expected['exact_undefined_delta']['removed']==['sync_child_event','do_process_vm_read_writev'] and expected['exact_undefined_delta']['added']==[]
 assert expected['cumulative_seed_undefined_added']==['f03_do_exit_debug_v2']
 for row in expected['baseline_C_objects'].values():assert ref(Path(row['object']['path']))==row['object']
 manifest=load(D/'VALIDATOR-TEMPLATE-SOURCES.json')
 for name,row in manifest['templates'].items():assert ref(D/'validator-templates'/name)['sha256']==row['template_sha256']
 for path in [D/'qualify_produced_cohort.py',D/'check_postbuild_current.py',*list((D/'validator-templates').glob('*.py'))]:ast.parse(path.read_text(),filename=str(path))
 provider=(D/'validator-templates/qualify_next_providers.py').read_text();assert "assert row['source']==baseline_ref" in provider and "assert ref(Path(baseline_ref['path']))==baseline_ref" in provider and "assert sorted(after)==EXPECTED['expected_C_function_sets'][token]['expected_remaining_names']" in provider
 clone=(D/'validator-templates/qualify_clone_pointer_and_warning_suffix.py').read_text();assert "new_process_object=ref(Path(next(r['source']['path']" in clone
 profile=(D/'validator-templates/qualify_actual_f02_profile.py').read_text();assert "NEXT_ADDED=set(EXPECTED['cumulative_seed_undefined_added'])" in profile
 witness=ast.parse((D/'validator-templates/profile_clone_witness.py').read_text());assignment=next(n for n in witness.body if isinstance(n,ast.Assign) and getattr(n.targets[0],'id','')=='EXPECTED_PROVIDERS')
 assert (set(ast.literal_eval(assignment.value))-set(expected['cumulative_seed_undefined_removed']))|set(expected['cumulative_seed_undefined_added'])==set(expected['expected_new_undefined'])
 assert not (D/'FUTURE-OUTPUT-NOT-CREATED').exists()
 report=dict(scope=__doc__.splitlines()[0],status='PASS_EXACT_PRIVATE_SOURCE_COMPOSITION_REAL_FOUR_COMMAND_API_106_FILE_CLOSURE_AND_PREPUBLISHED_ACCEPTANCE',runtime_authority=None,source_plan=ref(D/'COHERENT-SOURCE-PLAN.NOT-GRANTED.json'),profile=ref(D/'PROFILE.SOURCE-ONLY.json'),acceptance=ref(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'),negative_source_controls=negatives,canonical_postimages=5,closed_Rust_files=106,prior_Rust_files_changed=['syscall_policy.rs'],new_leaf_files=['f06_process_vm_entry.rs'],C_baseline_counts=[76,45],expected_C_remaining=[75,31],carried_Rust_exports=33,new_public_Rust_exports=2,total_expected_exports=35,expected_U_removed=2,expected_U_added=0,commands=4,retained_C_inputs=8,runner_unchanged=ref(runnerpath),no_current_capture_compiler_container_guest_Git_Root_grant_actions=True,default_acceptance=False,native_acceptance=False,whole_file_retirement=False)
 (D/'RESULT.SOURCE-ONLY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
