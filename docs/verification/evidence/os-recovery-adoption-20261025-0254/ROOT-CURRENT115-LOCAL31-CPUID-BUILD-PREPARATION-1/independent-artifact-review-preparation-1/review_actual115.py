"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite offline CURRENT115 object/image review; no compiler, runtime or ownership API.
"""
from pathlib import Path
import ast,collections,hashlib,json,struct,datetime,re,subprocess
D=Path(__file__).resolve().parent; E=D.parent.parent
P=E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-4'
OLD=E/'ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1'
B=P/'OUTPUT/work/output/build/kernel'; OB=OLD/'OUTPUT/work/output/build/kernel'
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def save(name,v):
 p=D/name
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
 return ref(p)
def extract(path,names):
 t=ast.parse(Path(path).read_text());ns=[n for n in t.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in names for x in n.targets)]
 exec(compile(ast.Module(body=ns,type_ignores=[]),str(path)+':READERS_ONLY','exec'),globals())
contract=read(D/'FINITE-ARTIFACT-REVIEW-PREPARATION.json')
extract(auth(contract['elf_reader']),{'_ReuseElf','_reuse_elf_function','_reuse_elf_owning_relocations','_reuse_elf_object_bytes'})
extract(auth(contract['final_reader']),{'Final','patched'})
Elf=_ReuseElf; rels=_reuse_elf_owning_relocations;data=_reuse_elf_object_bytes
def elf(p):
 e=Elf(Path(p));e.path=Path(p);return e
def own(e,n):
 ss=[s for s in e.symbols if s['name']==n and s['shndx']];assert len(ss)==1,(n,len(ss));return ss[0]
def allocated(e,t):return {s['name']:s for s in e.symbols if s['type']==t and s['shndx'] and e.sections[s['shndx']]['flags']&2}
def cstring(final,addr):
 assert addr;s=next(s for s in final.sections if s['flags']&2 and s['addr']<=addr<s['addr']+s['size']);assert not s['flags']&5
 raw=final.payload(s);pos=addr-s['addr'];end=raw.index(b'\0',pos)+1;assert end-pos<=4096;return raw[pos:end]
profile=read(P/'PROFILE.SOURCE-ONLY.json');oldprofile=read(OLD/'PROFILE.SOURCE-ONLY.json')
assert profile['exact_commands']==contract['exact_commands']
assert profile['actual_root_adoption']==contract['actual_source_adoption'];auth(profile['actual_root_adoption'])
assert profile['origin_source_materialization']['actual_origin_producer']==contract['actual_origin_producer']
for r in contract['actual_origin']:auth(r)
tool=read(P/'ROOT-ACTUAL-TOOL-RESULT.json');assert ref(P/'ROOT-ACTUAL-TOOL-RESULT.json')['sha256']=='d871dbbb42e7e4866d8b433da58538162d1dfef224925147920bae21cfa5af81'
assert tool['tool_returncode']==0 and tool['tool_session_id']==54261
for k in ('runner_started','runner_joined','holder_local_terminal','container_terminal','worker_result'):auth(tool[k])
assert read(tool['runner_joined']['path'])['returncode']==0 and read(tool['holder_local_terminal']['path'])['joined'] is True
assert read(tool['container_terminal']['path'])['state']['ExitCode']==0
worker=read(tool['worker_result']['path']);prod=read(P/'OUTPUT/work/evidence/producer-contract.json')
assert len(worker['commands'])==len(prod['commands'])==4
for w,c in zip(worker['commands'],contract['exact_commands']):
 assert w['argv']==c['argv'] and w['cwd']==c['cwd'] and w['returncode']==0
 r=w['output'];a=ref(P/'OUTPUT/work'/Path(r['path']).relative_to('/work'));assert (a['bytes'],a['sha256'])==(r['bytes'],r['sha256'])
assert [r for r in profile['inputs']['objects'] if not r['replace']]==contract['retained_objects']
objects=[]
for r in profile['inputs']['objects']:
 path=B/r['link_token'] if r['replace'] else auth(r['source']);objects.append((r,elf(path)))
assert len(objects)==11 and sum(r['replace'] for r,e in objects)==3
assert [x for x in worker['commands'][-1]['argv'] if x.endswith('.o')]==[r['link_token'] for r,e in objects]
assert all(r['link_token'] in (B/'CMakeFiles/mckernel.img.dir/link.d').read_text() for r,e in objects)
bytoken={r['link_token']:e for r,e in objects};new=bytoken['rust/mckernel_rust.o'];pc=bytoken['CMakeFiles/mckernel.img.dir/process.c.o'];ac=bytoken['CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'];kc=bytoken['CMakeFiles/mckernel.img.dir/syscall.c.o']
old=elf(OB/'rust/mckernel_rust.o');oldpc=elf(OB/'CMakeFiles/mckernel.img.dir/process.c.o');oldac=elf(auth(next(r['source'] for r in oldprofile['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o')));image=Final(B/'mckernel.img');oldimage=Final(OB/'mckernel.img')
def pointer(e,r,final,value):
 t=r['target'];assert r['type']==1
 if t['name']:
  fs=final.sym(t['name']);assert value==fs['value']+r['addend'];return dict(kind='NAMED',target=t['name'],addend=r['addend'])
 assert t['type']==3 and t['bind']==0 and t['value']==0
 sec=e.sections[t['shndx']];pos=r['addend'];assert 0<=pos<sec['size']
 if sec['name'] in ('.lrodata.str1.1','.rodata.str1.1'):
  assert sec['flags']&0x32==0x32 and not sec['flags']&5
  at=sec['offset']+pos;literal=e.raw[at:e.raw.index(b'\0',at)+1];assert final.at(value,len(literal),True)[0]==literal
  return dict(kind='EXACT_SECTION_STRING',literal_hex=literal.hex())
 owners=[s for s in e.symbols if s['name'] and s['type'] in (1,2) and s['shndx']==sec['index'] and s['value']<=pos<s['value']+s['size']]
 assert len(owners)==1,(sec['name'],pos,owners)
 s=owners[0];fs=final.sym(s['name']);assert value==fs['value']+pos-s['value'];assert (s['type'],s['bind'],s['size'])==(fs['type'],fs['bind'],fs['size'])
 return dict(kind='EXACT_SECTION_NAMED_OWNER',target=s['name'],addend=pos-s['value'])
def storage(n,readonly,size,align):
 s=own(new,n);f=image.sym(n);sec=new.sections[s['shndx']];assert s['type']==f['type']==1 and s['size']==f['size']==size and s['value']%align==f['value']%align==0 and sec['align']>=align
 assert sec['flags']&2 and not sec['flags']&4 and bool(sec['flags']&1)==(not readonly)
 raw=bytearray(data(new,s));actual=image.bytes(f);rr=rels(new,s);targets=[]
 for r in rr:
  off=r['offset'];value=struct.unpack_from('<Q',actual,off)[0];targets.append(dict(offset=off,**pointer(new,r,image,value)));struct.pack_into('<Q',raw,off,value)
 assert bytes(raw)==actual
 return dict(name=n,input=s,final=f,section=sec,readonly=readonly,raw_hex=data(new,s).hex(),targets=targets,complete_final_bytes_reproduced=True)
spec=contract['F02_target31'];locals14=spec['internal_debug14'];configs=spec['configs3'];cells=spec['readonly14'];names={r['name'] for r in locals14+configs+cells}
assert len(names)==31 and set(allocated(oldpc,1))-set(allocated(pc,1))==names and not set(allocated(pc,1))-set(allocated(oldpc,1))
assert not any(s['name'] in names and s['shndx'] for r,e in objects if e is not new for s in e.symbols)
storage31=[storage(r['name'],False,32,8) for r in locals14]+[storage(r['name'],True,r['bytes'],r['alignment']) for r in configs]+[storage(r['name'],True,r['bytes'],4 if r['name']=='process_sched_timer_configuration' or r['bytes']==4 else 8) for r in cells]
def registry(final):
 start=final.sym('__start___verbose')['value'];stop=final.sym('__stop___verbose')['value'];assert start%8==0 and stop>start and (stop-start)%32==0
 records=[]
 for addr in range(start,stop,32):
  raw,sec=final.at(addr,32);assert sec['flags']&3==3
  file,func,fmt,bits,pad=struct.unpack('<QQQII',raw);assert pad==0
  records.append((cstring(final,file).hex(),cstring(final,func).hex(),None if not fmt else cstring(final,fmt).hex(),bits))
 return dict(start=start,stop=stop,bytes=stop-start,slots=len(records),records=records)
currentregistry=registry(image);priorregistry=registry(oldimage);assert collections.Counter(currentregistry['records'])==collections.Counter(priorregistry['records'])
process_records=[]
for row in spec['registry46']:
 s=own(new,row['name']);f=image.sym(row['name']);sec=new.sections[s['shndx']]
 assert (s['type'],s['size'],s['bind'])==(1,row['bytes'],row['binding']) and s['value']%8==f['value']%8==0 and sec['align']>=8 and sec['name']=='__verbose' and sec['flags']&0x200003==0x200003
 assert currentregistry['start']<=f['value'] and f['value']+f['size']<=currentregistry['stop']
 raw=data(new,s);rr=rels(new,s);assert len(rr)==len(row['entries'])*2
 for i,entry in enumerate(row['entries']):
  assert struct.unpack_from('<QQQII',raw,i*32)==(0,0,0,entry['line'],0)
  actual=image.bytes(f);assert struct.unpack_from('<QII',actual,i*32+16)==(0,entry['line'],0)
  for off,want in [(0,b'/src/kernel/process.c\0'),(8,entry['function'].encode()+b'\0')]:
   rel=next(r for r in rr if r['offset']==i*32+off);value=struct.unpack_from('<Q',actual,i*32+off)[0];pointer(new,rel,image,value);assert cstring(image,value)==want
 process_records.append(dict(name=row['name'],slots=len(row['entries']),bytes=s['size'],all_fields_R64_final_registry=True))
diagnostics=[]
for item in contract['CPUID']['diagnostics']:
 ss=[s for s in new.symbols if item['source_name'] in s['name'] and s['shndx']];assert len(ss)==1;name=ss[0]['name'];p=storage(name,False,32,8);raw=bytes.fromhex(p['raw_hex']);assert struct.unpack('<QQQII',raw)==(0,0,0,item['line_flags'],0)
 f=image.sym(name);actual=image.bytes(f);assert struct.unpack_from('<QII',actual,16)==(0,item['line_flags'],0)
 assert len(p['targets'])==2 and {t['offset'] for t in p['targets']}=={0,8}
 assert cstring(image,struct.unpack_from('<Q',actual,0)[0])==b'/src/arch/x86_64/kernel/syscall.c\0' and cstring(image,struct.unpack_from('<Q',actual,8)[0])==b'obtain_clone_cpuid\0'
 assert currentregistry['start']<=f['value'] and f['value']+32<=currentregistry['stop'];diagnostics.append(p)
exports=contract['accepted114_selected_exports']+[contract['additional_selected_export']];providers=[]
for name in exports:
 s=own(new,name);fs=image.sym(name);assert s['type']==fs['type']==2 and s['bind']==fs['bind']==1 and s['size']==fs['size'] and new.sections[s['shndx']]['flags']&6==6
 assert not any(x['name']==name and x['shndx'] for r,e in objects if e is not new for x in e.symbols)
 providers.append(dict(name=name,input=s,final=fs))
assert 'obtain_clone_cpuid' in allocated(oldac,2) and 'obtain_clone_cpuid' not in allocated(ac,2)
for n in ['arch_start','main','monitor_init','init_host_ikc2linux','init_host_ikc2mckernel','prepare_process_ranges_args_envs','mcexec_v10_trace_enter_user']:assert image.sym(n)['shndx']
assert struct.unpack_from('<16sHHIQQQIHHHHHH',image.raw)[4]==image.sym('arch_start')['value']
commands=[dict(index=w['index'],started_at_epoch=w['started_at_epoch'],finished_at_epoch=w['finished_at_epoch'],wall_seconds=w['finished_at_epoch']-w['started_at_epoch'],CPU_seconds=w['CPU_seconds'],maximum_child_RSS_KiB=w['maximum_child_RSS_KiB'],returncode=w['returncode'],output=w['output']) for w in worker['commands']]
base_report=dict(scope=__doc__.splitlines()[0],decision='PASS_CURRENT115_ACTUAL_PRODUCER_STORAGE_REGISTRY_ORIGIN_PREFIX_PENDING_CURRENT_CONSUMER_REVIEW',independent=True,reviewer='/root/current110_execution_review',profile=ref(P/'PROFILE.SOURCE-ONLY.json'),actual_Root_tool=ref(P/'ROOT-ACTUAL-TOOL-RESULT.json'),source_preparation=ref(D/'FINITE-ARTIFACT-REVIEW-PREPARATION.json'),previous_acceptance=contract['accepted114'],tuple=dict(Rust=ref(new.path),process_C=ref(pc.path),arch_C=ref(ac.path),retained_kernel_C=ref(kc.path),image=ref(image.path)),actual_commands=commands,span_seconds=commands[-1]['finished_at_epoch']-commands[0]['started_at_epoch'],sum_command_wall_seconds=sum(r['wall_seconds'] for r in commands),CPU_seconds=sum(r['CPU_seconds'] for r in commands),maximum_child_RSS_KiB_worker_cumulative=max(r['maximum_child_RSS_KiB'] for r in commands),counts=dict(selected_Rust_providers=len(providers),kernel_C_functions=len(allocated(kc,2)),arch_C_functions=len(allocated(ac,2)),process_C_objects=len(allocated(pc,1))),storage31=storage31,process46_records=process_records,whole_registry=currentregistry,accepted114_registry=priorregistry,registry_multiset_equal=True,registry_order_equal=currentregistry['records']==priorregistry['records'],CPUID_diagnostics=diagnostics,selected_providers=providers,new_C_imports=sorted({s['name'] for s in new.symbols if s['name'] and not s['shndx']}-{s['name'] for s in old.symbols if s['name'] and not s['shndx']}),native_acceptance=False,wholefile_retirement=False,current_free_authority=None,runtime_authority=None)
if __name__=='__main__':print(json.dumps(dict(proof=save('ACTUAL-STORAGE-REGISTRY-PRODUCER-PREFIX.json',base_report),decision=base_report['decision'])))
