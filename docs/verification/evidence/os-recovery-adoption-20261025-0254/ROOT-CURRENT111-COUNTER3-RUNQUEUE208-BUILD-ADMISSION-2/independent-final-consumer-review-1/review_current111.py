"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact retained-artifact CURRENT111 review. No build, tests or native invocation.
"""
from pathlib import Path
import ast, collections, datetime, hashlib, json, re, struct, subprocess
D=Path(__file__).resolve().parent; P=D.parent; E=P.parent; B=P/'OUTPUT/work/output/build/kernel'
OLD=E/'ROOT-CURRENT110-HOST19-BUILD-ADMISSION-1'; OB=OLD/'OUTPUT/work/output/build/kernel'
Q=E/'current111-counter3-runqueue208-production-preparation-source-1'
def ref(f):
    f=Path(f); raw=f.read_bytes(); return dict(path=str(f),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(f): return json.loads(Path(f).read_bytes())
def authenticate(row):
    assert ref(row['path'])==row
    return read(row['path'])
prior=OLD/'independent-final-consumer-review-1'
assert ref(prior/'DEFAULT-ARTIFACT-REVIEW.json')['sha256']=='01e8f3771fb2dbf807b56bd68e3a86c88b54519a503772bd47ea78002db227f8'
assert ref(prior/'CONSUMER-REVIEW.json')['sha256']=='cb63220e522a7de8410d08bc18ea9e9f5dcc384c3f60162297072aa27e7346a3'
driver=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py'
assert ref(driver)['sha256']=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd'
ns=dict(Path=Path,struct=struct,hashlib=hashlib)
want={'_reuse_elf_function','_reuse_elf_owning_relocations','_reuse_elf_object_bytes'}
nodes=[n for n in ast.parse(driver.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='_ReuseElf' or isinstance(n,ast.FunctionDef) and n.name in want]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'retained exact ET_REL readers','exec'),ns)
ns.update(fn=ns['_reuse_elf_function'],rels=ns['_reuse_elf_owning_relocations'],data=ns['_reuse_elf_object_bytes'])
nodes=[n for n in ast.parse((prior/'review_consumers.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Final' or isinstance(n,ast.FunctionDef) and n.name=='patched']
exec(compile(ast.Module(body=nodes,type_ignores=[]),'retained exact named/anonymous target readers','exec'),ns)
Elf=ns['_ReuseElf']; Final=ns['Final']; fn=ns['fn']; rels=ns['rels']; data=ns['data']; patched=ns['patched']
p=read(P/'PROFILE.SOURCE-ONLY.json'); op=read(OLD/'PROFILE.SOURCE-ONLY.json'); actual=read(P/'OUTPUT/work/evidence/worker-result.json')
assert ref(P/'PROFILE.SOURCE-ONLY.json')['sha256']=='82b1159fc5e39220a370f5024b9df4069d2f764748015f017203e824288313fa'
assert ref(B/'rust/mckernel_rust.o')['sha256']=='1836ac74294186335742d17b4d53cd2217b2b17f6f471d317e55faf1fa7f346b'
assert ref(B/'mckernel.img')['sha256']=='0bbe8259f4c2dd1d0b54616b3b84842bcf2991e2417346371449cfd66ed9fb69'
source_review=read(Q/'independent-source-review-1/REVIEW.json'); assert ref(Q/'independent-source-review-1/REVIEW.json')['sha256']=='cdeebb42941bf2afdfd6d1ab5de621be21673363e9fd009ce077f67623c3f1b9'
assert source_review['decision']=='PASS_SOURCE'
sources={r['relative']:r['postimage'] for r in p['cohort_source_bindings']}; olds={r['relative']:r['postimage'] for r in op['cohort_source_bindings']}
for r in sources.values(): assert ref(r['path'])==r
changed=[n for n in sources if sources[n]['sha256']!=olds[n]['sha256']]
assert set(changed)=={'kernel/CMakeLists.txt','kernel/process.c','kernel/syscall.c','kernel/rust/sched_helpers.rs','kernel/rust/syscall_policy.rs'}
pub=read(P/'ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json')
for row in pub['rows']: assert ref(row['actual']['path'])==row['actual']
assert pub['commit']=='6440c9f476d058b9867d76df9affe7402ecb4cac'
assert len(actual['commands'])==4
for a,c in zip(actual['commands'],p['exact_commands']):
    assert a['argv']==c['argv'] and a['cwd']==c['cwd'] and a['returncode']==0
    r=a['output']; f=P/'OUTPUT/work'/Path(r['path']).relative_to('/work')
    assert (ref(f)['bytes'],ref(f)['sha256'])==(r['bytes'],r['sha256'])
objects=[]
for row in p['inputs']['objects']:
    f=B/row['link_token'] if row['replace'] else Path(row['source']['path'])
    if not row['replace']: assert ref(f)==row['source']
    objects.append((row,Elf(f)))
assert len(objects)==11 and sum(not row['replace'] for row,elf in objects)==8
assert actual['commands'][-1]['argv']==op['exact_commands'][-1]['argv']
tokens=[a for a in actual['commands'][-1]['argv'] if a.endswith('.o')]
assert tokens==[row['link_token'] for row,elf in objects]
dep=(B/'CMakeFiles/mckernel.img.dir/link.d').read_text()
for token in tokens: assert token in dep
new=Elf(B/'rust/mckernel_rust.o'); old=Elf(OB/'rust/mckernel_rust.o'); image=Final(B/'mckernel.img'); oldimage=Final(OB/'mckernel.img')
def defined(elf,name):
    rows=[s for s in elf.symbols if s['name']==name and s['shndx']!=0]; assert len(rows)==1,(name,len(rows)); return rows[0]
def allocated(elf,kind): return {s['name']:s for s in elf.symbols if s['type']==kind and s['shndx']!=0 and elf.sections[s['shndx']]['flags']&2}
bytoken={row['link_token']:elf for row,elf in objects}
newnames=['perf_counter_mask_check_bridge','perf_counter_start_bridge','perf_counter_stop_bridge']
old_next=read(E/'current110-host19-production-preparation-source-1/resource-and-qualifier-preparation-1/next-provider-path-correction-source-1/actual-suffix-qualification-1/NEXT-PROVIDERS-RESULT.json')
names=[r['name'] for r in old_next['phases']['actual_forty_five_Rust_exports']]+newnames; assert len(set(names))==48
exports=[]
for name in names:
    s=defined(new,name); f=image.sym(name); assert s['bind']==f['bind']==1 and s['type']==f['type']==2 and s['size']==f['size']
    assert not [v for row,elf in objects if row['link_token']!='rust/mckernel_rust.o' for v in elf.symbols if v['name']==name and v['shndx']!=0]
    exports.append(dict(name=name,Rust=s,final=f))
kc=bytoken['CMakeFiles/mckernel.img.dir/syscall.c.o']; pc=bytoken['CMakeFiles/mckernel.img.dir/process.c.o']; ac=bytoken['CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o']
oldkc=Elf(OB/'CMakeFiles/mckernel.img.dir/syscall.c.o'); oldpc=Elf(OB/'CMakeFiles/mckernel.img.dir/process.c.o')
assert set(allocated(oldkc,2))-set(allocated(kc,2))==set(newnames) and not set(allocated(kc,2))-set(allocated(oldkc,2))
assert len(allocated(kc,2))==66 and len(allocated(ac,2))==25 and len(allocated(pc,1))==67
assert set(allocated(oldpc,1))-set(allocated(pc,1))=={'process_sched_runqueue_offsets'} and not set(allocated(pc,1))-set(allocated(oldpc,1))
undef=lambda elf:{s['name'] for s in elf.symbols if s['shndx']==0 and s['name']}
assert undef(old)-undef(new)=={'process_sched_runqueue_offsets'} and not undef(new)-undef(old)

# Exact existing 13 folded arguments, timer and idle current final bytes.
previous=read(prior/'CONSUMER-REVIEW.json'); comparisons=[]
for entry in previous['consumer_comparisons']:
    name=entry['consumer']; before,br=patched(old,name,oldimage); after,ar=patched(new,name,image)
    assert before['size']==after['size']; ba=bytearray(data(old,before)); aa=bytearray(data(new,after))
    shape=lambda rs:[(r['offset'],r['type'],r['addend'],r.get('target'),r['kind'],r.get('literal_hex')) for r in rs]
    assert shape(br)==shape(ar)
    for row in ar: ba[row['offset']:row['offset']+8]=bytes(8);aa[row['offset']:row['offset']+8]=bytes(8)
    assert ba==aa
    comparisons.append(dict(consumer=name,nonrelocated_bytes_equal=True,current_final=image.sym(name),old_targets=br,current_targets=ar))
arguments=[]
def disassemble(name):
    s=image.sym(name)
    return subprocess.check_output(['objdump','--no-show-raw-insn','-d','--start-address='+str(s['value']),'--stop-address='+str(s['value']+s['size']),str(image.path)],text=True)
for row in previous['thirteen_current_ABI_arguments']:
    dis=disassemble(row['consumer']); value=row['signed_CInt']; reg=row['ABI_argument']
    pattern=(r'push\s+\$0x%x\b'%value) if reg=='stack eighth' else r'mov\s+\$0x%x,%%%s\b'%(value,reg)
    rows=[s.strip() for s in dis.splitlines() if re.search(pattern,s)];assert len(rows)==1
    arguments.append(dict(data=row['data'],consumer=row['consumer'],signed_CInt=value,ABI_argument=reg,current_instruction=rows[0]))
idle_s,idle_rels=patched(new,'process_idle_entry',image); idledis=disassemble('process_idle_entry')
for name,reg in [('process_idle_offsets','rdx'),('process_idle_values','rcx'),('process_idle_callbacks','r8')]:
    address=image.sym(name)['value']; assert re.search(r'movabs\s+\$0x%x,%%%s\b'%(address,reg),idledis)
for name,table in previous['idle116']['tables'].items():
    s=defined(new,name);f=image.sym(name);raw,sec=image.at(f['value'],f['size'],True)
    assert data(new,s)==raw==bytes.fromhex(table['bytes_hex']) and not rels(new,s) and f['value']%table['alignment']==0
timer=previous['timer']; t=defined(new,'process_timer_runtime_offsets'); ft=image.sym(t['name']);traw,ts=image.at(ft['value'],120,True)
assert list(struct.unpack('<15Q',traw))==timer['all15_words'] and traw==data(new,t) and not rels(new,t) and ft['value']%8==0
timerdis=disassemble('set_timer')
for token in timer['current_consumed_instruction_tokens'].values():assert token in timerdis

# All new descriptor words are proved; schedule has genuine constant folding.
name='process_sched_runqueue_offsets'; table=defined(new,name); sec=new.sections[table['shndx']]
assert (table['bind'],table['type'],table['size'])==(1,1,208) and sec['align']>=8 and sec['flags']&2 and not sec['flags']&5 and not rels(new,table)
raw=data(new,table); prior_table=defined(oldpc,name); assert raw==data(oldpc,prior_table)
host=E/'m14-f02-next-readonly-data-new12h-1/successor-host-profile-3/HOST-output-proposed-3';hostproof=read(host/'OWNERSHIP.json')
assert all(row['bytes_hex']==raw.hex() for row in hostproof['data'])
f=image.sym(name);finalraw,fs=image.at(f['value'],208,True);assert finalraw==raw and f['value']%8==0 and f['type']==1 and f['bind']==1
assert not [s for row,elf in objects if row['link_token']!='rust/mckernel_rust.o' for s in elf.symbols if s['name']==name and s['shndx']!=0]
schedsrc=Path(sources['kernel/rust/sched_helpers.rs']['path']).read_text(); fields=re.findall(r'pub (\w+): usize,',schedsrc.split('pub struct SchedRunqueueOffsets {',1)[1].split('\n}',1)[0]);words=list(struct.unpack('<26Q',raw));assert len(fields)==26
def patched_schedule(elf,final):
    # Exact additional original scheduler log counter, never a generic anonymous skip.
    symbol=fn(elf,'schedule'); raw=bytearray(data(elf,symbol)); f=final.sym('schedule')
    actualbytes=final.bytes(f); records=[];last=-8
    counter='_RNvNtNtCsbVRkTr4hvpt_13mckernel_rust15process_helpers32remaining_process_schedule_entry25MCEXEC_V10_SCHEDULER_LOGS'
    for r in sorted(rels(elf,symbol),key=lambda x:x['offset']):
        off=r['offset']; assert r['type']==1 and off>=last+8 and off+8<=len(raw);last=off
        target=r['target'];value=struct.unpack_from('<Q',actualbytes,off)[0]
        if target['name']:
            fs=final.sym(target['name']);assert value==(fs['value']+r['addend'])&((1<<64)-1)
            rec=dict(kind='NAMED',target=target['name'],final_symbol=fs)
        else:
            sec=elf.sections[target['shndx']];assert target['type']==3 and target['bind']==0 and target['value']==0
            if sec['name']=='.lbss.'+counter:
                assert sec['type']==8 and sec['size']==4 and sec['align']==4 and sec['flags']&7==3 and r['addend']==0
                matches=[s for s in elf.symbols if s['name']==counter and s['shndx']==target['shndx'] and s['type']==1 and s['value']==0 and s['size']==4]
                assert len(matches)==1
                fs=final.sym(counter);assert fs['type']==1 and fs['size']==4 and fs['value']%4==0 and value==fs['value'] and final.bytes(fs)==bytes(4)
                rec=dict(kind='EXACT_NAMED_SCHEDULER_LOG_COUNTER',target=counter,input_named_owner=matches[0],final_symbol=fs,initial_hex='00000000')
            else:
                assert sec['name']=='.lrodata.str1.1' and sec['flags']&0x32==0x32 and not sec['flags']&5
                section=elf.raw[sec['offset']:sec['offset']+sec['size']];start=r['addend'];assert 0<=start<len(section);end=section.index(b'\0',start)+1;literal=section[start:end];assert len(literal)>1
                found,fs=final.at(value,len(literal),readonly=True);assert found==literal
                rec=dict(kind='EXACT_SECTION_STRING',literal_hex=literal.hex(),literal=literal[:-1].decode(),final_readonly_section=fs['name'])
        struct.pack_into('<Q',raw,off,value);records.append(dict(offset=off,type=1,addend=r['addend'],actual_final_address=hex(value),**rec))
    assert bytes(raw)==actualbytes and len([r for r in records if r['kind']=='EXACT_NAMED_SCHEDULER_LOG_COUNTER'])==1
    return symbol,records
schedule,schrels=patched_schedule(new,image); oldschedule,oldschrels=patched_schedule(old,oldimage)
oldtable=[r for r in oldschrels if r.get('target')==name];assert len(oldtable)==26 and not [r for r in schrels if r.get('target')==name]
schedule_dis=disassemble('schedule'); folded=[]
for index in sorted({r['addend']//8 for r in oldtable}):
    val=words[index]
    pattern=r'(?<![0-9a-f])0x%x\b'%val
    matches=[line.strip() for line in schedule_dis.splitlines() if re.search(pattern,line)]
    derivation=None
    if index==10:
        assert fields[index]=='thread_mod_clone_offset' and val==5212 and words[5]==4328
        assert 'lea    -0x10e8(%r13),%r14' in schedule_dis
        matches=[line.strip() for line in schedule_dis.splitlines() if 'mov    0x374(%r13),%ecx' in line]
        derivation='sched_list pointer + (thread_mod_clone5212 - thread_sched_list4328) = +884/0x374; current Thread base separately lea-0x10e8(%r13),%r14'
    assert matches,(fields[index],val)
    folded.append(dict(index=index,field=fields[index],value=val,instructions=matches,exact_derived_offset=derivation))
assert len(folded)==17
# The standalone same-source typed provider remains current object/final exact.
provider='sched_schedule_prepare_body_result';bps,bpr=patched(old,provider,oldimage);aps,apr=patched(new,provider,image)
assert bps['size']==aps['size'];ba=bytearray(data(old,bps));aa=bytearray(data(new,aps))
assert [(r['offset'],r.get('target'),r['addend'],r['kind']) for r in bpr]==[(r['offset'],r.get('target'),r['addend'],r['kind']) for r in apr]
for r in apr:ba[r['offset']:r['offset']+8]=bytes(8);aa[r['offset']:r['offset']+8]=bytes(8)
assert ba==aa

# New mask/start bodies are exact compiler aliases of genuine existing providers.
bridges=[]
for name,provider in [('perf_counter_mask_check_bridge','ihk_mc_perf_counter_mask_check'),('perf_counter_start_bridge','ihk_mc_perfctr_start')]:
    a=defined(new,name); b=defined(new,provider);fa=image.sym(name);fb=image.sym(provider)
    assert (a['shndx'],a['value'],a['size'])==(b['shndx'],b['value'],b['size']) and (fa['value'],fa['size'])==(fb['value'],fb['size'])
    patched(new,name,image)
    bridges.append(dict(name=name,provider=provider,exact_Rust_alias=True,Rust=a,final=fa,disassembly=disassemble(name)))
stop,sr=patched(new,'perf_counter_stop_bridge',image); assert stop['size']==17 and len(sr)==1 and sr[0]['target']=='ihk_mc_perfctr_stop' and sr[0]['addend']==0
bridges.append(dict(name='perf_counter_stop_bridge',provider='ihk_mc_perfctr_stop',unchanged_mask_RDI_signed_flags_ESI=True,targets=sr,disassembly=disassemble('perf_counter_stop_bridge')))

# Entire stderr equals the accepted old stream; source contexts are still bound.
stderr=P/'OUTPUT/work/evidence/00.stderr'; oldstderr=OLD/'OUTPUT/work/evidence/00.stderr'; assert stderr.read_bytes()==oldstderr.read_bytes()
headers=re.findall(r'^warning(?:\[[^\]]+\])?: .+$',stderr.read_text(),re.M);assert headers[-1]=='warning: 143 warnings emitted'
for n in ['kernel/rust/init.rs','kernel/rust/arch_rt_sigreturn_syscall_bridge.rs','kernel/rust/abi.rs']:assert sources[n]['sha256']==olds[n]['sha256']
bridge,br=patched(new,'arch_rt_sigreturn_syscall_bridge',image);assert bridge['size']==17 and len(br)==1 and br[0]['target']=='syscall' and br[0]['addend']==0
warnings=dict(actual=ref(stderr),baseline=ref(oldstderr),entire_stream_byte_identical=True,headers_multiset_equal=collections.Counter(headers)==collections.Counter(re.findall(r'^warning(?:\[[^\]]+\])?: .+$',oldstderr.read_text(),re.M)),count=143,original_ABI_disposition=ref(OLD/'ABI-WARNING-DISPOSITION.json'),actual_tailjump=br,actual_tailjump_disassembly=disassemble('arch_rt_sigreturn_syscall_bridge'))

report=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_CURRENT111_DEFAULT_SELECTED_ARTIFACT',reviewer='/root/custody_release_review',independent=True,implementation_ownership=False,recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 tuple=dict(Rust=ref(B/'rust/mckernel_rust.o'),image=ref(B/'mckernel.img'),process=ref(B/'CMakeFiles/mckernel.img.dir/process.c.o'),kernel_C=ref(B/'CMakeFiles/mckernel.img.dir/syscall.c.o')),
 profile=ref(P/'PROFILE.SOURCE-ONLY.json'),source_review=ref(Q/'independent-source-review-1/REVIEW.json'),source_publication=ref(P/'ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json'),prior_default_acceptance=ref(prior/'DEFAULT-ARTIFACT-REVIEW.json'),
 actual_commands=4,command_returncodes=[0]*4,new_objects=3,retained_objects=8,rawlink_inputs=11,rawlink_command=actual['commands'][-1],link_d=ref(B/'CMakeFiles/mckernel.img.dir/link.d'),
 actual_Rust_exports=48,exports=exports,selected_C_functions=dict(F03=66,F06=25,total=91),actual_process_OBJECTs=67,three_exact_removed_C_callbacks=newnames,new_Rust_bridges=bridges,
 inherited_consumers=comparisons,thirteen_current_ABI_arguments=arguments,current_R64_inherited_targets=sum(len(r['current_targets']) for r in comparisons),anonymous_strings_positive=sum(r['kind']=='EXACT_SECTION_STRING' for row in comparisons for r in row['current_targets']),idle116=dict(current_targets=idle_rels,disassembly=idledis,exact_original_bytes=True),timer120=dict(all15_words=timer['all15_words'],nine_consumed=timer['nine_consumed_word_indices'],six_data_only=timer['six_data_only_word_indices'],current_positive_instruction_bindings=True),
 runqueue208=dict(Rust=table,final=f,bytes_hex=raw.hex(),fields=[dict(index=i,name=n,value=v) for i,(n,v) in enumerate(zip(fields,words))],HOST=ref(host/'OWNERSHIP.json'),old_C_origin=prior_table,new_C_definition_absent=True,readonly_min_alignment8=True,hidden_relocations=0,actual_schedule= schedule,old_schedule_size=oldschedule['size'],new_schedule_size=schedule['size'],current_full_final_targets=schrels,folded_descriptor_fields=folded,old_table_relocations=oldtable,actual_direct_table_relocations=0,other9_fields_preserved_data_only_for_schedule=[i for i in range(26) if i not in {r['index'] for r in folded}],unchanged_standalone_provider=provider,provider_full_current_targets=apr,provider_nonrelocated_instructions_equal=True,schedule_disassembly=schedule_dis),
 warnings=warnings,build_elapsed_seconds=actual['commands'][-1]['finished_at_epoch']-actual['commands'][0]['started_at_epoch'],build_CPU_seconds=sum(c['CPU_seconds'] for c in actual['commands']),maximum_child_RSS_KiB_worker_cumulative_ceiling=max(c['maximum_child_RSS_KiB'] for c in actual['commands']),
 original_scripted_OPEN_and_FAILURES_preserved=True,native_acceptance=False,whole_file_retirement=False,M14_M15='OPEN',new_native_apps=0,limitations=['Exact selected default artifact scope only; no matching native lifecycle execution.','17 runqueue fields are positively observed folded schedule inputs; nine others are preserved readonly data for this consumer, not an execution claim.','Original FP4096/1024FAIL, MM/usercopy/lifetime/Source38/native/whole-file holds remain unchanged.'],review_actions=dict(artifact_source_reads_and_offline_checks_only=True,compiler_or_workload_or_native_or_cleanup=0,only_assigned_review_directory_written=True))
with (D/'DEFAULT-ARTIFACT-REVIEW.json').open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(dict(decision=report['decision'],receipt=ref(D/'DEFAULT-ARTIFACT-REVIEW.json'))))
