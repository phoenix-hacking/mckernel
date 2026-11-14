"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact offline CURRENT112 logger/metadata complement; no original gates changed.
"""
from pathlib import Path
import ast, hashlib, json, re, struct
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent;B=P/'OUTPUT/work/output/build/kernel'
OLD=E/'ROOT-CURRENT110-HOST19-BUILD-ADMISSION-1';OB=OLD/'OUTPUT/work/output/build/kernel'
def ref(f):
    f=Path(f);b=f.read_bytes();return dict(path=str(f),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(f):return json.loads(Path(f).read_bytes())
ns=dict(Path=Path,struct=struct)
t=ast.parse((OLD/'independent-final-consumer-review-1/review_consumers.py').read_text())
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.ClassDef) and n.name=='Final'],type_ignores=[]),'retained final reader','exec'),ns)
dr=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py'
want={'_reuse_elf_function','_reuse_elf_owning_relocations','_reuse_elf_object_bytes'}
exec(compile(ast.Module(body=[n for n in ast.parse(dr.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='_ReuseElf' or isinstance(n,ast.FunctionDef) and n.name in want],type_ignores=[]),'retained REL readers','exec'),ns)
Elf=ns['_ReuseElf'];Final=ns['Final'];data=ns['_reuse_elf_object_bytes'];rels=ns['_reuse_elf_owning_relocations'];fn=ns['_reuse_elf_function']
new=Elf(B/'rust/mckernel_rust.o');old=Elf(OB/'rust/mckernel_rust.o');img=Final(B/'mckernel.img')
profile=read(P/'PROFILE.SOURCE-ONLY.json'); pc=Elf(Path(next(r['source']['path'] for r in profile['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o')));opc=Elf(OB/'CMakeFiles/mckernel.img.dir/process.c.o')
def own(elf,name):
    r=[s for s in elf.symbols if s['name']==name and s['shndx']!=0];assert len(r)==1;return r[0]
q=E/'current110-host19-production-preparation-source-1/resource-and-qualifier-preparation-1/next-provider-path-correction-source-1/actual-suffix-qualification-1'
proof=read(q/'fresh-compiled-rust-ownership-proof.json');records=[];mapsections={}
for label,row in proof['logger_proof'].items():
    name=row['record']['symbol']['name'];s=own(new,name);before=own(old,name)
    assert (s['bind'],s['type'],s['size'])==(0,1,32)
    assert data(new,s)==data(old,before)==bytes.fromhex(row['record']['initial_hex'])
    rr=rels(new,s);assert len(rr)==2 and [r['offset'] for r in rr]==[0,8]
    patched=bytearray(data(new,s));f=img.sym(name);assert f['bind']==0 and f['type']==1 and f['size']==32
    final=img.bytes(f);strs=[]
    for r,expected in zip(rr,[row['record']['filename'],row['record']['function']]):
        assert r['type']==1 and not r['target']['name'] and r['target']['type']==3
        sec=new.sections[r['target']['shndx']];assert sec['name']=='.lrodata.str1.1' and not sec['flags']&5
        start=sec['offset']+r['target']['value']+r['addend'];literal=new.raw[start:new.raw.index(b'\0',start)+1]
        assert literal==expected.encode()+b'\0'
        address=struct.unpack_from('<Q',final,r['offset'])[0];actual,fs=img.at(address,len(literal),True);assert actual==literal
        struct.pack_into('<Q',patched,r['offset'],address);strs.append(dict(input_offset=r['offset'],literal=expected,current_final_address=hex(address)))
    assert bytes(patched)==final and struct.unpack_from('<Q',final,24)[0]==row['record']['line']
    mapsections[s['shndx']]=f
    records.append(dict(label=label,Rust=s,final=f,strings=strs,line=row['record']['line'],initial_nonpointer_bytes=final[16:].hex()))
cb=fn(new,'arch_process_vm_rw_log_bridge');oldcb=fn(old,cb['name']);assert cb['size']==oldcb['size']==337
raw=bytearray(data(new,cb));before=bytearray(data(old,oldcb));actual=img.bytes(img.sym(cb['name']));bindings=[];other_targets=[]
for r in rels(new,cb):
    off=r['offset'];assert r['type']==1;value=struct.unpack_from('<Q',actual,off)[0]
    if r['target']['name']:
        assert value==(img.sym(r['target']['name'])['value']+r['addend'])&((1<<64)-1)
    elif r['target']['shndx'] in mapsections:
        assert r['addend']==24 and r['target']['type']==3
        f=mapsections[r['target']['shndx']];assert value==f['value']+24
        bindings.append(dict(offset=off,record=f['name'],line_flags_address=hex(value)))
    else:
        sec=new.sections[r['target']['shndx']]
        if sec['name']=='.lrodata.str1.1':
            assert not sec['flags']&5;start=sec['offset']+r['addend'];literal=new.raw[start:new.raw.index(b'\0',start)+1]
            found,_=img.at(value,len(literal),True);assert found==literal
            other_targets.append(dict(offset=off,kind='EXACT_STRING',address=hex(value),literal=literal[:-1].decode()))
        else:
            assert sec['name']=='.lrodata.arch_process_vm_rw_log_bridge' and sec['size']==32 and sec['align']==8 and sec['flags']&7==2 and r['addend']==0
            relocation_sections=[s for s in new.sections if s['type']==4 and s['info']==sec['index']]
            assert len(relocation_sections)==1 and relocation_sections[0]['size']==96
            rs=relocation_sections[0];expected=[]
            for offset,addend in zip(range(0,32,8),[26,281,75,162]):
                o,info,a=struct.unpack_from('<QQq',new.raw,rs['offset']+(offset//8)*24);target=new.symbols[info>>32]
                assert o==offset and info&0xffffffff==1 and a==addend and target['type']==3 and target['shndx']==cb['shndx'] and target['value']==0
                expected.append(img.sym(cb['name'])['value']+a)
            found,_=img.at(value,32,True);assert found==struct.pack('<4Q',*expected)
            other_targets.append(dict(offset=off,kind='EXACT_FOUR_ENTRY_LOGGER_JUMP_TABLE',address=hex(value),exact_current_callback_offsets=[26,281,75,162],final_values=expected))
    struct.pack_into('<Q',raw,off,value);before[off:off+8]=bytes(8)
assert bytes(raw)==actual and len(bindings)==4
clean=bytearray(data(new,cb))
for r in rels(new,cb):clean[r['offset']:r['offset']+8]=bytes(8)
assert clean==before
metadata=[]
for s in pc.symbols:
    if s['type']!=1 or s['shndx']==0 or not pc.sections[s['shndx']]['flags']&2:continue
    before=own(opc,s['name']);assert (s['bind'],s['type'],s['size'])==(before['bind'],before['type'],before['size'])
    assert data(pc,s)==data(opc,before)
    shape=lambda elf,sym:[(r['offset'],r['type'],r['addend'],r['target']['name']) for r in rels(elf,sym)]
    assert shape(pc,s)==shape(opc,before)
    metadata.append(dict(name=s['name'],bytes=s['size'],input_bytes_types_bindings_and_relocations_equal=True))
assert len(metadata)==67
for name in ['arch_start','main','monitor_init','init_host_ikc2linux','init_host_ikc2mckernel','prepare_process_ranges_args_envs','mcexec_v10_trace_enter_user']:assert img.sym(name)['shndx']!=0
header=struct.unpack_from('<16sHHIQQQIHHHHHH',img.raw);assert header[4]==img.sym('arch_start')['value']
assert (P/'OUTPUT/work/evidence/03.stderr').read_bytes()==(OLD/'OUTPUT/work/evidence/04.stderr').read_bytes()
assert (P/'OUTPUT/work/evidence/02.stderr').read_bytes()==b''
oldwarn=OLD/'OUTPUT/work/evidence/02.stderr';newwarn=P/'OUTPUT/work/evidence/01.stderr'
assert re.findall(r'warning: (.+)',newwarn.read_text())==re.findall(r'warning: (.+)',oldwarn.read_text())
def kernel_source(root):
    profile=read(root/'PROFILE.SOURCE-ONLY.json')
    return Path(next(r['postimage']['path'] for r in profile['cohort_source_bindings'] if r['relative']=='kernel/syscall.c'))
osrc=kernel_source(OLD);nsrc=kernel_source(P);declarations=[]
for name in ['syscall_itimer_offsets','sched_syscall_offsets','syscall_cputime_offsets','wait_scan_kernel_offsets']:
    pattern=r'(?m)^static const struct [^\n]*\b'+name+r'\b[^=]*=\s*\{.*?^\};'
    before=re.findall(pattern,osrc.read_text(),re.S);after=re.findall(pattern,nsrc.read_text(),re.S)
    assert len(before)==len(after)==1 and before==after
    declarations.append(dict(name=name,unchanged_initializer_sha256=hashlib.sha256(after[0].encode()).hexdigest(),initializer=after[0]))
cwarning=dict(actual=ref(newwarn),baseline=ref(oldwarn),exact_warning_messages_equal=True,changed_presentation='Rendered source excerpts differ; source-location shifts from exact event2 insertion. Exact source initializer texts are unchanged and authenticated below. No new warning or suppression.',source_old=ref(osrc),source_new=ref(nsrc),four_unchanged_declarations=declarations)
for removed in proof['removed_original_panic_imports']:assert not [s for s in new.symbols if s['name']==removed]
report=dict(scope=__doc__.splitlines()[0],reviewer='/root/custody_release_review',independent=True,decision='PASS_EXACT_CURRENT112_INHERITED_LOCAL_LOGGERS_METADATA_PANIC_AND_ELF_GATES',default_artifact_review=ref(D/'DEFAULT-ARTIFACT-REVIEW.json'),prior_logger_proof=ref(q/'fresh-compiled-rust-ownership-proof.json'),current_Rust=ref(B/'rust/mckernel_rust.o'),current_image=ref(B/'mckernel.img'),four_LOCAL_debug_records=records,logger_current_337B_full_final_code_reproduced=True,logger_four_line_flags_bindings=bindings,other_positive_current_logger_targets=other_targets,all67_C_process_metadata_equal=metadata,original_two_panic_imports_absent=proof['removed_original_panic_imports'],all_undefined_names_exactly_equal_CURRENT111='Verified by DEFAULT-ARTIFACT-REVIEW; native cfg generic sigreturn route inactive',ELF_entry_arch_start_and_required_symbols=True,arch_C_stderr_empty_link_stderr_byte_identical_to_CURRENT110=True,kernel_C_exact_warning_disposition=cwarning,native_acceptance=False,whole_file_retirement=False,original_scripted_failures_OPEN_and_Source38_holds_preserved=True,compiler_workload_actions=0)
with (D/'INHERITED-CORE-POSTCHECK.json').open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(ref(D/'INHERITED-CORE-POSTCHECK.json')))
