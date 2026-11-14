"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite retained source/symbol extraction; not an observer retry or acceptance.
"""
from pathlib import Path
import re,json,hashlib
D=Path(__file__).resolve().parent;B=D.parent;A=B/'actual-bounded-suffix-1';R=Path('/home/holden/mckernel')
def binding(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def parse(p):
 secs={};syms=[]
 for number,line in enumerate(p.read_text().splitlines(),1):
  m=re.match(r'\s*\[\s*(\d+)\]\s+(\S+)\s+(\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s*(.*?)\s+(\d+)\s+(\d+)\s+(\d+)\s*$',line)
  if m: secs[m[1]]={'name':m[2],'type':m[3],'address':hex(int(m[4],16)),'size':int(m[6],16),'flags':m[8].strip(),'alignment':int(m[11]),'capture_line':number}
  m=re.match(r'\s*(\d+):\s+([0-9a-f]+)\s+(\d+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s*(.*)',line)
  if m:syms.append({'value':hex(int(m[2],16)),'size':int(m[3]),'type':m[4],'bind':m[5],'ndx':m[7],'name':m[8],'capture_line':number})
 return secs,syms
art={k:parse(A/p/'stdout') for k,p in [('Rust','00'),('image','01')]}
j=json.loads((A/'FOCUSED-SYMBOL-ABI-EVALUATION.json').read_text());abi={r['symbol']:r for r in j['data_rows']}
s=R/'kernel/rust/x86_memory_helpers.rs';c=R/'arch/x86_64/kernel/memory.c';lines=s.read_text().splitlines();clines=c.read_text().splitlines()
pairs=[('fixed_virt','OWNED_FIXED_VIRT','x86_memory_fixed_virt_slot'),('init_pt_lock','OWNED_INIT_PT_LOCK','x86_memory_init_pt_lock_address'),('init_pt_loaded','OWNED_INIT_PT_LOADED','x86_memory_init_pt_loaded_slot'),('boot_pt','OWNED_BOOT_PT','x86_memory_boot_pt_slot'),('init_pt','OWNED_INIT_PT','x86_memory_init_pt_slot'),('last_page','OWNED_LAST_PAGE','x86_memory_last_page_slot'),('use_1gb_page','OWNED_USE_1GB_PAGE','x86_clear_l3_use_1gb_page')]
rows=[]
for old,new,slot in pairs:
 row={'C_name':old,'C_size':abi[old]['C_size'],'C_alignment':abi[old]['C_alignment'],'Rust_source_identity':'mckernel_rust::x86_memory_helpers::owned_memory_data::'+new,'pointer_cell':slot,'relation':'distinct readonly pointer cell initialized to addr_of_mut!(Rust owned storage); not an ELF alias and not C storage','source_initializer':[{'line':n,'text':line.strip()} for n,line in enumerate(lines,1) if re.search(r'\bstatic mut '+new+r'\b',line)],'source_pointer_initializer':[{'line':n,'text':line.strip()} for n,line in enumerate(lines,1) if 'addr_of_mut!('+new+')' in line],'C_reference_declaration':[{'line':n,'text':line.strip()} for n,line in enumerate(clines,1) if re.search(r'^static .*\b'+old+r'\b',line)],'source_consumer_refs':[{'line':n,'text':line.strip()} for n,line in enumerate(lines,1) if n<9500 and re.search(r'\b'+slot+r'\b',line) and not line.strip().startswith('static ')]}
 for kind,(secs,syms) in art.items():
  defs=[v for v in syms if v['name'].endswith(str(len(new))+new) and '17owned_memory_data' in v['name'] and v['ndx']!='UND']
  cells=[v for v in syms if v['name']==slot and v['ndx']!='UND']
  row[kind]={'storage_definitions':[dict(v,section=secs.get(v['ndx'])) for v in defs],'pointer_cell_definitions':[dict(v,section=secs.get(v['ndx'])) for v in cells],'literal_C_storage_definitions':[v for v in syms if v['name']==old and v['ndx']!='UND']}
 row['initializer_evidence']='Explicit null/zero Rust initializer and allocated writable NOBITS section (zero-filled initial storage). Pointer cell intended target is source-bound only; compiled pointer target not read by this extraction.'
 rows.append(row)
inputs=[s,c,A/'00/stdout',A/'01/stdout',A/'02/stdout',A/'FOCUSED-SYMBOL-ABI-EVALUATION.json',A/'INPUTS-JOIN.json']
join=json.loads((A/'INPUTS-JOIN.json').read_text());pins={v['path']:v['sha256'] for v in join['inputs']}
record={'scope':__doc__.splitlines()[0],'status':'FINITE_SEVEN_ROW_IDENTITY_EXTRACTION_NOT_ACCEPTANCE','rows':rows,'inputs':[binding(p) for p in inputs],'canonical_sources_equal_retained_join':{str(p):binding(p)['sha256']==pins[str(p)] for p in [s,c]},'prior_failures_preserved':str(A/'FOCUSED-SYMBOL-ABI-EVALUATION.json'),'limits':['No compiler/readelf/native execution or observer retry','No source rename, no canonical modification, no guard change','Rust relocation dump omitted by prior bounded correction; compiled cell-to-pointee and compiled function reference edges remain unproved by these captures','Image symbol table contains definitions, not a data-section hex dump; pointer cell target bytes have not been validated','No default image acceptance/native/file retirement inferred'],'expert_recommendation':'Independent reviewer may consider a finite source-bound storage identity map for these7 historical internal C names, keeping unique exact owned symbol, C ABI size/alignment, NOBITS/WA/nonexec, distinct-address and initializer checks. Preserve literal-name failure, all72 existing ABI checks and function checks. Do not map storage to the8byte pointer cell or accept arbitrary symbol suffixes. Before claiming compiled target/reference proof obtain separately reviewed bounded exact7cell bytes/relocations (no whole-Rust dump/rebuild); this extraction itself grants no observer replay.'}
(D/'SEVEN-STORAGE-IDENTITIES.SOURCE-ONLY.json').write_text(json.dumps(record,indent=2)+'\n')
md=['Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','','Finite source/symbol mapping for independent review; original failure remains unchanged. Pointer cells are distinct objects, not aliases or the mutable storage.','','| C storage | Exact Rust leaf | Image address | Size/align | Pointer cell |','|---|---|---|---|---|']
for row in rows:
 v=row['image']['storage_definitions'][0];md.append('| '+row['C_name']+' | '+row['Rust_source_identity'].split('::')[-1]+' | '+v['value']+' | '+str(v['size'])+'/'+str(row['C_alignment'])+' | '+row['pointer_cell']+' |')
md+=['','All seven Rust storage definitions are allocated writable NOBITS, with zero/null source initializers matching the retained C declarations and seven C ABI rows. See JSON for exact mangled names, section indices/alignment, source line references and input hashes.','','No compiled pointer-cell target/consumer relocation edge is proved: the complete Rust relocation dump was intentionally omitted and the image capture has no cell hex dump. Source consumer references are recorded separately. A future bounded exact-seven-cell byte/relocation observation needs its own coordinator/reviewer decision; this is not a third observer retry. No C retirement or native credit.']
(D/'HANDOFF.md').write_text('\n'.join(md)+'\n')
print(json.dumps({'rows':len(rows),'source_equal':record['canonical_sources_equal_retained_join'],'output':str(D)}))
