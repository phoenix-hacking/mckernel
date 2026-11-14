"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact successor data binding of accepted read-only existing-owner admission gates.
"""
from pathlib import Path
import sys,os,json,hashlib,fcntl,datetime,importlib.util
sys.path.insert(0,'/home/holden/mckernel/scripts')
D=json.loads(Path(sys.argv[1]).read_text())
def bound(ref):
 raw=Path(ref['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];return json.loads(raw)
assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
assert os.sched_getaffinity(0)=={7}
request=bound(D['request']);assert request['request_path']==D['request']['path'] and request['nonce']=='9850d940ac3649a6b8e7ebebf3251853'
source=bound(D['source_review']);assert source['decision']=='PASS_SOURCE' and source['implementation_ownership']is False and source['source_sha256']==D['source11']
physical=bound(D['latest_physical_acceptance']);assert physical['physical_clearance'] is True and physical['decision']=='PASS_FAILED235_HOST_CONTAINER_AND_OWNERSHIP_PHYSICAL_RETIREMENT' and physical['nonce']=='8646cb69db21440ca31573ab1b3d0691'
stage=bound(D['actual_staging']);assert stage['status']=='SOURCE_INPUTS_STAGED_EXACT_REQUEST_NO_EXECUTION_RELEASE' and stage['request_sha256']==D['request']['sha256'] and stage['nonce']==request['nonce']
owner=Path(D['runtime_owner']['path']);assert hashlib.sha256(owner.read_bytes()).hexdigest()==D['runtime_owner']['sha256']
spec=importlib.util.spec_from_file_location('exact_successor_owner',owner);o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
fd=o.guard._development_lock(o.guard.DEVELOPMENT_LOCK,(27,4),(0,0))
try:
 meta=os.fstat(fd);assert (meta.st_dev,meta.st_ino)==(27,4)
 o.validate_runtime_source_bindings(D['source11'])
 rows=[]
 for name in D['current_canonical_records']:
  try:os.lstat(name)
  except FileNotFoundError as exc:
   assert exc.errno==2;rows.append(dict(path=name,observation='ENOENT',absent=True))
  else:raise AssertionError('current canonical heavy record present: '+name)
 for name in D['new_nonce_required_absent_paths']:
  try:os.lstat(name)
  except FileNotFoundError as exc:assert exc.errno==2
  else:raise AssertionError('new SDK nonce namespace already present: '+name)
 cgroup={p:Path(p).read_text().strip()for p in D['expected_cgroup']};assert cgroup==D['expected_cgroup']
 try:o.validate_request(request,Path(D['request']['path']))
 except o.Refusal as exc:
  assert type(exc)is o.Refusal and str(exc)=='fresh authenticated historical lease observation required'
 else:raise AssertionError('expected in-owner historical observation boundary missing')
 mount=o.live_admission(request);resources=o.measure(request)
 at=datetime.datetime.now(datetime.timezone.utc).isoformat()
 admission=dict(status='PASS_FRESH_EXISTING_SUCCESSOR_OWNER_GATES_UP_TO_IN_OWNER_HISTORICAL_OBSERVATION',at=at,request=D['request'],source_sha256=D['source11'],mount=mount,resources=resources,permanent_mutex=dict(device=meta.st_dev,inode=meta.st_ino),current_canonical_records=rows,cgroup=cgroup,in_owner_historical_observation_required=True,standalone_historical_observer_executed=False,new_heavy_operations=0)
 current=dict(status='PASS_CURRENT_POSTJOIN_AND_CANONICAL_RECORD_OBSERVATION',at=at,latest_heavy_physical_acceptance=D['latest_physical_acceptance'],source_sha256=D['source11'],current_canonical_records=rows,observed_under_permanent_mutex=dict(device=meta.st_dev,inode=meta.st_ino),in_owner_historical_observation_required=True,new_heavy_operations=0,root_mutations=0,observation_scope='Fresh exact successor owner request/source/resource/UUID/backing/cgroup and eight conflict paths; preceding failed235 physical clearance separately independently accepted. Fresh SDK nonce name/label query captures separately required. Authenticated historical observer remains inside actual SDK owner before create.')
 print(json.dumps(dict(status='PASS_READONLY_EXISTING_SUCCESSOR_OWNER_ADMISSION_AND_POSTJOIN',admission=admission,current_live_postjoin=current,planned_output_paths=D['planned_output_paths']),sort_keys=True))
finally:
 fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
