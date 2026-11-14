"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fixed actual folded-consumer ELF readback; never executes built code.
"""
from pathlib import Path
import ast,hashlib,json,struct,subprocess
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent
B=P/'relative-module-context-correction-source-1/HOST-output-proposed-1'
A=E/'ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1'
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
f=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py';t=ast.parse(f.read_text());wanted={'_ReuseElf','_reuse_elf_owning_relocations','_reuse_elf_object_bytes'};exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in wanted],type_ignores=[]),'retained exact ELF readers','exec'),globals())
Elf=_ReuseElf;rels=_reuse_elf_owning_relocations;data=_reuse_elf_object_bytes
new=Elf(B/'rust-selected.o');old=Elf(A/'OUTPUT/work/output/build/kernel/rust/mckernel_rust.o')
new.path=B/'rust-selected.o';old.path=A/'OUTPUT/work/output/build/kernel/rust/mckernel_rust.o'
def own(e,name):
 a=[s for s in e.symbols if s['name']==name and s['shndx']];assert len(a)==1,(name,len(a));return a[0]
def dis(e,name):return subprocess.check_output(['objdump','-drw','--section='+e.sections[own(e,name)['shndx']]['name'],'--disassemble='+name,str(e.path)],text=True)
configmap=read(P/'EXACT-LOCAL14-CONFIG3-MAP.json');finals=read(P/'EXACT14-TYPES-AND-CONSUMERS.json')
consumer_names={'copy_user_pte','extend_process_region','init_process_stack','schedule','process_sched_rusage_debug_bridge','process_sched_timer_init_bridge','process_add_range_memclear_bridge','process_init_stack_alloc_aligned_bridge','process_init_stack_free_pages_bridge','process_page_fault_anon_allocate_body_result','process_page_fault_cow_allocate_body_result','remap_one_page'}
# Exact original filename cell users are already listed in the source packet.
tracked=[s['name'] for s in old.symbols if s['type']==2 and s['shndx'] and any(r['target']['name']=='process_tracked_allocator_source_file' for r in rels(old,s))]
consumer_names.update(tracked)
rows=[]
for name in sorted(consumer_names):
 a=own(old,name);b=own(new,name);row=dict(name=name,old_symbol=a,new_symbol=b,old_relocations=rels(old,a),new_relocations=rels(new,b))
 for e,label in [(old,'old114'),(new,'newHOST')]:
  q=D/('section-'+label+'--'+name+'.objdump');q.write_text(dis(e,name));row[label+'_disassembly']=ref(q)
 rows.append(row)
out=D/'ACTUAL-FOLDED-CONSUMER-INPUTS.json'
with out.open('x') as o:json.dump(dict(old_Rust=ref(old.path),new_Rust=ref(new.path),consumers=rows,tracked_users=tracked),o,indent=2);o.write('\n')
print(json.dumps(dict(proof=ref(out),consumers=len(rows),tracked_users=len(tracked),sizes=[dict(name=r['name'],old=r['old_symbol']['size'],new=r['new_symbol']['size']) for r in rows])))
