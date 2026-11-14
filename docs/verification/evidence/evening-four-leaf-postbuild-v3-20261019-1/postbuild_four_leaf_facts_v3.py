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

# Exact completed-operation receipts supplement mechanical symbol/descriptor facts.
import os,stat
REQUIRED_FACT_INDICES={1,2,4,7,8,9,10,11,12,13,14}

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def need(value,why):
 if not value:raise RuntimeError(why)
def read_fd(path,cap,expected_hash=None):
 path=Path(path);need(path.is_absolute() and path.resolve()==path,'exact non-symlink absolute file path required')
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as stream:
  first=os.fstat(stream.fileno());need(stat.S_ISREG(first.st_mode) and first.st_nlink==1 and first.st_size<cap,'regular single-link bounded file required')
  h=hashlib.sha256();raw=bytearray()
  for block in iter(lambda:stream.read(65536),b''):
   raw.extend(block);need(len(raw)<cap,'hard capture bound reached');h.update(block)
  last=os.fstat(stream.fileno());named=path.lstat();fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  need(all(getattr(first,k)==getattr(last,k)==getattr(named,k) for k in fields),'held FD/current-name identity changed')
 digest=h.hexdigest();need(expected_hash is None or digest==expected_hash,'exact FD content hash differs')
 row=dict(path=str(path),device=first.st_dev,inode=first.st_ino,mode=oct(stat.S_IMODE(first.st_mode)),uid=first.st_uid,gid=first.st_gid,size=first.st_size,nlink=first.st_nlink,sha256=digest,mtime_ns=first.st_mtime_ns,ctime_ns=first.st_ctime_ns)
 return bytes(raw),row

def bound_json(ref,cap=1048576):
 need(isinstance(ref.get('sha256'),str) and re.fullmatch('[0-9a-f]{64}',ref['sha256']) is not None,'typed exact JSON hash required')
 raw,row=read_fd(ref['path'],cap,ref['sha256'])
 if 'bytes' in ref:need(row['size']==ref['bytes'],'typed receipt size differs')
 return json.loads(raw),row

def reviewed_release(path,digest):
 value,fd=bound_json(dict(path=str(path),sha256=digest),16*1024**2)
 need(value['status']=='PASS_EXACT_ORDINARY_POSTBUILD_READONLY_RELEASE','exact observation release required')
 review,reviewfd=bound_json(value['execution_review']);payload={k:v for k,v in value.items() if k!='execution_review'}
 need(review['decision']=='PASS_EXACT_ORDINARY_POSTBUILD_READONLY' and review['implementation_ownership'] is False and review['reviewer']!=value['author'],'independent exact observation review required')
 need(review['reviewed_release_payload_sha256']==hashlib.sha256(canonical(payload)).hexdigest(),'reviewed exact payload differs')
 sources=[]
 for key in ['dispatcher','descriptor_facts_producer']:
  ref=value[key];need(isinstance(ref.get('sha256'),str) and re.fullmatch('[0-9a-f]{64}',ref['sha256']) is not None,'source SHA required')
  _,row=read_fd(ref['path'],4*1024**2,ref['sha256']);sources.append(row)
 return value,dict(release=fd,review=reviewfd,sources=sources)

def joined_operation(op,expected_release,expected_stage,expected_rc,stderr_policy):
 raw,statusfd=read_fd(op['status_path'],1048576);status=json.loads(raw)
 raw,commandfd=read_fd(op['status_path']+'.command.json',1048576);command=json.loads(raw)
 raw,childfd=read_fd(op['status_path']+'.child.json',1048576);child=json.loads(raw)
 need(status['argv']==command['argv']==op['argv'] and status['stage']==command['stage']==expected_stage,'exact declared argv/stage differs')
 need(command['release_sha256']==expected_release and command['reservation_bytes']==op['both_stream_reservation_bytes'],'exact command release/reservation differs')
 need(status['direct_child_joined'] is True and status['observer_error'] is None and type(status['returncode']) is int and status['returncode']==expected_rc,'direct join/observed exit differs')
 need(type(child['pid']) is int and child['pid']>0 and child['proc_queries'] is False,'original child identity receipt differs')
 streams={};texts={}
 for name in ['stdout','stderr']:
  need(isinstance(status.get(name+'_sha256'),str) and re.fullmatch('[0-9a-f]{64}',status[name+'_sha256']) is not None,'stream hash required')
  raw,fd=read_fd(op[name+'_path'],op['each_stream_hard_fsize_bytes'],status[name+'_sha256']);need(fd['size']==status[name+'_bytes'],'exact stream size differs')
  if name=='stderr' and stderr_policy=='empty':need(fd['size']==0,'clean stderr required')
  streams[name]=fd;texts[name]=raw.decode()
 return texts,dict(observed_status=status,status=statusfd,command=commandfd,child=childfd,streams=streams,returncode=expected_rc,direct_child_joined=True)

def saved_symbol(text,tag):
 rows=[line.split() for line in text.splitlines() if line.split() and tag in line.split()[-1]]
 need(len(rows)==1,'unique saved exact descriptor symbol required');v=rows[0]
 need(len(v)>=8 and v[3]=='OBJECT' and int(v[2],0)==32 and v[6].isdigit(),'saved descriptor size/type/Ndx differs')
 return dict(symbol=v[-1],value=int(v[1],16),size=32,section_index=int(v[6]))

def section_headers(text):
 rows={}
 for line in text.splitlines():
  match=re.match(r'^\s*\[\s*(\d+)\]\s+(\S+)\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+(.+)$',line)
  if match:
   tail=match.group(8).split();rows[int(match.group(1))]=dict(name=match.group(2),type=match.group(3),address=int(match.group(4),16),offset=int(match.group(5),16),size=int(match.group(6),16),alignment=int(tail[-1],0))
 return rows

def indexed_hex(text):
 need(text.count("Hex dump of section '__verbose':")==1,'one exact indexed __verbose dump required')
 rows={}
 for line in text.splitlines():
  v=line.split()
  if not v or not re.fullmatch('0x[0-9a-fA-F]+',v[0]):continue
  words=[]
  for word in v[1:5]:
   if not re.fullmatch('[0-9a-fA-F]{8}',word):break
   words.append(word)
  for i,b in enumerate(bytes.fromhex(''.join(words))):
   address=int(v[0],16)+i;need(address not in rows,'duplicate indexed bytes');rows[address]=b
 need(set(rows)==set(range(32)),'exact one 32B inputsection required')
 return bytes(rows[i] for i in range(32))

def validate_completion(plan_path,plan_sha,release_path,release_sha,completion_path,completion_sha):
 plan,planfd=bound_json(dict(path=str(plan_path),sha256=plan_sha),16*1024**2)
 release,newfd=reviewed_release(release_path,release_sha);need(release['commands']==dict(path=str(plan_path),sha256=plan_sha),'remaining exact plan differs')
 need(Path(release['descriptor_facts_producer']['path'])==Path(__file__).resolve(),'exact v3 source required')
 base_ref=release['original_observation_release'];base,basefd=reviewed_release(Path(base_ref['path']),base_ref['sha256']);original,originalfd=bound_json(base['commands'],16*1024**2)
 need(len(original['operations'])==14 and {o['index'] for o in original['operations']}==set(range(1,15)),'original fourteen declared operations required')
 captures={};original_rows=[]
 for op in original['operations']:
  i=op['index'];declared=base['operation_completion_contracts'][str(i)]
  need(declared['returncode']==0 and declared['classification']=='MECHANICAL_INPUT','original declared contract must stay unchanged')
  texts,row=joined_operation(op,base_ref['sha256'],'command-'+str(i),1 if i==14 else 0,'bounded' if i==14 else 'empty')
  if i==14:
   need('__verbose' in texts['stderr'] and 'not found' in texts['stderr'],'specific unexpected image-section failure differs')
   row.update(classification='UNEXPECTED_FAILURE_PRESERVED_NOT_ACCEPTED',declared_returncode=0,acceptance_credit=False)
  else:row.update(classification='ORIGINAL_SUCCESS_PRESERVED',declared_returncode=0)
  row['index']=i;captures[i]=texts['stdout'];original_rows.append(row)
 # Source and genuine compiler facts remain strict, no ABI waiver.
 c71=base['actual_C71'];raw,_=read_fd(c71['assertion_source']['path'],1048576,c71['assertion_source']['sha256']);need(raw.count(b'_Static_assert(')==71,'full actualC71 required')
 tu,_=read_fd(c71['full_actual_C_TU']['path'],16*1024**2,c71['full_actual_C_TU']['sha256']);need(tu.endswith(raw),'actual C TU/assertion source join required')
 proof,proof_fd=bound_json(c71['compiler_proof']);need(proof['status']=='PASS','actualC compiler proof required')
 for phase in ['release-tid-full-process-selected','release-tid-full-process-fallback']:
  rows=[r for r in proof['checks'] if r['phase']==phase];need(len(rows)==1 and rows[0]['exit_code']==0 and rows[0]['full_TU_fixture_sha256']==c71['full_actual_C_TU']['sha256'],'selected/fallback actualC71 compile joins required')
 cpu,_=bound_json(base['actual_CPU_fullcrate_proof']);need(cpu['status']=='PASS','CPU/fullcrate proof required')
 # Pinned linked script is evidence of input __verbose placement, never a linker change.
 lref=release['linked_script'];raw,linkedfd=read_fd(lref['path'],1048576,lref['sha256']);script=raw.decode()
 need(re.search(r'\.data\s*:\s*\{[^}]*__start___verbose[^}]*\*\(__verbose\)[^}]*__stop___verbose',script,re.S) is not None,'actual script must merge __verbose into .data')
 descriptors={tag:saved_symbol(captures[9],tag) for tag in ['RELEASE_TID_DEBUG','REPLACE_TID_DEBUG']}
 need(descriptors['RELEASE_TID_DEBUG']['section_index']!=descriptors['REPLACE_TID_DEBUG']['section_index'],'distinct input section indices required')
 completion,completionfd=bound_json(dict(path=str(completion_path),sha256=completion_sha),16*1024**2)
 need(completion['release_sha256']==release_sha,'remaining completed receipt release differs')
 operations=plan['operations'];need(len(operations)==3 and {o['role'] for o in operations}=={'rust-release','rust-replace','image-range'},'exact remaining-only three operations required')
 texts={};newrows=[]
 for op in operations:
  role=op['role'];need(op['argv'][-len(op['actual_artifact_argv']):]==op['actual_artifact_argv'],'exact wrapper tool suffix differs');text,row=joined_operation(op,release_sha,'remaining-'+role,0,'empty')
  status=row['observed_status'];need(sum(r==status for r in completion['results'])==1,'exact remaining status completion join required')
  row['role']=role;newrows.append(row);texts[role]=text['stdout']
  if role.startswith('rust-'):
   tag='RELEASE_TID_DEBUG' if role=='rust-release' else 'REPLACE_TID_DEBUG';index=descriptors[tag]['section_index'];args=op['actual_artifact_argv']
   need(args==['/usr/bin/readelf']+(['-SW'] if role=='rust-release' else [])+['-x',str(index),release['input_artifacts']['rust']['path']],'exact symbol-index dump argv required')
  else:
   args=op['actual_artifact_argv'];need(args[0]=='/usr/bin/objdump' and '-j' not in args and args[-1]==release['input_artifacts']['image']['path'],'exact output address-window argv required')
 headers=section_headers(texts['rust-release']);rust_bytes={}
 for role,tag in [('rust-release','RELEASE_TID_DEBUG'),('rust-replace','REPLACE_TID_DEBUG')]:
  desc=descriptors[tag];h=headers.get(desc['section_index']);need(h is not None and h['name']=='__verbose' and h['type']=='PROGBITS' and h['size']==32 and h['alignment']>=8 and h['address']==desc['value']==0,'exact symbolNdx/32B/alignment section association differs')
  rust_bytes[tag]=indexed_hex(texts[role])
 need(headers[descriptors['RELEASE_TID_DEBUG']['section_index']]['offset']!=headers[descriptors['REPLACE_TID_DEBUG']['section_index']]['offset'],'distinct input file offsets required')
 nm=nm_rows(captures[10]);bounds={name:next(v[0] for v in nm if v[2]==name) for name in ['__start___verbose','__stop___verbose']}
 image_symbols={tag:saved_symbol(captures[12],tag) for tag in descriptors};start=min(v['value'] for v in image_symbols.values());stop=max(v['value']+32 for v in image_symbols.values())
 need(stop-start==64 and bounds['__start___verbose']<=start<stop<=bounds['__stop___verbose'],'exact image descriptor range within linked input-array bounds required')
 image_op=next(o for o in operations if o['role']=='image-range');args=image_op['actual_artifact_argv'];need(args==['/usr/bin/objdump','-s','--start-address='+hex(start),'--stop-address='+hex(stop),release['input_artifacts']['image']['path']],'saved image symbols must bind exact64B command')
 need(texts['image-range'].count('Contents of section .data:')==1,'actual output must identify .data')
 image_bytes=section_bytes(texts['image-range']);need(set(image_bytes)==set(range(start,stop)),'exact64B image window only required');captures[14]=texts['image-range']
 receipt=dict(status='PASS_REMAINING_DESCRIPTOR_ASSOCIATION_AND_ORIGINAL_RECEIPT_JOINS_ONLY',original_release=basefd,original_plan=originalfd,original_operations=original_rows,remaining_release=newfd,remaining_plan=planfd,remaining_completion=completionfd,remaining_operations=newrows,linked_script=linkedfd,Rust_symbol_section_associations={tag:dict(**descriptors[tag],**{'section':headers[descriptors[tag]['section_index']]}) for tag in descriptors},image_bounds=bounds,actual_consumed_artifacts=release['input_artifacts'],actual_C71=base['actual_C71'],actual_CPU_fullcrate_proof=base['actual_CPU_fullcrate_proof'],original14_failure_preserved=True,original_full_DWARF_acceptance=False,no_1_through_13_or_copy_replay=True)
 return original,captures,receipt,rust_bytes

def bridge_target(text,bridge,target,nm):
 b=body(text,bridge);rows=[r for r in nm if r[2]==target and r[1]=='T'];need(len(rows)==1,'unique actual image target required')
 # Actual linked large-code-model bridge materializes absolute address then jumps.
 need(re.search(r'movabs\s+\$0x'+format(rows[0][0],'x')+r',%rax',b) is not None and re.search(r'jmpq?\s+\*%rax',b) is not None,'exact linked target immediate/indirect jump required')

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True);p.add_argument('--release',type=Path,required=True);p.add_argument('--release-sha256',required=True);p.add_argument('--completion',type=Path,required=True);p.add_argument('--completion-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv);assert not a.output.exists()
 plan,captures,completion,rust_bytes=validate_completion(a.plan,a.plan_sha256,a.release,a.release_sha256,a.completion,a.completion_sha256)
 ops={v['index']:v for v in plan['operations']}
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
 assert '__release_tid' in body(captures[2],'process_destroy_thread_release_tid_bridge')
 bridge_target(captures[11],'process_destroy_thread_release_tid_bridge','__release_tid',nms['image'])
 actualbody=body(captures[8],'__release_tid');assert not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',actualbody)
 for kind in nms:
  defined=[r for r in nms[kind] if r[1]=='T' and r[2]=='__find_and_replace_tid'];unresolved=[r for r in nms[kind] if r[1]=='U' and r[2]=='__find_and_replace_tid']
  assert len(defined)==(0 if kind=='process' else 1),(kind,defined)
  assert len(unresolved)==(1 if kind=='process' else 0),(kind,unresolved)
 for kind in ['process','image']:
  assert len([r for r in nms[kind] if r[1]=='T' and r[2]=='process_destroy_thread_replace_tid_bridge'])==1
 assert '__find_and_replace_tid' in body(captures[2],'process_destroy_thread_replace_tid_bridge')
 bridge_target(captures[11],'process_destroy_thread_replace_tid_bridge','__find_and_replace_tid',nms['image'])
 replacebody=body(captures[8],'__find_and_replace_tid');assert not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',replacebody)
 facts={};windows=[]
 for descriptor_tag,logger in [('RELEASE_TID_DEBUG','process_release_tid_log_bridge'),('REPLACE_TID_DEBUG','process_replace_tid_log_bridge')]:
  for kind,rawslot,symbolslot in [('rust',13,9),('image',14,12)]:
   descriptors=[r for r in nms[kind] if descriptor_tag in r[2]];assert len(descriptors)==1;address,_,symbol=descriptors[0];assert address%8==0
   symrows=[line.split() for line in captures[symbolslot].splitlines() if line.split() and line.split()[-1]==symbol];assert len(symrows)==1 and int(symrows[0][2],0)==32
   raw=section_bytes(captures[rawslot]) if kind=='image' else {};data=bytes(raw[address+i] for i in range(32)) if kind=='image' else rust_bytes[descriptor_tag];lineflags=int.from_bytes(data[24:28],'little');assert lineflags>>24==0 and lineflags&0xffffff;assert data[16:24]==bytes(8)
   facts[kind if descriptor_tag=='RELEASE_TID_DEBUG' else kind+'_replace']=dict(input_section_index=completion['Rust_symbol_section_associations'][descriptor_tag]['section_index'] if kind=='rust' else None,address=address,symbol=symbol,bytes_hex=data.hex(),line=lineflags&0xffffff,flags=lineflags>>24,fmt_null=True,size=32,alignment=8)
   if kind=='image':
    artifact=completion['actual_consumed_artifacts']['image']['path']
    for field,offset,extent in [('file',0,256),('func',8,64)]:
     pointer=int.from_bytes(data[offset:offset+8],'little');assert pointer
     windows.append(dict(descriptor=descriptor_tag,field=field,address=pointer,bytes=extent,actual_artifact_argv=['/usr/bin/objdump','-s','--start-address='+hex(pointer),'--stop-address='+hex(pointer+extent),artifact],each_stream_hard_fsize_bytes=1048576,expected='UTF8 C string ending /kernel/rust/process_helpers.rs' if field=='file' else 'exact C string '+logger,status='INPUTS_ONLY_DERIVED_AFTER_ACTUAL14_NOT_EXECUTED'))
 for tag,key in [('RELEASE_TID_DEBUG','rust'),('REPLACE_TID_DEBUG','rust_replace')]:
  imagekey='image' if tag=='RELEASE_TID_DEBUG' else 'image_replace';assert facts[key]['bytes_hex'][48:56]==facts[imagekey]['bytes_hex'][48:56],'object/image same-symbol lineflags must agree'
 result=dict(status='PASS_MECHANICAL_SYMBOL_CONSUMER_DESCRIPTOR_FACTS_ONLY',completed_capture_receipt=completion,plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),descriptor_facts=facts,derived_pointer_windows=windows,pending=['Execute independently released bounded pointer windows and compare declared exact function/truthful Rust file provenance','Independent actual release-body ownership/order/first-match scalar semantic review','Native evidence and positive retirement'],body_disassembly=actualbody,time_account_body_disassembly=timebody,hash_detach_body_disassembly=hashbody,replace_tid_body_disassembly=replacebody,native_acceptance=False)
 a.output.write_text(json.dumps(result,indent=2)+chr(10))
 print('PASS preserved13/failure14 +indexedRustsections +image.data64B; originalDWARFgap OPEN; four pointer windows pending')
if __name__=='__main__':main()
