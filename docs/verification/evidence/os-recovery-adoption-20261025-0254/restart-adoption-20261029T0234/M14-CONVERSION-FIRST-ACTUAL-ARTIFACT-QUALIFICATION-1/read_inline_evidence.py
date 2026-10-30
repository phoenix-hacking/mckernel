"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read actual Rust object DWARF for selected optimized callback consumers.
"""
from pathlib import Path
import json,subprocess,re,hashlib
D=Path(__file__).resolve().parent;A=D.parent;B=A/'ROOT-CONVERSION-FIRST-BUILD-ADMISSION-1/OUTPUT/work/output/build/kernel';p=B/'rust/mckernel_rust.o';targets=set(json.loads((D/'CHANGE-SCAN.ACTUAL.json').read_text())['Rust_new'])
proc=subprocess.Popen(['readelf','--debug-dump=info',str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);nodes={};stack={};current=None
for line in proc.stdout:
 m=re.match(r'\s*<(\d+)><([0-9a-f]+)>: Abbrev Number: (\d+)(?: \(([^)]+)\))?',line)
 if m:
  depth=int(m[1]);off=int(m[2],16)
  if m[3]=='0':current=None;continue
  current={'offset':off,'tag':m[4],'parent':stack.get(depth-1)};nodes[off]=current;stack[depth]=off
  continue
 m=re.match(r'\s*<[0-9a-f]+>\s+(DW_AT_\w+)\s*:\s*(.*)',line)
 if m and current is not None:
  key=m[1][6:];value=m[2]
  if key in ['abstract_origin','type','specification']:
   z=re.search(r'<0x([0-9a-f]+)>',value);value=int(z[1],16)if z else value
  if key in ['name','linkage_name','abstract_origin','specification','low_pc','high_pc','ranges','call_file','call_line','decl_file','decl_line','type','byte_size','alignment','encoding','calling_convention']:current[key]=value
stderr=proc.stderr.read();rc=proc.wait();assert rc==0 and not stderr,(rc,stderr)
def clean_name(x):return x.rsplit(': ',1)[-1]if isinstance(x,str)else x
def resolved(n,key):
 for _ in range(4):
  if key in n:return n[key]
  n=nodes.get(n.get('abstract_origin',n.get('specification')),{});
 return None
selected={o:n for o,n in nodes.items()if clean_name(n.get('name'))in targets or clean_name(n.get('linkage_name'))in targets};inline=[]
for o,n in nodes.items():
 if n.get('tag')=='DW_TAG_inlined_subroutine'and n.get('abstract_origin')in selected:
  ancestor=nodes.get(n.get('parent'),{});trail=[]
  while ancestor:
   if ancestor['tag'] in ['DW_TAG_subprogram','DW_TAG_inlined_subroutine']:trail.append(dict(name=clean_name(resolved(ancestor,'name')),linkage_name=clean_name(resolved(ancestor,'linkage_name')),offset=ancestor['offset']))
   ancestor=nodes.get(ancestor.get('parent'),{})
  inline.append(dict(callback=clean_name(resolved(selected[n['abstract_origin']],'name')),DIE=n,consumer_ancestry=trail))
result=dict(scope=__doc__.splitlines()[0],object=dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()),selected_function_DIEs=list(selected.values()),actual_inlined_consumers=inline,readelf_returncode=rc,stderr=stderr)
(D/'ACTUAL-INLINE-CALLBACK-CONSUMERS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(selected_DIEs=len(selected),inlines=len(inline),callbacks=sorted(set(x['callback']for x in inline)))))
