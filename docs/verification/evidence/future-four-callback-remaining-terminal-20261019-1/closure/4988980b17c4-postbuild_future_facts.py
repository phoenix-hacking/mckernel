"""Actual future fifteen-capture consumer, with late section-aware descriptors."""
from pathlib import Path
import argparse,ast,hashlib,json,re,types
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from terminal_contract import need,checked_bytes,cleanup_canonical,digest
BASE=Path('/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/postbuild-consumer-v2/postbuild_four_leaf_facts_v2.py')
SYMBOLS=('process_current_resource_set_bridge','process_release_hash_detach_bridge','process_release_sibling_detach_bridge','process_release_final_cleanup_bridge')
ARGUMENT_INDICES=(8,9,10,17)  # frozen zero-based Rust body-result argument convention
DESCRIPTORS=('RELEASE_TID_DEBUG','REPLACE_TID_DEBUG')

def base_adapter(ref):
 need(Path(ref['path'])==BASE,'accepted facts source path')
 raw=checked_bytes(ref);source=raw.decode();m=types.ModuleType('_accepted_fourleaf_facts');m.__file__=str(Path(__file__).resolve());exec(compile(raw,str(BASE),'exec'),m.__dict__)
 node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='validate_completion')
 fn=ast.get_source_segment(source,node)
 old="operations=plan['operations'];need(len(operations)==14 and len({o['index'] for o in operations})==14,'exact fourteen DECLARED operation receipts required')"
 new="operations=plan['operations'];need(len(operations)==15 and len({o['index'] for o in operations})==15,'exact fifteen DECLARED operation receipts required')"
 need(fn.count(old)==1,'frozen completion adaptation point');fn=fn.replace(old,new).replace('range(1,15)','range(1,16)')
 m.REQUIRED_FACT_INDICES=set(range(1,16));m.__file__=str(Path(__file__).resolve());exec(compile(fn,str(Path(__file__).resolve()),'exec'),m.__dict__)
 return m

def symbol_sections(text,tag):
 rows=[line.split() for line in text.splitlines() if line.split() and tag in line.split()[-1]]
 need(len(rows)==1,'one exact descriptor symbol '+tag);r=rows[0]
 need(len(r)>=8 and r[0].endswith(':') and r[6].isdigit(),'numeric actual ELF symbol Ndx')
 need(int(r[2],0)==32,'descriptor size32');return dict(symbol=r[-1],address=int(r[1],16),size=32,ndx=int(r[6]))

def descriptor_facts(m,captures,ops):
 # Each Rust capture is independently section-qualified. Equal address zero in
 # two different sections is valid and must never share one byte dictionary.
 rust=[symbol_sections(captures[9],tag) for tag in DESCRIPTORS]
 image=[symbol_sections(captures[12],tag) for tag in DESCRIPTORS]
 need(rust[0]['ndx']!=rust[1]['ndx'],'distinct actual Rust descriptor sections')
 out={}
 for n,row in enumerate(rust):
  index=13+n;argv=ops[index]['actual_artifact_argv'];need(argv[-3:-1]==['-x',str(row['ndx'])] and argv[0]=='/usr/bin/readelf','late exact Rust section argv')
  names=re.findall(r"Hex dump of section '([^']+)'",captures[index]);need(len(names)==1 and DESCRIPTORS[n] in names[0],'unique descriptor section header')
  bytes_by_address=m.section_bytes(re.sub(r'(?m)^(\s*)0x([0-9a-fA-F]+)',r'\1\2',captures[index]));need(set(bytes_by_address)==set(range(row['address'],row['address']+32)),'exact distinct32B Rust section capture')
  data=bytes(bytes_by_address[row['address']+i] for i in range(32));out['rust_'+DESCRIPTORS[n]]=check_descriptor(row,data)
 start=min(row['address'] for row in image);stop=start+64
 need(sorted(row['address'] for row in image)==[start,start+32],'two exact adjacent32B linked descriptors')
 need(image[0]['ndx']==image[1]['ndx'],'one actual linked descriptor output section')
 argv=ops[15]['actual_artifact_argv'];need(argv[:2]==['/usr/bin/objdump','-s'] and '--start-address='+hex(start) in argv and '--stop-address='+hex(stop) in argv,'late exact64B linked range argv')
 need('-j' not in argv and '__verbose' not in argv,'no invented output section')
 need(len(re.findall(r'Contents of section \S+:',captures[15]))==1,'one actual output section capture')
 raw=m.section_bytes(captures[15]);need(set(raw)==set(range(start,stop)),'exact linked64B bytes')
 for tag,row in zip(DESCRIPTORS,image):out['image_'+tag]=check_descriptor(row,bytes(raw[row['address']+i] for i in range(32)))
 return out

def check_descriptor(row,data):
 need(row['address']%8==0 and len(data)==32,'descriptor size/alignment');need(int.from_bytes(data[:8],'little') and int.from_bytes(data[8:16],'little'),'live file/func pointers')
 flags=int.from_bytes(data[24:28],'little');need(flags>>24==0 and flags&0xffffff and data[16:24]==bytes(8),'default-disabled logger flags/fmt')
 return dict(**row,bytes_hex=data.hex(),line=flags&0xffffff,flags=flags>>24,fmt_null=True)

def actual_callback_facts(m,captures):
 nms={k:m.nm_rows(captures[i]) for k,i in [('process',1),('fallback',4),('rust',7),('image',10)]};facts=[]
 for symbol,index in zip(SYMBOLS,ARGUMENT_INDICES):
  for kind,rows in nms.items():
   defs=[r for r in rows if r[1]=='T' and r[2]==symbol];unresolved=[r for r in rows if r[1]=='U' and r[2]==symbol]
   need(len(defs)==(0 if kind=='process' else 1),'selected/fallback unique definition '+kind+':'+symbol)
   need(not unresolved,'no obsolete C callback dependency '+kind+':'+symbol)
  rustbody=m.body(captures[8],symbol);need(not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',rustbody),'no FP '+symbol)
  for slot in (8,11):
   body=m.body(captures[slot],'release_process');need(symbol in body and 'process_release_process_body_result' in body,'actual default consumer edge '+symbol)
  facts.append(dict(symbol=symbol,consumer='release_process',argument_index_from_frozen_Rust_source=index,index_convention='zero-based-body-result-argument',actual_machine_consumer_edges=['rust','image'],machine_argument_slot_independently_decoded=False))
 return facts

def old_four_leaf_facts(m,captures):
 nm_rows=m.nm_rows;body=m.body
 nms={k:nm_rows(captures[i]) for k,i in [('process',1),('fallback',4),('rust',7),('image',10)]}
 for kind in nms:
  defs=[r for r in nms[kind] if r[1]=='T' and r[2]=='__release_tid'];unresolved=[r for r in nms[kind] if r[1]=='U' and r[2]=='__release_tid']
  assert len(defs)==(0 if kind=='process' else 1),(kind,defs)
  assert len(unresolved)==(1 if kind=='process' else 0),(kind,unresolved)
 for kind in nms:
  for normal_symbol in ['process_destroy_thread_time_account_bridge','process_destroy_thread_hash_detach_bridge']:
   defined=[v for v in nms[kind] if v[1]=='T' and v[2]==normal_symbol]
   unresolved=[v for v in nms[kind] if v[1]=='U' and v[2]==normal_symbol]
   assert len(defined)==(0 if kind=='process' else 1),(kind,normal_symbol,defined)
   assert not unresolved,(kind,normal_symbol,unresolved)
 timebody=body(captures[8],'process_destroy_thread_time_account_bridge')
 hashbody=body(captures[8],'process_destroy_thread_hash_detach_bridge')
 for normal_body in [timebody,hashbody]:
  assert not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',normal_body)
 for kind in ['process','image']:
  assert len([r for r in nms[kind] if r[1]=='T' and r[2]=='process_destroy_thread_release_tid_bridge'])==1
 for i in [2,11]:assert '__release_tid' in body(captures[i],'process_destroy_thread_release_tid_bridge')
 actualbody=body(captures[8],'__release_tid');assert not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',actualbody)
 for kind in nms:
  defined=[r for r in nms[kind] if r[1]=='T' and r[2]=='__find_and_replace_tid'];unresolved=[r for r in nms[kind] if r[1]=='U' and r[2]=='__find_and_replace_tid']
  assert len(defined)==(0 if kind=='process' else 1),(kind,defined)
  assert len(unresolved)==(1 if kind=='process' else 0),(kind,unresolved)
 for kind in ['process','image']:
  assert len([r for r in nms[kind] if r[1]=='T' and r[2]=='process_destroy_thread_replace_tid_bridge'])==1
 for i in [2,11]:assert '__find_and_replace_tid' in body(captures[i],'process_destroy_thread_replace_tid_bridge')
 replacebody=body(captures[8],'__find_and_replace_tid');assert not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',replacebody)
 return dict(status="PASS_OLD_FOUR_LEAF_MECHANICAL_FACTS_FROM_THIS_FIFTEEN_CAPTURE_SET",native_acceptance=False)

def main():
 a=argparse.ArgumentParser();a.add_argument('--known',required=True);a.add_argument('--known-sha256',required=True)
 for stem in ('plan','release','completion'):a.add_argument('--'+stem,required=True);a.add_argument('--'+stem+'-sha256',required=True)
 a.add_argument('--output',required=True);x=a.parse_args();known=json.loads(checked_bytes(dict(path=x.known,sha256=x.known_sha256)))
 m=base_adapter(known['engines']['facts']);plan,captures,completion=m.validate_completion(Path(x.plan),x.plan_sha256,Path(x.release),x.release_sha256,Path(x.completion),x.completion_sha256)
 ops={op['index']:op for op in plan['operations']}
 # The already accepted old-four-leaf code is a mandatory independent input to
 # the additive canonical report; fifteen captures alone do not assert old scope.
 old_report=old_four_leaf_facts(m,captures)
 result=dict(schema='mckernel.future-four-callback.postbuild-additive-facts.v1',status='PASS_ADDITIVE_MECHANICAL_FACTS_ONLY',completion=completion,old_four_leaf_facts=old_report,callbacks=actual_callback_facts(m,captures),descriptors=descriptor_facts(m,captures,ops),original_full_syscall_DWARF_gap='OPEN_NO_REPLAY_NO_WAIVER',derived_pointer_windows=[dict(tag=tag,field=field,address=int.from_bytes(bytes.fromhex(value['bytes_hex'])[offset:offset+8],'little'),extent=extent,artifact=plan['paths']['image']) for tag,value in descriptor_facts(m,captures,ops).items() if tag.startswith('image_') for field,offset,extent in [('file',0,256),('func',8,64)]],pending=['four actual linked file/func pointer windows','independent additive canonical review'],production_or_native_acceptance=False)
 p=Path(x.output)
 with p.open('xb') as f:f.write(json.dumps(result,sort_keys=True,indent=2).encode()+b'\n')
 print('PASS actual15 completion and additive4callback/section-aware descriptor facts only; no native acceptance')
if __name__=='__main__':main()
