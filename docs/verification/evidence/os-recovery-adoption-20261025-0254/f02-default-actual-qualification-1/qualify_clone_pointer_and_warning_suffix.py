"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Targeted exact clone-thread source/REL-object/final-pointer and warning qualification.
"""
import ast,hashlib,json,re,struct
from collections import Counter
from pathlib import Path
D=Path(__file__).resolve().parent;E=D.parent;B=E/'ROOT-F02-DATA-DEFAULT-BUILD-ADMISSION-1/OUTPUT/work/output/build';A=E/'ROOT-F02-DATA-DEFAULT-BUILD-ADMISSION-1/OUTPUT/work/evidence';P=json.loads((E/'ROOT-F02-DATA-DEFAULT-BUILD-ADMISSION-1/PROFILE.SOURCE-ONLY.json').read_text());SRC=Path(P['inputs']['source6153'])
DRIVER=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py';source=DRIVER.read_bytes();assert hashlib.sha256(source).hexdigest()=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd'
names={'_reuse_elf_function','_reuse_elf_owning_relocations','_reuse_elf_object_bytes'}
nodes=[n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='_ReuseElf' or isinstance(n,ast.FunctionDef) and n.name in names];ns=dict(Path=Path,struct=struct);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(DRIVER)+':UNCHANGED_REL_POINTER_HELPERS','exec'),ns)
Elf=ns['_ReuseElf'];rust=Elf(B/'kernel/rust/mckernel_rust.o');process=Elf(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o')
# Strict EXEC-only byte reader, separate from unchanged ET_REL validator.
raw=(B/'kernel/mckernel.img').read_bytes();eh=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);assert eh[0][:7]==b'\x7fELF\x02\x01\x01' and eh[1:3]==(2,62) and eh[11]==64
sections=[dict(zip(['name_off','type','flags','addr','offset','size','link','info','align','entsize'],struct.unpack_from('<IIQQQQIIQQ',raw,eh[6]+i*64))) for i in range(eh[12])]
def payload(s):return raw[s['offset']:s['offset']+s['size']]
def string(s,n):return s[n:s.index(b'\0',n)].decode()
section_names=payload(sections[eh[13]])
for i,s in enumerate(sections):s.update(index=i,name=string(section_names,s['name_off']))
tables=[s for s in sections if s['type']==2];assert len(tables)==1 and tables[0]['entsize']==24;table=tables[0];strings=payload(sections[table['link']]);symbols=[]
for i in range(table['size']//24):
 no,info,other,idx,value,size=struct.unpack_from('<IBBHQQ',raw,table['offset']+i*24);symbols.append(dict(index=i,name=string(strings,no),bind=info>>4,type=info&15,other=other,shndx=idx,value=value,size=size))
def final(name):
 rows=[s for s in symbols if s['name']==name and s['shndx']!=0];assert len(rows)==1,(name,len(rows));return rows[0]
def data(sym):
 sec=sections[sym['shndx']];start=sym['value']-sec['addr'];assert 0<=start and start+sym['size']<=sec['size'];return bytes(sym['size']) if sec['type']==8 else payload(sec)[start:start+sym['size']]
def ref(p):
 x=Path(p);b=x.read_bytes();return dict(path=str(x),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
clone=ns['_reuse_elf_function'](rust,'clone_thread');rels=ns['_reuse_elf_owning_relocations'](rust,clone);code=bytearray(ns['_reuse_elf_object_bytes'](rust,clone));assert len(code)==27
assert len(rels)==2 and {r['target']['name'] for r in rels}=={'process_clone_thread_body_result','process_clone_config'}
resolved=[]
for r in rels:
 assert r['type']==1 and r['addend']==0;target=final(r['target']['name']);assert target['bind']==1
 struct.pack_into('<Q',code,r['offset'],target['value']+r['addend']);resolved.append(dict(relocation=r,final_target=target))
fclone=final('clone_thread');assert fclone['bind']==1 and fclone['type']==2 and fclone['size']==27 and data(fclone)==bytes(code)
assert not [s for s in process.symbols if s['name']=='clone_thread' and s['shndx']!=0]
config=process.sym('process_clone_config');assert config['type']==1 and config['bind']==1 and config['shndx']!=0
for row in P['inputs']['objects']:
 if not row['replace']:
  elf=Elf(Path(row['source']['path']));assert not [s for s in elf.symbols if s['name'] in ['clone_thread','resource_set_list','resource_set_lock','runq_reservation_lock'] and s['shndx']!=0]
storage={}
for name,size,align in [('resource_set_list',16,16),('resource_set_lock',64,64),('runq_reservation_lock',4,4)]:
 s=final(name);assert s['type']==1 and s['bind']==1 and s['size']==size and s['value']%align==0 and data(s)==bytes(size);storage[name]=dict(symbol=s,section=sections[s['shndx']],initial_hex=data(s).hex())
sourcefile=Path(next(r['postimage']['path'] for r in P['inputs']['postimages'] if r['relative']=='kernel/rust/process_helpers.rs'));lines=sourcefile.read_text().splitlines();start=next(i for i,l in enumerate(lines) if l.startswith('pub unsafe extern "C" fn clone_thread('));assert lines[start-1]=='#[no_mangle]';snippet='\n'.join(lines[start-1:start+16]);assert 'process_clone_thread_body_result(' in snippet and 'core::ptr::addr_of!(process_clone_config)' in snippet and 'const _: unsafe extern "C" fn(*mut Thread, CULong, CULong, CInt) -> *mut Thread = clone_thread;' in snippet
keep={}
for marker in ['x86_interrupt_log_debug','REPLACE_TID_DEBUG','RELEASE_TID_DEBUG','RELEASE_FP_REGS_DEBUG']:
 rs=[s for s in rust.symbols if marker in s['name'] and s['type']==1 and s['shndx']!=0];matches=[]
 for s in rs:
  f=final(s['name']);matches.append(dict(input_symbol=s,input_section_flags=rust.sections[s['shndx']]['flags'],final_symbol=f,final_section_flags=sections[f['shndx']]['flags'],input_GNU_RETAIN=bool(rust.sections[s['shndx']]['flags']&0x200000),final_GNU_RETAIN=bool(sections[f['shndx']]['flags']&0x200000)))
 keep[marker]=matches
newwarn=(A/'00.stderr').read_text();headers=re.findall(r'^warning(?:\[[^\]]+\])?: .+$',newwarn,re.M)
assert newwarn.rstrip().endswith('warning: 137 warnings emitted') and not (A/'01.stderr').read_bytes()
ld=(A/'02.stderr').read_text();assert ld=='/usr/bin/ld: warning: mckernel.img has a LOAD segment with RWX permissions\n'
oldwarning=E/'ROOT-CURRENT290-BUILD-ONLY-ADMISSION-3/OUTPUT/work/evidence/00.stderr'
oldtext=oldwarning.read_text();oh=re.findall(r'^warning(?:\[[^\]]+\])?: .+$',oldtext,re.M)
added=Counter(headers)-Counter(oh);removed=Counter(oh)-Counter(headers)
assert added==Counter({'warning: `process_spin_lock_bridge_c` redeclares `process_spin_lock_bridge` with a different signature':1,'warning: `process_spin_unlock_bridge_c` redeclares `process_spin_unlock_bridge` with a different signature':1,'warning: 137 warnings emitted':1})
assert removed==Counter({'warning: 135 warnings emitted':1})
comparison=dict(original=ref(oldwarning),warning_headers_equal=oh==headers,new_only=dict(added),old_only=dict(removed),new_redeclaration_ABI='usize versus u64 parameters on current x86_64; exact warning bodies retained in actual compiler stderr; warning debt remains open')

report=dict(scope=__doc__.splitlines()[0],status='PASS_CURRENT_DEFAULT_RUST_DEFINED_CLONE_SOURCE_OBJECT_FINAL_POINTER_PROOF_NOT_ORIGINAL_WITNESS_WAIVER',source=ref(sourcefile),source_lines=[start,start+15],source_snippet=snippet,new_Rust_object=ref(B/'kernel/rust/mckernel_rust.o'),new_process_object=ref(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o'),new_image=ref(B/'kernel/mckernel.img'),clone_thread_object_symbol=clone,clone_thread_final_symbol=fclone,resolved_R64_final_pointers=resolved,final_function_exact_object_code_with_only_two_R64_patches=True,no_C_or_nine_input_duplicate_clone_or_storage_definitions=True,C_config_object=config,three_final_storage_objects=storage,source38_target_retention_in_actual_current_default_link=keep,Source38_HOST_ld234_partial_debt='OPEN_DIFFERENT_SOURCE37_COHERENT_GRAPH_NOT_CLEARED_BY_CURRENT290_FINAL_LINK',original_generic_clone_U_witness_failure_preserved=True,independent_disposition_of_obsolete_U_witness_required=True,Rust_warning_count=137,Rust_warning_headers=headers,Rust_warning_comparison=comparison,process_compiler_stderr_empty=True,ld_RWX_warning_preserved=ld,default_native_retirement_acceptance=False)
(D/'CLONE-FINAL-POINTER-AND-WARNINGS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],clone_thread_final_address=hex(fclone['value']),resolved_final_pointers=len(resolved),Rust_warnings=137,warning_comparison=comparison,Source38_debt='OPEN')))
