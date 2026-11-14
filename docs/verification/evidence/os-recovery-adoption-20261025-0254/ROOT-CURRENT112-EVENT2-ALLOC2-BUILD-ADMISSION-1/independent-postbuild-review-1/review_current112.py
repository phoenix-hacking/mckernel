"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact offline CURRENT112 artifact review; no compiler, guest or replay.
"""
from pathlib import Path
import ast, collections, datetime, hashlib, json, re, struct, subprocess
D=Path(__file__).resolve().parent; P=D.parent; E=P.parent; B=P/'OUTPUT/work/output/build/kernel'
OLD=E/'ROOT-CURRENT111-COUNTER3-RUNQUEUE208-BUILD-ADMISSION-2'; OB=OLD/'OUTPUT/work/output/build/kernel'
R110=E/'ROOT-CURRENT110-HOST19-BUILD-ADMISSION-1'
def read(p): return json.loads(Path(p).read_bytes())
def ref(p):
    p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
prior=OLD/'independent-final-consumer-review-1'
assert ref(prior/'DEFAULT-ARTIFACT-REVIEW.json')['sha256']=='ffa9df9dbbde40440bc7b07b50876ea22fea2829d8987f26e2a11e04febcd545'
assert ref(prior/'INHERITED-CORE-POSTCHECK.json')['sha256']=='32db9081758fd79ddcf625590e0a5af16ef0058cc7d4ba916c998ef26ce89c26'
driver=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py'
assert ref(driver)['sha256']=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd'
ns=dict(Path=Path,struct=struct,hashlib=hashlib)
want={'_reuse_elf_function','_reuse_elf_owning_relocations','_reuse_elf_object_bytes'}
nodes=[n for n in ast.parse(driver.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='_ReuseElf' or isinstance(n,ast.FunctionDef) and n.name in want]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'retained exact readers','exec'),ns)
ns.update(fn=ns['_reuse_elf_function'],rels=ns['_reuse_elf_owning_relocations'],data=ns['_reuse_elf_object_bytes'])
cp=R110/'independent-final-consumer-review-1/review_consumers.py'
nodes=[n for n in ast.parse(cp.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Final' or isinstance(n,ast.FunctionDef) and n.name=='patched']
exec(compile(ast.Module(body=nodes,type_ignores=[]),'retained exact named/anonymous target readers','exec'),ns)
Elf=ns['_ReuseElf'];Final=ns['Final'];fn=ns['fn'];rels=ns['rels'];data=ns['data'];patched=ns['patched']
p=read(P/'PROFILE.SOURCE-ONLY.json');op=read(OLD/'PROFILE.SOURCE-ONLY.json');actual=read(P/'OUTPUT/work/evidence/worker-result.json')
assert ref(P/'PROFILE.SOURCE-ONLY.json')['sha256']=='a95aa8ee04f2f26b3f1275dfe5e5c471dbb793ee5d15c15533949f976dfcc3fe'
assert len(actual['commands'])==4
for a,c in zip(actual['commands'],p['exact_commands']):
    assert a['argv']==c['argv'] and a['cwd']==c['cwd'] and a['returncode']==0
    r=a['output'];f=P/'OUTPUT/work'/Path(r['path']).relative_to('/work');v=ref(f)
    assert (v['bytes'],v['sha256'])==(r['bytes'],r['sha256'])
objects=[]
for row in p['inputs']['objects']:
    f=B/row['link_token'] if row['replace'] else Path(row['source']['path'])
    if not row['replace']: assert ref(f)==row['source']
    objects.append((row,Elf(f)))
assert len(objects)==11 and sum(not row['replace'] for row,elf in objects)==8
tokens=[a for a in actual['commands'][-1]['argv'] if a.endswith('.o')]
assert tokens==[row['link_token'] for row,elf in objects]
assert actual['commands'][-1]['argv']==op['exact_commands'][-1]['argv']
dep=(B/'CMakeFiles/mckernel.img.dir/link.d').read_text()
for token in tokens: assert token in dep
new=Elf(B/'rust/mckernel_rust.o');old=Elf(OB/'rust/mckernel_rust.o');image=Final(B/'mckernel.img');oldimage=Final(OB/'mckernel.img')
def string_section(elf):
    sec=next(s for s in elf.sections if s['name']=='.lrodata.str1.1');assert sec['flags']&0x32==0x32 and not sec['flags']&5
    return elf.raw[sec['offset']:sec['offset']+sec['size']]
oldstrings=string_section(old);newstrings=string_section(new)
origin_literal=b'/src/arch/x86_64/kernel/syscall.c\0';origin_insert=9566
assert len(origin_literal)==34 and oldstrings[:origin_insert]+origin_literal+oldstrings[origin_insert:]==newstrings
def own(elf,name):
    rows=[s for s in elf.symbols if s['name']==name and s['shndx']!=0];assert len(rows)==1,(name,len(rows));return rows[0]
def allocated(elf,kind):return {s['name']:s for s in elf.symbols if s['type']==kind and s['shndx']!=0 and elf.sections[s['shndx']]['flags']&2}
def disassemble(name):
    s=image.sym(name)
    return subprocess.check_output(['objdump','--no-show-raw-insn','-d','--start-address='+str(s['value']),'--stop-address='+str(s['value']+s['size']),str(image.path)],text=True)
def compare(name,patch=patched):
    a,ar=patch(old,name,oldimage);b,br=patch(new,name,image)
    assert a['size']==b['size'],(name,a['size'],b['size'])
    def shape(rs,before):
        out=[]
        for r in rs:
            addend=r['addend']
            if before and r['kind']=='EXACT_SECTION_STRING' and addend>=origin_insert:addend+=34
            out.append((r['offset'],r.get('type'),addend,r.get('target'),r['kind'],r.get('literal_hex')))
        return out
    assert shape(ar,True)==shape(br,False),(name,shape(ar,True),shape(br,False))
    aa=bytearray(data(old,a));bb=bytearray(data(new,b))
    for r in br:aa[r['offset']:r['offset']+8]=bytes(8);bb[r['offset']:r['offset']+8]=bytes(8)
    assert aa==bb,name
    return dict(name=name,current_final=image.sym(name),current_positive_targets=br,nonrelocated_bytes_equal=True)
baseline=read(prior/'DEFAULT-ARTIFACT-REVIEW.json');core=read(prior/'INHERITED-CORE-POSTCHECK.json')
newnames=['perf_event_set_period_bridge','perf_event_update_bridge','arch_rt_sigreturn_alloc_bridge','arch_rt_sigreturn_free_bridge']
names=[r['name'] for r in baseline['exports']]+newnames;assert len(set(names))==52
exports=[]
for name in names:
    s=own(new,name);f=image.sym(name);assert s['bind']==f['bind']==1 and s['type']==f['type']==2 and s['size']==f['size']
    assert not [v for row,elf in objects if row['link_token']!='rust/mckernel_rust.o' for v in elf.symbols if v['name']==name and v['shndx']!=0]
    exports.append(dict(name=name,Rust=s,final=f))
bytoken={row['link_token']:elf for row,elf in objects};kc=bytoken['CMakeFiles/mckernel.img.dir/syscall.c.o'];ac=bytoken['CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'];pc=bytoken['CMakeFiles/mckernel.img.dir/process.c.o']
oldkc=Elf(OB/'CMakeFiles/mckernel.img.dir/syscall.c.o');oldac=Elf(Path(next(r['source']['path'] for r in op['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o')))
assert set(allocated(oldkc,2))-set(allocated(kc,2))==set(newnames[:2]) and not set(allocated(kc,2))-set(allocated(oldkc,2))
assert set(allocated(oldac,2))-set(allocated(ac,2))==set(newnames[2:]) and not set(allocated(ac,2))-set(allocated(oldac,2))
assert len(allocated(kc,2))==64 and len(allocated(ac,2))==23 and len(allocated(pc,1))==67
undef=lambda elf:{s['name'] for s in elf.symbols if s['shndx']==0 and s['name']}
undefined_delta=dict(removed=sorted(undef(old)-undef(new)),added=sorted(undef(new)-undef(old)))
assert not undefined_delta['removed'] and not undefined_delta['added'],undefined_delta
# Exact native cfg selects native_signal::sigreturn; generic alloc/free callbacks
# are cfg(not native_linux_irq_work_v6_12), so no old Rust imports disappear.
policy_source=Path(next(r['postimage']['path'] for r in p['cohort_source_bindings'] if r['relative']=='kernel/rust/syscall_policy.rs')).read_text()
sigreturn_source=policy_source.split('pub unsafe extern "C" fn sys_rt_sigreturn(',1)[1].split('\n#[no_mangle]',1)[0]
assert '#[cfg(native_linux_irq_work_v6_12)]' in sigreturn_source and 'crate::native_signal::sigreturn(' in sigreturn_source
assert '#[cfg(not(native_linux_irq_work_v6_12))]' in sigreturn_source and 'Some(arch_rt_sigreturn_alloc_bridge)' in sigreturn_source and 'Some(arch_rt_sigreturn_free_bridge)' in sigreturn_source
comparisons=[compare(row['consumer']) for row in baseline['inherited_consumers']]
arguments=[]
for row in baseline['thirteen_current_ABI_arguments']:
    dis=disassemble(row['consumer']);value=row['signed_CInt'];reg=row['ABI_argument'];pattern=(r'push\s+\$0x%x\b'%value) if reg=='stack eighth' else r'mov\s+\$0x%x,%%%s\b'%(value,reg)
    found=[s.strip() for s in dis.splitlines() if re.search(pattern,s)];assert len(found)==1
    arguments.append(dict(data=row['data'],consumer=row['consumer'],signed_CInt=value,ABI_argument=reg,current_instruction=found[0]))
for name in ['process_idle_entry','set_timer','sched_schedule_prepare_body_result','arch_rt_sigreturn_syscall_bridge']:
    comparisons.append(compare(name))
tables=[]
for name,size in [('process_idle_offsets',80),('process_idle_values',36),('process_timer_runtime_offsets',120),('process_sched_runqueue_offsets',208)]:
    a=own(old,name);b=own(new,name);f=image.sym(name);sec=new.sections[b['shndx']]
    assert b['size']==size and data(old,a)==data(new,b)==image.bytes(f) and not rels(new,b) and not sec['flags']&5 and f['value']%(8 if size!=36 else 4)==0
    assert not [s for row,elf in objects if row['link_token']!='rust/mckernel_rust.o' for s in elf.symbols if s['name']==name and s['shndx']!=0]
    tables.append(dict(name=name,Rust=b,final=f,bytes_hex=data(new,b).hex(),readonly_exact=True,hidden_relocations=0))
# Preserve exact anonymous scheduler-counter resolution, rather than accepting unknown targets.
t=ast.parse((prior/'review_current111.py').read_text());node=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='patched_schedule')
exec(compile(ast.Module(body=[node],type_ignores=[]),'retained exact scheduler target resolver','exec'),globals())
def schedule_patch(elf,name,final):assert name=='schedule';return patched_schedule(elf,final)
schedule=compare('schedule',schedule_patch);dis=disassemble('schedule')
for field in baseline['runqueue208']['folded_descriptor_fields']:
    for instruction in field['instructions']:assert instruction.split(':',1)[1].strip() in dis
idle=disassemble('process_idle_entry')
for name,reg in [('process_idle_offsets','rdx'),('process_idle_values','rcx'),('process_idle_callbacks','r8')]:assert re.search(r'movabs\s+\$0x%x,%%%s\b'%(image.sym(name)['value'],reg),idle)
# New event providers must be genuine exact Rust aliases of the existing provider bodies.
event=[]
for name,provider in [('perf_event_set_period_bridge','ihk_mc_event_set_period'),('perf_event_update_bridge','ihk_mc_event_update')]:
    a=own(new,name);b=own(new,provider);fa=image.sym(name);fb=image.sym(provider)
    assert (a['shndx'],a['value'],a['size'])==(b['shndx'],b['value'],b['size']) and (fa['value'],fa['size'])==(fb['value'],fb['size'])
    patched(new,name,image);event.append(dict(name=name,provider=provider,exact_Rust_alias=True,disassembly=disassemble(name)))
origin=[]
for name,line,reg in [('arch_rt_sigreturn_alloc_bridge',385,'ecx'),('arch_rt_sigreturn_free_bridge',391,'edx')]:
    s,rr=patched(new,name,image);dis=disassemble(name)
    assert re.search(r'mov\s+\$0x%x,%%%s\b'%(line,reg),dis)
    literals=[r for r in rr if r['kind']=='EXACT_SECTION_STRING' and bytes.fromhex(r['literal_hex'])==origin_literal]
    if name=='arch_rt_sigreturn_alloc_bridge':
        assert s['size']==210 and [r['offset'] for r in literals]==[8,172]
        assert [(r['offset'],r['target']) for r in rr if r['kind']=='NAMED']==[(18,'_kmalloc'),(63,'locals'),(88,'num_processors'),(123,'clv'),(182,'kprintf')]
        assert 'movabs $0x%x,%%rdx'%int(literals[0]['actual_final_address'],16) in dis
        assert 'mov    $0x181,%edx' in dis
    else:
        assert s['size']==32 and [r['offset'] for r in literals]==[6]
        assert [(r['offset'],r['target']) for r in rr if r['kind']=='NAMED']==[(16,'_kfree')]
        assert 'movabs $0x%x,%%rsi'%int(literals[0]['actual_final_address'],16) in dis
        assert 'jmp    *%rax' in dis
    origin.append(dict(name=name,Rust=s,final=image.sym(name),tracking_line=line,current_final_targets=rr,exact_filename_bytes=34,disassembly=dis))
stderr=P/'OUTPUT/work/evidence/00.stderr';oldstderr=OLD/'OUTPUT/work/evidence/00.stderr';assert stderr.read_bytes()==oldstderr.read_bytes()
headers=re.findall(r'^warning(?:\[[^\]]+\])?: .+$',stderr.read_text(),re.M);assert headers[-1]=='warning: 143 warnings emitted'
bridge,br=patched(new,'arch_rt_sigreturn_syscall_bridge',image);assert bridge['size']==17 and len(br)==1 and br[0]['target']=='syscall' and br[0]['addend']==0
assert (P/'OUTPUT/work/evidence/02.stderr').read_bytes()==b'' and (P/'OUTPUT/work/evidence/03.stderr').read_bytes()==(OLD/'OUTPUT/work/evidence/03.stderr').read_bytes()
newwarn=P/'OUTPUT/work/evidence/01.stderr';oldwarn=OLD/'OUTPUT/work/evidence/02.stderr';assert re.findall(r'warning: (.+)',newwarn.read_text())==re.findall(r'warning: (.+)',oldwarn.read_text())
def source(root,name):return Path(next(r['postimage']['path'] for r in read(root/'PROFILE.SOURCE-ONLY.json')['cohort_source_bindings'] if r['relative']==name))
declarations=[]
for name in ['syscall_itimer_offsets','sched_syscall_offsets','syscall_cputime_offsets','wait_scan_kernel_offsets']:
    pattern=r'(?m)^static const struct [^\n]*\b'+name+r'\b[^=]*=\s*\{.*?^\};';a=re.findall(pattern,source(OLD,'kernel/syscall.c').read_text(),re.S);b=re.findall(pattern,source(P,'kernel/syscall.c').read_text(),re.S);assert len(a)==len(b)==1 and a==b;declarations.append(dict(name=name,initializer=a[0]))
for removed in core['original_two_panic_imports_absent']:assert not [s for s in new.symbols if s['name']==removed]
header=struct.unpack_from('<16sHHIQQQIHHHHHH',image.raw);assert header[4]==image.sym('arch_start')['value']
for name in ['arch_start','main','monitor_init','init_host_ikc2linux','init_host_ikc2mckernel','prepare_process_ranges_args_envs','mcexec_v10_trace_enter_user']:assert image.sym(name)['shndx']!=0
report=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_CURRENT112_SELECTED_DEFAULT_ARTIFACT_PENDING_LOGGER_COMPLEMENT',independent=True,reviewer='/root/custody_release_review',tuple=dict(Rust=ref(B/'rust/mckernel_rust.o'),image=ref(B/'mckernel.img'),kernel_C=ref(B/'CMakeFiles/mckernel.img.dir/syscall.c.o'),arch_C=ref(B/'CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o')),profile=ref(P/'PROFILE.SOURCE-ONLY.json'),previous_acceptance=ref(prior/'INDEPENDENT-ACCEPTANCE.json'),rawlink_inputs=11,retained_inputs=8,new_objects=3,actual_Rust_exports=52,exports=exports,actual_C_counts=dict(F03=64,F06=23,total=87,process_OBJECTs=67),exact_C_removals=newnames,undefined_delta=undefined_delta,inherited_consumer_comparisons=comparisons,thirteen_folded_arguments=arguments,inherited_readonly_tables=tables,schedule=schedule,runqueue17_fields_revalidated=baseline['runqueue208']['folded_descriptor_fields'],timer15_words=baseline['timer120'],event_providers=event,new_filename_origins=origin,Rust_warnings=dict(actual=ref(stderr),accepted111=ref(oldstderr),entire_stream_byte_identical=True,count=143,actual_syscall_tailjmp=br,original_ABI_disposition=ref(R110/'ABI-WARNING-DISPOSITION.json')),kernel_C_warning_initializers_unchanged=declarations,arch_C_stderr_empty=True,link_stderr_unchanged=True,required_ELF_entry_and_symbols=True,original_panic_imports_absent=True,elapsed_seconds=actual['commands'][-1]['finished_at_epoch']-actual['commands'][0]['started_at_epoch'],CPU_seconds=sum(r['CPU_seconds'] for r in actual['commands']),maximum_child_RSS_KiB_worker_cumulative=max(r['maximum_child_RSS_KiB'] for r in actual['commands']),native_acceptance=False,wholefile_retirement=False,original_failures_OPEN_preserved=True)
with (D/'DEFAULT-ARTIFACT-REVIEW.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(ref(D/'DEFAULT-ARTIFACT-REVIEW.json')))
