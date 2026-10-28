"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite CURRENT115 current-function/RELA readback using qualified114 and F02 HOST inputs.
"""
from pathlib import Path
import importlib.util,json,struct,collections
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('current115_actual_prefix',D/'review_actual115.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
globals().update({k:v for k,v in vars(m).items() if not k.startswith('__')})
F=E/'m14-f02-local14-final14-qualified-preparation-source-1';FR=F/'independent-actual-qualification-review-1'
fa=read(auth(contract['qualified_F02_actual_HOST_and_folded']));host=elf(auth(fa['actual_artifacts']['rust-selected.o']))
folded_inputs=read(auth(fa['folded_proofs']['ACTUAL-FOLDED-CONSUMER-INPUTS.json']))
folded_names={r['name'] for r in folded_inputs['consumers']}
# Exact codegen changes already present in qualified F02 wholeRust object.
qualified_codegen_names={'_RNvNtCsbVRkTr4hvpt_13mckernel_rust13sched_helpers23runq_add_thread_checked','page_fault_process_memory_range'}
HOST_X86_FILE=(str(F/'relative-module-context-correction-source-1/context-root/kernel/rust/x86_cpu_helpers.rs')+'\0').encode();PROD_X86_FILE=b'/src/kernel/rust/x86_cpu_helpers.rs\0'
HOST_FILE=(str(F/'candidate/kernel/process.c')+'\0').encode();PROD_FILE=b'/src/kernel/process.c\0'
finite=read(OLD/'independent-artifact-review-1/FINITE-ANONYMOUS-OWNER-INVENTORY.json');finite_sections={r['section']['name'] for r in finite}
def literal(e,t,add):
 sec=e.sections[t['shndx']];assert sec['type']==1 and sec['flags']&0x32==0x32 and not sec['flags']&5
 at=sec['offset']+t['value']+add;assert sec['offset']<=at<sec['offset']+sec['size'];end=e.raw.index(b'\0',at)+1;assert end<=sec['offset']+sec['size'];return e.raw[at:end]
def relocated_function(e,name,final=None):
 s=own(e,name);assert s['type'] in (1,2) and e.sections[s['shndx']]['flags']&2
 if s['type']==2:assert e.sections[s['shndx']]['flags']&6==6
 raw=bytearray(data(e,s));actual=None if final is None else final.bytes(final.sym(name));tokens=[];records=[]
 for r in rels(e,s):
  off=r['offset'];t=r['target'];assert r['type']==1 and 0<=off<=len(raw)-8;sec=e.sections[t['shndx']] if t['shndx'] else None
  val=None if actual is None else struct.unpack_from('<Q',actual,off)[0]
  if sec and sec['name'] in ('.lrodata.str1.1','.rodata.str1.1'):
   lit=literal(e,t,r['addend']);canonical=PROD_FILE if e is host and lit==HOST_FILE else PROD_X86_FILE if e is host and lit==HOST_X86_FILE else lit
   token=('EXACT_NUL_STRING',canonical.hex())
   if final:assert final.at(val,len(lit),True)[0]==lit
   detail=dict(kind='EXACT_INPUT_NUL_STRING',literal_hex=lit.hex(),canonical_FILE_context_only=(lit!=canonical))
  elif t['name']:
   token=('NAMED',t['name'],r['addend'])
   if final:assert val==final.sym(t['name'])['value']+r['addend']
   detail=dict(kind='NAMED',target=t['name'],addend=r['addend'])
  else:
   assert t['type']==3 and t['bind']==0 and t['value']==0
   pos=r['addend'];owners=[z for z in e.symbols if z['name'] and z['type'] in (1,2) and z['shndx']==t['shndx'] and z['value']<=pos<z['value']+z['size']]
   if owners:
    shapes={(z['value'],z['size'],z['type']) for z in owners};assert len(shapes)==1,(name,off,'ambiguous section range',owners)
    z=sorted(owners,key=lambda z:z['name'])[0];delta=pos-z['value'];token=('NAMED_SECTION_OWNER',tuple(sorted(z['name'] for z in owners)),delta)
    if final:
     f=final.sym(z['name']);assert val==f['value']+delta and (z['bind'],z['type'],z['size'])==(f['bind'],f['type'],f['size'])
    detail=dict(kind='EXACT_INPUT_SECTION_OWNER',owners=[z['name'] for z in owners],delta=delta)
   else:
    assert (sec['name'] in finite_sections and sec['name']=='.lrodata.'+name and name in {'process_add_range_log_bridge','process_init_stack_log_bridge','process_range_public_log_bridge','process_remove_range_log_bridge','process_sched_runq_log_bridge'}) or (name=='f03_prlimit_body_result' and sec['name'] in ('.lrodata.f03_prlimit_body_result','.lrodata..Lswitch.table.f03_prlimit_body_result')), (name,off,'unresolved anonymous target',sec['name'],pos)
    assert sec['flags']&7==2 and sec['align']==8 and sec['size'] in ((128,) if name=='f03_prlimit_body_result' else (40,72,64,88)) and pos==0
    payload=e.raw[sec['offset']:sec['offset']+sec['size']];assert payload==bytes(sec['size'])
    rr=[z for z in e.sections if z['type']==4 and z['info']==sec['index']];assert len(rr)==1 and rr[0]['size']==sec['size']//8*24
    adds=[]
    for i in range(sec['size']//8):
     a,info,add=struct.unpack_from('<QQq',e.raw,rr[0]['offset']+i*24);tt=e.symbols[info>>32]
     assert a==i*8 and info&0xffffffff==1 and tt['type']==3 and tt['shndx']==s['shndx'] and tt['value']==0 and 0<=add<s['size'];adds.append(add)
    token=('EXACT_SELF_JUMP_TABLE',tuple(adds));detail=dict(kind='EXACT_SELF_JUMP_TABLE',section=sec['name'],function_relative_targets=adds)
    if final:assert final.at(val,sec['size'],True)[0]==struct.pack('<'+'Q'*len(adds),*[final.sym(name)['value']+x for x in adds])
  tokens.append((off,r['type'],token));raw[off:off+8]=bytes(8)
  records.append(dict(offset=off,type=r['type'],input_addend=r['addend'],actual_final_address=None if val is None else hex(val),**detail))
 if final:
  patched=bytearray(data(e,s))
  for r in records:struct.pack_into('<Q',patched,r['offset'],int(r['actual_final_address'],16))
  assert bytes(patched)==actual,(name,'full actual final bytes')
 return s,bytes(raw),tokens,records
oldcore=read(auth(contract['accepted114_core']))
names=set(contract['accepted114_selected_exports'])|folded_names
for key in ['actual_selected_consumer_proofs','registry_function_proofs','inherited_consumer_proofs','inherited_scalar_consumers']:
 names.update(r['name'] for r in oldcore[key])
proofs=[];failures=[]
for name in sorted(names):
 reference=host if name in folded_names|qualified_codegen_names else old
 try:
  a,ab,ar,_=relocated_function(reference,name);b,bb,br,rr=relocated_function(new,name,image)
  assert (a['bind'],a['type'],a['size'])==(b['bind'],b['type'],b['size']),(name,'function shape')
  assert ab==bb,(name,'nonrelocated instruction bytes')
  assert ar==br,(name,'exact relocation target provenance',ar,br)
  proofs.append(dict(name=name,reference='qualified_F02_selected_HOST' if reference is host else 'accepted_CURRENT114_Rust',reference_function=a,current_function=b,final=image.sym(name),all_nonrelocated_instruction_bytes_equal=True,all_relocation_targets_equal=True,full_current_final_bytes_reproduced=True,actual_targets=rr))
 except Exception as exc:failures.append(dict(name=name,error=repr(exc)))
cpuid,raw,tokens,rr=relocated_function(new,'obtain_clone_cpuid',image)
cpuidproof=dict(name='obtain_clone_cpuid',input=cpuid,final=image.sym('obtain_clone_cpuid'),full_current_final_bytes_reproduced=True,actual_targets=rr,qualified_behavior_reused=contract['qualified_CPUID_actual_HOST'],native_lifetime_acceptance=False)
targets=set(contract['accepted114_selected_exports'])|{'obtain_clone_cpuid'}|{r['name'] for r in contract['F02_target31']['internal_debug14']+contract['F02_target31']['configs3']+contract['F02_target31']['readonly14']};edges=[]
for row,e in objects:
 for s in e.symbols:
  if not s['shndx'] or s['type'] not in (1,2) or not e.sections[s['shndx']]['flags']&2:continue
  for r in rels(e,s):
   if r['target']['name'] not in targets:continue
   assert r['type']==1;f=image.sym(s['name']);value=struct.unpack_from('<Q',image.bytes(f),r['offset'])[0];assert value==image.sym(r['target']['name'])['value']+r['addend']
   edges.append(dict(input=row['link_token'],consumer=s['name'],consumer_type=s['type'],offset=r['offset'],target=r['target']['name'],addend=r['addend'],final_address=hex(value)))
report=dict(scope=__doc__.splitlines()[0],decision='PASS_FINITE_CURRENT115_CURRENT_CONSUMER_BODY_AND_RELOCATION_READBACK' if not failures else 'OPEN_EXACT_CURRENT115_CONSUMER_DELTA_REQUIRES_DISPOSITION',independent=True,reviewer='/root/current110_execution_review',actual_Rust=ref(new.path),actual_image=ref(image.path),qualified_HOST_Rust=ref(host.path),selected_function_and_consumer_proofs=proofs,failures=failures,CPUID_full_current_function=cpuidproof,actual_selected_data_and_callback_edges=edges,FILE_literal_mapping=dict(only_exact_HOST_fixture_FILE=HOST_FILE.decode()[:-1],production_FILE=PROD_FILE.decode()[:-1]),default_native_acceptance=False,wholefile_acceptance=False)
if __name__=='__main__':print(json.dumps(dict(proof=save('ACTUAL-CURRENT-CONSUMER-READBACK.CORRECTED.json',report),decision=report['decision'],proven_functions=len(proofs),failure_names=[r['name'] for r in failures])))
