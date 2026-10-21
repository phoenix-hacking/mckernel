#!/usr/bin/env python3
"""One scoped eight-event physical readback, never cleanup replay.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse,ast,base64,hashlib,json,os,resource,stat,sys,types
from pathlib import Path
D=Path(__file__).resolve().parent
RECORDS=D.parent.parent/'records'
CAP=1<<20
FIELDS=('device','inode','mode','nlink','uid','gid','size','mtime_ns','ctime_ns')
CHECKS=('strict_process_report_validated','required_original_births_clear','no_publishers','container_absent','permanent_root_mutex_reacquired','transaction_mutex_reacquired','nine_regulars_preserved','active_common_shared_absent','current_mount_uuid_valid','floors_and_growth_valid')
def need(ok,why):
 if not ok:raise RuntimeError(why)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
def checked(r,cap=32<<20):
 need(isinstance(r,dict) and r.get('path') and r.get('sha256') and type(r.get('bytes')) is int,'unresolved exact input')
 fd=os.open(r['path'],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_size<=cap,'bounded regular exact input');parts=[];count=0
  while True:
   b=os.read(fd,65536)
   if not b:break
   count+=len(b);need(count<=cap,'input cap');parts.append(b)
  raw=b''.join(parts);after=os.fstat(fd);named=os.lstat(r['path'])
  need(full9(before)==full9(after)==full9(named) and len(raw)==r['bytes'] and sha(raw)==r['sha256'],'input full9/hash drift');return raw
 finally:os.close(fd)
def full9(s):return dict(device=s.st_dev,inode=s.st_ino,mode=s.st_mode,nlink=s.st_nlink,uid=s.st_uid,gid=s.st_gid,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def descriptor(path,raw):return dict(path=str(path),sha256=sha(raw),bytes=len(raw))
def load_engine(row):
 raw=checked(row);m=types.ModuleType('_exact_eight_event_readback_engine');m.__file__=row['path'];exec(compile(raw,row['path'],'exec'),m.__dict__);return m

def bind_readback(m,r):
 # Existing a4e postjoin pattern: configure validates now-absent active records.
 # Bind only hash-authenticated original release DATA, never call configure/run.
 obs=r['observation'];target=obs['target'];selected={x['path']:x for x in obs['selected_files']}
 m.RELEASE=r;m.DEVICE=obs['root']['device'];m.BOOT_ID=obs['boot_id']
 m.ROOT_LOCK_BINDING=obs['root_lock'];m.EXPECTED_CONTAINER=obs['container_inspect'];m.EXPECTED_EXIT=target['exit_code']
 m.CONTAINER=target['container_id'];m.CONTAINER_NAME=target['container_name'];m.OWNER_NONCE=target['owner_nonce'];m.OWNER_PID=target['owner_pid'];m.OWNER_START=target['owner_starttime'];m.WAITER_PIDS=tuple(x['pid'] for x in obs['client_ledger'])
 m.RECORDS={Path(x['path']):(x['sha256'],x['inode'],x['size']) for x in obs['retained_exclusions']};m.PROTECTED=obs['selected_files']
 terminal=selected[str(m.TERMINAL)];m.TERMINAL_SHA,m.TERMINAL_INODE,m.TERMINAL_SIZE=terminal['sha256'],terminal['inode'],terminal['size']
 m.DIRS={path:(obs['inventories'][str(path)][0]['device'],obs['inventories'][str(path)][0]['inode'],obs['inventories'][str(path)][0]['nlink']) for path in (m.OUTPUT,m.EVIDENCE)}
 need(r['transaction_paths']==m.transaction_paths(),'same original transaction paths');m.validate_mount()
def preserved_snapshot(row,export=False):
 path=Path(row['path']);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=full9(os.fstat(fd));need(stat.S_ISREG(before['mode']) and before==row['full9']==full9(path.lstat()),'preserved regular/full9 differs');parts=[];count=0
  while True:
   b=os.read(fd,65536)
   if not b:break
   count+=len(b);need(count<=CAP,'preserved input cap');parts.append(b)
  raw=b''.join(parts);after=full9(os.fstat(fd));named=full9(path.lstat());need(before==after==named and sha(raw)==row['sha256'],'preserved full9/SHA drift')
  result=dict(path=str(path),sha256=sha(raw),bytes=len(raw),full9=before,before=before,fd_after=after,named_after=named)
  if export:result['raw_base64']=base64.b64encode(raw).decode()
  return result,raw
 finally:os.close(fd)
def actor():
 f=Path('/proc/self/stat').read_bytes().rsplit(b') ',1)[1].split();return dict(pid=os.getpid(),starttime=f[19].decode(),parent=int(f[1]),pgrp=int(f[2]),uid=os.getuid(),gid=os.getgid())
def main():
 p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--release',required=True);p.add_argument('--release-sha256',required=True);a=p.parse_args()
 need(os.getuid()==os.geteuid()==0 and resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1),'released root readonly critical profile required')
 raw=Path(a.release).read_bytes();need(sha(raw)==a.release_sha256,'exact physical release');r=json.loads(raw);need(r.get('schema')=='mckernel.current-insert-clear-image.eight-event-readonly-physical-release.v1' and r.get('status')=='PASS_EXECUTION_RELEASE','separate scoped physical release required')
 need(r.get('execution_count')==1 and r.get('fetched_source_verified') is True,'one published current source invocation');need(r['source']['path']==str(Path(__file__).resolve()) and checked(r['source'])==Path(__file__).read_bytes(),'source identity')
 review=json.loads(checked(r['execution_review']));payload={k:v for k,v in r.items() if k!='execution_review'};need(review.get('decision')=='PASS_EXECUTION' and review.get('implementation_ownership') is False and review.get('reviewer') and review['reviewer']!=r.get('author') and review.get('reviewed_release_payload_sha256')==sha(canonical(payload)),'exact independent scoped execution review')
 cfg=json.loads(checked(r['bindings']));profile=json.loads(checked(cfg['retirement_profile']));acceptance=json.loads(checked(cfg['durable_retirement_acceptance']));need(acceptance.get('reviewer') and acceptance.get('implementation_ownership') is False,'genuine actual retirement acceptance required')
 failed=json.loads(checked(cfg['original_failed_cleanup_status']));need(failed['status']=='FAIL_PRESERVED_STOPPED' and failed['returncode']==-9 and failed['direct_child_joined'] is True and failed['process_group_absent'] is True and failed['streams_closed'] is True and failed['cpu7_released'] is True,'original failure closure exact shape')
 exported=json.loads(checked(cfg['retirement_export']));need(exported['status']=='PASS_READ_ONLY_TWO_RECEIPTS','genuine two receipt export');receipts={}
 for role in ('prepared','complete'):
  row=exported[role];b=base64.b64decode(row['raw_base64']);need(row['status']=='PASS_EXACT_ROOT_RECEIPT_READ_ONLY' and row['stable_full9'] is True and row['named_before']==row['fd_before']==row['fd_after']==row['named_after'] and sha(b)==row['sha256'],'actual root receipt export');need(checked(cfg['retirement_'+role])==b,'ordinary exact original receipt copy');receipts[role]=json.loads(b)
 complete=receipts['complete'];need(exported['complete']['sha256']=='2dc61852874e32c0c3bd706e2175e150abcbb35a4cbdb63a70ce3a8cd7be9067' and complete['status']=='COMPLETE_IDLE_HOLDER_RETIREMENT_ONLY' and complete['prepared_sha256']==exported['prepared']['sha256'] and complete['target']==receipts['prepared']['target'] and complete['target']['pid']==2761636 and complete['target']['starttime']=='40670236' and complete['signal_count']==1 and complete['pidfd_exit_ready'] is True and complete['protected_inputs_unchanged'] is True and complete['quarantine_mutex_preserved'] is True and complete['replacement_root_lock']==[27,4],'current exact durable retirement')
 original=json.loads(checked(cfg['cleanup_release']));need(original['status']=='PASS_EXECUTION_RELEASE' and original['script_sha256']==cfg['engine']['sha256'],'honest original release/source binding');need(cfg['cleanup_release']['sha256']=='e95ee126d683bcb548b48fc70e6995d32d117e7e225b3142e4a22015014e034a' and cfg['engine']['sha256']=='86654275eced623bb15ce289ca6555264b2820b56336e629fe084cb9aed96ce0','immutable current release and engine')
 m=load_engine(cfg['engine']);need(original['publisher_contract']==m.PUBLISHER_CONTRACT,'same publisher contract')
 proc_raw=checked(cfg['process_source']);need(cfg['process_source']['sha256']=='b8c7d0f6ff3dc7303ca2063575c1affe0b63a4b283b0cc3223c4f3a11f93d80a','accepted current repaired PROC source');tree=ast.parse(proc_raw);proc=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROC_CODE' for t in n.targets)))
 # Only accepted PROC literal changes; strict current validator/other engine bodies stay original.
 m.PROC_CODE=proc;reuse=json.loads(checked(cfg['process_reuse_review']));need(reuse.get('reviewer'),'genuine current PROC reuse authority')
 out=Path(cfg['output_directory']);need(out.parent==RECORDS and out.name=='actual-eight-event-physical-reconciliation-1' and not os.path.lexists(out),'fresh finite root evidence directory');out.mkdir(mode=0o700);exports={};command_rows=[];process_refs=[];ps_refs=[]
 def store(name,b):
  path=out/name;fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  try:
   view=memoryview(b)
   while view:
    n=os.write(fd,view);need(n>0,'short evidence write');view=view[n:]
   os.fsync(fd)
  finally:os.close(fd)
  result=descriptor(path,b);exports[str(path)]=dict(result,raw_base64=base64.b64encode(b).decode());return result
 old_command=m.root_command
 def captured(args,limit):
  is_proc=(len(args)==8 and args[:4]==['/usr/bin/python3','-I','-B','-c'] and args[4]==proc)
  is_ps=args==['/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-a','--no-trunc','--format','{{json .}}']
  is_mount=args==['/usr/bin/findmnt','-J','-T',str(m.ROOT),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN']
  need(is_proc or is_ps or is_mount,'finite readonly commands only');b=old_command(args,limit);ref=store('command-%02d.stdout'%len(command_rows),b);command_rows.append(dict(argv=args if not is_proc else args[:4]+['EXACT_ACCEPTED_PROC_CODE',*args[5:]],stdout=ref))
  if is_proc:process_refs.append(ref)
  if is_ps:ps_refs.append(ref)
  return b
 m.root_command=captured;bind_readback(m,original);need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==profile['boot_id']==m.BOOT_ID,'exact current boot')
 need(len(profile['preserved_regulars'])==9 and profile['absent_paths']==[str(m.ATTEMPT),str(m.SHARED)],'exact9/active2 profile')
 tx=None
 try:
  tx=m.Transaction();tx.lock(False);need(tx.mfd is not None and not tx.mutation_started,'existing readonly transaction mutex required');need((os.fstat(tx.rfd).st_dev,os.fstat(tx.rfd).st_ino)==(27,4) and (os.fstat(tx.mfd).st_dev,os.fstat(tx.mfd).st_ino)==(1828,116329),'exact held lock FDs')
  first=[preserved_snapshot(row,export=i in (1,2))[0] for i,row in enumerate(profile['preserved_regulars'])]
  for path in profile['absent_paths']:need(not os.path.lexists(path),'released active name reappeared')
  need(not m.census(),'current exact CID must absent');plan=tx.load_plan();rows,phases=tx.state(plan);need(len(rows)==8 and phases==['after_release','after_release'] and rows[-1]['event']=='after_release' and rows[-1]['index']==1,'exact preserved eight-event state')
  # state() is readonly: never run(), append(), recover(), rename or remove.
  need(not m.census(),'CID reappeared');need(process_refs and ps_refs,'actual strict process and container evidence')
  process=json.loads(checked(process_refs[-1]));need(process['publishers']==[],'no publisher');retired=complete['target'];need(all(not any(row[0]==retired['pid'] and row[2]==retired['starttime'] for row in snap) for snap in process['snapshots']),'retired original birth reappeared')
  final=[preserved_snapshot(row,export=i in (1,2))[0] for i,row in enumerate(profile['preserved_regulars'])];need(final==first,'nine originals changed');need(all(not os.path.lexists(path) for path in profile['absent_paths']) and not os.path.lexists(m.LEASE),'active ownership/lease reappeared');tx.pinned();tx.preserved();need(not tx.mutation_started,'readonly latch changed')
  reserve=16<<20;host=os.statvfs('/home/holden/mckernel');scratch=os.statvfs(m.ROOT);hostfree=host.f_bavail*host.f_frsize;scratchfree=scratch.f_bavail*scratch.f_frsize;need(hostfree>=(16<<30)+reserve and scratchfree>=(12<<30)+reserve,'floors plus metadata reserve')
  rootproof=store('root-mutex.json',canonical(dict(identity=full9(os.fstat(tx.rfd)),permanent=[27,4],reacquired=True,actor=actor(),owned_close_in_finally=True)))
  mutexproof=store('transaction-mutex.json',canonical(dict(identity=full9(os.fstat(tx.mfd)),expected=[1828,116329],reacquired=True,readonly_open=True,owned_close_in_finally=True)))
  containerproof=store('container-absence.json',canonical(dict(container_id=m.CONTAINER,container_name=m.CONTAINER_NAME,owner_nonce=m.OWNER_NONCE,absent=True,qualified_census_calls=2,raw_ps=ps_refs)))
  target={k:original['observation']['target'][k] for k in ('container_id','container_name','owner_nonce','owner_pid','owner_starttime')};target.update(lease_path=str(m.LEASE),common_exclusion_path=str(m.ATTEMPT))
  result=dict(schema='mckernel.current-insert-clear-image.postmutation-eight-event-readonly-reconciliation-result.v1',status='PASS_ACTUAL_POSTMUTATION_EIGHT_EVENT_READONLY_RECONCILIATION_ONLY',scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',boot_id=m.BOOT_ID,filesystem_uuid=m.UUID,target=target,journal=dict(events=8,final_event='after_release',final_index=1,plan_canonical_sha256=m.digest(m.canonical(plan)),final_chain_hash=rows[-1]['hash'],phases=phases),preservation=dict(nine_rows_equal=True,objects=final),active_records_absent=profile['absent_paths'],plan=first[1],journal_descriptor=first[2],plan_raw_base64=first[1]['raw_base64'],journal_raw_base64=first[2]['raw_base64'],parsed_plan=plan,parsed_journal=rows,process_report=process_refs[-1],container_absence=containerproof,root_mutex=rootproof,transaction_mutex=mutexproof,original_failed_cleanup_status=cfg['original_failed_cleanup_status'],durable_retirement_acceptance=cfg['durable_retirement_acceptance'],retirement_prepared=cfg['retirement_prepared'],retirement_complete=cfg['retirement_complete'],root_original_retirement_receipt_export=cfg['retirement_export'],source=r['source'],physical_execution_release=descriptor(a.release,raw),configuration_release=cfg['cleanup_release'],process_source=cfg['process_source'],process_reuse_review=cfg['process_reuse_review'],checks={k:True for k in CHECKS},resource_headroom=dict(host_free_bytes=hostfree,scratch_free_bytes=scratchfree,reserve_bytes=reserve),root_actor=actor(),mutation=False,signals_sent=False,container_removed=False,ownership_records_removed=False,normal_cleanup_pass=False,normal_journal_complete=False,quarantine_retained=True,physical_acceptance=None,native_acceptance=False,application_acceptance=False,C_retirement_credit=False,command_evidence=command_rows,evidence_raw_exports=exports)
  store('result.json',canonical(result));pfd=os.open(out,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
  try:os.fsync(pfd)
  finally:os.close(pfd)
  print(json.dumps(result,sort_keys=True,allow_nan=False))
 finally:
  if tx is not None:tx.close()
if __name__=='__main__':main()
