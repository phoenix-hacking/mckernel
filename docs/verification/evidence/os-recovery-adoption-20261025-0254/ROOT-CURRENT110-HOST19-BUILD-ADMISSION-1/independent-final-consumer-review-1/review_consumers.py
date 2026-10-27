"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Offline, exact CURRENT109/110 consumer review; no original qualifier is modified.
"""
from pathlib import Path
import ast, hashlib, json, re, struct, subprocess

D = Path(__file__).resolve().parent
E = D.parent.parent
P = D.parent
Q = E / 'current110-host19-production-preparation-source-1/resource-and-qualifier-preparation-1'
G = Q / 'next-provider-path-correction-source-1/actual-suffix-qualification-1'
B = P / 'OUTPUT/work/output/build/kernel'
def ref(path):
    path = Path(path); raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def read(path): return json.loads(Path(path).read_bytes())
def auth(row):
    assert ref(row['path']) == row
    return read(row['path'])

profile = read(P / 'PROFILE.SOURCE-ONLY.json')
assert ref(P / 'PROFILE.SOURCE-ONLY.json')['sha256'] == '64242ef204a7696369462487e5ca17e63f24d1a9d4c9957e43778b643a2fa288'
X = read(Q / 'ACCEPTANCE-INPUTS.SOURCE-ONLY.json')
driver = E / 'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py'
assert ref(driver)['sha256'] == '9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd'
want = {'_reuse_elf_function','_reuse_elf_owning_relocations','_reuse_elf_object_bytes'}
nodes = [n for n in ast.parse(driver.read_text()).body if isinstance(n,ast.ClassDef) and n.name == '_ReuseElf' or isinstance(n,ast.FunctionDef) and n.name in want]
ns = dict(Path=Path, struct=struct)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(driver)+':READ_ONLY_SELECTED_READERS','exec'),ns)
Elf=ns['_ReuseElf']; fn=ns['_reuse_elf_function']; rels=ns['_reuse_elf_owning_relocations']; data=ns['_reuse_elf_object_bytes']

class Final:
    def __init__(self,path):
        self.path=Path(path); self.raw=self.path.read_bytes()
        h=struct.unpack_from('<16sHHIQQQIHHHHHH',self.raw)
        assert h[0][:7]==b'\x7fELF\x02\x01\x01' and h[1:3]==(2,62) and h[11]==64
        self.sections=[dict(zip(['name_off','type','flags','addr','offset','size','link','info','align','entsize'],struct.unpack_from('<IIQQQQIIQQ',self.raw,h[6]+i*64))) for i in range(h[12])]
        strings=self.payload(self.sections[h[13]])
        for i,s in enumerate(self.sections): s.update(index=i,name=self.string(strings,s['name_off']))
        tables=[s for s in self.sections if s['type']==2]; assert len(tables)==1 and tables[0]['entsize']==24
        table=tables[0]; strings=self.payload(self.sections[table['link']]); self.symbols=[]
        for i in range(table['size']//24):
            n,info,other,idx,value,size=struct.unpack_from('<IBBHQQ',self.raw,table['offset']+i*24)
            self.symbols.append(dict(name=self.string(strings,n),bind=info>>4,type=info&15,other=other,shndx=idx,value=value,size=size))
    def string(self,raw,n): return raw[n:raw.index(b'\0',n)].decode()
    def payload(self,s): return bytes(s['size']) if s['type']==8 else self.raw[s['offset']:s['offset']+s['size']]
    def sym(self,name):
        rows=[s for s in self.symbols if s['name']==name and s['shndx']!=0]; assert len(rows)==1,(name,len(rows)); return rows[0]
    def at(self,address,length,readonly=False):
        rows=[s for s in self.sections if s['flags']&2 and s['addr']<=address and address+length<=s['addr']+s['size']]; assert len(rows)==1,(hex(address),length)
        s=rows[0]
        if readonly: assert not s['flags']&5
        offset=address-s['addr']; return self.payload(s)[offset:offset+length],s
    def bytes(self,sym): return self.at(sym['value'],sym['size'])[0]

for key in ['current110_baseline_Rust','current110_baseline_image','current110_baseline_process']:
    assert ref(X[key]['path'])==X[key]
old=Elf(Path(X['current110_baseline_Rust']['path'])); new=Elf(B/'rust/mckernel_rust.o')
oldimage=Final(X['current110_baseline_image']['path']); image=Final(B/'mckernel.img')
assert ref(B/'rust/mckernel_rust.o')['sha256']=='e2c3032791bbd657a85629dd48ca86b3b93f3ef729305568031776d5674ad9d0'
assert ref(B/'mckernel.img')['sha256']=='60e62f97ef48ecaf14174af1c5b75d7181969f439c1b45c618d6c16d4bc40d57'

def patched(elf,name,final):
    symbol=fn(elf,name); raw=bytearray(data(elf,symbol)); f=final.sym(name)
    assert f['size']==symbol['size'] and f['type']==2
    actual=final.bytes(f); records=[]; last=-8
    for r in sorted(rels(elf,symbol),key=lambda v:v['offset']):
        off=r['offset']; assert r['type']==1 and off>=last+8 and off+8<=len(raw); last=off
        target=r['target']; value=struct.unpack_from('<Q',actual,off)[0]
        if target['name']:
            fs=final.sym(target['name']); expected=(fs['value']+r['addend'])&((1<<64)-1)
            assert value==expected
            rec=dict(kind='NAMED',target=target['name'],final_symbol=fs)
        else:
            s=elf.sections[target['shndx']]
            assert target['type']==3 and target['bind']==0 and target['value']==0
            assert s['name']=='.lrodata.str1.1' and s['flags']&0x32==0x32 and not s['flags']&5
            start=r['addend']; assert 0<=start<s['size']
            section=elf.raw[s['offset']:s['offset']+s['size']]; end=section.index(b'\0',start)+1
            literal=section[start:end]; assert len(literal)>1
            found,fs=final.at(value,len(literal),readonly=True); assert found==literal
            rec=dict(kind='EXACT_SECTION_STRING',input_section=s['name'],input_section_sha256=hashlib.sha256(section).hexdigest(),input_addend=start,literal_hex=literal.hex(),literal=literal[:-1].decode(),final_readonly_section=fs['name'])
        struct.pack_into('<Q',raw,off,value)
        records.append(dict(offset=off,type=1,addend=r['addend'],actual_final_address=hex(value),**rec))
    assert bytes(raw)==actual,(name,'actual complete final instructions differ')
    return symbol,records

names=sorted(set(X['HOST13_production_consumer_map'].values())|{'set_timer','timer_set_timer_body_result'})
comparisons=[]
for name in names:
    before,br=patched(old,name,oldimage); after,ar=patched(new,name,image)
    assert before['size']==after['size']
    ba=bytearray(data(old,before)); aa=bytearray(data(new,after))
    def shape(elf,s):
        return [(r['offset'],r['type'],r['addend'],r['target']['name'],elf.sections[r['target']['shndx']]['name'] if not r['target']['name'] else None) for r in rels(elf,s)]
    assert shape(old,before)==shape(new,after)
    for r in ar: ba[r['offset']:r['offset']+8]=bytes(8); aa[r['offset']:r['offset']+8]=bytes(8)
    assert ba==aa
    for a,b in zip(br,ar):
        if a['kind']=='EXACT_SECTION_STRING': assert a['literal_hex']==b['literal_hex'] and a['input_section_sha256']==b['input_section_sha256']
    comparisons.append(dict(consumer=name,old_symbol=before,current_symbol=after,current_final_symbol=image.sym(name),nonrelocated_bytes_equal=True,nonrelocated_sha256=hashlib.sha256(aa).hexdigest(),old_final_targets=br,current_final_targets=ar))

storage=read(G/'HOST13-STORAGE-AND-CONSUMERS.json'); argument_rows=[]
regs=['edx','edx','edx','ecx','edx','stack eighth','ecx','edx','r8d','ecx','edx','stack eighth','r8d']
for r,reg in zip(storage['records'],regs):
    name=r['production_consumer']; value=r['value']; dis=subprocess.check_output(['objdump','-d','--disassemble='+name,str(image.path)],text=True)
    pattern=(r'push\s+\$0x%x\b'%value) if reg=='stack eighth' else (r'mov\s+\$0x%x,%%%s\b'%(value,reg))
    instructions=[line for line in dis.splitlines() if re.search(pattern,line)]; assert len(instructions)==1,(name,value,reg,instructions)
    argument_rows.append(dict(data=r['data'],consumer=name,signed_CInt=value,ABI_argument=reg,current_instruction=instructions[0].strip()))

idle=read(G/'IDLE116-AND-INHERITED-CONSUMERS.json')['idle116']; _,idle_rels=patched(new,'process_idle_entry',image)
targets={r['target']:r for r in idle_rels if r['kind']=='NAMED'}
for name in ['process_idle_offsets','process_idle_values','process_idle_callbacks','sched_idle_loop_body_result']: assert name in targets
idledis=subprocess.check_output(['objdump','-d','--disassemble=process_idle_entry',str(image.path)],text=True)
for name,reg in [('process_idle_offsets','rdx'),('process_idle_values','rcx'),('process_idle_callbacks','r8')]:
    assert re.search(r'movabs\s+\$%s,%%%s\b'%(targets[name]['actual_final_address'],reg),idledis)
for name,table in idle.items():
    s=image.sym(name); payload,section=image.at(s['value'],s['size'],True)
    assert payload.hex()==table['bytes_hex'] and s['size']==table['size'] and s['value']%table['alignment']==0

nextproof=read(G/'NEXT-PROVIDERS-RESULT.json'); retained=read(G/'RETAINED-F02-DATA-OWNERS-RESULT.json')
assert nextproof['status'].startswith('PASS') and retained['status'].startswith('PASS')
assert len(nextproof['phases']['actual_forty_five_Rust_exports'])==45
timer=nextproof['phases']['timer120']; ts=image.sym('process_timer_runtime_offsets'); tb,tsec=image.at(ts['value'],120,True)
assert list(struct.unpack('<15Q',tb))==timer['exact15_current_words'] and ts['value']%8==0
timerdis=subprocess.check_output(['objdump','-d','--disassemble=set_timer',str(image.path)],text=True)
needed={0:'-0x90(%rdx)',1:'0x1ec0(%r13)',3:'0x1c(%rdx)',4:'0x13d0(%rcx)',5:'0x1e98(%r13)',6:'0x1ec0(%r13)',8:'0x1ea8(%r13)',9:'0x1f2c(%r13)',10:'0x1f78(%r13)'}
for token in needed.values(): assert token in timerdis

report=dict(scope=__doc__.splitlines()[0],reviewer='/root/custody_release_review',independent=True,
 decision='PASS_EXACT_CURRENT110_INHERITED13_TIMER9_AND_IDLE116_FINAL_CONSUMERS',
 tuple=dict(Rust=ref(B/'rust/mckernel_rust.o'),image=ref(B/'mckernel.img'),process=ref(B/'CMakeFiles/mckernel.img.dir/process.c.o')),
 original_failures_preserved=[ref(G/'FINAL-SUFFIX-QUALIFICATION.json'),ref(G/'IDLE116-AND-INHERITED-CONSUMERS.json')],
 evidence=[ref(G/n) for n in ['NEXT-PROVIDERS-RESULT.json','RETAINED-F02-DATA-OWNERS-RESULT.json','HOST13-STORAGE-AND-CONSUMERS.json']],
 consumer_comparisons=comparisons,thirteen_current_ABI_arguments=argument_rows,
 actual_current_R64_targets=sum(len(r['current_final_targets']) for r in comparisons),
 anonymous_string_targets=sum(r['kind']=='EXACT_SECTION_STRING' for row in comparisons for r in row['current_final_targets']),
 no_anonymous_target_skipped=True,idle116=dict(tables=idle,consumer='process_idle_entry',current_final_targets=idle_rels,final_disassembly=idledis,ABI=dict(offsets='RDX',values='RCX',callbacks='R8',provider='sched_idle_loop_body_result')),
 timer=dict(all15_words=timer['exact15_current_words'],readonly120B_aligned8=True,nine_consumed_word_indices=sorted(needed),six_data_only_word_indices=[2,7,11,12,13,14],current_consumed_instruction_tokens=needed,final_set_timer_disassembly=timerdis),
 scripted_HOST13_OPEN_preserved=True,scope_limit='Exact current default selected artifact consumers only; no execution/native/whole-file or Source38 clearance.',
 compiler_or_workload_actions=0,native_acceptance=False,whole_file_retirement=False)
with (D/'CONSUMER-REVIEW.json').open('x') as stream: json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(dict(decision=report['decision'],R64=report['actual_current_R64_targets'],anonymous=report['anonymous_string_targets'],receipt=ref(D/'CONSUMER-REVIEW.json'))))
