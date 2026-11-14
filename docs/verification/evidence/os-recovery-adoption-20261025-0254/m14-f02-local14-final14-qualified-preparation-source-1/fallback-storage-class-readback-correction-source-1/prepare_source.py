"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded qualifier-only C fallback storage-class correction; no workload/guard.
"""
import ast,copy,difflib,hashlib,json,os,stat
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent
ATTEMPT=P/'relative-module-context-correction-source-1'
G=E/'m14-f02-verbose32-host-preparation-source-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def identity(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 return dict(reference=ref(p),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),nlink=s.st_nlink,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def write(n,b):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b,n
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(n,x):return ref(write(n,json.dumps(x,indent=2)+'\n'))
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
diag=read(D/'STORAGE-CLASS-DIAGNOSIS.RAW.json');bylabel={a['label']:a for a in diag['artifacts']}
original=bylabel['retained_original_GLOBAL32_HOST_C'];prod=bylabel['retained_actual114_C'];coff=bylabel['new_optionOFF_C'];offjoint=bylabel['new_optionOFF_joint'];rust=bylabel['new_selected_Rust'];joint=bylabel['new_selected_joint']
classes=[]
for old,production,now,linked,rr,jj in zip(original['records'],prod['records'],coff['records'],offjoint['records'],rust['records'],joint['records']):
 assert len({x['name'] for x in [old,production,now,linked,rr,jj]})==1
 assert all(x['size']==x['expected_size']==old['size'] and x['kind']==1 and x['binding']==1 for x in [old,production,now,linked,rr,jj])
 assert production['flags']==2 and production['section']=='.rodata'
 assert now['section']==linked['section']==old['section'] and now['flags']==linked['flags']==old['flags'] and now['alignment']==linked['alignment']==old['alignment']
 assert old['section'] in ['.rodata','.data.rel.ro','.data.rel.ro.local'] and old['flags']==(2 if old['section']=='.rodata' else 3)
 assert rr['flags']==jj['flags']==0x10000002 and rr['section']==jj['section']=='.lrodata.'+old['name']
 classes.append(dict(name=old['name'],bytes=old['size'],kind=1,binding=1,HOST_C_original_section=old['section'],HOST_C_original_flags=old['flags'],HOST_C_original_section_alignment=old['alignment'],production_C_baseline_section=production['section'],production_C_baseline_flags=production['flags'],new_Rust_section=rr['section'],new_Rust_flags=rr['flags']))
assert len(classes)==17
storage_ref=save('EXACT17-ORIGINAL-HOST-C-STORAGE.json',dict(scope=SCOPE,runtime_authority=None,status='EXACT_EXISTING_HOST_C_COMPILER_CLASS_DEFAULT_FALLBACK_ONLY',original_HOST_C=identity(original['path']),original_HOST_recipe=ref(G/'COMMAND-RECIPE.NOT-ADMITTED.json'),production_baseline=identity(prod['path']),records=classes,physical_C_readonly_claim=False,semantic_limit='HOST GCC9 original const objects with pointers use original .data.rel.ro[.local]/WA before final RELRO; exact same named classes/size/bind/alignment only. Production C and new Rust remain required physically read-only. No generic writable class or new Rust waiver.',raw_readback=ref(D/'STORAGE-CLASS-DIAGNOSIS.RAW.json')))
results_path=ATTEMPT/'future-capture-1/RESULTS.json';results=read(results_path);assert len(results['results'])==7
for index,row in enumerate(results['results']):
 assert row['index']==index and row['join']['returncode']==(0 if index<6 else 1)
 assert row['join']['direct_child_joined'] is True and row['join']['group_absent'] is True and row['join']['closed_streams'] is True
objects=ATTEMPT/'HOST-output-proposed-1'
paths=[objects/n for n in ['rust-selected.o','selected.o','optionOFF.o','selected-joint.o','optionOFF-joint.o','CPP-CONTROL-RESULT.json','CPP-CONTROL-PREFIX.json']]
cpp=read(objects/'CPP-CONTROL-RESULT.json');assert len(cpp['records'])==8 and cpp['status']=='PASS_FIXED_SELECTED_REJECTION_AND_OPTIONOFF_CPP_ONLY'
for r in cpp['records']:
 paths += [Path(r[k]['path']) for k in ['stdout','stderr']]
 if r['preprocessed_output'] is not None:paths.append(Path(r['preprocessed_output']['path']))
for i in range(6):paths += [ATTEMPT/'future-capture-1'/('step'+str(i))/n for n in ['stdout','stderr']]
paths += [Path(original['path']),Path(prod['path'])]
unique=list(dict.fromkeys(paths));identities=save('RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json',dict(scope=SCOPE,runtime_authority=None,original_results=ref(results_path),records=[identity(p) for p in unique],all_six_commands_passed=True,ABI_witness='Selected and optionOFF actual process TU include frozen genuine3config384B and actual168B static assertions; both compiler returns0 retained.',CPP8_outputs_and_streams_preserved=True,compiler_CPP_link_replays=0))
REPORT=D/'QUALIFIER-output-proposed-1';CAPTURE=D/'future-capture-1';assert not REPORT.exists() and not CAPTURE.exists()
# Keep strict readonly() for Rust/production. Only exact C fallback call sites use
# original HOST counterpart section/flags/ABI, never a general writable allowance.
before=(ATTEMPT/'qualify_changed_objects.py').read_text()
text=once(before,'import copy,hashlib,importlib.util,json,re,struct,sys','import copy,hashlib,importlib.util,json,os,re,stat,struct,sys')
text=once(text,'COUNTER_REF=',"STORAGE_MANIFEST=Path("+repr(str(D/'EXACT17-ORIGINAL-HOST-C-STORAGE.json'))+")\nSTORAGE_MANIFEST_REF="+repr(storage_ref)+"\nRETAINED_IDENTITIES=Path("+repr(str(D/'RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json'))+")\nRETAINED_IDENTITIES_REF="+repr(identities)+"\nCOUNTER_REF=")
helper='''def verify_retained_identities():
 assert ref(RETAINED_IDENTITIES)==RETAINED_IDENTITIES_REF
 for row in read(RETAINED_IDENTITIES)['records']:
  path=Path(row['reference']['path']);s=path.lstat()
  assert stat.S_ISREG(s.st_mode) and not path.is_symlink()
  assert (s.st_dev,s.st_ino,s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode),s.st_nlink,s.st_mtime_ns,s.st_ctime_ns)==(row['device'],row['inode'],row['uid'],row['gid'],row['mode'],row['nlink'],row['mtime_ns'],row['ctime_ns'])
  assert ref(path)==row['reference']

def exact_original_C_fallback_storage(elf,name,size):
 assert ref(STORAGE_MANIFEST)==STORAGE_MANIFEST_REF
 manifest=read(STORAGE_MANIFEST)
 row=next(row for row in manifest['records'] if row['name']==name)
 symbol,section,raw,relocations=one(elf,name,size,readonly=False)
 assert size==row['bytes'] and symbol['kind']==row['kind']==1 and symbol['bind']==row['binding']==1
 assert section['name']==row['HOST_C_original_section'] and section['flags']==row['HOST_C_original_flags'] and section['align']==row['HOST_C_original_section_alignment']
 assert section['name'] in ('.rodata','.data.rel.ro','.data.rel.ro.local')
 # The original C compiler class is not physical read-only proof for a partial
 # HOST link; production baseline and selected Rust still use strict one().
 return dict(name=name,bytes=size,original_HOST_C_section=section['name'],original_HOST_C_flags=section['flags'],physical_C_readonly_claim=False)

'''
text=once(text,'def main():\n',helper+'def main():\n')
text=once(text," out=Path(sys.argv[1]);proposal=read(CURRENT_PROPOSAL)"," verify_retained_identities()\n out=Path(sys.argv[1]);report_out=Path(sys.argv[2]);proposal=read(CURRENT_PROPOSAL)")
text=once(text,"one(fallback,name,size);one(offjoint,name,size)","exact_original_C_fallback_storage(fallback,name,size);exact_original_C_fallback_storage(offjoint,name,size)")
text=once(text,"one(fallback,name,row['bytes']);one(offjoint,name,row['bytes'])","exact_original_C_fallback_storage(fallback,name,row['bytes']);exact_original_C_fallback_storage(offjoint,name,row['bytes'])")
text=once(text," (out/'LOCAL14-FINAL14-HOST-QUALIFICATION.json').write_text"," (report_out/'LOCAL14-FINAL14-HOST-QUALIFICATION.json').write_text")
text=once(text,"retained_counterexample=COUNTER_REF,local14_configs=configs","retained_counterexample=COUNTER_REF,exact_C_fallback_storage=STORAGE_MANIFEST_REF,retained_artifact_identities=RETAINED_IDENTITIES_REF,physical_C_fallback_readonly_claim=False,local14_configs=configs")
ast.parse(text);write('qualify_changed_objects.py',text)
write('one-storage-class-correction.diff',''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='retained-failed-qualifier',tofile='exact-original-HOST-C-class-qualifier')))
command=dict(name='00-retained-six-prefix-exact-C-storage-readback',argv=['/usr/bin/python3','-B',str(D/'qualify_changed_objects.py'),str(objects),str(REPORT)],purpose=SCOPE+' Qualifier-only exact original C relocation-backed const storage; retain all six successful producer/CPP/link objects.')
planref=save('EXACT-ONE-QUALIFIER-COMMAND.NOT-GRANTED.json',dict(scope=SCOPE,runtime_authority=None,commands=[command],retained_prefix_inputs=identities,old_qualifier_stderr=ref(ATTEMPT/'future-capture-1/step6/stderr'),compiler_CPP_link_commands_to_replay=0))
p=read(ATTEMPT/'PROFILE.NOT-GRANTED.json');base=copy.deepcopy(p['commands'][6]);base.update(id=command['name'],argv=command['argv'],purpose=command['purpose'],cwd=str(D),leaf='F02local14final14qualifierOnly')
base['argv_compact_json_LF_sha256']=hashlib.sha256((json.dumps(base['argv'],separators=(',',':'))+'\n').encode()).hexdigest()
p.update(task_id='NEW12H-ORDINARY-HOST-F02-LOCAL14-FINAL14-QUALIFIER-STORAGE-CORRECTION-1',status='ONE_BOUNDED_QUALIFIER_ONLY_SOURCE_PROFILE_NOT_GRANTED',capture_root=str(CAPTURE),commands=[base],leaves=[dict(name='F02local14final14qualifierOnly',first=0,last=0,plan=planref,output=str(REPORT),expected_stdout='F02 LOCAL14+FINAL14 HOST boundary PASS\n')])
p['qualifier_only_retained_prefix']=identities
new_refs=[ref(D/'qualify_changed_objects.py'),storage_ref,identities,planref]+[row['reference'] for row in read(D/'RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json')['records']]
seen={row['path'] for row in p['inputs']}
for row in new_refs:
 if row['path'] not in seen:p['inputs'].append(row);seen.add(row['path'])
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';tree=ast.parse(runner.read_text());nodes=[]
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['THREAD','CUTOFFS'] for t in node.targets):nodes.append(node)
 if isinstance(node,ast.FunctionDef) and node.name in ['need','validate_profile']:nodes.append(node)
ns={'Path':Path,'json':json,'hashlib':hashlib};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(runner),'exec'),ns);ns['validate_profile'](p)
profile=save('PROFILE.NOT-GRANTED.json',p)
save('EXACT-DIAGNOSIS-AND-CORRECTION.json',dict(scope=SCOPE,runtime_authority=None,original_profile=ref(ATTEMPT/'PROFILE.NOT-GRANTED.json'),original_results=ref(results_path),original_failed_qualifier=ref(ATTEMPT/'qualify_changed_objects.py'),original_stderr=ref(ATTEMPT/'future-capture-1/step6/stderr'),original_failure_returncode=1,original_failure_wall_seconds=results['results'][6]['join']['seconds'],first_failing_name='process_clone_config',production_baseline='All17 .rodata/A(2)',original_HOST_C_and_new_Cfallback='Exact per-name original .data.rel.ro/.data.rel.ro.local WA(3), or .rodata A(2); unchanged ABI/binding/size/alignment',new_Rust_and_selected_joint='All17 .lrodata.<name> ALLOC|LARGE 0x10000002; noWRITE',classification='Original HOST compiler relocation-backed C const class, not observed Rust layout/storage mismatch. PartialHOST C data is not claimed physically readonly or finalRELRO.',bounded_correction='Only two Cfallback call sites use exact17 original named class; strict Rust/production readonly remains unchanged. All rawfield/callback/metadata/consumer/defaultlimit predicates remain unchanged.',storage_manifest=storage_ref,retained_input_identities=identities,successful_prefix_metrics=[dict(index=row['index'],returncode=row['join']['returncode'],wall_seconds=row['join']['seconds'],direct_join=True,group_absent=True,closed_streams=True) for row in results['results'][:6]],correction_count=1,compiler_CPP_link_replay=0,Rust_or_C_source_body_changes=0,canonical_or_Git_writes=0,actual_next_grant=None,on_further_real_ABI_mismatch='Stop/report exact artifact predicates; never broadly accept writable storage or edit Rust to satisfy reader.'))
save('SOURCE-READY.json',dict(scope=SCOPE,status='ONE_BOUNDED_QUALIFIER_ONLY_EXACT_ORIGINAL_HOST_C_STORAGE_CORRECTION_SOURCE_READY_NOT_GRANTED',runtime_authority=None,profile=profile,one_command=planref,diagnosis=ref(D/'EXACT-DIAGNOSIS-AND-CORRECTION.json'),storage_manifest=storage_ref,retained_prefix_identity=identities,successful_producer_CPP_link_commands_replayed=0,compiler_commands=0,qualifier_commands=1,new_capture=str(CAPTURE),new_output=str(REPORT),actual_next_nonce=None,actual_Root_ordinary_grant=None,source_bodies_changed=0,default_ON_nondefault_limits_still_OPEN=True,missing_folded_consumer_predicates_still_OPEN=True,all_actual_guard_query_compiler_workload_calls=0,cleanup_or_canonical_or_Git_changes=0))
print(json.dumps(dict(decision='QUALIFIER_ONLY_SOURCE_READY_NOT_GRANTED',ready=ref(D/'SOURCE-READY.json'),profile=profile,qualifier_commands=1,compiler_CPP_link_replays=0)))
