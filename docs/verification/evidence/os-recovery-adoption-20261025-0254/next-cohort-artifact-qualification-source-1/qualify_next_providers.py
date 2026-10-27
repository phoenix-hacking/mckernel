"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual next-cohort source/23 Rust exports/selected-C ownership and exact U closure.
"""
from pathlib import Path
import collections,hashlib,importlib.util,json,struct,traceback
D=Path(__file__).resolve().parent;E=D.parent
s=(D/'qualify_clone_pointer_and_warning_suffix.py').read_text();ns={'__file__':str(D/'qualify_next_providers.py')};exec(compile(s[:s.index("\nclone=ns['_reuse_elf_function']")],'accepted strict REL/EXEC readers for actual next cohort','exec'),ns)
P=ns['P'];B=ns['B'];Elf=ns['Elf'];rust=ns['rust'];final=ns['final'];ref=ns['ref'];sections=ns['sections']
expected=['reset_cputime','set_cputime','f03_perf_counter_attr_flags_v1','f03_perf_read_attr_flags_v1','f03_prlimit_body_result','f03_prlimit_forward_request_result','syscall_do_prlimit64_bridge','f03_execveat_install_user_context_v1','f03_execveat_ptrace_report_v1','f03_execveat_finish_switch_v1','f03_do_exit_supported_v2','exit_do_exit_bridge','f03_unmap_begin','f03_unmap_remove','f03_unmap_finish','f03_do_mmap_smaller_page_v2','f03_wait_release_thread','arch_mmap_supported_flags_bridge','arch_mmap_ignored_flags_bridge','arch_mmap_error_flags_bridge','arch_prctl_set_register_bridge','arch_prctl_get_register_bridge','arch_do_mmap_bridge']
removed_kernel={'reset_cputime','set_cputime','perf_counter_attr_flags_bridge','perf_read_attr_flags_bridge','syscall_do_prlimit64_bridge','do_exit','exit_do_exit_bridge','do_munmap_begin_bridge','do_munmap_remove_range_bridge','do_munmap_finish_bridge','do_mmap_smaller_page_bridge','wait_thread_release_bridge'}
removed_kernel|={'do_prlimit64','ptrace_report_exec_arch_event_bridge'}
removed_arch=set(expected[-6:]);report=dict(scope=__doc__.splitlines()[0],status='IN_PROGRESS',phases={},native_acceptance=False,Source38_debt='OPEN',compiler_container_grant_canonical_Git_actions=0)
def definitions(elf,name):return [s for s in elf.symbols if s['name']==name and s['shndx']!=0]
def funcs(elf):return {s['name']:s for s in elf.symbols if s['type']==2 and 0<s['shndx']<len(elf.sections) and elf.sections[s['shndx']]['flags']&2}
try:
 # Reuse the exact Root runner's source-only map and auth helpers after pinning
 # that source to the actual execution publication; no execute()/Docker call.
 ROOT=E/'ROOT-F03-F06-QUALIFIED-DEFAULT-BUILD-ADMISSION-1';publication=json.loads((ROOT/'ACTUAL-STATIC-SOURCE-PUBLICATION.json').read_text())
 runnerpath=ROOT/'run_build_only.py';grant=json.loads((ROOT/'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json').read_text());assert ref(runnerpath)==grant['runner']
 spec=importlib.util.spec_from_file_location('actual_frozen_readonly_cohort_runner',runnerpath);runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
 source_rows=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[r['postimage'] for r in runner.source_directory_postimages(P)]
 export=json.loads(Path(grant['input_export_authority']['path']).read_text());assert export['qualified_readonly_files']==source_rows
 for row in source_rows:runner.auth(row)
 report['phases']['source_view_and_eight_prefix_inputs']='PASS_EXACT_CURRENT_CLOSED_SOURCE_POSTIMAGES_CONFIGURATION_AND_EIGHT_RETAINED_OBJECTS'
 objects={}
 for row in P['inputs']['objects']:
  path=B/row['build_relative'] if row['replace'] else Path(row['source']['path']);objects[row['link_token']]=Elf(path)
 rustkey='rust/mckernel_rust.o';C={k:v for k,v in objects.items() if k!=rustkey};providers=[]
 for name in expected:
  rows=definitions(rust,name);assert len(rows)==1,(name,'Rust definition count',len(rows));a=rows[0]
  assert a['bind']==1 and a['type']==2 and a['size']>0 and rust.sections[a['shndx']]['flags']&6==6 and not rust.sections[a['shndx']]['flags']&1
  assert rust.raw[rust.table['offset']+a['index']*24+5]==0
  assert not [(key,s) for key,elf in C.items() for s in definitions(elf,name)],(name,'duplicate C provider')
  b=final(name);assert (b['bind'],b['type'],b['other'],b['size'])==(1,2,0,a['size']) and sections[b['shndx']]['flags']&6==6
  providers.append(dict(name=name,Rust_symbol=a,final_symbol=b,unique_actual_Rust_provider=True))
 report['phases']['actual_twenty_three_Rust_exports']=providers
 changes={}
 for token,wanted in [('CMakeFiles/mckernel.img.dir/syscall.c.o',removed_kernel),('CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o',removed_arch)]:
  row=next(r for r in P['inputs']['objects'] if r['link_token']==token);old=Elf(Path(row['source']['path']));new=objects[token];before=funcs(old);after=funcs(new);removed=set(before)-set(after);added=set(after)-set(before)
  assert wanted==removed,(token,'exact frozen source-selected C removal set',wanted-removed,removed-wanted)
  assert not added,(token,'new C function names',added)
  changes[token]=dict(original_allocated_FUNC_count=len(before),actual_allocated_FUNC_count=len(after),actual_removed_names=sorted(removed),new_C_function_names=sorted(added),exact_expected_selected_provider_removals=sorted(wanted),retained_partial_bodies=sorted(set(after)&{'do_execveat','do_fork','do_mmap','terminate'}))
 report['phases']['actual_selected_C_provider_delta']=changes
 source_path=Path(next(r['postimage']['path'] for r in P['inputs']['postimages'] if r['relative']=='kernel/syscall.c'));newsource=source_path.read_text();oldsource=(Path(P['inputs']['source6153'])/'kernel/syscall.c').read_text()
 def static_helper(text,name):
  start=text.index('static long\n'+name+'(');end=text.index('\n}',start)+2;return text[start:end]
 assert static_helper(newsource,'ptrace_report_exec_arch_event_bridge')==static_helper(oldsource,'ptrace_report_exec_arch_event_bridge')
 assert '#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_PRLIMIT_BODY) && defined(__x86_64__)\nextern long syscall_do_prlimit64_bridge(int, int, unsigned long, unsigned long);\n#else\nstatic int do_prlimit64(' in newsource
 report['phases']['two_additional_source_supported_C_removals']=dict(do_prlimit64='Qualified PRLIMIT_BODY C fallback is unselected; Rust body+forward exports verified',ptrace_report_exec_arch_event_bridge='Original static C helper source unchanged; compiler no longer emits it after qualified exec-tail consumer selection; no separate new-body port claim',source=ref(source_path))

 for name,type_,size in [('f03_do_exit_debug_v2',1,64),('sync_child_event',2,None)]:
  matches=[(key,s,elf) for key,elf in C.items() for s in definitions(elf,name)]
  assert len(matches)==1,(name,'exact genuine C provider',[(key,s) for key,s,_ in matches]);key,a,elf=matches[0];assert a['bind']==1 and a['type']==type_ and (size is None or a['size']==size)
  b=final(name);assert b['bind']==1 and b['type']==type_ and b['size']==a['size']
  report['phases'][name]=dict(actual_C_provider=key,symbol=a,final_symbol=b)
 # Current producer selected only the frozen cfgs, preserving genuine undefined NOCACHE.
 argv=P['exact_commands'][0]['argv'];assert 'f06_use_nocache_mmap' not in argv and not any('USE_NOCACHE_MMAP' in a for c in P['exact_commands'] for a in c['argv'])
 assert P['unchanged_completed_process_prefix']['Root_decision']=='REUSE_EXACT_F02_B8168C1F'
 report['status']='PASS_ACTUAL_NEXT_23_RUST_EXPORTS_SELECTED_C_PROVIDER_SOURCE_AND_IMPORT_CLOSURE'
except BaseException as error:
 report['status']='FAIL_FIRST_NEXT_PROVIDER_VALIDATOR_PRESERVED';report['first_failure']=repr(error);report['traceback']=traceback.format_exc()
(D/'NEXT-PROVIDERS-RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],first_failure=report.get('first_failure'),phases=list(report['phases']))))
if report['status'].startswith('FAIL'):raise SystemExit(1)
