"""Functional OS only; no security testing. READONLY producer; no cleanup entry calls."""
import argparse,ast,hashlib,importlib.util,json,os,stat,subprocess,fcntl,signal
from contextlib import contextmanager
from pathlib import Path
PROFILE=Path(__file__).parent/'EXACT-OWNER1043716-DEAD-CALLER-READONLY-OBSERVATION-PROFILE.json'
PROFILE_SHA='c5d3283eedee466a6115165e11ac034d852e4db86ca8d7455547eb1268f748e5'
REQUIRED=frozenset(('mount','root','boot_id','root_lock','request','target','container_inspect','retained_exclusions','request_lease_absent','inventories','candidate_root','candidate_commit','candidate_tree','selected_files','backup_root','namespace_binding','namespace_ancestry','client_ledger','ownership_case','shared_record_already_absent','normal_owner_join'))
def need(value,message):
 if not value:raise ValueError(message)
def pinned(row):
 p=Path(row['path']);raw=p.read_bytes();need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'pinnedbytes:'+str(p));return raw
def bootstrap():
 raw=PROFILE.read_bytes();need(hashlib.sha256(raw).hexdigest()==PROFILE_SHA,'profilepin');p=json.loads(raw)
 for key in ('cleanup','protocol','contract','recipe','owner_receipt','ready','join','process','caller_entry'):pinned(p[key])
 spec=importlib.util.spec_from_file_location('existing5119_readonlyhelpers',p['cleanup']['path']);e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
 return p,e
def publish(out,name,raw):
 p=out/name;fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  view=memoryview(raw)
  while view:view=view[os.write(fd,view):]
  os.fsync(fd)
 finally:os.close(fd)
 fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
 return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
class ObserverDeadlineExpired(RuntimeError):
 pass

@contextmanager
def own_observer_deadline(seconds=240):
 need(seconds==240,'exact240seconddeadline')
 previous_handler=signal.getsignal(signal.SIGALRM)
 previous_timer=signal.getitimer(signal.ITIMER_REAL)
 # Refuse an existing timer; do not steal or reset another owner's deadline.
 need(previous_timer==(0.0,0.0),'existingalarmrefused')
 def expired(signum,frame):
  raise ObserverDeadlineExpired('readonly observer overall240s deadline expired')
 signal.signal(signal.SIGALRM,expired)
 try:
  signal.setitimer(signal.ITIMER_REAL,seconds)
  yield
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  signal.signal(signal.SIGALRM,previous_handler)

def query(p,out,label):
 need(label in ('inspect','findmnt'),'queryallowlist');argv=p['query_allowlist'][label];status={};deadline=None
 paths={stream:out/(label+'.'+stream) for stream in ('stdout','stderr')}
 # File-backed capture preserves bytes even when our own SIGALRM interrupts
 # subprocess.run. Its BaseException path kills/reaps only this query child.
 streams={}
 try:
  for stream,path in paths.items():
   fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
   streams[stream]=os.fdopen(fd,'wb',buffering=0)
  try:
   result=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=streams['stdout'],stderr=streams['stderr'],timeout=p['query_timeout_seconds'],check=False)
   status={'returncode':result.returncode}
  except subprocess.TimeoutExpired:status={'error':'TimeoutExpired'}
  except ObserverDeadlineExpired as exc:
   status={'error':'ObserverDeadlineExpired'};deadline=exc
  except OSError as exc:status={'error':type(exc).__name__,'errno':exc.errno}
 finally:
  try:
   for stream in streams.values():os.fsync(stream.fileno())
  finally:
   for stream in streams.values():stream.close()
 stdout=paths['stdout'].read_bytes();stderr=paths['stderr'].read_bytes()
 refs={stream:dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for stream,path in paths.items()}
 status.update(argv=argv,timeout=p['query_timeout_seconds'],captures=refs);publish(out,label+'.status.json',(json.dumps(status,sort_keys=True)+'\n').encode())
 if deadline is not None:raise deadline
 need(status.get('returncode')==0 and stderr==b'' and len(stdout)<=p['query_caps'][label],'readonlyqueryrefused:'+label)
 return stdout

def dead_caller_check(e,p,ready):
 need(p['dead_caller_new_ofd']==e.DEAD_CALLER_FROZEN,'exactdeadcallerprofile')
 e.DEAD_CALLER_BINDING=e.validate_dead_caller_binding(dict(cleanup_mode=e.DEAD_CALLER_MODE,inherited_root_lock=None,dead_caller_new_ofd=p['dead_caller_new_ofd']))
 need(ready['holder']['pid']==1043200 and ready['holder']['starttime']=='80013658','actualdeadcallerbirth')
 e.dead_caller_absent()
 return True

def acquire_readonly_custody(e,p):
 # All source/runtime authentication precedes lock acquisition. Lock only: no
 # cleanup/Transaction/configure entry, Docker mutation or ownership mutation.
 e.DEAD_CALLER_BINDING=e.validate_dead_caller_binding(dict(cleanup_mode=e.DEAD_CALLER_MODE,inherited_root_lock=None,dead_caller_new_ofd=p['dead_caller_new_ofd']))
 ready=e.parse(pinned(p['ready']));dead_caller_check(e,p,ready)
 before=e.observe_identity(e.ROOT_LOCK)
 need(before['device']==27 and before['inode']==4 and before['uid']==0 and before['gid']==0 and before['mode']=='0o644' and before['nlink']==1 and before['size']==0,'permanent27:4namedidentity')
 fd=os.open(e.ROOT_LOCK,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  need(e.observe_identity(e.ROOT_LOCK)==before and e.identity(os.fstat(fd))==(27,4),'newOFDpermanentidentity')
  e.dead_caller_absent()
  return fd
 except BaseException:
  os.close(fd);raise

def normal_entry_references(p):
 # The normal owner proof consumes a separate exact chain in addition to the
 # readonly-mode runtime paths. Follow only these actual authenticated edges.
 entry=json.loads(pinned(p['caller_entry']))
 grant_ref=entry['root_execution_grant'];grant=json.loads(pinned(grant_ref))
 payload_ref=grant['payload'];payload=json.loads(pinned(payload_ref))
 rows=[grant_ref,grant['independent_review'],payload_ref,payload['fetched_publication']]
 seen={}
 for row in rows:
  need(isinstance(row,dict) and set(row)=={'path','bytes','sha256'},'normalentryreferenceshape')
  need(row['path'] not in seen or seen[row['path']]==row,'normalentryconflictingreference')
  pinned(row);seen[row['path']]=row
 return list(seen.values())

def produce(p,e,queryfn):
 ready=e.parse(pinned(p['ready']));receipt=e.parse(pinned(p['owner_receipt']));joined=e.parse(pinned(p['join']));process=e.parse(pinned(p['process']));c=e.parse(pinned(p['contract']));request=e.parse(pinned(c['static']['request']));dead_caller_check(e,p,ready)
 need(ready['owner_join']==joined and ready['owner_receipt']==p['owner_receipt'] and joined['pid']==1043716 and joined['starttime']=='80020161' and joined['returncode']==1 and all(joined[k] is True for k in ('direct_child_joined','group_absent','closed_streams')) and joined['error'] is None and joined['retirement_error'] is None,'joinedactualowner')
 need(request['candidate_sha']=='eb3ce544eb1f479a56933a5c7fa8300ab6dfe533' and p['candidate_tree']=='a2da2013134a682d8c22c1843eda39f85e96176a','exactrequestBASEgittree');target=p['target'];need(receipt['status']=='FAIL' and all(receipt[k]==target[k] for k in ('container_id','container_name','owner_nonce','exit_code')) and process['pid']==target['owner_pid'] and process['starttime']==target['owner_starttime'],'actualtarget')
 raw=queryfn('inspect');items=e.parse(raw);need(isinstance(items,list) and len(items)==1,'exactoneinspect');item=items[0];need(item['Id']==target['container_id'] and item['Name']=='/'+target['container_name'] and item['Image']==target['image_id'] and item['Config']['Labels']['mckernel.owner']==target['owner_nonce'],'inspecttarget')
 expected={'Status':'exited','Running':False,'Paused':False,'Restarting':False,'OOMKilled':False,'Dead':False,'Pid':0,'ExitCode':target['exit_code'],'Error':''};need(all(e.canonical(item['State'].get(k))==e.canonical(v) for k,v in expected.items()),'terminalstate');e.image_owner_receipt_binding(receipt,item,p['owner_receipt']['sha256'])
 mounts=e.parse(queryfn('findmnt'))['filesystems'];need(len(mounts)==1,'onescratchmount');mount=mounts[0];need(mount['target']==str(e.ROOT) and mount['uuid']==e.UUID and mount['fstype']=='ext4' and {'rw','nodev','nosuid'}<=set(mount['options'].split(',')),'scratchmount')
 need(not os.path.lexists(e.LEASE),'requestleaseabsent');ancestry=e.namespace_ancestry();need(ancestry==e.NAMESPACE_ANCESTRY,'namespaceancestry')
 statuses=sorted((e.EVIDENCE/'attempt').glob('command-*/status.json'));need(len(statuses)==p['expected_client_count'],'complete7clientledger');ledger=[]
 for path in statuses:
  raw=e.read_bounded(path);value=e.parse(raw);need(type(value['pid']) is int and value['pid']>0 and value['state']=='exited' and type(value['exit_code']) is int and value['exit_code']>=0 and not value.get('client_retirement_unproven'),'positiveclientstatus');ledger.append(dict(pid=value['pid'],status_path=str(path),status_sha256=e.digest(raw)))
 need(len({v['pid'] for v in ledger})==len(ledger),'uniqueclients');e.WAITER_PIDS=tuple(row['pid'] for row in ledger)
 identities=[e.observe_identity(v) for v in (e.ATTEMPT,e.SHARED)];obs=dict(mount=mount,root=e.observe_identity(e.ROOT),boot_id=ready['holder']['boot_id'],root_lock=e.observe_identity(e.ROOT_LOCK),request=e.observe_identity(e.REQUEST),target=target,container_inspect=item,retained_exclusions=identities,request_lease_absent=True,inventories={str(path):e.metadata_inventory(path) for path in (e.OUTPUT,e.EVIDENCE)},candidate_root=e.observe_identity(Path(request['source_root'])),candidate_commit=request['candidate_sha'],candidate_tree=p['candidate_tree'],selected_files=[],backup_root=e.observe_identity(Path(request['backup_root'])),namespace_binding=e.NAMESPACE_BINDING,namespace_ancestry=ancestry,client_ledger=ledger,ownership_case='FAIL_COMMON_AND_SHARED',shared_record_already_absent=False,normal_owner_join=e.observe_identity(Path(p['join']['path'])))
 e.ownership_case_binding(receipt,obs,identities)
 for row in identities:e.image_record_binding(Path(row['path']),row,e.parse(e.read_bounded(Path(row['path']))),request,target,obs['boot_id'])
 protocol=e.current230_contract();needed={str(e.REQUEST),str(e.TERMINAL),p['join']['path'],str(e.EVIDENCE/'attempt/container.log'),str(e.OUTPUT/'evidence/receipt.json')};needed.update(row['status_path'] for row in ledger)
 joins={'driver_path':'driver_sha256','provenance_path':'provenance_sha256','host_owner_path':'host_owner_sha256','source_manifest':'source_manifest_sha256','toolchain_manifest':'toolchain_manifest_sha256'}
 if request.get('gitlink_manifest') is not None:joins['gitlink_manifest']='gitlink_manifest_sha256'
 needed.update(request[k] for k in joins);needed.update(protocol.required_runtime_references(request,receipt));needed.update(row['path'] for row in normal_entry_references(p));needed.update(str(Path(c['caller_capture_root'])/name) for name in ('owner.PROCESS.json','ACTUAL-OWNER-ENTRY.json','ROOT-NORMAL-CLEANUP-COMPLETION-READY.json','owner.stdout','owner.stderr'));static=protocol.required_static_references();needed.update(row['path'] for row in static);needed.update(row['path'] for row in p['dead_caller_new_ofd']['references'].values());obs['selected_files']=[e.observe_identity(Path(path)) for path in sorted(needed)];selected={row['path']:row for row in obs['selected_files']}
 for row in static:need(selected[row['path']]['sha256']==row['sha256'] and selected[row['path']]['size']==row['bytes'],'selectedstaticpin')
 for key,hkey in joins.items():need(selected[request[key]]['sha256']==request[hkey],'requestsourcehash')
 protocol.normal_owner_join_binding(receipt,joined,target,item,p['owner_receipt']['sha256'],request,obs,selected);protocol.typed_source_binding(request,obs,selected)
 need(set(obs)==REQUIRED,'exactproduction21keys');need(e.metadata_inventory(e.OUTPUT)==obs['inventories'][str(e.OUTPUT)] and e.metadata_inventory(e.EVIDENCE)==obs['inventories'][str(e.EVIDENCE)],'inventoryraced')
 for row in obs['selected_files']:need(e.observe_identity(Path(row['path']))==row,'selectedraced')
 for row in identities:need(e.observe_identity(Path(row['path']))==row,'recordraced')
 dead_caller_check(e,p,ready);need(not os.path.lexists(e.LEASE) and e.namespace_ancestry()==ancestry,'leaseornamespaceraced');return obs

def readable_evidence(raw):
 need(len(raw)<=20<<20,'readableevidencebound')
 return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),raw_utf8=raw.decode('utf-8','strict'))

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--execute-readonly',action='store_true');args=parser.parse_args();need(args.execute_readonly and os.geteuid()==0,'explicitrootreadonlyrequired')
 result=None;readable={}
 try:
  with own_observer_deadline(240):
   p,e=bootstrap();need(p['overall_deadline_seconds']==240,'profile240seconddeadline');out=Path(p['capture_directory']);out.mkdir(mode=0o700);fd=None
   try:
    fd=acquire_readonly_custody(e,p)
    obs=produce(p,e,lambda label:query(p,out,label))
    observation_raw=e.canonical(obs);publish(out,'OBSERVATION.json',observation_raw)
    readable['observation']=readable_evidence(observation_raw)
    result=dict(status='PASS_READONLY_OBSERVATION_ONLY_NOT_CLEANUP_RELEASE',observation=str(out/'OBSERVATION.json'),keys=len(obs),queries=2,cleanup_actions=0)
   finally:
    # Root originals remain0600/root0700. UID1000 receives exact lossless JSON
    # through its existing outer full-EOF stdout capture; no ownership changes.
    try:
     proc_raw=e.canonical(e.DEAD_CALLER_OBSERVATIONS)
     publish(out,'dead-caller-proc-evidence.json',proc_raw)
     readable['process_evidence']=readable_evidence(proc_raw)
    finally:
     if fd is not None:os.close(fd)
 except Exception as error:
  print(json.dumps(dict(status='REFUSED_READONLY_OBSERVER',error=type(error).__name__+':'+str(error),readable_evidence=readable),sort_keys=True))
  raise
 # PASS is emitted only after custody/evidence cleanup and deadline restoration.
 result['readable_evidence']=readable
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
