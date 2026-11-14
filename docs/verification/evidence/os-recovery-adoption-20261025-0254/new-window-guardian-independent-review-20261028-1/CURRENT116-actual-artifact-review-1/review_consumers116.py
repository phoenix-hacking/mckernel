"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite actual116 vs accepted115 instruction/relocation/data/registry readback.
"""
from pathlib import Path
import ast,collections,hashlib,json,struct,importlib.util
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actual116_inventory',D/'review_actual116.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
globals().update({k:v for k,v in vars(m).items() if not k.startswith('__')})
# Reuse exact accepted115 symbolic relocation reader, without executing its original review.
def extract_current(path,names):
 tree=ast.parse(Path(path).read_bytes());nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names];assert {n.name for n in nodes}==names
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path)+':CURRENT_REVIEW_NAMESPACE','exec'),globals())
extract_current(auth(accepted['reader_sources']['review_consumers115.py']),{'literal','relocated_function'})
host=None;HOST_FILE=b'';PROD_FILE=b'';HOST_X86_FILE=b'';PROD_X86_FILE=b''
finite_sections={'.lrodata.'+n for n in ['process_add_range_log_bridge','process_init_stack_log_bridge','process_range_public_log_bridge','process_remove_range_log_bridge','process_sched_runq_log_bridge']}
prior=read(auth(accepted['proofs']['ACTUAL-CURRENT-CONSUMER-READBACK.CORRECTED.json']));supp=read(auth(accepted['proofs']['ACTUAL-PRLIMIT-DATA-FOLDED-WARNING-SUPPLEMENT.json']));comp=read(auth(accepted['proofs']['ACTUAL-INHERITED-LOGGER-ABI-COMPLEMENT.json']));prefix=read(auth(accepted['proofs']['ACTUAL-STORAGE-REGISTRY-PRODUCER-PREFIX.json']))
names={r['name'] for r in prior['selected_function_and_consumer_proofs']}|{'obtain_clone_cpuid','f03_prlimit_body_result','arch_process_vm_log_bridge'}|{r['consumer'] for r in comp['thirteen_current_folded_arguments']}
proofs=[];failures=[]
for name in sorted(names):
 try:
  a,ab,ar,_=relocated_function(old,name);b,bb,br,rr=relocated_function(new,name,image)
  assert (a['bind'],a['type'],a['size'])==(b['bind'],b['type'],b['size']),(name,'shape')
  assert ab==bb,(name,'nonrelocatedbytes')
  assert ar==br,(name,'relocationprovenance',ar,br)
  proofs.append(dict(name=name,input=b,final=image.sym(name),full_current_final_bytes_reproduced=True,instructions_and_relocation_provenance_equal115=True))
 except Exception as error:failures.append(dict(name=name,error=repr(error)))
newproof=[]
for name in providers:
 try:
  s,raw,tokens,rr=relocated_function(new,name,image);newproof.append(dict(name=name,input=s,final=image.sym(name),full_current_final_bytes_reproduced=True,actual_targets=rr))
 except Exception as error:failures.append(dict(name=name,error=repr(error)))
# Every inherited selected data owner checked at actual new-final addresses.
data_names={r['name'] for r in prefix['storage31']}|{r['name'] for r in prefix['process46_records']}
for row in supp['inherited_readonly_tables_and_scalars']:
 if isinstance(row,dict) and isinstance(row.get('name'),str):data_names.add(row['name'])
for row in comp['four_LOCAL_logger_records']:
 if isinstance(row,dict) and isinstance(row.get('name'),str):data_names.add(row['name'])
dataproofs=[]
for name in sorted(data_names):
 try:
  a,ab,ar,_=relocated_function(old,name);b,bb,br,rr=relocated_function(new,name,image)
  assert (a['bind'],a['type'],a['size'])==(b['bind'],b['type'],b['size']) and ab==bb and ar==br
  dataproofs.append(dict(name=name,input=b,final=image.sym(name),allbytes_and_relocations_equal115=True,full_current_final_bytes_reproduced=True))
 except Exception as error:failures.append(dict(data=name,error=repr(error)))
def cstring(final,addr):
 s=next(s for s in final.sections if s['flags']&2 and s['addr']<=addr<s['addr']+s['size']);assert not s['flags']&5;raw=final.payload(s);start=addr-s['addr'];end=raw.index(b'\0',start)+1;assert end-start<4096;return raw[start:end]
def registry(final):
 start=final.sym('__start___verbose')['value'];stop=final.sym('__stop___verbose')['value'];assert start%8==0 and (stop-start)%32==0
 result=[]
 for addr in range(start,stop,32):
  raw,sec=final.at(addr,32);assert sec['flags']&3==3;file,func,fmt,bits,pad=struct.unpack('<QQQII',raw);assert pad==0
  result.append((cstring(final,file).hex(),cstring(final,func).hex(),None if not fmt else cstring(final,fmt).hex(),bits))
 return result
before=registry(oldimage);after=registry(image);assert collections.Counter(before)==collections.Counter(after)
report=dict(scope=__doc__.splitlines()[0],decision='PASS_CURRENT116_FINITE_INHERITED_AND_NEW_CONSUMERS_REGISTRY' if not failures else 'OPEN_CURRENT116_CURRENT_CONSUMER_DELTA',actual_Rust=ref(new.path),actual_image=ref(image.path),inherited_function_proofs=proofs,new_provider_proofs=newproof,inherited_data_proofs=dataproofs,failures=failures,registry=dict(prior_slots=len(before),actual_slots=len(after),complete_multiset_equal115=True,order_equal=before==after,records=after),runtime_authority=None)
p=D/'ACTUAL-CURRENT-CONSUMERS-REGISTRY.json';p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':ref(p),'inherited_functions':len(proofs),'new_providers':len(newproof),'dataowners':len(dataproofs),'registry_slots':len(after),'failures':failures}))
