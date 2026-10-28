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
oldkc=Elf(Path(next(r['source']['path'] for r in oldprofile['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/syscall.c.o')));oldpc=Elf(OB/'CMakeFiles/mckernel.img.dir/process.c.o')
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

prefix=read(D/'POSITIVE-PREFIX-READBACK.json')
exports=prefix['exports'];provider_proofs=prefix['providers'];debug_globals=prefix['GLOBAL32'];debug_locals=prefix['LOCAL14'];newregistry=prefix['registry'];oldregistry=prefix['old_registry'];edges=prefix['edges'];consumers=prefix['consumers']
finite=read(D/'FINITE-ANONYMOUS-OWNER-INVENTORY.json')
finite_sections={r['section']['name'] for r in finite}
finite_owners={v['name'] for r in finite for v in r['owners']}
def finite_patch(elf,name,final):
 s=fn(elf,name);raw=bytearray(data(elf,s));actual=final.bytes(final.sym(name));records=[]
 for r in rels(elf,s):
  off=r['offset'];t=r['target'];assert r['type']==1 and 0<=off<=len(raw)-8;value=struct.unpack_from('<Q',actual,off)[0]
  if t['name'].startswith('.Lanon'):
   sec=elf.sections[t['shndx']];literal=data(elf,t);assert t['bind']==0 and t['type']==1 and sec['name']=='.lrodata.str1.1' and sec['flags']&0x32==0x32 and not sec['flags']&5
   assert literal in [b'file \0',b'func \0',b'line \0',b' \n\0'] and 0<=r['addend']<len(literal)
   assert final.at(value-r['addend'],len(literal),True)[0]==literal
   target=literal.hex();kind='EXACT_NAMED_LOCAL_LITERAL';detail=dict(literal_hex=literal.hex(),input_symbol=t)
  elif t['name']:
   target=t['name'];assert value==final.sym(target)['value']+r['addend'];kind='NAMED';detail={}
  else:
   sec=elf.sections[t['shndx']];assert t['type']==3 and t['bind']==0 and t['value']==0
   if sec['name']=='.lrodata.str1.1':
    assert sec['flags']&0x32==0x32 and not sec['flags']&5 and 0<=r['addend']<sec['size']
    start=sec['offset']+r['addend'];literal=elf.raw[start:elf.raw.index(b'\0',start)+1];assert final.at(value,len(literal),True)[0]==literal
    kind='EXACT_SECTION_STRING';target=None;detail=dict(literal_hex=literal.hex())
   else:
    assert sec['name'] in finite_sections,(name,off,sec['name'])
    other=old if elf is new else new;os=next(v for v in other.sections if v['name']==sec['name'])
    assert (sec['type'],sec['flags'],sec['size'],sec['align'])==(os['type'],os['flags'],os['size'],os['align'])
    owners=[v for v in elf.symbols if v['name'] in finite_owners and v['shndx']==sec['index'] and v['value']==0 and v['size']==sec['size']]
    if owners:
     assert len(owners)==1;owner=owners[0];prior=own(other,owner['name']);f=final.sym(owner['name'])
     assert (owner['bind'],owner['type'],owner['size'])==(prior['bind'],prior['type'],prior['size'])==(f['bind'],f['type'],f['size']) and owner['bind']==0
     assert r['addend']==0 and value==f['value']
     aa=bytearray(data(elf,owner));bb=bytearray(data(other,prior));rr=rels(elf,owner);pr=rels(other,prior)
     assert len(rr)==len(pr)
     for x,y in zip(rr,pr):
      assert (x['offset'],x['type'],x['target']['name'])==(y['offset'],y['type'],y['target']['name'])
      aa[x['offset']:x['offset']+8]=bytes(8);bb[y['offset']:y['offset']+8]=bytes(8)
     assert aa==bb
     if owner['type']==1:
      assert sec['type']==8 and sec['flags']&7==3 and sec['size'] in (4,8) and not rr and final.bytes(f)==bytes(sec['size'])
     kind='EXACT_NAMED_LOCAL_SECTION_OWNER';target=owner['name'];detail=dict(input_owner=owner,final_owner=f,original113_nonrelocated_owner_bytes_equal=True)
    else:
     assert sec['name']=='.lrodata.'+name and name in {'process_add_range_log_bridge','process_init_stack_log_bridge','process_range_public_log_bridge','process_remove_range_log_bridge','process_sched_runq_log_bridge'}
     assert sec['size'] in (40,72,64,88) and sec['flags']&7==2 and sec['align']==8 and r['addend']==0
     rawtable=elf.raw[sec['offset']:sec['offset']+sec['size']];assert rawtable==other.raw[os['offset']:os['offset']+os['size']]==bytes(sec['size'])
     rs=[v for v in elf.sections if v['type']==4 and v['info']==sec['index']];ors=[v for v in other.sections if v['type']==4 and v['info']==os['index']];assert len(rs)==len(ors)==1 and rs[0]['size']==ors[0]['size']==sec['size']//8*24
     targets=[]
     for i in range(sec['size']//8):
      a,info,add=struct.unpack_from('<QQq',elf.raw,rs[0]['offset']+i*24);oa,oi,od=struct.unpack_from('<QQq',other.raw,ors[0]['offset']+i*24);tt=elf.symbols[info>>32];ot=other.symbols[oi>>32]
      assert (a,info&0xffffffff,add)==(oa,oi&0xffffffff,od) and a==i*8 and info&0xffffffff==1 and 0<=add<s['size']
      assert tt['type']==ot['type']==3 and tt['shndx']==s['shndx'] and ot['shndx']==fn(other,name)['shndx'] and tt['value']==ot['value']==0
      targets.append(final.sym(name)['value']+add)
     assert final.at(value,sec['size'],True)[0]==struct.pack('<'+'Q'*len(targets),*targets)
     kind='EXACT_SELF_FUNCTION_JUMP_TABLE';target=sec['name'];detail=dict(table_bytes=sec['size'],actual_targets=targets,original113_table_equal=True)
  struct.pack_into('<Q',raw,off,value);records.append(dict(offset=off,type=1,addend=r['addend'],kind=kind,target=target,actual_final_address=hex(value),**detail))
 assert bytes(raw)==actual,(name,'complete final bytes')
 return s,records
extract(E/'ROOT-CURRENT111-COUNTER3-RUNQUEUE208-BUILD-ADMISSION-2/independent-final-consumer-review-1/review_current111.py',{'patched_schedule'},globals())
def schedule_resolver(e,name,final):assert name=='schedule';return patched_schedule(e,final)
consumer_proofs=read(D/'SELECTED-DATA-CONSUMERS.json')

debug_registry_functions=[]
for tail in ['dynamic_debug_sysfs_show','dynamic_debug_sysfs_store']:
 candidates=[s['name'] for s in new.symbols if s['type']==2 and tail in s['name']];assert len(candidates)==1,(tail,candidates)
 debug_registry_functions.append(compare(candidates[0],finite_patch))

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
report=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_CURRENT114_CORE_ARTIFACT_READBACK_PENDING_FULL_SCOPE_DISPOSITION',independent=True,reviewer='/root/current110_execution_review',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),profile=ref(P/'PROFILE.SOURCE-ONLY.json'),tuple=dict(Rust=ref(B/'rust/mckernel_rust.o'),kernel_C=ref(B/'CMakeFiles/mckernel.img.dir/syscall.c.o'),process_C=ref(B/'CMakeFiles/mckernel.img.dir/process.c.o'),retained_arch=next(r['source'] for r,e in objects if r['link_token']=='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'),image=ref(B/'mckernel.img')),previous_acceptance=ref(OLD/'independent-artifact-review-1/INDEPENDENT-ACCEPTANCE.json'),actual_commands=worker['commands'],counts=dict(Rust_selected_providers=59,C_kernel_functions=61,C_arch_functions=19,C_total=80,C_process_OBJECTs=31),exports=exports,new_perf_provider_proofs=provider_proofs,GLOBAL32=debug_globals,LOCAL14=debug_locals,registry=newregistry,old_registry=oldregistry,actual_selected_edges=edges,actual_selected_consumer_proofs=consumer_proofs,registry_function_proofs=debug_registry_functions,inherited_scalar_proofs=scalar_proofs,inherited_consumer_proofs=inherited,inherited_scalar_consumers=scalar_consumers,inherited_tables=tables,schedule=schedule,thirteen_folded_arguments=folded,undefined_delta=undefined_delta,warning_stream=warning,all_C_stderr_empty=True,link_stderr_equal113=True,native_acceptance=False,wholefile_retirement=False)
out=D/'CORE-ARTIFACT-READBACK.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=report['decision'],proof=ref(out),registry_original_order_equal=newregistry['original_order_equal'])))
