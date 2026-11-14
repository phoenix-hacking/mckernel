"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Static retained source/ELF extraction; no compiler, link or observer execution.
"""
from pathlib import Path
import ast,hashlib,json,struct
B=Path(__file__).resolve().parent
R=json.loads((B/'EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json').read_text());M=json.loads(Path(R['input_map']['path']).read_text())
def pin(p):
 p=Path(p);v=p.read_bytes();return dict(path=str(p),bytes=len(v),sha256=hashlib.sha256(v).hexdigest())
ns=dict(Path=Path,struct=struct);nodes=[n for n in ast.parse(Path(M['qualified_Elf_source']['path']).read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='Elf' or isinstance(n,ast.FunctionDef) and n.name in {'object_bytes','owning_relocations'}];exec(compile(ast.Module(body=nodes,type_ignores=[]),'<static ELF reader>','exec'),ns)
Elf=ns['Elf'];obj=ns['object_bytes'];own=ns['owning_relocations']
oldpin=M['compile_rows'][1]['baseline_selected_C_object'];old=Elf(Path(oldpin['path']));newpin=pin(B/'output-1/syscall.selected.o');new=Elf(Path(newpin['path']))
def D(e):return {s['name'] for s in e.symbols if s['name'] and s['shndx'] and s['bind'] in (1,2)}
def U(e):return {s['name'] for s in e.symbols if s['name'] and not s['shndx']}
removed=sorted(D(old)-D(new));assert len(removed)==35 and not D(new)-D(old) and len(U(old)-U(new))==21 and not U(new)-U(old)
X=Path(oldpin['path']).parents[1];source=X/'source/kernel/syscall.c';lines=source.read_text().splitlines(keepends=True)
objects=[]
for name in removed:
 s=old.sym(name);sec=old.sections[s['shndx']];assert s['bind']==1 and s['type']==1 and sec['flags']&2 and not sec['flags']&4
 occurrences=[dict(line=i+1,text=line.rstrip('\n')) for i,line in enumerate(lines) if name in line]
 objects.append(dict(name=name,symbol=s,section=sec,bytes_hex=obj(old,s).hex(),outgoing_RELA=own(old,s),source_occurrences=occurrences))
actual=X/'genuine-uti-header-transport-suffix04-source-1/actual-suffix04-12-attempt-1/04'
producer=json.loads((actual/'command.json').read_text());joined=json.loads((actual/'WHOLE-JOIN.json').read_text())
assert producer['argv'][producer['argv'].index('-c')+1]==str(source) and producer['argv'][producer['argv'].index('-o')+1]==oldpin['path']
assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams']
targets={r['target']['name'] for f in objects for r in f['outgoing_RELA'] if not r['target']['shndx']}
proof=dict(scope=R['scope'],status='STATIC_FACTS_ONLY_AWAIT_EXPERT_DESIGN',old_syscall=oldpin,actual_syscall=newpin,actual_partial=pin(B/'output-1/coherent-selected.partial.o'),old_source=pin(source),current_source=M['compile_rows'][1]['source'],actual_old_producer=pin(actual/'command.json'),actual_old_join=pin(actual/'WHOLE-JOIN.json'),D_removed=removed,D_added=sorted(D(new)-D(old)),U_removed=sorted(U(old)-U(new)),U_added=sorted(U(new)-U(old)),closed35_objects=objects,undefined_targets_from_closed35=sorted(targets),removed_U_is_subset_of_closed35_undefined_targets=U(old)-U(new)<=targets,old_source_append=dict(first_line=29331,last_line=len(lines),exact_text=''.join(lines[29330:]),sha256=hashlib.sha256(''.join(lines[29330:]).encode()).hexdigest()),current_source_occurrences={name:[i+1 for i,line in enumerate(Path(M['compile_rows'][1]['source']['path']).read_text().splitlines()) if name in line] for name in removed},execution=False,observer_correction=False,extractor=pin(__file__))
p=B/'STATIC-SYSCALL-CLOSED35-SOURCE-AND-OUTGOING-RELA.FACTS.json'
with p.open('x') as f:json.dump(proof,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(facts=pin(p),removed_D=len(removed),removed_U=len(U(old)-U(new)),outgoing_RELA=sum(len(f['outgoing_RELA']) for f in objects),undefined_targets=len(targets),Uremoved_subset=proof['removed_U_is_subset_of_closed35_undefined_targets']),indent=2))
