"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Offline exact CURRENT113 artifact and selected consumer review; no workload.
"""
from pathlib import Path
import ast, hashlib, json, re, struct, subprocess, datetime
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent;B=P/'OUTPUT/work/output/build/kernel'
OLD=E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1';OB=OLD/'OUTPUT/work/output/build/kernel';Q=OLD/'independent-postbuild-review-1'
R110=E/'ROOT-CURRENT110-HOST19-BUILD-ADMISSION-1'
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
driver=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py'
assert ref(driver)['sha256']=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd'
ns=dict(Path=Path,struct=struct,hashlib=hashlib)
want={'_reuse_elf_function','_reuse_elf_owning_relocations','_reuse_elf_object_bytes'}
nodes=[n for n in ast.parse(driver.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='_ReuseElf' or isinstance(n,ast.FunctionDef) and n.name in want]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'retained ELF readers','exec'),ns)
ns.update(fn=ns['_reuse_elf_function'],rels=ns['_reuse_elf_owning_relocations'],data=ns['_reuse_elf_object_bytes'])
cp=R110/'independent-final-consumer-review-1/review_consumers.py'
nodes=[n for n in ast.parse(cp.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Final' or isinstance(n,ast.FunctionDef) and n.name=='patched']
exec(compile(ast.Module(body=nodes,type_ignores=[]),'retained exact positive target readers','exec'),ns)
Elf=ns['_ReuseElf'];Final=ns['Final'];fn=ns['fn'];rels=ns['rels'];data=ns['data'];patched=ns['patched']
p=read(P/'PROFILE.SOURCE-ONLY.json');op=read(OLD/'PROFILE.SOURCE-ONLY.json');actual=read(P/'OUTPUT/work/evidence/worker-result.json')
baseline=read(Q/'DEFAULT-ARTIFACT-REVIEW.json');accepted=read(Q/'INDEPENDENT-ACCEPTANCE.json')
assert ref(Q/'INDEPENDENT-ACCEPTANCE.json')['sha256']=='c2e8bba1120d2e289819c1991b2e5d18321741074b3ec1bbc16dee3f628ec323'
assert len(actual['commands'])==4
for a,c in zip(actual['commands'],p['exact_commands']):
 assert a['argv']==c['argv'] and a['cwd']==c['cwd'] and a['returncode']==0
 r=a['output'];f=P/'OUTPUT/work'/Path(r['path']).relative_to('/work');v=ref(f);assert (v['bytes'],v['sha256'])==(r['bytes'],r['sha256'])
objects=[]
for row in p['inputs']['objects']:
 f=B/row['link_token'] if row['replace'] else Path(row['source']['path'])
 if not row['replace']:assert ref(f)==row['source']
 objects.append((row,Elf(f)))
assert len(objects)==11 and sum(not r['replace'] for r,e in objects)==8
assert [x for x in actual['commands'][-1]['argv'] if x.endswith('.o')]==[r['link_token'] for r,e in objects]
assert actual['commands'][-1]['argv']==op['exact_commands'][-1]['argv']
for row,e in objects:assert row['link_token'] in (B/'CMakeFiles/mckernel.img.dir/link.d').read_text()
new=Elf(B/'rust/mckernel_rust.o');old=Elf(OB/'rust/mckernel_rust.o');image=Final(B/'mckernel.img');oldimage=Final(OB/'mckernel.img')
def own(e,name):
 rows=[s for s in e.symbols if s['name']==name and s['shndx']!=0];assert len(rows)==1,(name,len(rows));return rows[0]
def allocated(e,kind):return {s['name']:s for s in e.symbols if s['type']==kind and s['shndx'] and e.sections[s['shndx']]['flags']&2}
def disassemble(name):
 s=image.sym(name);return subprocess.check_output(['objdump','--no-show-raw-insn','-d','--start-address='+str(s['value']),'--stop-address='+str(s['value']+s['size']),str(image.path)],text=True)
def compare(name,patch=patched,exact_target_equivalence=None):
 a,ar=patch(old,name,oldimage);b,br=patch(new,name,image)
 assert a['size']==b['size'],(name,a['size'],b['size'])
 shape=lambda rs,mapping:[(r['offset'],r.get('type'),r['addend'],mapping.get(r.get('target'),r.get('target')),r['kind'],r.get('literal_hex')) for r in rs]
 assert shape(ar,exact_target_equivalence or {})==shape(br,{}),(name,shape(ar,{}),shape(br,{}))
 aa=bytearray(data(old,a));bb=bytearray(data(new,b))
 for r in br:aa[r['offset']:r['offset']+8]=bytes(8);bb[r['offset']:r['offset']+8]=bytes(8)
 assert aa==bb,name
 return dict(name=name,current_final=image.sym(name),current_positive_targets=br,nonrelocated_bytes_equal=True)
for section in ('.lrodata.str1.1',):
 a=next(s for s in old.sections if s['name']==section);b=next(s for s in new.sections if s['name']==section)
 assert old.raw[a['offset']:a['offset']+a['size']]==new.raw[b['offset']:b['offset']+b['size']],section
newnames=['arch_clone_reader_lock_bridge','arch_clone_reader_unlock_bridge','arch_ptrace_find_thread_bridge','arch_ptrace_thread_unlock_bridge']
names=[r['name'] for r in baseline['exports']]+newnames;assert len(set(names))==56
bytoken={r['link_token']:e for r,e in objects};kc=bytoken['CMakeFiles/mckernel.img.dir/syscall.c.o'];ac=bytoken['CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'];pc=bytoken['CMakeFiles/mckernel.img.dir/process.c.o']
oldac=Elf(OB/'CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o')
oldpc=Elf(Path(next(r['source']['path'] for r in op['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o')))
counts=dict(F03=len(allocated(kc,2)),F06=len(allocated(ac,2)),process_OBJECTs=len(allocated(pc,1)))
assert counts==dict(F03=64,F06=19,process_OBJECTs=63),counts
assert set(allocated(oldac,2))-set(allocated(ac,2))==set(newnames) and not set(allocated(ac,2))-set(allocated(oldac,2))
scalars={'process_init_stack_user_category':1,'process_page_fault_anon_clear_profile_event':4002,'process_memset_smp_fast_word_pattern':1,'process_dump_tree_enabled':0}
assert set(allocated(oldpc,1))-set(allocated(pc,1))==set(scalars) and not set(allocated(pc,1))-set(allocated(oldpc,1))
# Reuse accepted finite table/LOCAL owner resolver. The two additional named
# LOCAL providers below are exact existing scalar consumers, never unknowns.
t=ast.parse((Q/'check_selected_edges.py').read_text())
nodes=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in ('exact_target_table','special') or isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='allowed_tails' for x in n.targets)]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'retained finite named target resolver','exec'),globals())
allowed_tails=allowed_tails|{'process_helpers22process_dump_tree_node','process_helpers30process_fault_set_range_target'}
special_names={'f03_prlimit_body_result','syscall_do_prlimit64_bridge','f03_do_exit_supported_v2','f03_wait_release_thread','f03_ptrace_io_unlock','do_process_vm_read_writev','arch_rt_sigreturn_check_signal_bridge','arch_ptrace_thread_unlock_bridge'}
exports=[]
for name in names:
 s=own(new,name);f=image.sym(name);assert (s['bind'],s['type'],s['size'])==(f['bind'],f['type'],f['size']) and s['bind']==1 and s['type']==2
 assert not [v for r,e in objects if r['link_token']!='rust/mckernel_rust.o' for v in e.symbols if v['shndx'] and v['name']==name]
 resolver=special if name in special_names else patched
 s,rr=resolver(new,name,image)
 if name not in newnames:compare(name,resolver)
 exports.append(dict(name=name,Rust=s,final=f,full_current_final_bytes_reproduced=True,positive_targets=rr,accepted112_nonrelocated_body_equal=name not in newnames))
providers=[]
for name,provider in [('arch_clone_reader_lock_bridge','__mcs_rwlock_reader_lock'),('arch_clone_reader_unlock_bridge','__mcs_rwlock_reader_unlock'),('arch_ptrace_thread_unlock_bridge','thread_unlock')]:
 a=own(new,name);b=own(new,provider);fa=image.sym(name);fb=image.sym(provider)
 if provider=='thread_unlock':
  assert a['size']==b['size']==143 and data(new,a)==data(new,b) and image.bytes(fa)==image.bytes(fb)
 else:assert (a['shndx'],a['value'],a['size'])==(b['shndx'],b['value'],b['size']) and (fa['value'],fa['size'])==(fb['value'],fb['size'])
 proof=compare(provider,special if provider=='thread_unlock' else patched)
 providers.append(dict(name=name,provider=provider,exact_current_Rust_and_final_alias=provider!='thread_unlock',exact_current_body_copy=provider=='thread_unlock',provider_unchanged_from112=proof,disassembly=disassemble(name)))
s,rr=patched(new,'arch_ptrace_find_thread_bridge',image);assert s['size']==17 and len(rr)==1 and rr[0]['target']=='find_thread' and rr[0]['addend']==0
assert 'jmp    *%rax' in disassemble('arch_ptrace_find_thread_bridge')
providers.append(dict(name='arch_ptrace_find_thread_bridge',exact_17B_tailjmp_to_find_thread=True,targets=rr,disassembly=disassemble('arch_ptrace_find_thread_bridge')))
edges=[];consumer_names=set()
for row,e in objects:
 for s in e.symbols:
  if s['type'] not in (1,2) or not s['shndx'] or not e.sections[s['shndx']]['flags']&2:continue
  for r in rels(e,s):
   if r['target']['name'] not in newnames:continue
   assert r['type']==1 and r['addend']==0
   f=image.sym(s['name']);value=struct.unpack_from('<Q',image.bytes(f),r['offset'])[0]
   assert value==image.sym(r['target']['name'])['value']
   edges.append(dict(input=row['link_token'],consumer=s['name'],offset=r['offset'],provider=r['target']['name'],actual_final_address=hex(value)))
   consumer_names.add(s['name'])
assert consumer_names=={'sys_sched_getaffinity','sys_sched_getparam','sys_sched_getscheduler','sys_sched_rr_get_interval','sys_sched_setaffinity','sys_sched_setparam','sys_sched_setscheduler'} and len(edges)==10
assert image.bytes(image.sym('f03_ptrace_io_unlock'))==image.bytes(image.sym('arch_ptrace_thread_unlock_bridge'))
new_consumer_comparisons=[compare(name,exact_target_equivalence={'f03_ptrace_io_unlock':'arch_ptrace_thread_unlock_bridge'}) for name in sorted(consumer_names)]
# Four exact C-int origin transfers; raw owners and actual folded/volatile reads.
scalar_records=[]
for name,value in scalars.items():
 s=own(new,name);f=image.sym(name);sec=new.sections[s['shndx']];before=own(oldpc,name)
 assert (s['bind'],s['type'],s['size'])==(1,1,4) and sec['align']==4 and sec['flags']&7==2
 assert not rels(new,s) and data(new,s)==data(oldpc,before)==struct.pack('<i',value)==image.bytes(f)
 assert f['value']%4==0 and f['bind']==1 and f['type']==1 and f['size']==4
 assert not [v for r,e in objects if r['link_token']!='rust/mckernel_rust.o' for v in e.symbols if v['name']==name and v['shndx']]
 scalar_records.append(dict(name=name,CInt=value,Rust=s,final=f,raw_hex=data(new,s).hex(),readonly_align4=True,original_C_bytes_equal=True,no_C_owner=True))
source=lambda prof,name:Path(next(r['postimage']['path'] for r in prof['cohort_source_bindings'] if r['relative']==name))
old_helpers=source(op,'kernel/rust/process_helpers.rs').read_bytes();new_helpers=source(p,'kernel/rust/process_helpers.rs').read_bytes()
assert new_helpers.startswith(old_helpers) and b'mod process_scalar_metadata_storage' in new_helpers[len(old_helpers):]
assert b'fn ' not in new_helpers[len(old_helpers):]
scalar_consumers=['vm_range_insert','vm_range_insert_dump_bridge','process_add_range_memclear_bridge','memset_smp_handler','page_fault_process_memory_range','process_init_stack_alloc_aligned_bridge','process_init_stack_free_pages_bridge','process_memset_smp_memset_bridge']
scalar_body=[]
for name in scalar_consumers:
 resolver=special if name in ('vm_range_insert','vm_range_insert_dump_bridge','page_fault_process_memory_range') else patched
 s,rr=resolver(new,name,image);dis=disassemble(name)
 scalar_body.append(dict(name=name,Rust=s,final=image.sym(name),full_final_bytes_reproduced=True,positive_targets=rr,disassembly=dis,source_body_identical_to112=True))
def exact_two_local_functions(e,name):
 expected={'process_helpers22process_dump_tree_node':122,'process_helpers30process_fault_set_range_target':34}
 matches=[size for tail,size in expected.items() if name.endswith(tail)];assert len(matches)==1
 s=own(e,name);assert s['bind']==0 and s['type']==2 and s['size']==matches[0] and e.sections[s['shndx']]['flags']&6==6
 return s
localns=dict(globals(),fn=exact_two_local_functions)
special_node=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='special')
exec(compile(ast.Module(body=[special_node],type_ignores=[]),'same positive body resolver for two exact LOCAL functions','exec'),localns)
local_proofs=[]
for tail in ['process_helpers22process_dump_tree_node','process_helpers30process_fault_set_range_target']:
 matches=[s['name'] for s in new.symbols if s['type']==2 and s['name'].endswith(tail)];assert len(matches)==1
 local_proofs.append(compare(matches[0],localns['special']))
for name,pattern in [('process_init_stack_alloc_aligned_bridge',r'mov\s+\$0x1,%r8d\b'),('process_init_stack_free_pages_bridge',r'mov\s+\$0x1,%edx\b')]:assert len(re.findall(pattern,disassemble(name)))==1
assert not rels(new,own(new,'process_memset_smp_memset_bridge')) and own(new,'process_memset_smp_memset_bridge')['size']==211
assert not any(r['target']['name'] in ['process_memset_smp_fast_word_pattern','memset'] for name in ['process_memset_smp_memset_bridge','process_add_range_memclear_bridge','memset_smp_handler'] for r in rels(new,own(new,name)))
assert all(any(r['target']['name']=='process_dump_tree_enabled' for r in rels(new,own(new,name))) for name in ['vm_range_insert','vm_range_insert_dump_bridge'])
assert not any(r['target']['name']=='process_page_fault_anon_clear_profile_event' for r in rels(new,own(new,'page_fault_process_memory_range')))
assert '$0xfa2' in disassemble('page_fault_process_memory_range')
inherited=[compare(r['name']) for r in baseline['inherited_consumer_comparisons']]
arguments=[]
for row in baseline['thirteen_folded_arguments']:
 dis=disassemble(row['consumer']);v=row['signed_CInt'];reg=row['ABI_argument'];pattern=(r'push\s+\$0x%x\b'%v) if reg=='stack eighth' else r'mov\s+\$0x%x,%%%s\b'%(v,reg)
 found=[line.strip() for line in dis.splitlines() if re.search(pattern,line)];assert len(found)==1
 arguments.append({**row,'current_instruction':found[0]})
tables=[]
for name,size in [('process_idle_offsets',80),('process_idle_values',36),('process_timer_runtime_offsets',120),('process_sched_runqueue_offsets',208)]:
 a=own(old,name);b=own(new,name);f=image.sym(name);sec=new.sections[b['shndx']]
 assert b['size']==size and data(old,a)==data(new,b)==image.bytes(f) and not rels(new,b) and not sec['flags']&5
 assert not [s for r,e in objects if r['link_token']!='rust/mckernel_rust.o' for s in e.symbols if s['name']==name and s['shndx']]
 tables.append(dict(name=name,current_final=f,raw_hex=data(new,b).hex(),readonly_exact=True))
prior111=E/'ROOT-CURRENT111-COUNTER3-RUNQUEUE208-BUILD-ADMISSION-2/independent-final-consumer-review-1/review_current111.py'
node=next(n for n in ast.parse(prior111.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='patched_schedule')
exec(compile(ast.Module(body=[node],type_ignores=[]),'retained exact scheduler resolver','exec'),globals())
def schedule_patch(e,name,final):assert name=='schedule';return patched_schedule(e,final)
schedule=compare('schedule',schedule_patch)
for field in baseline['runqueue17_fields_revalidated']:
 for instruction in field['instructions']:assert instruction.split(':',1)[1].strip() in disassemble('schedule')
# Existing logger qualification code is reused unchanged against this new tuple.
logger_source=(Q/'check_inherited_core_current112.py').read_text()
logger_segment='q=E/'+logger_source.split('q=E/',1)[1].split('\nmetadata=[]',1)[0]
lns=dict(globals(),img=image)
exec(compile(logger_segment,'retained exact four LOCAL logger/current jump-table proof','exec'),lns)
metadata=[]
for token,e,before in [('CMakeFiles/mckernel.img.dir/process.c.o',pc,oldpc),('CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o',ac,oldac)]:
 for name,s in allocated(e,1).items():
  a=own(before,name);assert (s['bind'],s['type'],s['size'])==(a['bind'],a['type'],a['size']) and data(e,s)==data(before,a)
  shape=lambda elf,sym:[(r['offset'],r['type'],r['addend'],r['target']['name'],elf.sections[r['target']['shndx']]['name'] if r['target']['shndx'] else '') for r in rels(elf,sym)]
  ar=shape(before,a);br=shape(e,s)
  metadata.append(dict(input=token,name=name,bytes=s['size'],raw_initializers_types_bindings_equal=True,relocations_equal=ar==br,old_relocations=ar,current_relocations=br))
assert sum(x['input'].endswith('/process.c.o') for x in metadata)==63
assert all(x['relocations_equal'] for x in metadata if x['input'].endswith('/process.c.o'))
undefined=lambda e:{s['name'] for s in e.symbols if not s['shndx'] and s['name']}
undefined_delta=dict(removed=sorted(undefined(old)-undefined(new)),added=sorted(undefined(new)-undefined(old)))
assert set(undefined_delta['removed'])==set(scalars)|set(newnames) and not undefined_delta['added'],undefined_delta
stderr=P/'OUTPUT/work/evidence/00.stderr';assert stderr.read_bytes()==(OLD/'OUTPUT/work/evidence/00.stderr').read_bytes()
assert stderr.read_text().splitlines()[-1]=='' or '143 warnings emitted' in stderr.read_text()
assert (P/'OUTPUT/work/evidence/01.stderr').read_bytes()==(P/'OUTPUT/work/evidence/02.stderr').read_bytes()==b''
assert (P/'OUTPUT/work/evidence/03.stderr').read_bytes()==(OLD/'OUTPUT/work/evidence/03.stderr').read_bytes()
abi_bridge,abi_rels=patched(new,'arch_rt_sigreturn_syscall_bridge',image);assert abi_bridge['size']==17 and len(abi_rels)==1 and abi_rels[0]['target']=='syscall' and abi_rels[0]['addend']==0
for name in ['arch_start','main','monitor_init','init_host_ikc2linux','init_host_ikc2mckernel','prepare_process_ranges_args_envs','mcexec_v10_trace_enter_user']:assert image.sym(name)['shndx']
assert struct.unpack_from('<16sHHIQQQIHHHHHH',image.raw)[4]==image.sym('arch_start')['value']
report=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_CURRENT113_SELECTED_DEFAULT_ARTIFACT_AND_CURRENT_CONSUMERS',independent=True,reviewer='/root/custody_release_review',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),tuple=dict(Rust=ref(B/'rust/mckernel_rust.o'),image=ref(B/'mckernel.img'),process_C=ref(B/'CMakeFiles/mckernel.img.dir/process.c.o'),arch_C=ref(B/'CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o')),profile=ref(P/'PROFILE.SOURCE-ONLY.json'),previous_acceptance=ref(Q/'INDEPENDENT-ACCEPTANCE.json'),rawlink_inputs=11,retained_inputs=8,new_objects=3,actual_Rust_exports=56,exports=exports,actual_C_counts=dict(**counts,total=counts['F03']+counts['F06']),new_callback_providers=providers,new_actual_callback_edges=edges,new_callback_consumers=new_consumer_comparisons,callback_scope='Actual named callback edges are10 thread-unlock calls in7 scheduler consumers; other3 genuine exported Rust providers are not claimed as native execution. Lock/unlock exact aliases of retained real IRQ-save providers; find exact tailjmp.',four_new_readonly_CInt_origins=scalar_records,eight_actual_scalar_consumers=scalar_body,scalar_source_prefix_identical_to112=True,scalar_folded_effects='category1 in actualr8d/edx; PROFILE4002 immediate; fastword1 retained original word-pattern loops without alternative memset branch; volatile dump0 actual named raw reads retained.',inherited_consumer_comparisons=inherited,thirteen_folded_arguments=arguments,inherited_readonly_tables=tables,schedule=schedule,runqueue17_fields=baseline['runqueue17_fields_revalidated'],timer15_words=baseline['timer15_words'],four_LOCAL_debug_records=lns['records'],logger_current_337B_full_final_code_reproduced=True,logger_line_flags_bindings=lns['bindings'],logger_other_positive_targets=lns['other_targets'],new_C_metadata_complement=metadata,undefined_delta=undefined_delta,Rust_warnings=dict(actual=ref(stderr),accepted112=ref(OLD/'OUTPUT/work/evidence/00.stderr'),entire_stream_byte_identical=True,count=143,actual17B_syscall_tailjmp=abi_rels,original_ABI_disposition=ref(R110/'ABI-WARNING-DISPOSITION.json')),new_process_and_arch_C_stderr_empty=True,link_stderr_byte_identical=True,required_ELF_entry_and_symbols=True,elapsed_seconds=actual['commands'][-1]['finished_at_epoch']-actual['commands'][0]['started_at_epoch'],CPU_seconds=sum(r['CPU_seconds'] for r in actual['commands']),maximum_child_RSS_KiB_worker_cumulative=max(r['maximum_child_RSS_KiB'] for r in actual['commands']),native_acceptance=False,wholefile_retirement=False,original_failures_OPEN_preserved=True)
out=D/'DEFAULT-ARTIFACT-REVIEW.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(ref(out)))
