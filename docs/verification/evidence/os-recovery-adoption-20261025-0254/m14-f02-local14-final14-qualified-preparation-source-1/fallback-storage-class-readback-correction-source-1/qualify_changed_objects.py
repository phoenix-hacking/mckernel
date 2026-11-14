"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Changed LOCAL14/config3/final14 actual objects; reuse original ELF/registry reader.
No executable/guest runs. Missing actual folded consumers remain OPEN, never PASS.
"""
import copy,hashlib,importlib.util,json,os,re,stat,struct,sys
from pathlib import Path
D=Path(__file__).resolve().parent.parent;E=D.parent
G=E/'m14-f02-verbose32-host-preparation-source-1'
N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f02-verbose46-source-1')
COUNTER=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/callback-target-reader-source-clarification-1/independent-source-profile-review-1/ACTUAL114-RETAINED-REGISTRY-COUNTEREXAMPLE.json')
RUST_CONTEXT_ROOT=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/relative-module-context-correction-source-1/context-root/kernel/rust')
CURRENT_PROPOSAL=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/relative-module-context-correction-source-1/EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json')
CURRENT_CONTEXT=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/relative-module-context-correction-source-1/CLOSED-RUST-MODULE-CONTEXT.json')
STORAGE_MANIFEST=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/fallback-storage-class-readback-correction-source-1/EXACT17-ORIGINAL-HOST-C-STORAGE.json')
STORAGE_MANIFEST_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/fallback-storage-class-readback-correction-source-1/EXACT17-ORIGINAL-HOST-C-STORAGE.json', 'bytes': 9776, 'sha256': '6bb1582edd42a7d0266c9f3c30be938f0fa889c199efb01baf81405b1321880b'}
RETAINED_IDENTITIES=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/fallback-storage-class-readback-correction-source-1/RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json')
RETAINED_IDENTITIES_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/fallback-storage-class-readback-correction-source-1/RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json', 'bytes': 25274, 'sha256': '2b0ae81a2076815c1facfa2c834a90c58a877ff993fa505a33e9423dd41068a2'}
COUNTER_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/callback-target-reader-source-clarification-1/independent-source-profile-review-1/ACTUAL114-RETAINED-REGISTRY-COUNTEREXAMPLE.json', 'bytes': 43493, 'sha256': '73af30120ba84d74519c6fe7b3c1d0c555b08bacee6328300149153de144bdbd'}

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

def process_metadata(elf,wanted,flags,file,require_retain=False):
 # Original per-record reader unchanged, scoped only to exact process symbol names.
 # Exhaustive whole-container + every unrelated record are separately checked below.
 names={row['name'] for row in wanted}
 view=copy.copy(elf)
 view.symbols=[s for s in elf.symbols if not (s['kind']==1 and 0<s['ndx']<len(elf.sections) and elf.sections[s['ndx']]['name']=='__verbose') or s['name'] in names]
 return m.metadata(view,wanted,flags,file,require_retain)

def verbose_symbols(elf):
 return [s for s in elf.symbols if s['kind']==1 and 0<s['ndx']<len(elf.sections) and elf.sections[s['ndx']]['name']=='__verbose']

def raw_verbose(elf,symbol):
 z=elf.sections[symbol['ndx']]
 assert z['flags']&3==3 and not z['flags']&4 and z['align']>=8 and symbol['value']%8==0 and symbol['size']%32==0
 at=z['off']+symbol['value']-z['addr'];raw=elf.data[at:at+symbol['size']]
 rel={off-symbol['value']:r for off,r in m.relocs(elf,symbol['ndx']).items() if symbol['value']<=off<symbol['value']+symbol['size']}
 assert all(off%32 in (0,8,16) and r[0]==1 for off,r in rel.items())
 return z,raw,rel

def preserve_unrelated(elf,baseline,manifest,label,source_files):
 others=manifest['unrelated_retained_records'];reports=[]
 for row in others:
  old=baseline.definitions(row['name']);new=elf.definitions(row['name'])
  assert len(old)==len(new)==1,(label,row['name'],'unrelated identity')
  old,new=old[0],new[0]
  assert old['kind']==new['kind']==row['type']==1 and old['bind']==new['bind']==row['bind'] and old['size']==new['size']==row['size']
  oz,raw,rel=raw_verbose(baseline,old);nz,nraw,nrel=raw_verbose(elf,new)
  assert (nz['flags']&0x200000)>=(oz['flags']&0x200000),(label,row['name'],'existing GNU_RETAIN')
  assert set(rel)==set(nrel) and normalized_raw(raw,rel)==normalized_raw(nraw,nrel),(label,row['name'],'unrelated packed words/padding/null cells')
  entries=[]
  for off,r in rel.items():
   original=string(baseline,r);actual=string(elf,nrel[off]);origin_binding='literal unchanged'
   if actual!=original:
    # HOST source FILE spelling changes only at the original FILE slot. Function,
    # FMT, words/flags, padding, bindings, sizes, and all record identities stay exact.
    assert off%32==0,(label,row['name'],off,'unrelated FUNC/FMT changed')
    if original=='/src/kernel/process.c':expected=str(D/'candidate/kernel/process.c');origin_binding='exact process C env/source operand'
    else:
     prefix='/src/kernel/rust/';assert original.startswith(prefix),(label,row['name'],original,actual)
     relative=original[len(prefix):];assert relative in source_files
     expected=str(RUST_CONTEXT_ROOT/relative);origin_binding='exact existing Rust source-directory relocation to HOST source argv'
    assert actual==expected,(label,row['name'],original,actual,expected)
   entries.append(dict(offset=off,original=original,actual=actual,provenance=origin_binding))
  reports.append(dict(name=row['name'],binding=row['bind'],bytes=row['size'],slots=row['size']//32,original_section_index=row['shndx'],actual_section=nz['name'],exact_packed_bytes_and_relocation_positions=True,string_provenance=entries))
 assert len(reports)==102 and sum(r['bytes'] for r in reports)==4064 and sum(r['slots'] for r in reports)==127
 return dict(artifact=ref(elf.path),records=reports,objects=102,slots=127,bytes=4064)

def whole_container(elf,manifest,process_rows,label):
 actual=verbose_symbols(elf);expected={r['name']:r['bytes'] for r in process_rows}
 expected.update({r['name']:r['size'] for r in manifest['unrelated_retained_records']})
 assert len(actual)==148 and len({s['name'] for s in actual})==148
 assert {s['name']:s['size'] for s in actual}==expected,(label,'exact process46 + retained unrelated102')
 assert sum(s['size'] for s in actual)==6560 and sum(s['size']//32 for s in actual)==205
 assert sum(z['size'] for z in elf.sections if z['name']=='__verbose')==6560,(label,'whole registry bytes')
 return dict(label=label,objects=148,slots=205,bytes=6560,process_objects=46,process_slots=78,process_bytes=2496,unrelated_objects=102,unrelated_slots=127,unrelated_bytes=4064)

def verify_retained_identities():
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

def main():
 verify_retained_identities()
 out=Path(sys.argv[1]);report_out=Path(sys.argv[2]);proposal=read(CURRENT_PROPOSAL)
 for key in ['retained_actual114_Rust','retained_actual114_process']:
  r=proposal[key];assert ref(r['path'])==r
 baseline=m.m.Elf(proposal['retained_actual114_process']['path'])
 rust=m.m.Elf(out/'rust-selected.o');selected=m.m.Elf(out/'selected.o');fallback=m.m.Elf(out/'optionOFF.o');joint=m.m.Elf(out/'selected-joint.o');offjoint=m.m.Elf(out/'optionOFF-joint.o')
 file=str(D/'candidate/kernel/process.c');baseline_file='/src/kernel/process.c'
 allrows=read(N/'EXACT46-SLOT78-MAP.json');locals=[x for x in allrows if x['local']]
 assert ref(COUNTER)==COUNTER_REF;manifest=read(COUNTER)
 assert manifest['retained_actual114_Rust']==proposal['retained_actual114_Rust']
 retained=m.m.Elf(proposal['retained_actual114_Rust']['path'])
 assert len(verbose_symbols(retained))==134 and sum(s['size'] for s in verbose_symbols(retained))==6112
 source_files={r['relative'] for r in read(CURRENT_CONTEXT)['Rust_files']}
 registry=[process_metadata(rust,allrows,0,file,True),m.metadata(selected,[],0,file),process_metadata(joint,allrows,0,file,True),m.metadata(fallback,locals,0,file)]
 whole_registry=[whole_container(elf,manifest,allrows,label) for elf,label in [(rust,'selectedRust'),(joint,'selectedjoint'),(offjoint,'optionOFFjoint')]]
 unrelated=[preserve_unrelated(elf,retained,manifest,label,source_files) for elf,label in [(rust,'selectedRust'),(joint,'selectedjoint'),(offjoint,'optionOFFjoint')]]
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
  exact_original_C_fallback_storage(fallback,name,size);exact_original_C_fallback_storage(offjoint,name,size)
  configs.append(dict(name=name,bytes=size,readonly=True,exact_scalar_padding_bytes=True,LOCAL_debug_pointer_fields=debug,file=file));allnew.append(name)
 finals=[]
 for row in read(D/'EXACT14-TYPES-AND-CONSUMERS.json')['objects']:
  name=row['name'];assert not selected.definitions(name);exact_original_C_fallback_storage(fallback,name,row['bytes']);exact_original_C_fallback_storage(offjoint,name,row['bytes'])
  finals.append(compare_readonly(name,row['bytes'],rust,baseline,file,baseline_file));allnew.append(name)
 # Actual compiled consumers are read from the genuine complete Rust and C objects.
 # A missing relocation may be valid folding, but requires exact compiled-code proof.
 consumers=[];open_predicates=[]
 for name in allnew:
  refs=dict(Rust=rust.allocated_references(name),C=selected.allocated_references(name),joint=joint.allocated_references(name))
  has_actual=bool(refs['Rust'] or refs['C'])
  consumers.append(dict(name=name,actual_references=refs,positive_current_reference=has_actual))
  if not has_actual:open_predicates.append(dict(name=name,predicate='Exact current folded consumer instruction/dataflow and original value/pointer ABI',reason='No surviving named relocation; do not infer consumer acceptance. Preserve these actual objects for independent focused readback, no compiler replay.'))
 result=dict(scope=__doc__.splitlines()[0],status='PASS_LOCAL14_FINAL14_HOST_OBJECT_CONFIG_AND_CONSUMERS' if not open_predicates else 'OPEN_CURRENT_FOLDED_CONSUMER_SUPPLEMENT_REQUIRED',registry=registry,whole_registry=whole_registry,retained102_provenance=unrelated,retained_counterexample=COUNTER_REF,exact_C_fallback_storage=STORAGE_MANIFEST_REF,retained_artifact_identities=RETAINED_IDENTITIES_REF,physical_C_fallback_readonly_claim=False,local14_configs=configs,final14=finals,current_consumer_readback=consumers,open_predicates=open_predicates,counts=dict(internal_debug_objects=14,slots=14,bytes=448,config_objects=3,config_bytes=384,final_objects=14,final_bytes=256),raw_pointer_cell_referent_Sync_claim=False,nondefault_full_object_link_native_acceptance=False,whole_file_retirement=False,native_acceptance=False,original_actual114_unchanged=True)
 (report_out/'LOCAL14-FINAL14-HOST-QUALIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
 if open_predicates:raise SystemExit(2)
 print('F02 LOCAL14+FINAL14 HOST boundary PASS')
if __name__=='__main__':main()
