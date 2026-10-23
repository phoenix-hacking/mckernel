from pathlib import Path
import sys,os,json,hashlib,fcntl,datetime,stat
sys.path.insert(0,'/home/holden/mckernel/scripts')
import native_running_external_modules_owner as o
D=json.loads(Path(sys.argv[1]).read_text())
def bound(ref):
 raw=Path(ref['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];return json.loads(raw)
assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
request=bound(D['request']);assert request['request_path']==D['request']['path'] and request['nonce']=='bc3cf0ecfe164d6bbcad77dd3bae8e16'
p05=bound(D['P05_physical_acceptance']);assert p05['physical_acceptance'] and p05['P_M05_02_literal_complete']
assert p05['owner_capture_status_sha256']=='060610e884bf2e1a0af03f7d9a190d105ebac9ddb20355c453511d7fbcb3a098'
assert p05['fresh_id_query_status_sha256']=='01950850b9032d9177aeb2e4d0ebe3b7a31e5400c8ae8acd7f939e72892c2762'
assert p05['verified']['owner_direct_joined_streams_closed_group_absent'] and p05['verified']['exact_container_name_label_id_absent'] and p05['verified']['permanent_mutex_preserved']==[27,4]
git=bound(D['fetched_checkpoint']);assert git['commit']==git['fetched_commit']=='5fd2c0d2e1e45130009a6d5eb7d88839eb029500'
source=bound(D['source_review']);assert source['decision']=='PASS_SOURCE' and source['implementation_ownership']is False and source['source_sha256']==D['source11']
static=bound(D['actual_static_materialization']);assert static['status']=='PASS_STATIC_MATERIALIZE_ACTUAL68_STATIC' and all(x['returncode']==0 and x['closed_streams'] and x['direct_child_joined'] and x['group_absent'] for x in static['results'])
fd=o.guard._development_lock(o.guard.DEVELOPMENT_LOCK,(27,4),(0,0))
try:
 meta=os.fstat(fd);assert (meta.st_dev,meta.st_ino)==(27,4)
 o.validate_runtime_source_bindings(D['source11'])
 rows=[]
 for name in D['six_canonical_records']:
  try: os.lstat(name)
  except FileNotFoundError as exc:
   assert exc.errno==2;rows.append(dict(path=name,observation='ENOENT',absent=True))
  else:raise AssertionError('current canonical heavy record present: '+name)
 try:o.validate_request(request,Path(D['request']['path']))
 except o.Refusal as exc:
  assert type(exc)is o.Refusal and str(exc)=='fresh authenticated historical lease observation required'
 else:raise AssertionError('expected in-owner historical observation boundary missing')
 mount=o.live_admission(request);resources=o.measure(request)
 at=datetime.datetime.now(datetime.timezone.utc).isoformat()
 admission=dict(status='PASS_FRESH_EXISTING_OWNER_GATES_UP_TO_IN_OWNER_HISTORICAL_OBSERVATION',at=at,request=D['request'],source_sha256=D['source11'],mount=mount,resources=resources,permanent_mutex=dict(device=meta.st_dev,inode=meta.st_ino),current_six_canonical_records=rows,in_owner_historical_observation_required=True,standalone_historical_observer_executed=False,new_heavy_operations=0)
 current=dict(status='PASS_CURRENT_POSTJOIN_AND_CANONICAL_RECORD_OBSERVATION',at=at,latest_heavy_P05_physical_acceptance=D['P05_physical_acceptance'],closed_P05_owner_capture_status_sha256=p05['owner_capture_status_sha256'],closed_fresh_P05_id_query_status_sha256=p05['fresh_id_query_status_sha256'],source_sha256=D['source11'],current_six_canonical_records=rows,observed_under_permanent_mutex=dict(device=meta.st_dev,inode=meta.st_ino),in_owner_historical_observation_required=True,new_heavy_operations=0,root_mutations=0,observation_scope='Fresh exact owner admission/conflict/resource guards and six canonical records; latest independently accepted P05 owner/name-label-ID closure joined. Authenticated complete historical lease observation remains inside SDK owner before create.')
 print(json.dumps(dict(status='PASS_READONLY_EXISTING_OWNER_ADMISSION_AND_POSTJOIN',admission=admission,current_live_postjoin=current,planned_output_paths=D['planned_output_paths']),sort_keys=True))
finally:
 fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
