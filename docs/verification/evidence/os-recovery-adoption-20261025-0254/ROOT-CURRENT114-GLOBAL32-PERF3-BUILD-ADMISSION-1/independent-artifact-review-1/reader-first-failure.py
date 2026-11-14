"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Offline CURRENT114 ELF/source evidence reader. Never executes a compiler or guest.
"""
from pathlib import Path
import ast, collections, datetime, hashlib, json, re, struct, subprocess

D=Path(__file__).resolve().parent; P=D.parent; E=P.parent
B=P/'OUTPUT/work/output/build/kernel'
OLD=E/'ROOT-CURRENT113-ABI-PRIVATE-CORRECTION-BUILD-ADMISSION-1'
OB=OLD/'OUTPUT/work/output/build/kernel'
def read(p): return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def extract(path,names,namespace):
 t=ast.parse(Path(path).read_text());nodes=[n for n in t.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in names for x in n.targets)]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path)+':READERS_ONLY','exec'),namespace)
driver=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py'
assert ref(driver)['sha256']=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd'
extract(driver,{'_ReuseElf','_reuse_elf_function','_reuse_elf_owning_relocations','_reuse_elf_object_bytes'},globals())
Elf=_ReuseElf; rels=_reuse_elf_owning_relocations; data=_reuse_elf_object_bytes
def own(e,name):
 ss=[s for s in e.symbols if s['name']==name and s['shndx']];assert len(ss)==1,(name,len(ss));return ss[0]
def fn(e,name):
 s=own(e,name);assert s['type']==2 and e.sections[s['shndx']]['flags']&6==6;return s
extract(E/'ROOT-CURRENT110-HOST19-BUILD-ADMISSION-1/independent-final-consumer-review-1/review_consumers.py',{'Final','patched'},globals())
extract(E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1/independent-postbuild-review-1/check_selected_edges.py',{'exact_target_table','special','allowed_tails'},globals())
allowed_tails=allowed_tails|{'process_helpers22process_dump_tree_node','process_helpers30process_fault_set_range_target'}
profile=read(P/'PROFILE.SOURCE-ONLY.json');oldprofile=read(OLD/'PROFILE.SOURCE-ONLY.json')
worker=read(P/'OUTPUT/work/evidence/worker-result.json');producer=read(P/'OUTPUT/work/evidence/producer-contract.json')
baseline=read(OLD/'independent-artifact-review-1/DEFAULT-ARTIFACT-REVIEW.json')
accepted=read(OLD/'independent-artifact-review-1/INDEPENDENT-ACCEPTANCE.json')
assert ref(OLD/'independent-artifact-review-1/INDEPENDENT-ACCEPTANCE.json')['sha256']=='02c1001e037ea4d57d3d2dc5fdffa3655ce6d94c36a77ff6ea84b409f1f18cbd'
assert len(worker['commands'])==len(producer['commands'])==4
for a,c in zip(worker['commands'],profile['exact_commands']):
 assert a['argv']==c['argv'] and a['cwd']==c['cwd'] and a['returncode']==0
 out=a['output'];actual=ref(P/'OUTPUT/work'/Path(out['path']).relative_to('/work'))
 assert (actual['bytes'],actual['sha256'])==(out['bytes'],out['sha256'])
assert read(P/'HOLDER/RUNNER.JOINED.json')['returncode']==0
assert read(P/'HOLDER/BUILD-LOCAL-TERMINAL.json')['joined'] is True
assert read(P/'OUTPUT/terminal.json')['state']['ExitCode']==0
objects=[]
for row in profile['inputs']['objects']:
 path=B/row['link_token'] if row['replace'] else Path(row['source']['path'])
 if not row['replace']:assert ref(path)==row['source']
 objects.append((row,Elf(path)))
assert len(objects)==11 and sum(r['replace'] for r,e in objects)==3
assert [x for x in worker['commands'][-1]['argv'] if x.endswith('.o')]==[r['link_token'] for r,e in objects]
assert worker['commands'][-1]['argv']==oldprofile['exact_commands'][-1]['argv']
assert all(r['link_token'] in (B/'CMakeFiles/mckernel.img.dir/link.d').read_text() for r,e in objects)
bytoken={r['link_token']:e for r,e in objects};kc=bytoken['CMakeFiles/mckernel.img.dir/syscall.c.o'];pc=bytoken['CMakeFiles/mckernel.img.dir/process.c.o'];ac=bytoken['CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o']
new=Elf(B/'rust/mckernel_rust.o');old=Elf(OB/'rust/mckernel_rust.o');image=Final(B/'mckernel.img');oldimage=Final(OB/'mckernel.img')
oldkc=Elf(OB/'CMakeFiles/mckernel.img.dir/syscall.c.o');oldpc=Elf(OB/'CMakeFiles/mckernel.img.dir/process.c.o')
def allocated(e,kind):return {s['name']:s for s in e.symbols if s['type']==kind and s['shndx'] and e.sections[s['shndx']]['flags']&2}
def disassemble(name):
 s=image.sym(name);return subprocess.check_output(['objdump','--no-show-raw-insn','-d','--start-address='+str(s['value']),'--stop-address='+str(s['value']+s['size']),str(image.path)],text=True)
special_names={'f03_prlimit_body_result','syscall_do_prlimit64_bridge','f03_do_exit_supported_v2','f03_wait_release_thread','f03_ptrace_io_unlock','do_process_vm_read_writev','arch_rt_sigreturn_check_signal_bridge','arch_ptrace_thread_unlock_bridge','vm_range_insert','vm_range_insert_dump_bridge','page_fault_process_memory_range'}
def resolver(name):return special if name in special_names else patched
def compare(name,resolve=None):
 resolve=resolve or resolver(name);a,ar=resolve(old,name,oldimage);b,br=resolve(new,name,image)
 assert (a['size'],a['bind'],a['type'])==(b['size'],b['bind'],b['type']),(name,'shape')
 def shape(rs):
  # String-section addends may move only when exact final NUL bytes are proven.
  return [(r['offset'],r['type'],r.get('kind'),r.get('target'),r.get('literal_hex'),None if r.get('kind')=='EXACT_SECTION_STRING' else r['addend']) for r in rs]
 assert shape(ar)==shape(br),(name,'relocation provenance',shape(ar),shape(br))
 aa=bytearray(data(old,a));bb=bytearray(data(new,b))
 for r in br:aa[r['offset']:r['offset']+8]=bytes(8);bb[r['offset']:r['offset']+8]=bytes(8)
 assert aa==bb,(name,'nonrelocated bytes')
 return dict(name=name,Rust=b,final=image.sym(name),full_final_bytes_reproduced=True,nonrelocated_bytes_equal_113=True,positive_targets=br)

perf_names=['perf_counter_extra_set_bridge','perf_counter_init_raw_bridge','syscall_atomic64_read_bridge']
oldnames=[x['name'] for x in baseline['exports']];names=oldnames+perf_names
assert len(set(oldnames))==56 and len(set(names))==59
exports=[]
for name in names:
 s=fn(new,name);f=image.sym(name);assert (s['bind'],s['type'],s['size'])==(f['bind'],f['type'],f['size']) and s['bind']==1
 assert not [v for r,e in objects if r['link_token']!='rust/mckernel_rust.o' for v in e.symbols if v['name']==name and v['shndx']]
 if name in oldnames or name=='syscall_atomic64_read_bridge':rec=compare(name)
 else:
  s,rr=patched(new,name,image);rec=dict(name=name,Rust=s,final=f,full_final_bytes_reproduced=True,positive_targets=rr,disassembly=disassemble(name))
 exports.append(rec)
removed={'perf_counter_extra_set_bridge','perf_counter_init_raw_bridge','perf_event_atomic64_read_bridge'}
assert set(allocated(oldkc,2))-set(allocated(kc,2))==removed and not set(allocated(kc,2))-set(allocated(oldkc,2))
assert (len(allocated(kc,2)),len(allocated(ac,2)),len(allocated(pc,1)))==(61,19,31)
provider_proofs=[compare(n) for n in ['ihk_mc_perfctr_set_extra','ihk_mc_perfctr_init_raw']]

N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f02-verbose46-source-1')
mapping=read(N/'EXACT46-SLOT78-MAP.json');globals32=[r for r in mapping if not r['local']];locals14=[r for r in mapping if r['local']]
assert len(globals32)==32 and sum(r['slots'] for r in globals32)==64 and len(locals14)==14
assert set(allocated(oldpc,1))-set(allocated(pc,1))=={r['name'] for r in globals32} and not set(allocated(pc,1))-set(allocated(oldpc,1))
def input_string(e,r):
 t=r['target'];sec=e.sections[t['shndx']];assert sec['flags']&2 and not sec['flags']&5
 assert sec['type']==1 and t['type'] in (1,3)
 pos=t['value']+r['addend'];assert 0<=pos<sec['size'];raw=e.raw[sec['offset']:sec['offset']+sec['size']];end=raw.index(b'\0',pos)+1
 return raw[pos:end]
def debug_record(e,final,row,want_bind,retain):
 s=own(e,row['name']);f=final.sym(row['name']);sec=e.sections[s['shndx']]
 assert (s['bind'],s['type'],s['size'])==(want_bind,1,row['slots']*32)
 assert sec['name']=='__verbose' and sec['flags']&3==3 and sec['align']>=8 and s['value']%8==0
 if retain:assert sec['flags']&0x200000
 assert (f['bind'],f['type'],f['size'])==(s['bind'],s['type'],s['size']) and f['value']%8==0
 raw=data(e,s);actual=final.bytes(f);rr=rels(e,s);assert len(rr)==row['slots']*2
 assert {(r['offset'],r['type']) for r in rr}=={(i*32+v,1) for i in range(row['slots']) for v in (0,8)}
 rec=[]
 for i,entry in enumerate(row['entries']):
  values=struct.unpack_from('<QQQII',raw,i*32);assert values==(0,0,0,entry['line'],0),(row['name'],i,values)
  assert struct.unpack_from('<QII',actual,i*32+16)==(0,entry['line'],0)
  for field,offset,want in [('file',0,b'/src/kernel/process.c\0'),('func',8,entry['function'].encode()+b'\0')]:
   r=next(r for r in rr if r['offset']==i*32+offset);literal=input_string(e,r);assert literal==want
   value=struct.unpack_from('<Q',actual,i*32+offset)[0];found,fs=final.at(value,len(literal),readonly=True);assert found==literal
   rec.append(dict(slot=i,field=field,input_relocation=r,exact_literal_hex=literal.hex(),final_address=hex(value),final_readonly_section=fs['name']))
 return dict(name=row['name'],slots=row['slots'],bytes=s['size'],Rust_or_C=s,final=f,section_flags=sec['flags'],GNU_RETAIN=bool(sec['flags']&0x200000),exact_fields_flags0_padding_arrays=True,string_R64_proofs=rec)
debug_globals=[]
for row in globals32:
 assert not [s for _,e in objects if e is not new for s in []]  # ownership checked explicitly below
 assert not [s for rr,e in objects if rr['link_token']!='rust/mckernel_rust.o' for s in e.symbols if s['name']==row['name'] and s['shndx']]
 current=debug_record(new,image,row,1,True);prior=debug_record(oldpc,oldimage,row,1,False)
 current['original_C_field_proof']=prior;debug_globals.append(current)
debug_locals=[]
for row in locals14:
 assert not [s for s in new.symbols if s['name']==row['name'] and s['shndx']]
 current=debug_record(pc,image,row,0,False);prior=debug_record(oldpc,oldimage,row,0,False);current['original_C_field_proof']=prior;debug_locals.append(current)

def cstring(final,addr):
 assert addr
 sec=next(s for s in final.sections if s['flags']&2 and s['addr']<=addr<s['addr']+s['size']);assert not sec['flags']&5
 raw=final.payload(sec);at=addr-sec['addr'];end=raw.index(b'\0',at)+1;assert end-at<=4096;return raw[at:end].hex()
def registry(final):
 start=final.sym('__start___verbose')['value'];stop=final.sym('__stop___verbose')['value'];assert start%8==0 and stop>start and (stop-start)%32==0
 records=[]
 for addr in range(start,stop,32):
  raw,sec=final.at(addr,32);assert sec['flags']&3==3
  file,func,fmt,bits,padding=struct.unpack('<QQQII',raw);assert padding==0
  records.append((cstring(final,file),cstring(final,func),None if fmt==0 else cstring(final,fmt),bits))
 return dict(start=start,stop=stop,bytes=stop-start,slots=len(records),stride=32,records=records)
oldregistry=registry(oldimage);newregistry=registry(image)
assert collections.Counter(oldregistry['records'])==collections.Counter(newregistry['records'])
for row in globals32+locals14:
 f=image.sym(row['name']);assert newregistry['start']<=f['value'] and f['value']+f['size']<=newregistry['stop'] and (f['value']-newregistry['start'])%32==0
newregistry['original_record_multiset_equal']=True;newregistry['original_order_equal']=newregistry['records']==oldregistry['records']

# Actual raw relocations to all selected providers and new data, then full final
# consumer bytes. Do not accept unresolved anonymous addresses or section guesses.
target_names=set(perf_names)|{r['name'] for r in globals32};edges=[];consumers=set()
for row,e in objects:
 for s in e.symbols:
  if not s['shndx'] or s['type'] not in (1,2) or not e.sections[s['shndx']]['flags']&2:continue
  for r in rels(e,s):
   target=r['target']['name']
   if target not in target_names:continue
   assert r['type']==1
   f=image.sym(s['name']);value=struct.unpack_from('<Q',image.bytes(f),r['offset'])[0]
   assert value==image.sym(target)['value']+r['addend']
   edges.append(dict(input=row['link_token'],consumer=s['name'],consumer_type=s['type'],offset=r['offset'],target=target,addend=r['addend'],actual_final_address=hex(value)))
   if s['type']==2:consumers.add(s['name'])
consumer_proofs=[compare(n) for n in sorted(consumers)]
debug_registry_functions=[]
for tail in ['dynamic_debug_sysfs_show','dynamic_debug_sysfs_store']:
 candidates=[s['name'] for s in new.symbols if s['type']==2 and tail in s['name']];assert len(candidates)==1,(tail,candidates)
 debug_registry_functions.append(compare(candidates[0]))

scalars={r['name']:r for r in baseline['four_new_readonly_CInt_origins']};scalar_proofs=[]
for name in scalars:
 a=own(old,name);b=own(new,name);f=image.sym(name);sec=new.sections[b['shndx']]
 assert b['size']==4 and b['bind']==1 and not sec['flags']&5 and data(old,a)==data(new,b)==image.bytes(f)
 scalar_proofs.append(dict(name=name,bytes_hex=data(new,b).hex(),final=f,original113_equal=True))
inherited=[]
for r in baseline['inherited_consumer_comparisons']:inherited.append(compare(r['name']))
scalar_consumers=[compare(r['name']) for r in baseline['eight_actual_scalar_consumers']]
tables=[]
for r in baseline['inherited_readonly_tables']:
 name=r['name'];a=own(old,name);b=own(new,name);f=image.sym(name);assert data(old,a)==data(new,b)==image.bytes(f) and not rels(new,b)
 assert not new.sections[b['shndx']]['flags']&5;tables.append(dict(name=name,final=f,original113_bytes_equal=True))
extract(E/'ROOT-CURRENT111-COUNTER3-RUNQUEUE208-BUILD-ADMISSION-2/independent-final-consumer-review-1/review_current111.py',{'patched_schedule'},globals())
def schedule_resolver(e,name,final):assert name=='schedule';return patched_schedule(e,final)
schedule=compare('schedule',schedule_resolver)
for field in baseline['runqueue17_fields']:
 for instruction in field['instructions']:assert instruction.split(':',1)[1].strip() in disassemble('schedule')
folded=[]
for r in baseline['thirteen_folded_arguments']:
 value=r['signed_CInt'];reg=r['ABI_argument'];pattern=(r'push\s+\$0x%x\b'%value) if reg=='stack eighth' else r'mov\s+\$0x%x,%%%s\b'%(value,reg)
 actual=[l.strip() for l in disassemble(r['consumer']).splitlines() if re.search(pattern,l)];assert len(actual)==1
 folded.append({**r,'current_instruction':actual[0]})
undefined=lambda e:{s['name'] for s in e.symbols if s['name'] and not s['shndx']}
undefined_delta=dict(removed=sorted(undefined(old)-undefined(new)),added=sorted(undefined(new)-undefined(old)))
assert not undefined_delta['added']
warning=dict(current=ref(P/'OUTPUT/work/evidence/00.stderr'),old113=ref(OLD/'OUTPUT/work/evidence/00.stderr'),entire_stream_equal=(P/'OUTPUT/work/evidence/00.stderr').read_bytes()==(OLD/'OUTPUT/work/evidence/00.stderr').read_bytes())
assert warning['entire_stream_equal']
assert (P/'OUTPUT/work/evidence/01.stderr').read_bytes()==(P/'OUTPUT/work/evidence/02.stderr').read_bytes()==b''
assert (P/'OUTPUT/work/evidence/03.stderr').read_bytes()==(OLD/'OUTPUT/work/evidence/03.stderr').read_bytes()
report=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_CURRENT114_CORE_ARTIFACT_READBACK_PENDING_FULL_SCOPE_DISPOSITION',independent=True,reviewer='/root/current110_execution_review',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),profile=ref(P/'PROFILE.SOURCE-ONLY.json'),tuple=dict(Rust=ref(B/'rust/mckernel_rust.o'),kernel_C=ref(B/'CMakeFiles/mckernel.img.dir/syscall.c.o'),process_C=ref(B/'CMakeFiles/mckernel.img.dir/process.c.o'),retained_arch=ref(ac.path),image=ref(B/'mckernel.img')),previous_acceptance=ref(OLD/'independent-artifact-review-1/INDEPENDENT-ACCEPTANCE.json'),actual_commands=worker['commands'],counts=dict(Rust_selected_providers=59,C_kernel_functions=61,C_arch_functions=19,C_total=80,C_process_OBJECTs=31),exports=exports,new_perf_provider_proofs=provider_proofs,GLOBAL32=debug_globals,LOCAL14=debug_locals,registry=newregistry,old_registry=oldregistry,actual_selected_edges=edges,actual_selected_consumer_proofs=consumer_proofs,registry_function_proofs=debug_registry_functions,inherited_scalar_proofs=scalar_proofs,inherited_consumer_proofs=inherited,inherited_scalar_consumers=scalar_consumers,inherited_tables=tables,schedule=schedule,thirteen_folded_arguments=folded,undefined_delta=undefined_delta,warning_stream=warning,all_C_stderr_empty=True,link_stderr_equal113=True,native_acceptance=False,wholefile_retirement=False)
out=D/'CORE-ARTIFACT-READBACK.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=report['decision'],proof=ref(out),registry_original_order_equal=newregistry['original_order_equal'])))
