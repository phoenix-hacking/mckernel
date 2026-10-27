"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual next-cohort source/23 Rust exports/selected-C ownership and exact U closure.
"""
from pathlib import Path
import collections,hashlib,importlib.util,json,struct,traceback
D=Path(__file__).resolve().parent;E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
EXPECTED=json.loads(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current110-host19-production-preparation-source-1/resource-and-qualifier-preparation-1/ACCEPTANCE-INPUTS.SOURCE-ONLY.json').read_text())
s=(D/'qualify_clone_pointer_and_warning_suffix.py').read_text();ns={'__file__':str(D/'qualify_next_providers.py')};exec(compile(s[:s.index("\nclone=ns['_reuse_elf_function']")],'accepted strict REL/EXEC readers for actual next cohort','exec'),ns)
P=ns['P'];B=ns['B'];Elf=ns['Elf'];rust=ns['rust'];final=ns['final'];ref=ns['ref'];sections=ns['sections']
expected=EXPECTED['all_Rust_exports']
removed_kernel=set(EXPECTED['expected_C_function_sets']['CMakeFiles/mckernel.img.dir/syscall.c.o']['remove'])
removed_arch=set(EXPECTED['expected_C_function_sets']['CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o']['remove']);report=dict(scope=__doc__.splitlines()[0],status='IN_PROGRESS',phases={},native_acceptance=False,Source38_debt='OPEN',compiler_container_grant_canonical_Git_actions=0)
def definitions(elf,name):return [s for s in elf.symbols if s['name']==name and s['shndx']!=0]
def funcs(elf):return {s['name']:s for s in elf.symbols if s['type']==2 and 0<s['shndx']<len(elf.sections) and elf.sections[s['shndx']]['flags']&2}
try:
 assert P['exact_commands']==json.loads(Path(EXPECTED['profile_template']['path']).read_text())['exact_commands'], 'actual compiler argv differs from prepublished plan'
 # Reuse the exact Root runner's source-only map and auth helpers after pinning
 # that source to the actual execution publication; no execute()/Docker call.
 ROOT=E/'__ACTUAL_ADMISSION_BASENAME__';publication=json.loads((ROOT/'ACTUAL-STATIC-SOURCE-PUBLICATION.json').read_text())
 runnerpath=ROOT/'run_build_only.py';grant=json.loads((ROOT/'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json').read_text());assert ref(runnerpath)==grant['runner']
 spec=importlib.util.spec_from_file_location('actual_frozen_readonly_cohort_runner',runnerpath);runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
 source_rows=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[r['postimage'] for r in runner.source_directory_postimages(P)]
 export=json.loads(Path(grant['input_export_authority']['path']).read_text());assert export['qualified_readonly_files']==source_rows
 for row in source_rows:runner.auth(row)
 report['phases']['source_view_and_seven_prefix_inputs']='PASS_EXACT_CURRENT_CLOSED_SOURCE_POSTIMAGES_CONFIGURATION_AND_SEVEN_RETAINED_OBJECTS'
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
 report['phases']['actual_forty_five_Rust_exports']=providers
 changes={}
 for token,wanted in [('CMakeFiles/mckernel.img.dir/syscall.c.o',removed_kernel),('CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o',removed_arch)]:
  row=next(r for r in P['inputs']['objects'] if r['link_token']==token)
  baseline_ref=EXPECTED['baseline_C_objects'][token]['object']
  assert row['source']==baseline_ref, 'actual predecessor reference differs from prepublished baseline'
  assert ref(Path(baseline_ref['path']))==baseline_ref, 'prepublished baseline C object bytes changed'
  old=Elf(Path(baseline_ref['path']));new=objects[token];before=funcs(old);after=funcs(new);removed=set(before)-set(after);added=set(after)-set(before)
  assert sorted(after)==EXPECTED['expected_C_function_sets'][token]['expected_remaining_names'], 'actual remaining C functions differ from prepublished exact set'
  assert wanted==removed,(token,'exact frozen source-selected C removal set',wanted-removed,removed-wanted)
  assert not added,(token,'new C function names',added)
  changes[token]=dict(original_allocated_FUNC_count=len(before),actual_allocated_FUNC_count=len(after),actual_removed_names=sorted(removed),new_C_function_names=sorted(added),exact_expected_selected_provider_removals=sorted(wanted),retained_partial_bodies=sorted(set(after)&{'do_execveat','do_fork','do_mmap','terminate'}))
 report['phases']['actual_selected_C_provider_delta']=changes
 for item in EXPECTED['genuine_C_providers_retained']:
  name,type_,size=item['name'],item['type'],item['size']
  matches=[(key,s,elf) for key,elf in C.items() for s in definitions(elf,name)]
  assert len(matches)==1,(name,'exact genuine C provider',[(key,s) for key,s,_ in matches]);key,a,elf=matches[0];assert a['bind']==1 and a['type']==type_ and (size is None or a['size']==size)
  b=final(name);assert b['bind']==1 and b['type']==type_ and b['size']==a['size']
  report['phases'][name]=dict(actual_C_provider=key,symbol=a,final_symbol=b)
 # Exact new Rust immutable data providers, bound to the genuine-header HOST witness.
 host_ref=EXPECTED['new_storage_HOST_object'];assert ref(Path(host_ref['path']))==host_ref
 data=ns['data'];object_bytes=ns['ns']['_reuse_elf_object_bytes'];storage={}
 for name,witness in EXPECTED['new_Rust_readonly_storage'].items():
  rows=definitions(rust,name);assert len(rows)==1;(a,)=rows;sec=rust.sections[a['shndx']]
  assert a['bind']==1 and a['type']==1 and a['size']==witness['size'] and sec['align']>=witness['alignment'] and a['value']%witness['alignment']==0
  assert sec['flags']&2 and not sec['flags']&5, 'new immutable metadata section must be allocated/read-only/non-executable'
  assert object_bytes(rust,a).hex()==witness['bytes_hex']
  assert not [(key,s) for key,elf in C.items() for s in definitions(elf,name)]
  b=final(name);assert (b['bind'],b['type'],b['size'])==(1,1,witness['size']) and b['value']%witness['alignment']==0
  assert sections[b['shndx']]['flags']&2 and not sections[b['shndx']]['flags']&5
  assert data(b).hex()==witness['bytes_hex'];storage[name]=dict(Rust_symbol=a,final_symbol=b,exact_HOST_bytes=True,unique_Rust_provider=True)
 report['phases']['new_Rust_immutable_metadata']=storage
 # One actual-qualified timer120 owner, distinct from function export counts.
 witness=EXPECTED['new_timer120'];name=witness['only_new_data_owner'];owned=definitions(rust,name);assert len(owned)==1;(a,)=owned;sec=rust.sections[a['shndx']]
 assert (a['bind'],a['type'],a['size'])==(1,1,120) and sec['align']>=8 and a['value']%8==0 and sec['flags']&2 and not sec['flags']&5
 assert object_bytes(rust,a).hex()==witness['expected_bytes_hex']
 assert not [(key,s) for key,elf in C.items() for s in definitions(elf,name)]
 b=final(name);assert (b['bind'],b['type'],b['size'])==(1,1,120) and b['value']%8==0 and sections[b['shndx']]['flags']&2 and not sections[b['shndx']]['flags']&5 and data(b).hex()==witness['expected_bytes_hex']
 table_rels=ns['ns']['_reuse_elf_owning_relocations'](rust,a);assert not table_rels, 'timer offset words cannot contain hidden pointer relocations'
 set_timer=definitions(rust,'set_timer');assert len(set_timer)==1 and set_timer[0]['type']==2
 consumer_rels=[r for r in ns['ns']['_reuse_elf_owning_relocations'](rust,set_timer[0]) if r['target']['name']==name]
 report['phases']['timer120']=dict(Rust_symbol=a,final_symbol=b,exact15_current_words=witness['expected_words'],unique_Rust_provider=True,set_timer_symbol=set_timer[0],set_timer_table_relocations=consumer_rels,real_consumer_binding='DIRECT_RELOCATION' if consumer_rels else 'OPEN_EXACT_FOLDED_TABLE_ARGUMENT_REVIEW',actual_HOST=witness['actual_HOST'])
 # Current producer selected only the frozen cfgs, preserving genuine undefined NOCACHE.
 argv=P['exact_commands'][0]['argv'];assert 'f06_use_nocache_mmap' not in argv and not any('USE_NOCACHE_MMAP' in a for c in P['exact_commands'] for a in c['argv'])
 assert P['producer_contract']['process_delta']==EXPECTED['process_compile_disposition']
 report['status']='PASS_ACTUAL_SYNC_PROCESSVM_45_RUST_EXPORTS_SELECTED_C_PROVIDER_SOURCE_AND_IMPORT_CLOSURE'
except BaseException as error:
 report['status']='FAIL_FIRST_NEXT_PROVIDER_VALIDATOR_PRESERVED';report['first_failure']=repr(error);report['traceback']=traceback.format_exc()
(D/'NEXT-PROVIDERS-RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],first_failure=report.get('first_failure'),phases=list(report['phases']))))
if report['status'].startswith('FAIL'):raise SystemExit(1)
