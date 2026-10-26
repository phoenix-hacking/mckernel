"""Functional OS only; no security testing. READONLY producer; no cleanup entry calls."""
import argparse,ast,hashlib,importlib.util,json,os,stat,subprocess
from pathlib import Path
PROFILE=Path(__file__).parent/'EXACT-OWNER935300-READONLY-OBSERVATION-PROFILE.json'
PROFILE_SHA='e4882d00fd14e233a7f8b50853c568172b24684c4214bbad888dfd397b39ba0e'
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
def query(p,out,label):
 need(label in ('inspect','findmnt'),'queryallowlist');argv=p['query_allowlist'][label];stdout=b'';stderr=b'';status={}
 try:
  result=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=p['query_timeout_seconds'],check=False);stdout=result.stdout;stderr=result.stderr;status={'returncode':result.returncode}
 except subprocess.TimeoutExpired as exc:
  stdout=exc.stdout or b'';stderr=exc.stderr or b'';status={'error':'TimeoutExpired'}
 except OSError as exc:status={'error':type(exc).__name__,'errno':exc.errno}
 # Raw capture is durable before all parsing/status/size oracles, including errors.
 refs={stream:publish(out,label+'.'+stream,raw) for stream,raw in [('stdout',stdout),('stderr',stderr)]}
 status.update(argv=argv,timeout=p['query_timeout_seconds'],captures=refs);publish(out,label+'.status.json',(json.dumps(status,sort_keys=True)+'\n').encode())
 need(status.get('returncode')==0 and stderr==b'' and len(stdout)<=p['query_caps'][label],'readonlyqueryrefused:'+label)
 return stdout
def holder_check(e,p,ready):
 h=ready['holder'];need(h['pid']==934813 and h['starttime']=='77967163' and h['fd']==3 and h['transport']=='STDIN_FD0_SUDO_A' and h['transported_fd']==0,'exactholder')
 before=e.same_ofd_process(h['pid']);need(before['starttime']==h['starttime'] and before['uids']==[1000]*4 and before['gids']==[1000]*4,'holderbirthcredentials')
 need(e.same_ofd_read('/proc/sys/kernel/random/boot_id',128).decode().strip()==h['boot_id'],'holderboot')
 caller=json.loads(pinned(p['contract']))['static']['caller'];cmd=e.same_ofd_read('/proc/934813/cmdline',65536);need(cmd.endswith(b'\0') and caller['path'].encode() in cmd[:-1].split(b'\0'),'holdercallerargv');pinned(caller)
 lock=['FLOCK','ADVISORY','WRITE','934813','00:1b:4','0','EOF'];need(e.same_ofd_fd_locks(934813,3)==[lock],'holderfd3lock')
 need([line.split()[1:] for line in e.same_ofd_read('/proc/locks').decode().splitlines() if '00:1b:4' in line.split()]==[lock],'solegloballock')
 named=os.stat(h['path'],follow_symlinks=False);held=os.stat('/proc/934813/fd/3');need(e.same_ofd_metadata(named)==e.same_ofd_metadata(held)==h['identity'] and named.st_size==held.st_size==0,'holderfdnamedidentity');need(e.same_ofd_process(h['pid'])==before,'holderraced')
 return True

def produce(p,e,queryfn):
 ready=e.parse(pinned(p['ready']));receipt=e.parse(pinned(p['owner_receipt']));joined=e.parse(pinned(p['join']));process=e.parse(pinned(p['process']));c=e.parse(pinned(p['contract']));request=e.parse(pinned(c['static']['request']));holder_check(e,p,ready)
 need(ready['owner_join']==joined and ready['owner_receipt']==p['owner_receipt'] and joined['pid']==935300 and joined['starttime']=='77972425' and joined['returncode']==1 and all(joined[k] is True for k in ('direct_child_joined','group_absent','closed_streams')) and joined['error'] is None and joined['retirement_error'] is None,'joinedactualowner')
 target=p['target'];need(receipt['status']=='FAIL' and all(receipt[k]==target[k] for k in ('container_id','container_name','owner_nonce','exit_code')) and process['pid']==target['owner_pid'] and process['starttime']==target['owner_starttime'],'actualtarget')
 raw=queryfn('inspect');items=e.parse(raw);need(isinstance(items,list) and len(items)==1,'exactoneinspect');item=items[0];need(item['Id']==target['container_id'] and item['Name']=='/'+target['container_name'] and item['Image']==target['image_id'] and item['Config']['Labels']['mckernel.owner']==target['owner_nonce'],'inspecttarget')
 expected={'Status':'exited','Running':False,'Paused':False,'Restarting':False,'OOMKilled':False,'Dead':False,'Pid':0,'ExitCode':target['exit_code'],'Error':''};need(all(e.canonical(item['State'].get(k))==e.canonical(v) for k,v in expected.items()),'terminalstate');e.image_owner_receipt_binding(receipt,item,p['owner_receipt']['sha256'])
 mounts=e.parse(queryfn('findmnt'))['filesystems'];need(len(mounts)==1,'onescratchmount');mount=mounts[0];need(mount['target']==str(e.ROOT) and mount['uuid']==e.UUID and mount['fstype']=='ext4' and {'rw','nodev','nosuid'}<=set(mount['options'].split(',')),'scratchmount')
 need(not os.path.lexists(e.LEASE),'requestleaseabsent');ancestry=e.namespace_ancestry();need(ancestry==e.NAMESPACE_ANCESTRY,'namespaceancestry')
 statuses=sorted((e.EVIDENCE/'attempt').glob('command-*/status.json'));need(len(statuses)==p['expected_client_count'],'complete7clientledger');ledger=[]
 for path in statuses:
  raw=e.read_bounded(path);value=e.parse(raw);need(type(value['pid']) is int and value['pid']>0 and value['state']=='exited' and type(value['exit_code']) is int and value['exit_code']>=0 and not value.get('client_retirement_unproven'),'positiveclientstatus');ledger.append(dict(pid=value['pid'],status_path=str(path),status_sha256=e.digest(raw)))
 need(len({v['pid'] for v in ledger})==len(ledger),'uniqueclients')
 identities=[e.observe_identity(v) for v in (e.ATTEMPT,e.SHARED)];obs=dict(mount=mount,root=e.observe_identity(e.ROOT),boot_id=ready['holder']['boot_id'],root_lock=e.observe_identity(e.ROOT_LOCK),request=e.observe_identity(e.REQUEST),target=target,container_inspect=item,retained_exclusions=identities,request_lease_absent=True,inventories={str(path):e.metadata_inventory(path) for path in (e.OUTPUT,e.EVIDENCE)},candidate_root=e.observe_identity(Path(request['source_root'])),candidate_commit=request['candidate_sha'],candidate_tree=None,selected_files=[],backup_root=e.observe_identity(Path(request['backup_root'])),namespace_binding=e.NAMESPACE_BINDING,namespace_ancestry=ancestry,client_ledger=ledger,ownership_case='FAIL_COMMON_AND_SHARED',shared_record_already_absent=False,normal_owner_join=e.observe_identity(Path(p['join']['path'])))
 e.ownership_case_binding(receipt,obs,identities)
 for row in identities:e.image_record_binding(Path(row['path']),row,e.parse(e.read_bounded(Path(row['path']))),request,target,obs['boot_id'])
 protocol=e.current230_contract();needed={str(e.REQUEST),str(e.TERMINAL),p['join']['path'],str(e.EVIDENCE/'attempt/container.log'),str(e.OUTPUT/'evidence/receipt.json')};needed.update(row['status_path'] for row in ledger)
 joins={'driver_path':'driver_sha256','provenance_path':'provenance_sha256','host_owner_path':'host_owner_sha256','source_manifest':'source_manifest_sha256','toolchain_manifest':'toolchain_manifest_sha256'}
 if request.get('gitlink_manifest') is not None:joins['gitlink_manifest']='gitlink_manifest_sha256'
 needed.update(request[k] for k in joins);needed.update(str(Path(c['caller_capture_root'])/name) for name in ('owner.PROCESS.json','ACTUAL-OWNER-ENTRY.json','ROOT-NORMAL-CLEANUP-COMPLETION-READY.json','owner.stdout','owner.stderr'));static=protocol.required_static_references();needed.update(row['path'] for row in static);obs['selected_files']=[e.observe_identity(Path(path)) for path in sorted(needed)];selected={row['path']:row for row in obs['selected_files']}
 for row in static:need(selected[row['path']]['sha256']==row['sha256'] and selected[row['path']]['size']==row['bytes'],'selectedstaticpin')
 for key,hkey in joins.items():need(selected[request[key]]['sha256']==request[hkey],'requestsourcehash')
 protocol.normal_owner_join_binding(receipt,joined,target,item,p['owner_receipt']['sha256'],request,obs,selected);protocol.typed_source_binding(request,obs,selected)
 need(set(obs)==REQUIRED,'exactproduction21keys');need(e.metadata_inventory(e.OUTPUT)==obs['inventories'][str(e.OUTPUT)] and e.metadata_inventory(e.EVIDENCE)==obs['inventories'][str(e.EVIDENCE)],'inventoryraced')
 for row in obs['selected_files']:need(e.observe_identity(Path(row['path']))==row,'selectedraced')
 for row in identities:need(e.observe_identity(Path(row['path']))==row,'recordraced')
 holder_check(e,p,ready);need(not os.path.lexists(e.LEASE) and e.namespace_ancestry()==ancestry,'leaseornamespaceraced');return obs

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--execute-readonly',action='store_true');args=parser.parse_args();need(args.execute_readonly and os.geteuid()==0,'explicitrootreadonlyrequired');p,e=bootstrap();out=Path(p['capture_directory']);out.mkdir(mode=0o700);obs=produce(p,e,lambda label:query(p,out,label));publish(out,'OBSERVATION.json',e.canonical(obs));print(json.dumps(dict(status='PASS_READONLY_OBSERVATION_ONLY_NOT_CLEANUP_RELEASE',observation=str(out/'OBSERVATION.json'),keys=len(obs),queries=2,cleanup_actions=0),sort_keys=True))
if __name__=='__main__':main()
