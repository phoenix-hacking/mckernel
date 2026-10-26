"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One ordinary reviewed initialization: exact three empty namespace dirs only.
No lease/common/shared/mutex/capture/output/root query or owner operation.
"""
from pathlib import Path
import hashlib,json,os,stat,sys,types
INPUT=Path(__file__).parent / 'ATTEMPT4-EXACT-THREE-DIRECTORY-INITIALIZATION.INPUTS.json'
INPUT_SHA='5d54fd67bf7a540f3a2b05f4745bd27d4e68f289f4fc32f64f2c1064e9a82b22'
VALIDATOR={'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/validate_actual08860_attempt3_normal_cleanup_current_physical.SOURCE-ONLY.py', 'sha256': '68b450c396f719dac64ec67ea93e428fb3dd6341f25fc3b95be549aadfea9e86', 'bytes': 2116}

def need(ok,message):
 if not ok:raise RuntimeError('namespace3 init: '+message)
def ref(path):
 path=Path(path);b=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(path,value):
 raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
 with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
 return ref(path)
def _q3_run(grant_path,grant_sha):
 need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0},'ordinary UID1000 CPU0')
 need(ref(INPUT)['sha256']==INPUT_SHA and ref(VALIDATOR['path'])==VALIDATOR,'exact source/data/physical consumer')
 d=json.loads(INPUT.read_bytes());g=json.loads(Path(grant_path).read_bytes());need(ref(grant_path)['sha256']==grant_sha,'exact actual one-shot root grant')
 need(g['author']=='/root' and g['decision']=='GRANT_ONE_ORDINARY_ATTEMPT4_THREE_NAMESPACE_INITIALIZATION' and g['maximum_invocations']==1 and g['source']==ref(__file__) and g['inputs']==ref(INPUT) and g['physical']==d['current_physical_acceptance'] and g['request']==d['request'] and g['image_entry_owner']==d['image_entry_owner'] and g['host_control_owner']==d['host_control_owner'] and g['actual_no_new_heavy_since_acceptance'] is True,'exact root one-use ordinary initialization grant')
 m=types.ModuleType('actual_newbe87_physical');m.__file__=VALIDATOR['path'];exec(compile(Path(m.__file__).read_bytes(),m.__file__,'exec'),m.__dict__);m.validate(d['current_physical_acceptance'],d['postreturn'])
 target=Path(d['planned_namespace']);q=json.loads(Path(d['request']['path']).read_bytes());need(q['work_root']==str(target/'owner-work') and q['owner_evidence_root']==str(target/'owner-evidence'),'exact request namespace paths')
 output=Path(__file__).parent/'ACTUAL-ATTEMPT4-THREE-NAMESPACE-INITIALIZATION.json';need(not os.path.lexists(output),'fresh initialization receipt')
 fds=[];rows=[]
 try:
  fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC);fds.append(fd)
  for index,expected in enumerate(d['parent_ancestry']):
   if index:fd=os.open(Path(expected['path']).name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd);fds.append(fd)
   s=os.fstat(fd);need(dict(path=expected['path'],device=s.st_dev,inode=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)==expected,'pinned parent ancestry')
  os.mkdir(target.name,mode=0o700,dir_fd=fd)
  rootfd=os.open(target.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd);fds.append(rootfd)
  def identity(path,s,entries):return dict(path=str(path),device=s.st_dev,inode=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,entries=entries)
  for name in ['owner-work','owner-evidence']:
   os.mkdir(name,mode=0o700,dir_fd=rootfd);child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=rootfd);fds.append(child);s=os.fstat(child);need(s.st_uid==s.st_gid==1000 and stat.S_IMODE(s.st_mode)==0o700 and os.listdir(child)==[],'actual empty private child');rows.append(identity(target/name,s,[]))
  s=os.fstat(rootfd);need(s.st_uid==s.st_gid==1000 and stat.S_IMODE(s.st_mode)==0o700 and sorted(os.listdir(rootfd))==['owner-evidence','owner-work'],'actual private base');rows.insert(0,identity(target,s,['owner-evidence','owner-work']))
  for expected in d['parent_ancestry']:
   s=os.lstat(expected['path']);need((s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid)==tuple(expected[k] for k in ['device','inode','mode','uid','gid']),'same parent ancestry after creation')
  need(all(not os.path.lexists(q[k]) for k in ['attempt_root','common_exclusion_path','lease_path','output_root','evidence_root']),'all driver-owned record/output/capture children absent')
  result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_ACTUAL_ORDINARY_SOURCE_PREPARATION_NAMESPACE_INITIALIZATION_ONLY',request=d['request'],owner=d['image_entry_owner'],host_control_owner=d['host_control_owner'],identities=rows,ancestry=d['parent_ancestry'],physical=d['current_physical_acceptance'],postreturn=d['postreturn'],grant=ref(grant_path),source=ref(__file__),no_live_query_or_owner_admission=True)
  receipt=write(output,result);print(json.dumps(receipt,sort_keys=True));return receipt
 finally:
  for fd in reversed(fds):os.close(fd)
def initializer_metadata_preflight(data):
 need(data['actual_namespace_identities'] is None and data['actual_root_grant'] is None,'truthful pending source data')
 for role in ['request','image_entry_owner','host_control_owner','driver','readonly_reuse_inputs','namespace_plan']:
  need(ref(data[role]['path'])==data[role],'exact '+role+' source bytes')
 request=json.loads(Path(data['request']['path']).read_bytes())
 target=Path(data['planned_namespace'])
 expected={'work_root':str(target/'owner-work'),'owner_evidence_root':str(target/'owner-evidence'),'output_root':str(target/'owner-work/output'),'evidence_root':str(target/'owner-work/evidence'),'attempt_root':str(target/'owner-evidence/attempt'),'common_exclusion_path':str(target/'common-exclusion.json'),'lease_path':str(target/'lease.json')}
 need(set(data['seven_request_namespace_keys'])==set(expected),'exact seven request namespace keys')
 need(all(request[key]==value and not os.path.lexists(value) for key,value in expected.items()) and not os.path.lexists(target),'all seven driver paths and base absent before effects')
 need(data['three_directory_allowlist']==[str(target),str(target/'owner-work'),str(target/'owner-evidence')],'exact three mkdir allowlist')
 need(request['driver_path']==data['driver']['path'] and request['driver_sha256']==data['driver']['sha256'] and request['readonly_reuse_inputs']==data['readonly_reuse_inputs']['path'],'actual selected request roles')
 for expected_parent in data['parent_ancestry']:
  value=os.lstat(expected_parent['path'])
  need((value.st_dev,value.st_ino,value.st_mode,value.st_uid,value.st_gid)==tuple(expected_parent[key] for key in ['device','inode','mode','uid','gid']),'same planned ancestry before effects')
 return True

def run(grant_path,grant_sha):
 need(ref(INPUT)['sha256']==INPUT_SHA,'exact initializer data before preflight')
 initializer_metadata_preflight(json.loads(INPUT.read_bytes()))
 return _q3_run(grant_path,grant_sha)

if __name__=='__main__':
 need(len(sys.argv)==3,'exact root grant path and SHA required');run(Path(sys.argv[1]),sys.argv[2])
