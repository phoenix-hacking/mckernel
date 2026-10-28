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

core=read(D/'CORE-ARTIFACT-READBACK.json')
assert core['decision']=='PASS_ACTUAL_CURRENT114_CORE_ARTIFACT_READBACK_PENDING_FULL_SCOPE_DISPOSITION'
# Reuse the exact already accepted four LOCAL logger readback, on actual114 bytes.
logger_source=(E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1/independent-postbuild-review-1/check_inherited_core_current112.py').read_text()
logger_segment='q=E/'+logger_source.split('q=E/',1)[1].split('\nmetadata=[]',1)[0]
lns=dict(globals(),img=image)
exec(compile(logger_segment,'retained four LOCAL logger and337B body proof','exec'),lns)

# Exact existing C metadata complement. Thirty-two globals were transferred to
# Rust above; no C local or config is silently retired.
metadata=[];delta_names={r['name'] for r in read(D/'C-METADATA-RELOCATION-DELTA.json')}
def pointer_proof(e,r,final,value):
 t=r['target'];assert r['type']==1
 if t['name']:
  f=final.sym(t['name']);assert value==f['value']+r['addend'];return dict(kind='NAMED',target=t['name'],delta=r['addend'],final_symbol=f)
 assert t['type']==3 and t['bind']==0 and t['value']==0
 sec=e.sections[t['shndx']];pos=r['addend']
 if sec['name']=='.rodata.str1.1':
  assert sec['type']==1 and sec['flags']&0x32==0x32 and not sec['flags']&5 and 0<=pos<sec['size']
  at=sec['offset']+pos;literal=e.raw[at:e.raw.index(b'\0',at)+1];assert final.at(value,len(literal),True)[0]==literal
  return dict(kind='EXACT_C_MERGED_STRING',literal_hex=literal.hex())
 owners=[v for v in e.symbols if v['name'] and v['type'] in (1,2) and v['shndx']==sec['index'] and v['value']<=pos<v['value']+v['size']]
 assert len(owners)==1,(sec['name'],pos,owners)
 owner=owners[0];f=final.sym(owner['name']);delta=pos-owner['value']
 assert (owner['bind'],owner['type'],owner['size'])==(f['bind'],f['type'],f['size']) and value==f['value']+delta
 return dict(kind='EXACT_C_SECTION_NAMED_OWNER',target=owner['name'],delta=delta,input_owner=owner,final_owner=f)
def normalize(r):
 if r['kind']=='EXACT_C_MERGED_STRING':return ('STRING',r['literal_hex'])
 name=r['target'];name='syscall_atomic64_read_bridge' if name=='perf_event_atomic64_read_bridge' else name
 return ('NAMED_OWNER',name,r['delta'])
for token,e,prior in [('kernel',kc,oldkc),('process',pc,oldpc),('arch',ac,ac)]:
 for name,s in allocated(e,1).items():
  before=own(prior,name);assert (s['bind'],s['type'],s['size'])==(before['bind'],before['type'],before['size']) and data(e,s)==data(prior,before)
  ar=rels(prior,before);br=rels(e,s);assert len(ar)==len(br)
  row=dict(input=token,name=name,bytes=s['size'],raw_initializers_types_bindings_equal113=True)
  if name in delta_names:
   f=image.sym(name);of=oldimage.sym(name);raw=bytearray(data(e,s));proofs=[]
   for a,b in zip(ar,br):
    assert (a['offset'],a['type'])==(b['offset'],b['type'])
    off=b['offset'];v=struct.unpack_from('<Q',image.bytes(f),off)[0];ov=struct.unpack_from('<Q',oldimage.bytes(of),off)[0]
    ap=pointer_proof(prior,a,oldimage,ov);bp=pointer_proof(e,b,image,v);assert normalize(ap)==normalize(bp),(name,ap,bp)
    struct.pack_into('<Q',raw,off,v);proofs.append(dict(offset=off,old=ap,current=bp,normalized_same=True))
   assert bytes(raw)==image.bytes(f);row.update(full_current_final_bytes_reproduced=True,positive_old_current_targets=proofs)
  else:
   shape=lambda elf,rr:[(r['offset'],r['type'],r['addend'],r['target']['name'],elf.sections[r['target']['shndx']]['name'] if r['target']['shndx'] else '') for r in rr]
   assert shape(e,br)==shape(prior,ar);row['all_raw_relocations_equal113']=True
  metadata.append(row)
assert len(metadata)==213 and sum(r['input']=='process' for r in metadata)==31 and len([r for r in metadata if r.get('full_current_final_bytes_reproduced')])==24

# Actual selected provider tables and their five genuine Rust consumers.
perf_tables=[]
for name in ['f03_perf_counter_providers_v1','f03_perf_read_providers_v1']:
 s=own(kc,name);f=image.sym(name);raw=bytearray(data(kc,s));rr=rels(kc,s);records=[]
 for r in rr:
  off=r['offset'];v=struct.unpack_from('<Q',image.bytes(f),off)[0];records.append(dict(offset=off,**pointer_proof(kc,r,image,v)));struct.pack_into('<Q',raw,off,v)
 assert bytes(raw)==image.bytes(f);perf_tables.append(dict(name=name,bytes=s['size'],full_final_bytes_reproduced=True,targets=records))
perf_users=[];perf_edges=[]
for s in new.symbols:
 if not s['shndx'] or s['type']!=2:continue
 for r in rels(new,s):
  if r['target']['name'] in {'f03_perf_counter_providers_v1','f03_perf_read_providers_v1'}:
   assert r['type']==1;v=struct.unpack_from('<Q',image.bytes(image.sym(s['name'])),r['offset'])[0];assert v==image.sym(r['target']['name'])['value']+r['addend']
   perf_edges.append(dict(consumer=s['name'],offset=r['offset'],table=r['target']['name'],table_field_offset=r['addend'],actual_address=hex(v)))
assert {r['consumer'] for r in perf_edges}=={'perf_counter_set','perf_event_read_value','f03_perf_stop_v1','perf_start','perf_reset'}
for n in sorted({r['consumer'] for r in perf_edges}):perf_users.append(compare(n))
assert {r['table_field_offset'] for r in perf_edges if r['consumer']=='perf_counter_set'}>={8,16}
assert any(r['consumer']=='perf_event_read_value' and r['table_field_offset']==16 for r in perf_edges)
selected={r['name'] for r in core['exports']};selected_edges=[]
for row,e in objects:
 for s in e.symbols:
  if not s['shndx'] or s['type'] not in (1,2) or not e.sections[s['shndx']]['flags']&2:continue
  for r in rels(e,s):
   if r['target']['name'] not in selected:continue
   assert r['type']==1
   f=image.sym(s['name']);v=struct.unpack_from('<Q',image.bytes(f),r['offset'])[0];assert v==image.sym(r['target']['name'])['value']+r['addend']
   selected_edges.append(dict(input=row['link_token'],consumer=s['name'],type=s['type'],offset=r['offset'],provider=r['target']['name'],addend=r['addend'],current_final_address=hex(v)))

# Preserve inherited warning disposition and real ELF/ABI witnesses.
abi,abi_rel=patched(new,'arch_rt_sigreturn_syscall_bridge',image);assert abi['size']==17 and len(abi_rel)==1 and abi_rel[0]['target']=='syscall' and abi_rel[0]['addend']==0
for name in ['arch_start','main','monitor_init','init_host_ikc2linux','init_host_ikc2mckernel','prepare_process_ranges_args_envs','mcexec_v10_trace_enter_user']:assert image.sym(name)['shndx']
assert struct.unpack_from('<16sHHIQQQIHHHHHH',image.raw)[4]==image.sym('arch_start')['value']
assert set(core['undefined_delta']['removed'])=={r['name'] for r in core['GLOBAL32']} and not core['undefined_delta']['added']
def source_path(prof,relative):return Path(next(r['postimage']['path'] for r in prof['cohort_source_bindings'] if r['relative']==relative))
osrc=source_path(oldprofile,'kernel/syscall.c');nsrc=source_path(profile,'kernel/syscall.c');declarations=[]
for name in ['syscall_itimer_offsets','sched_syscall_offsets','syscall_cputime_offsets','wait_scan_kernel_offsets','wait_zombie_kernel_offsets','ptrace_detach_kernel_offsets']:
 pattern=r'(?m)^static const struct [^\n]*\b'+name+r'\b[^=]*=\s*\{.*?^\};'
 a=re.findall(pattern,osrc.read_text(),re.S);b=re.findall(pattern,nsrc.read_text(),re.S);assert len(a)==len(b)==1 and a==b
 declarations.append(dict(name=name,initializer=a[0],sha256=hashlib.sha256(a[0].encode()).hexdigest()))
commands=[dict(index=r['index'],started_at_epoch=r['started_at_epoch'],finished_at_epoch=r['finished_at_epoch'],wall_seconds=r['finished_at_epoch']-r['started_at_epoch'],CPU_seconds=r['CPU_seconds'],maximum_child_RSS_KiB_worker_cumulative=r['maximum_child_RSS_KiB'],returncode=r['returncode'],output=r['output']) for r in worker['commands']]
report=dict(scope=__doc__.splitlines()[0],decision='PASS_EXACT_CURRENT114_METADATA_SELECTED_EDGES_LOGGERS_ABI_AND_WARNING_COMPLEMENT',reviewer='/root/current110_execution_review',independent=True,core=ref(D/'CORE-ARTIFACT-READBACK.json'),actual_commands=commands,span_seconds=commands[-1]['finished_at_epoch']-commands[0]['started_at_epoch'],sum_command_wall_seconds=sum(r['wall_seconds'] for r in commands),CPU_seconds=sum(r['CPU_seconds'] for r in commands),maximum_child_RSS_KiB_worker_cumulative=max(r['maximum_child_RSS_KiB_worker_cumulative'] for r in commands),C_metadata_213=metadata,changed_metadata24_exact_positive_final_targets=True,perf_provider_tables=perf_tables,five_perf_table_consumers=perf_users,actual_perf_table_field_edges=perf_edges,all_selected_current_final_edges=selected_edges,selected_provider_names_without_direct_object_relocation=sorted(selected-{r['provider'] for r in selected_edges}),four_inherited_LOCAL_logger_records=lns['records'],logger337B_full_final_code_reproduced=True,logger_four_flags_bindings=lns['bindings'],logger_other_targets=lns['other_targets'],required_ELF_entry_symbols=True,inherited_syscall17B_ABI_target=abi_rel,seven_inherited_kernel_warning_messages=core['kernel_C_warning'],six_unchanged_C_unused_initializers=declarations,Rust_warning_stream_byte_identical143=core['warning_stream'],undefined_removed_exactly32_now_Rust_defined_data=True,registry_order_disposition=dict(original_order_equal=False,all389_record_multiset_equal=True,actual_show_store_complete_code_equal113=True,stride32=True,explanation='Link-set section placement moves32 GLOBAL descriptors to Rust; show row order changes. No record, file/function/line selector, flags or update traversal is dropped. show enumerates start..stop; store applies predicate to every record without index-based addressing. No byte-identical sysfs listing claim.'),original_seven_older_C_section_relative_deltas_OPEN_preserved=True,native_acceptance=False,whole_file_retirement=False)
out=D/'METADATA-EDGE-ABI-WARNING-COMPLEMENT.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=report['decision'],proof=ref(out),selected_edges=len(selected_edges),providers_without_edges=report['selected_provider_names_without_direct_object_relocation'])))
