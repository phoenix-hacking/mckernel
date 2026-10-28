"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Changed LOCAL14/config3/final14 actual objects; reuse original ELF/registry reader.
No executable/guest runs. Missing actual folded consumers remain OPEN, never PASS.
"""
import hashlib,importlib.util,json,re,struct,sys
from pathlib import Path
D=Path(__file__).resolve().parent.parent;E=D.parent
G=E/'m14-f02-verbose32-host-preparation-source-1'
N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f02-verbose46-source-1')

def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load(G/'qualify_metadata.py','existing_global32_registry_and_ELF_reader')
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def one(elf,name,size,bind=1,readonly=True):
 found=elf.definitions(name);assert len(found)==1,(elf.path,name,found)
 symbol=found[0];z=elf.sections[symbol['ndx']]
 assert symbol['kind']==1 and symbol['bind']==bind and symbol['size']==size
 assert z['flags']&2 and not z['flags']&4 and z['align']>=min(size,8) and symbol['value']%min(size,8)==0
 if readonly:assert not z['flags']&1
 begin=z['off']+symbol['value']-z['addr'];raw=elf.data[begin:begin+size]
 reloc={off-symbol['value']:value for off,value in m.relocs(elf,symbol['ndx']).items() if symbol['value']<=off<symbol['value']+size}
 return symbol,z,raw,reloc

def target(elf,reloc):
 kind,symbol,addend=reloc;assert kind==1
 if not 0<symbol['ndx']<len(elf.sections):return dict(undefined_name=symbol['name'])
 z=elf.sections[symbol['ndx']];value=symbol['value']+addend
 names=[s['name'] for s in elf.symbols if s['name'] and s['ndx']==symbol['ndx'] and s['value']==value and s['kind'] in (1,2)]
 return dict(ndx=symbol['ndx'],value=value,names=names,section=z['name'])
def string(elf,reloc):
 kind,symbol,addend=reloc;assert kind==1 and 0<symbol['ndx']<len(elf.sections)
 z=elf.sections[symbol['ndx']];at=z['off']+symbol['value']+addend-z['addr'];end=z['off']+z['size']
 data=elf.data[at:end];assert b'\0' in data;return data.split(b'\0',1)[0].decode()
def same_callback(old_target,new_target):
 expected={old_target['undefined_name']} if 'undefined_name' in old_target else set(old_target['names'])
 actual={new_target['undefined_name']} if 'undefined_name' in new_target else set(new_target['names'])
 assert expected and expected&actual,('actual callback identity',old_target,new_target)
 return sorted(expected&actual)
def normalized_raw(raw,relocs):
 b=bytearray(raw)
 for off in relocs:b[off:off+8]=b'\0'*8
 return bytes(b)

def compare_readonly(name,size,new,baseline,file,baseline_file):
 _,_,raw,rel=one(new,name,size);_,_,old,oldrel=one(baseline,name,size)
 assert normalized_raw(raw,rel)==normalized_raw(old,oldrel),(name,raw.hex(),old.hex())
 assert set(rel)==set(oldrel),(name,'pointer field positions',rel,oldrel)
 targets=[]
 for off,oldr in oldrel.items():
  oldt=target(baseline,oldr);newt=target(new,rel[off])
  if 'undefined_name' in oldt or baseline.sections[oldt['ndx']]['flags']&4:
   names=same_callback(oldt,newt)
   targets.append(dict(offset=off,callback_names=names,actual=newt))
  else:
   # The fourteen default final cells/config use only source strings or callbacks.
   assert string(baseline,oldr)==baseline_file
   assert string(new,rel[off])==file
   targets.append(dict(offset=off,file=file,original_filename_context=baseline_file))
 return dict(name=name,bytes=size,readonly=True,exact_nonpointer_bytes=True,relocations=targets)

def main():
 out=Path(sys.argv[1]);proposal=read(D/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json')
 for key in ['retained_actual114_Rust','retained_actual114_process']:
  r=proposal[key];assert ref(r['path'])==r
 baseline=m.m.Elf(proposal['retained_actual114_process']['path'])
 rust=m.m.Elf(out/'rust-selected.o');selected=m.m.Elf(out/'selected.o');fallback=m.m.Elf(out/'optionOFF.o');joint=m.m.Elf(out/'selected-joint.o');offjoint=m.m.Elf(out/'optionOFF-joint.o')
 file=str(D/'candidate/kernel/process.c');baseline_file='/src/kernel/process.c'
 allrows=read(N/'EXACT46-SLOT78-MAP.json');locals=[x for x in allrows if x['local']]
 registry=[m.metadata(rust,allrows,0,file,True),m.metadata(selected,[],0,file),m.metadata(joint,allrows,0,file,True),m.metadata(fallback,locals,0,file)]
 assert sum(z['size'] for z in joint.sections if z['name']=='__verbose')==2496
 localmap=read(D/'EXACT-LOCAL14-CONFIG3-MAP.json');configs=[];allnew=[]
 for row in localmap['configs']:
  name=row['name'];size=row['bytes'];assert not selected.definitions(name)
  sym,z,raw,rel=one(rust,name,size);old_sym,old_z,old_raw,old_rel=one(baseline,name,size)
  assert normalized_raw(raw,rel)==normalized_raw(old_raw,old_rel),(name,'scalar/padding bytes')
  assert set(rel)==set(old_rel),(name,'relocation fields')
  mapping=localmap['interface_mapping'][name];debug=[]
  for field,debug_name in mapping.items():
   if field.startswith('debug['):off=row['fields']['debug'][0]+int(field[6:-1])*8
   else:off=row['fields'][field][0]
   dest=target(rust,rel[off]);actual=rust.definitions(debug_name);assert len(actual)==1 and actual[0]['bind']==0
   assert dest['ndx']==actual[0]['ndx'] and dest['value']==actual[0]['value'],(name,field,debug_name,dest)
   debug.append(dict(field=field,offset=off,actual_Rust_LOCAL=debug_name))
  fileoff=row['fields']['file'][0];assert string(rust,rel[fileoff])==file and string(baseline,old_rel[fileoff])==baseline_file
  for field,(off,kind) in row['fields'].items():
   if kind=='fn':
    original=target(baseline,old_rel[off]);actual=target(rust,rel[off]);same_callback(original,actual)
  # Existing optionOFF C owners are unique and retain original LOCAL debug targets.
  one(fallback,name,size);one(offjoint,name,size)
  configs.append(dict(name=name,bytes=size,readonly=True,exact_scalar_padding_bytes=True,LOCAL_debug_pointer_fields=debug,file=file));allnew.append(name)
 finals=[]
 for row in read(D/'EXACT14-TYPES-AND-CONSUMERS.json')['objects']:
  name=row['name'];assert not selected.definitions(name);one(fallback,name,row['bytes']);one(offjoint,name,row['bytes'])
  finals.append(compare_readonly(name,row['bytes'],rust,baseline,file,baseline_file));allnew.append(name)
 # Actual compiled consumers are read from the genuine complete Rust and C objects.
 # A missing relocation may be valid folding, but requires exact compiled-code proof.
 consumers=[];open_predicates=[]
 for name in allnew:
  refs=dict(Rust=rust.allocated_references(name),C=selected.allocated_references(name),joint=joint.allocated_references(name))
  has_actual=bool(refs['Rust'] or refs['C'])
  consumers.append(dict(name=name,actual_references=refs,positive_current_reference=has_actual))
  if not has_actual:open_predicates.append(dict(name=name,predicate='Exact current folded consumer instruction/dataflow and original value/pointer ABI',reason='No surviving named relocation; do not infer consumer acceptance. Preserve these actual objects for independent focused readback, no compiler replay.'))
 result=dict(scope=__doc__.splitlines()[0],status='PASS_LOCAL14_FINAL14_HOST_OBJECT_CONFIG_AND_CONSUMERS' if not open_predicates else 'OPEN_CURRENT_FOLDED_CONSUMER_SUPPLEMENT_REQUIRED',registry=registry,local14_configs=configs,final14=finals,current_consumer_readback=consumers,open_predicates=open_predicates,counts=dict(internal_debug_objects=14,slots=14,bytes=448,config_objects=3,config_bytes=384,final_objects=14,final_bytes=256),raw_pointer_cell_referent_Sync_claim=False,nondefault_full_object_link_native_acceptance=False,whole_file_retirement=False,native_acceptance=False,original_actual114_unchanged=True)
 (out/'LOCAL14-FINAL14-HOST-QUALIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
 if open_predicates:raise SystemExit(2)
 print('F02 LOCAL14+FINAL14 HOST boundary PASS')
if __name__=='__main__':main()
