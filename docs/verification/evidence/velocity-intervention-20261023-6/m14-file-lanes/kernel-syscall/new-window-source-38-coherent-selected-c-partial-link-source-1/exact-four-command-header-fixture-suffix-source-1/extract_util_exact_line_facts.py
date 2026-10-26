"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only retained ELF/source extraction of exact compiler trace line immediates.
"""
from pathlib import Path
import ast,hashlib,json,re,struct
B=Path(__file__).resolve().parent
F=json.loads((B/'STATIC-SYSCALL-CLOSED35-SOURCE-AND-OUTGOING-RELA.FACTS.json').read_text());R=json.loads((B/'EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json').read_text());M=json.loads(Path(R['input_map']['path']).read_text())
def pin(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
ns=dict(Path=Path,struct=struct);nodes=[n for n in ast.parse(Path(M['qualified_Elf_source']['path']).read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='Elf' or isinstance(n,ast.FunctionDef) and n.name in {'object_bytes','owning_relocations'}];exec(compile(ast.Module(body=nodes,type_ignores=[]),'<static ELF reader>','exec'),ns)
old,new=[ns['Elf'](Path(F[k]['path'])) for k in ['old_syscall','actual_syscall']];obj=ns['object_bytes'];own=ns['owning_relocations'];before,after=old.sym('util_thread'),new.sym('util_thread');a,c=obj(old,before),obj(new,after)
assert before['size']==after['size']==1510
srca=Path(F['old_source']['path']).read_text().splitlines();srcc=Path(F['current_source']['path']).read_text().splitlines()
assert srca[28395:28503]==srcc[28422:28530]
def logical(lines,physical):
 line=1;directive=None
 for n,text in enumerate(lines[:physical],1):
  m=re.match(r'\s*#\s*(?:line\s+)?(\d+)(?:\s+"([^"]*)")?',text)
  if n==physical:return dict(physical_line=n,logical_line=line,text=text,latest_directive=directive)
  if m:line=int(m.group(1));directive=dict(physical_line=n,text=text,next_logical_line=line)
  else:line+=1
rows=[];allowed=set()
for offset,register,oldimm,newimm,phys in [(0x801b,'ecx',28314,28341,28438),(0x80b0,'ecx',28323,28350,28447),(0x82e9,'edx',28369,28396,28493),(0x8311,'edx',28372,28399,28496),(0x838f,'edx',28395,28422,28519),(0x83a1,'edx',28396,28423,28520)]:
 i=offset-before['value'];opcode=0xb9 if register=='ecx' else 0xba
 assert a[i]==c[i]==opcode and int.from_bytes(a[i+1:i+5],'little')==oldimm and int.from_bytes(c[i+1:i+5],'little')==newimm
 left,right=logical(srca,phys-27),logical(srcc,phys)
 assert left['logical_line']==oldimm and right['logical_line']==newimm and left['text']==right['text'] and '__LINE__' in right['text'] and '__FILE__' in right['text'] and ('kmalloc_tracked(' in right['text'] or 'kfree_tracked(' in right['text'])
 allowed.update(range(i+1,i+5));rows.append(dict(function_relative_instruction_offset=i,section_relative_instruction_offset=offset,opcode=opcode,register=register,old_instruction_hex=a[i:i+5].hex(),new_instruction_hex=c[i:i+5].hex(),old_source_line=left,new_source_line=right))
assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(a,c)))
other=[]
for s in old.symbols:
 if s['bind']==1 and s['type']==2 and s['shndx'] and s['name']!='util_thread':
  t=new.sym(s['name']);assert (s['bind'],s['type'],s['size'])==(t['bind'],t['type'],t['size']) and obj(old,s)==obj(new,t)
  other.append(dict(name=s['name'],size=s['size'],machine_sha256=hashlib.sha256(obj(old,s)).hexdigest()))
assert len(other)==30
result=dict(scope=R['scope'],status='STATIC_EXACT_SIX_LINE_IMMEDIATE_FACTS_ONLY',old_object=F['old_syscall'],new_object=F['actual_syscall'],old_source=F['old_source'],new_source=F['current_source'],old_symbol=before,new_symbol=after,old_bytes_hex=a.hex(),new_bytes_hex=c.hex(),old_function_RELA=own(old,before),new_function_RELA=own(new,after),exact_six_instruction_source_bindings=rows,all_other_function_bytes_identical=True,other30_global_functions=other,changed_byte_count=sum(x!=y for x,y in zip(a,c)),new_runtime_logic=False,execution=False,extractor=pin(__file__))
p=B/'STATIC-UTIL-THREAD-EXACT-SIX-LINE-IMMEDIATES.FACTS.json'
with p.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(facts=pin(p),changed_bytes=result['changed_byte_count'],unchanged_other_global_functions=len(other)),indent=2))
