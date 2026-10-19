"""Consume completed bounded 14 captures only; emit facts/window INPUTS, no tools."""
from pathlib import Path
import argparse,json,re,hashlib

def nm_rows(text):
 rows=[]
 for line in text.splitlines():
  v=line.split()
  if len(v)>=3 and re.fullmatch('[0-9a-fA-F]+',v[0]):rows.append((int(v[0],16),v[-2],v[-1]))
  elif len(v)==2 and v[0]=='U':rows.append((None,'U',v[1]))
 return rows

def section_bytes(text):
 result={}
 for line in text.splitlines():
  v=line.split()
  if not v or not re.fullmatch('[0-9a-fA-F]+',v[0]):continue
  groups=[]
  for word in v[1:5]:
   if not re.fullmatch('[0-9a-fA-F]{8}',word):break
   groups.append(word)
  if groups:
   base=int(v[0],16)
   for i,b in enumerate(bytes.fromhex(''.join(groups))):result[base+i]=b
 return result

def body(text,name):
 m=re.search(r'(?m)^\s*[0-9a-fA-F]+ <'+re.escape(name)+r'>:',text);assert m,name
 rest=text[m.start():];end=re.search(r'(?m)^\s*[0-9a-fA-F]+ <[^>]+>:',rest[m.end()-m.start():])
 return rest if end is None else rest[:m.end()-m.start()+end.start()]

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
 plan=json.loads(a.plan.read_text());ops={v['index']:v for v in plan['operations']};captures={i:Path(v['stdout_path']).read_text() for i,v in ops.items()}
 for v in ops.values():
  assert Path(v['stderr_path']).stat().st_size==0
  assert Path(v['stdout_path']).stat().st_size<v['each_stream_hard_fsize_bytes']
 nms={k:nm_rows(captures[i]) for k,i in [('process',1),('fallback',4),('rust',7),('image',10)]}
 for kind in nms:
  defs=[r for r in nms[kind] if r[1]=='T' and r[2]=='__release_tid'];unresolved=[r for r in nms[kind] if r[1]=='U' and r[2]=='__release_tid']
  assert len(defs)==(0 if kind=='process' else 1),(kind,defs)
  assert len(unresolved)==(1 if kind=='process' else 0),(kind,unresolved)
 for kind in nms:
  defined=[v for v in nms[kind] if v[1]=='T' and v[2]=='process_destroy_thread_time_account_bridge']
  unresolved=[v for v in nms[kind] if v[1]=='U' and v[2]=='process_destroy_thread_time_account_bridge']
  assert len(defined)==(0 if kind=='process' else 1),(kind,defined)
  assert not unresolved,(kind,unresolved)
 timebody=body(captures[8],'process_destroy_thread_time_account_bridge')
 assert not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',timebody)
 for kind in ['process','image']:
  assert len([r for r in nms[kind] if r[1]=='T' and r[2]=='process_destroy_thread_release_tid_bridge'])==1
 for i in [2,11]:assert '__release_tid' in body(captures[i],'process_destroy_thread_release_tid_bridge')
 actualbody=body(captures[8],'__release_tid');assert not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',actualbody)
 facts={};windows=[]
 for kind,rawslot,symbolslot in [('rust',13,9),('image',14,12)]:
  descriptors=[r for r in nms[kind] if 'RELEASE_TID_DEBUG' in r[2]];assert len(descriptors)==1;address,_,symbol=descriptors[0];assert address%8==0
  symrows=[line.split() for line in captures[symbolslot].splitlines() if line.split() and line.split()[-1]==symbol];assert len(symrows)==1 and int(symrows[0][2],0)==32
  raw=section_bytes(captures[rawslot]);data=bytes(raw[address+i] for i in range(32));lineflags=int.from_bytes(data[24:28],'little');assert lineflags>>24==0 and lineflags&0xffffff;assert data[16:24]==bytes(8)
  facts[kind]=dict(address=address,symbol=symbol,bytes_hex=data.hex(),line=lineflags&0xffffff,flags=lineflags>>24,fmt_null=True,size=32,alignment=8)
  if kind=='image':
   artifact=plan['paths']['image']
   for field,offset,extent in [('file',0,256),('func',8,64)]:
    pointer=int.from_bytes(data[offset:offset+8],'little');assert pointer
    windows.append(dict(field=field,address=pointer,bytes=extent,actual_artifact_argv=['/usr/bin/objdump','-s','--start-address='+hex(pointer),'--stop-address='+hex(pointer+extent),artifact],each_stream_hard_fsize_bytes=1048576,expected='UTF8 C string ending /kernel/rust/process_helpers.rs' if field=='file' else 'exact C string process_release_tid_log_bridge',status='INPUTS_ONLY_DERIVED_AFTER_ACTUAL14_NOT_EXECUTED'))
 result=dict(status='PASS_MECHANICAL_SYMBOL_CONSUMER_DESCRIPTOR_FACTS_ONLY',plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),descriptor_facts=facts,derived_pointer_windows=windows,pending=['Execute independently released bounded pointer windows and compare declared exact function/truthful Rust file provenance','Independent actual release-body ownership/order/first-match scalar semantic review','Native evidence and positive retirement'],body_disassembly=actualbody,time_account_body_disassembly=timebody,native_acceptance=False)
 a.output.write_text(json.dumps(result,indent=2)+chr(10))
 print('PASS mechanical actual symbols/consumer/descriptor; two derived pointer-window INPUTS remain unexecuted')
if __name__=='__main__':main()
