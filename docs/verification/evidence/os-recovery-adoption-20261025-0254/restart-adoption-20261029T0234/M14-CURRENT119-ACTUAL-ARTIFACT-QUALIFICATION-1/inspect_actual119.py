"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only actual119 artifact facts using frozen accepted validator functions.
No compiler, HOST payload, Docker, native or cleanup operation.
"""
from pathlib import Path
import ast,collections,hashlib,json,struct,re,time
D=Path(__file__).resolve().parent;A=D.parent;E=A.parent;R=A/'ROOT-CURRENT119-BUILD-ADMISSION-1';W=R/'OUTPUT/work';B=W/'output/build/kernel';AD=A/'M14-ORIGINAL-CLOSURE-AND-POST119-REMAINING-1/CURRENT119-ARTIFACT-CONSUMER-READINESS-1/FULL-ARTIFACT-DATA-ADAPTER-1'

def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r,r['path'];return Path(r['path'])
template=read(AD/'FULL-ARTIFACT-INPUT.TEMPLATE.NOT-AUTHORITY.json')
for row in template['validator_nodes']:
 p=auth(row['source']);raw=p.read_text();node=next(n for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name==row['name'])
 assert hashlib.sha256(ast.get_source_segment(raw,node).encode()).hexdigest()==row['source_segment_sha256']
 assert hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()==row['AST_sha256']
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(p)+':EXACT_ACCEPTED_VALIDATOR','exec'),globals())
# own/allocated/relocated_function are the exact accepted functions. Only context changes.
rels=_reuse_elf_owning_relocations;data=_reuse_elf_object_bytes;host=None;HOST_FILE=PROD_FILE=HOST_X86_FILE=PROD_X86_FILE=b''
finite_sections={'.lrodata.'+n for n in ['process_add_range_log_bridge','process_init_stack_log_bridge','process_range_public_log_bridge','process_remove_range_log_bridge','process_sched_runq_log_bridge']}

def elf(p):
 e=_ReuseElf(Path(p));e.path=Path(p);return e

def defined(e,n):return[s for s in e.symbols if s['name']==n and s['shndx']]

grant=read(R/'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json');profile=read(auth(grant['profile']));worker=read(W/'evidence/worker-result.json');producer=read(W/'evidence/producer-contract.json');assert len(worker['commands'])==4 and producer['commands']==worker['commands']and producer['contract']==profile['producer_contract']
for actual,planned in zip(worker['commands'],profile['exact_commands']):
 assert actual['argv']==planned['argv']and actual['cwd']==planned['cwd']and actual['returncode']==0
 p=W/Path(actual['output']['path']).relative_to('/work');r=ref(p);assert (r['bytes'],r['sha256'])==(actual['output']['bytes'],actual['output']['sha256'])
objects=[(r,elf(B/r['link_token']if r['replace']else auth(r['source'])))for r in profile['inputs']['objects']];bytoken={r['link_token']:e for r,e in objects};new=bytoken['rust/mckernel_rust.o'];kc=bytoken['CMakeFiles/mckernel.img.dir/syscall.c.o'];ac=bytoken['CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'];pc=bytoken['CMakeFiles/mckernel.img.dir/process.c.o'];image=Final(B/'mckernel.img')
accept=read(auth(template['historical_accepted116']));old=elf(auth(accept['tuple']['Rust']));oldkc=elf(auth(accept['tuple']['generic_C']));oldac=elf(auth(accept['tuple']['arch_C']));oldimage=Final(auth(accept['tuple']['image']))
assert len(objects)==11 and sum(r['replace']for r,e in objects)==3
assert[s for s in worker['commands'][-1]['argv']if s.endswith('.o')]==[r['link_token']for r,e in objects]
assert not [s for s in image.symbols if s['shndx']==0 and s['bind']==1 and s['name']]
inputs=template['source_facts']['source_qualified_ABI_and_declared_providers'];f03=read(auth(inputs['F03']));f06=read(auth(inputs['F06']));providers=sorted(set(f03['exported_functions_once'])|set(f06['ten_function_providers'])|{'clear_host_pte','f03_perf_mmap_v1','vdso_get_vdso_info','arch_native_signal_restore_fp_bridge'})
proofs=[];failures=[]
for n in providers:
 try:
  s=own(new,n);f=image.sym(n);assert(s['type'],s['bind'],s['size'])==(f['type'],f['bind'],f['size'])and s['type']==2 and s['bind']==1
  assert not [(r['link_token'],q)for r,e in objects if e is not new for q in defined(e,n)]
  q,raw,tokens,records=relocated_function(new,n,image)
  proofs.append(dict(name=n,input=s,final=f,unique_Rust_provider=True,full_final_instruction_and_relocation_bytes=True,relocations=records))
 except Exception as exc:failures.append(dict(group='new_provider',name=n,error=repr(exc)))
# Original registry comparator remains exact and authenticates all fields, not counts alone.
registry_before=registry(oldimage);registry_after=registry(image);compare(registry_before,registry_after)
oldproof=read(auth(accept['proofs']['ACTUAL-CURRENT-CONSUMERS-REGISTRY.json']));names={r['name']for r in oldproof['inherited_function_proofs']+oldproof['new_provider_proofs']};inherited=[]
for n in sorted(names):
 try:
  a,ab,ar,_=relocated_function(old,n);b,bb,br,rr=relocated_function(new,n,image)
  assert(a['bind'],a['type'],a['size'])==(b['bind'],b['type'],b['size']),(n,'shape')
  assert ab==bb,(n,'nonrelocatedbytes');assert ar==br,(n,'relocationprovenance')
  inherited.append(dict(name=n,all_nonrelocated_and_target_bytes_equal116=True,full_current_final_bytes=True))
 except Exception as exc:failures.append(dict(group='inherited_function',name=n,error=repr(exc)))
data_names={r['name']for r in oldproof['inherited_data_proofs']};inherited_data=[]
for n in sorted(data_names):
 try:
  a,ab,ar,_=relocated_function(old,n);b,bb,br,rr=relocated_function(new,n,image)
  assert(a['bind'],a['type'],a['size'])==(b['bind'],b['type'],b['size'])and ab==bb and ar==br
  inherited_data.append(dict(name=n,all_data_bytes_and_targets_equal116=True,full_current_final_bytes=True))
 except Exception as exc:failures.append(dict(group='inherited_data',name=n,error=repr(exc)))
storage_names=sorted(set(f06['five_Rust_storage_owners'])|{f03['data_only_BODY13']['symbol']});storage=[]
for n in storage_names:
 try:
  s=own(new,n);f=image.sym(n);assert s['type']==f['type']==1 and(s['bind'],s['size'])==(f['bind'],f['size'])
  assert not[(r['link_token'],q)for r,e in objects if e is not new for q in defined(e,n)]
  _,raw,tokens,rr=relocated_function(new,n,image);storage.append(dict(name=n,input=s,final=f,unique_Rust_data_owner=True,full_final_bytes_and_relocations=True,relocations=rr))
 except Exception as exc:failures.append(dict(group='new_storage',name=n,error=repr(exc)))
bindings=[]
for role,e in [('generic',kc),('arch',ac)]:
 for n,s in allocated(e,1).items():
  if 'binding'not in n:continue
  try:
   assert not e.sections[s['shndx']]['flags']&5
   _,raw,tokens,rr=relocated_function(e,n,image);bindings.append(dict(name=n,role=role,input=s,final=image.sym(n),actual_input_hex=data(e,s).hex(),relocations=rr,full_final_bytes_and_relocations=True))
  except Exception as exc:failures.append(dict(group='C_binding_readback',name=n,error=repr(exc)))
counts={role:dict(FUNC=len(allocated(e,2)),OBJECT=len(allocated(e,1)))for role,e in [('generic_C',kc),('arch_C',ac),('process_C',pc)]};counts['selected_C_functions']=counts['generic_C']['FUNC']+counts['arch_C']['FUNC'];counts['qualified_new_Rust_functions_observed']=len(proofs)
alloc=[s for s in pc.sections if s['flags']&2 and s['size']];counts['process_nonNOTE_ALLOC_bytes']=sum(s['size']for s in alloc if s['type']!=7);counts['process_GNU_property_NOTE_bytes']=sum(s['size']for s in alloc if s['type']==7)
function_deltas={role:dict(removed=sorted(set(allocated(old,2))-set(allocated(current,2))),added=sorted(set(allocated(current,2))-set(allocated(old,2))))for role,old,current in [('generic',oldkc,kc),('arch',oldac,ac)]}
warning_delta={}
for i in range(4):
 current=W/'evidence'/('%02d.stderr'%i);prior=Path(accept['actual_worker']['path']).parent/('%02d.stderr'%i)
 warning_delta[str(i)]=dict(actual_stderr=ref(current),prior_stderr=ref(prior),messages_added=list((collections.Counter(warnings(current))-collections.Counter(warnings(prior))).elements()),messages_removed=list((collections.Counter(warnings(prior))-collections.Counter(warnings(current))).elements()),raw_equal=current.read_bytes()==prior.read_bytes())
imports=lambda e:{s['name']for s in e.symbols if s['shndx']==0 and s['bind']==1}
result=dict(scope=__doc__.splitlines()[0],status='ACTUAL119_BOUNDED_ARTIFACT_FACTS_FULL_QUALIFICATION_OPEN',profile=grant['profile'],worker=ref(W/'evidence/worker-result.json'),producer=ref(W/'evidence/producer-contract.json'),tuple=dict(Rust=ref(new.path),generic_C=ref(kc.path),arch_C=ref(ac.path),process_C=ref(pc.path),image=ref(image.path)),counts=counts,function_deltas=function_deltas,unique_new_provider_proofs=proofs,new_storage_proofs=storage,C_readonly_binding_proofs=bindings,inherited_function_proofs=inherited,inherited_data_proofs=inherited_data,failures=failures,original389=dict(count=len(registry_after),complete_multiset_equal=True,oracle=template['original389']),warnings=warning_delta,imports_added=sorted(imports(new)-imports(old)),imports_removed=sorted(imports(old)-imports(new)),final_GLOBAL_undefined=0,artifact_acceptance=False,native_acceptance=False,wholefile_acceptance=False,runtime_authority=None,compiler_HOST_Docker_native_cleanup_calls=0)
(D/'ACTUAL119-ARTIFACT-FACTS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(counts=counts,providers=len(proofs),storage=len(storage),bindings=len(bindings),inherited_functions=len(inherited),inherited_data=len(inherited_data),failures=failures,warning_deltas=warning_delta,report=ref(D/'ACTUAL119-ARTIFACT-FACTS.json'))))
