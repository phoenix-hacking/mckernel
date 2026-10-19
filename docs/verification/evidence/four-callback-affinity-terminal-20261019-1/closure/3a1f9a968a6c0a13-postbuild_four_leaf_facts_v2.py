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

def validate_completion(plan_path,plan_sha,release_path,release_sha,completion_path,completion_sha):
 plan,planfd=bound_json(dict(path=str(plan_path),sha256=plan_sha),16*1024**2)
 release,releasefd=bound_json(dict(path=str(release_path),sha256=release_sha),16*1024**2)
 need(release.get('status')=='PASS_EXACT_ORDINARY_POSTBUILD_READONLY_RELEASE','exact independently released observation required')
 need(release.get('commands')==dict(path=str(plan_path),sha256=plan_sha),'declared command plan release binding differs')
 review,reviewfd=bound_json(release['execution_review'])
 payload={k:v for k,v in release.items() if k!='execution_review'}
 need(review.get('decision')=='PASS_EXACT_ORDINARY_POSTBUILD_READONLY' and review.get('implementation_ownership') is False and review.get('reviewer')!=release.get('author') and bool(review.get('reviewer')),'independent observation review required')
 need(review.get('reviewed_release_payload_sha256')==hashlib.sha256(canonical(payload)).hexdigest(),'exact observation payload review differs')
 sources=[]
 for key in ('dispatcher','descriptor_facts_producer'):
  ref=release[key];need(isinstance(ref.get('sha256'),str) and re.fullmatch('[0-9a-f]{64}',ref['sha256']) is not None,'source hash required');raw,row=read_fd(ref['path'],4*1024**2,ref['sha256']);sources.append(row)
 need(Path(release['descriptor_facts_producer']['path'])==Path(__file__).resolve(),'exact v2 facts source required')
 completion,completionfd=bound_json(dict(path=str(completion_path),sha256=completion_sha),16*1024**2)
 need(completion.get('release_sha256')==release_sha,'actual completed observer receipt release differs')
 completed=completion.get('results',[]);need(isinstance(completed,list),'completed result rows required')
 operations=plan['operations'];need(len(operations)==14 and len({o['index'] for o in operations})==14,'exact fourteen DECLARED operation receipts required')
 need({o['index'] for o in operations}==set(range(1,15)),'declared fourteen indices differ')
 contracts=release['operation_completion_contracts'];need(set(contracts)=={str(i) for i in range(1,15)},'per-operation reviewed completion contracts required')
 captures={};receipts=[]
 for op in operations:
  i=op['index'];contract=contracts[str(i)];label=contract.get('receipt_stage','command-'+str(i))
  need(type(contract.get('returncode')) is int and contract.get('classification') in ('MECHANICAL_INPUT','PRESERVED_FAILURE_ONLY'),'explicit expected result classification required')
  if contract['classification']=='MECHANICAL_INPUT':need(contract['returncode']==0 and contract.get('stderr_policy')=='empty','mechanical input must complete cleanly')
  else:
   need(contract.get('acceptance_credit') is False and isinstance(contract.get('original_failure_reference'),dict),'original failure must remain unaccepted')
   ref=contract['original_failure_reference'];read_fd(ref['path'],4*1024**2,ref['sha256'])
  need(contract.get('stderr_policy') in ('empty','bounded'),'explicit stderr contract required')
  if i in REQUIRED_FACT_INDICES:need(contract['classification']=='MECHANICAL_INPUT','required mechanical capture cannot use failed/alternative output')
  statusraw,statusfd=read_fd(op['status_path'],1048576);status=json.loads(statusraw)
  commandraw,commandfd=read_fd(op['status_path']+'.command.json',1048576);command=json.loads(commandraw)
  childraw,childfd=read_fd(op['status_path']+'.child.json',1048576);child=json.loads(childraw)
  need(sum(row==status for row in completed)==1,'exact status must appear once in actual completed observer receipt')
  need(status.get('argv')==op['argv'] and command.get('argv')==op['argv'],'exact declared argv differs')
  need(status.get('stage')==command.get('stage')==label and command.get('reservation_bytes')==op['both_stream_reservation_bytes'],'operation label/reservation differs')
  need(command.get('release_sha256')==contract.get('receipt_execution_release_sha256',release_sha),'actual command receipt release provenance differs')
  need(status.get('direct_child_joined') is True and status.get('observer_error') is None and type(status.get('returncode')) is int and status.get('returncode')==contract['returncode'],'expected returncode/direct join/observer status differs')
  need(type(child.get('pid')) is int and child['pid']>0 and child.get('proc_queries') is False and isinstance(child.get('monotonic_start'),(int,float)),'actual direct child identity receipt missing')
  streamrows={}
  for stream in ('stdout','stderr'):
   need(isinstance(status.get(stream+'_sha256'),str) and re.fullmatch('[0-9a-f]{64}',status[stream+'_sha256']) is not None,'completed stream hash required')
   raw,row=read_fd(op[stream+'_path'],op['each_stream_hard_fsize_bytes'],status.get(stream+'_sha256'))
   need(row['size']==status.get(stream+'_bytes'),'stream length receipt differs')
   if stream=='stderr' and contract.get('stderr_policy')=='empty':need(row['size']==0,'clean operation stderr nonempty')
   streamrows[stream]=row
   if stream=='stdout':captures[i]=raw.decode()
  receipts.append(dict(index=i,expected=contract,status=statusfd,command=commandfd,child=childfd,streams=streamrows,direct_child_joined=True,returncode=status['returncode']))
 return plan,captures,dict(status='PASS_ALL14_DECLARED_COMPLETION_CONTRACTS_FD_AND_HASH_JOINS_ONLY',plan=planfd,release=releasefd,review=reviewfd,completion=completionfd,sources=sources,operations=receipts,original_failure_contract=plan.get('old_syscall_dwarf13',plan.get('old_syscall_DWARF13')),original_full_DWARF_acceptance=False,not_all_original14_pass=True)

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True);p.add_argument('--release',type=Path,required=True);p.add_argument('--release-sha256',required=True);p.add_argument('--completion',type=Path,required=True);p.add_argument('--completion-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv);assert not a.output.exists()
 plan,captures,completion=validate_completion(a.plan,a.plan_sha256,a.release,a.release_sha256,a.completion,a.completion_sha256)
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
 facts={};windows=[]
 for descriptor_tag,logger in [('RELEASE_TID_DEBUG','process_release_tid_log_bridge'),('REPLACE_TID_DEBUG','process_replace_tid_log_bridge')]:
  for kind,rawslot,symbolslot in [('rust',13,9),('image',14,12)]:
   descriptors=[r for r in nms[kind] if descriptor_tag in r[2]];assert len(descriptors)==1;address,_,symbol=descriptors[0];assert address%8==0
   symrows=[line.split() for line in captures[symbolslot].splitlines() if line.split() and line.split()[-1]==symbol];assert len(symrows)==1 and int(symrows[0][2],0)==32
   raw=section_bytes(captures[rawslot]);data=bytes(raw[address+i] for i in range(32));lineflags=int.from_bytes(data[24:28],'little');assert lineflags>>24==0 and lineflags&0xffffff;assert data[16:24]==bytes(8)
   facts[kind if descriptor_tag=='RELEASE_TID_DEBUG' else kind+'_replace']=dict(address=address,symbol=symbol,bytes_hex=data.hex(),line=lineflags&0xffffff,flags=lineflags>>24,fmt_null=True,size=32,alignment=8)
   if kind=='image':
    artifact=plan['paths']['image']
    for field,offset,extent in [('file',0,256),('func',8,64)]:
     pointer=int.from_bytes(data[offset:offset+8],'little');assert pointer
     windows.append(dict(descriptor=descriptor_tag,field=field,address=pointer,bytes=extent,actual_artifact_argv=['/usr/bin/objdump','-s','--start-address='+hex(pointer),'--stop-address='+hex(pointer+extent),artifact],each_stream_hard_fsize_bytes=1048576,expected='UTF8 C string ending /kernel/rust/process_helpers.rs' if field=='file' else 'exact C string '+logger,status='INPUTS_ONLY_DERIVED_AFTER_ACTUAL14_NOT_EXECUTED'))
 result=dict(status='PASS_MECHANICAL_SYMBOL_CONSUMER_DESCRIPTOR_FACTS_ONLY',completed_capture_receipt=completion,plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),descriptor_facts=facts,derived_pointer_windows=windows,pending=['Execute independently released bounded pointer windows and compare declared exact function/truthful Rust file provenance','Independent actual release-body ownership/order/first-match scalar semantic review','Native evidence and positive retirement'],body_disassembly=actualbody,time_account_body_disassembly=timebody,hash_detach_body_disassembly=hashbody,replace_tid_body_disassembly=replacebody,native_acceptance=False)
 a.output.write_text(json.dumps(result,indent=2)+chr(10))
 print('PASS declared14completion/FD/hash and mechanical facts only; originalDWARFgap OPEN; four pointer windows pending')
if __name__=='__main__':main()
