"""Actual pure consumers/configure and observer main with explicit live-edge fixture.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No subprocess, Docker, root mutex, census, cleanup, guest or runtime release.
"""
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import ast,copy,hashlib,importlib.util,io,json,os,stat,sys,types,contextlib
D=Path(__file__).resolve().parent;B=D/'bound-current-controller-source-5'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def load(p):return json.loads(Path(p).read_bytes())
def module(p,name):
 m=types.ModuleType(name);m.__file__=str(p);exec(compile(Path(p).read_bytes(),str(p),'exec'),m.__dict__);return m
def forbidden(*a,**k):raise AssertionError('no process/root/cleanup operation in functional consumer fixture')
def whole_identity(p):
 p=Path(p);s=p.lstat();v=dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=oct(stat.S_IMODE(s.st_mode)),uid=s.st_uid,gid=s.st_gid,size=s.st_size,nlink=s.st_nlink)
 if p.is_file():v['sha256']=ref(p)['sha256']
 return v
def main():
 c=module(D/'current_controller_contract.py','actual_controller_contract');proofref=ref(D/'CURRENT-CONTROLLER-PROOF.json');reviewref=ref(D/'INDEPENDENT-ACTUAL-CONTROLLER-AND-CLIENT-ACCEPTANCE.json');case=load(B/'LAUNCHER-CASE-STATIC.json')
 print('PHASE actual-proof',flush=True)
 result=c.validate(proofref,reviewref);assert len(result['ledger']['docker_clients'])==7 and len(result['pids'])==8
 e=module(B/'cleanup_launcher.py','actual_current_engine');o=module(B/'observe_current_launcher_retirement.py','actual_current_observer');post=module(B/'postjoin_launcher.py','actual_current_postjoin');fresh=module(B/'check_launcher_fresh_preflight.py','actual_current_fresh')
 print('PHASE actual-observer-prerequisites',flush=True)
 actual=o.current_controller_prerequisites(case);assert actual['pids']==result['pids']
 obs_min=dict(target=case['target'],container_inspect=result['owner']['terminal_container_info'],controller_client_ledger=result['ledger'],controller_review=reviewref)
 assert e.controller_proof_binding(proofref,obs_min)['pids']==result['pids']
 args,mounts=e.image_layout(result['request']);item=result['owner']['terminal_container_info'];assert args==item['Args']==item['Config']['Cmd'] and mounts==sorted((m['Destination'],m['Source'],m['Type'],m['RW'])for m in item['Mounts']if m['Type']=='bind')
 cases=[]
 def refusal(name,fn,expected_type,expected_message):
  try:fn()
  except expected_type as exc:
   assert type(exc)is expected_type and str(exc)==expected_message,(name,type(exc).__name__,str(exc));cases.append(dict(case=name,result='REFUSED',reason=str(exc),exception_type=type(exc).__name__));return
  raise AssertionError('required refusal not observed '+name)
 refusal('missing-independent-review',lambda:c.validate(proofref,None),c.Refusal,'independent controller review pending')
 altered=copy.deepcopy(case);altered['current_live_postjoin']={};refusal('invented-guard-postjoin',lambda:o.current_controller_prerequisites(altered),RuntimeError,'no invented guard/postjoin/runtime authority')
 altered_obs=copy.deepcopy(obs_min);altered_obs['controller_client_ledger']['docker_clients'].pop();refusal('omitted-saved-Docker-client',lambda:e.controller_proof_binding(proofref,altered_obs),e.Refusal,'exact controller target/client ledger')
 altered_obs=copy.deepcopy(obs_min);altered_obs['target']['owner_starttime']='0';refusal('changed-owner-birth',lambda:e.controller_proof_binding(proofref,altered_obs),e.Refusal,'exact controller target/client ledger')
 altered_ref=dict(proofref,sha256='0'*64);refusal('changed-proof-descriptor',lambda:e.controller_proof_binding(altered_ref,obs_min),e.Refusal,'exact current controller proof reference')
 # Actual full configure consumer. Fixture supplies only unavailable publication
 # and live root/mount/metadata edges; all current source/proof/status bytes real.
 selected_paths={Path(p)for p in case['finite_unique_paths']}|{B/'cleanup_launcher.py',B/'observe_current_launcher_retirement.py',B/'LAUNCHER-CASE-STATIC.json',e.SELFTEST}
 selected=[whole_identity(p)for p in sorted(selected_paths)]
 lock=dict(path=str(e.ROOT_LOCK),device=27,inode=4,uid=0,gid=0,mode='0o644',nlink=1,size=0,sha256=hashlib.sha256(b'').hexdigest())
 obs=dict(mount=dict(target=str(e.ROOT),uuid=e.UUID,fstype='ext4',options='rw,nodev,nosuid'),root=whole_identity(e.ROOT),boot_id=o.BOOT,root_lock=lock,request=whole_identity(e.REQUEST),target=case['target'],container_inspect=item,retained_exclusions=list(case['retained_ownership'].values()),request_lease_absent=True,inventories={str(p):[whole_identity(p)]for p in (e.OUTPUT,e.EVIDENCE)},candidate_root=whole_identity(Path(result['request']['source_root'])),candidate_commit=e.IMAGE_CANDIDATE,candidate_tree=None,selected_files=selected,backup_root=whole_identity(Path(result['request']['backup_root'])),namespace_binding=e.NAMESPACE_BINDING,namespace_ancestry=e.NAMESPACE_ANCESTRY,controller_client_ledger=result['ledger'],controller_proof=proofref,controller_review=reviewref)
 value=e.prepare_release(obs,'1'*40,'2'*40);value.update(status='PASS_EXECUTION_RELEASE',author='TEST_ONLY_NO_RELEASE',fetched_source_verified=True,source_review=dict(status='PASS',reviewer='TEST_ONLY_SOURCE_BOUNDARY',evidence_sha256='0'*64),execution_review=dict(status='PASS',reviewer='TEST_ONLY_UNAVAILABLE_RELEASE_EDGE',evidence_sha256='0'*64))
 def git(argv,**kwargs):
  if argv[-1]=='1'*40+'^{tree}':return ('2'*40+'\n').encode()
  if argv[-1]=='1'*40+':'+e.PUBLISHED_SCRIPT:return (B/'cleanup_launcher.py').read_bytes()
  if argv[-1]=='1'*40+':'+e.PUBLISHED_TESTS:return e.SELFTEST.read_bytes()
  raise AssertionError('unexpected Git fixture edge')
 print('PHASE actual-configure-and-negatives',flush=True)
 with patch.object(e.subprocess,'check_output',git),patch.object(e,'validate_mount',lambda:None),patch.object(e,'protected_files',lambda:None):
  e.configure(copy.deepcopy(value),execute=False)
  assert e.WAITER_PIDS==result['pids'] and e.ROOT_TERMINAL==Path(proofref['path'])
  changed=copy.deepcopy(value);changed['observation']['controller_client_ledger']['docker_clients'].pop()
  refusal('configure-omitted-client',lambda:e.configure(changed,False),e.Refusal,'exact controller client ledger')
  changed=copy.deepcopy(value);changed['observation']['client_ledger']=[]
  refusal('configure-mixed-legacy-controller-ledgers',lambda:e.configure(changed,False),e.Refusal,'future-runtime-observation-required')
 assert 'controller_proof'in obs and 'guard_proof'not in obs and 'client_ledger'not in obs
 # Actual observer main, all pure consumer checks real; only root/live/capture
 # edges mocked. Writes are confined to an explicitly TEST_ONLY output directory.
 print('PHASE actual-observer-main-fixture',flush=True)
 fixture=D/'TEST_ONLY-observer-main-5';fixture.mkdir();o.OUTPUT=fixture/'observation';dummy=fixture/'dummy-mutex';dummy.write_bytes(b'');dummy_stat=dummy.stat();edges=[];real_open=os.open;real_identity=None
 mount=obs['mount'];mountbytes=json.dumps(dict(filesystems=[mount])).encode();oldtrace=sys.gettrace();installed=[]
 def install(m):
  original_identity=m.identity;original_observe=m.observe_identity
  def identity(s):
   if (s.st_dev,s.st_ino)==(dummy_stat.st_dev,dummy_stat.st_ino):return (27,4)
   return original_identity(s)
  def observe(path):return copy.deepcopy(lock)if Path(path)==m.ROOT_LOCK else original_observe(Path(path))
  m.identity=identity;m.observe_identity=observe;m.census=lambda:True;m.docker=lambda argv:json.dumps([item]).encode();m.metadata_inventory=lambda p:[whole_identity(p)]
  installed.append(True);edges.extend(['ROOT_MUTEX','LIVE_MOUNT_AND_DOCKER','PROCESS_CENSUS','FULL_LIVE_METADATA_INVENTORY'])
 def trace(frame,event,arg):
  if frame.f_code.co_filename!=str(B/'observe_current_launcher_retirement.py'):return None
  if event=='line'and 'm'in frame.f_locals and not installed:
   install(frame.f_locals['m']);sys.settrace(None);return None
  return trace
 def open_mock(path,flags,*a,**kw):
  if str(path)==e.ROOT_LOCK.name and kw.get('dir_fd')is not None:return real_open(dummy,flags)
  return real_open(path,flags,*a,**kw)
 def observed(argv,limit,retain):
  if argv[0]=='/usr/bin/findmnt':return mountbytes
  if 'inspect'in argv:return json.dumps([item]).encode()
  if 'ps'in argv:return b''
  raise AssertionError('unexpected observer command fixture')
 with ExitStack()as stack:
  for owner,name,replacement in [(o.os,'getuid',lambda:0),(o.os,'geteuid',lambda:0),(o.os,'open',open_mock),(o.resource,'setrlimit',lambda *a:None),(o.fcntl,'flock',lambda *a:None),(o,'validate_observation_release',lambda *a:edges.append('UNAVAILABLE_ROOT_OBSERVATION_RELEASE')),(o,'observed_command',observed),(o.subprocess,'Popen',forbidden),(o.subprocess,'run',forbidden)]:stack.enter_context(patch.object(owner,name,replacement))
  output=io.StringIO()
  try:
   sys.settrace(trace)
   with contextlib.redirect_stdout(output):o.main(['--git-commit','1'*40,'--git-tree','2'*40,'--observation-release','TEST_ONLY_UNAVAILABLE','--observation-release-sha256','0'*64])
  finally:sys.settrace(oldtrace)
 assert installed and json.loads(output.getvalue())['status']=='PASS_READ_ONLY_OBSERVATION_ONLY'
 actual_obs=load(o.OUTPUT/'observation.json');assert actual_obs['controller_client_ledger']==result['ledger'] and actual_obs['controller_proof']==proofref and 'guard_proof'not in actual_obs and 'client_ledger'not in actual_obs
 assert load(o.OUTPUT/'cleanup-release-draft.json')['status']=='NOT_RELEASED'
 # Concrete postjoin/fresh source rows use the same actual proof helper and
 # retain all source4 report diagnostics, not legacy ledger assumptions.
 assert "m.controller_proof_binding(obs['controller_proof'],obs)['pids']"in (B/'postjoin_launcher.py').read_text()
 assert 'process_reports=m.PROCESS_REPORTS'in (B/'postjoin_launcher.py').read_text()and 'process_reports=m.PROCESS_REPORTS'in (B/'check_launcher_fresh_preflight.py').read_text()
 result_report=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_ACTUAL_CONTROLLER_CONTRACT_BINDER_CONFIGURE_AND_OBSERVER_MAIN_FIXTURE_ONLY',actual_proof=proofref,actual_independent_review=reviewref,actual_Docker_clients=7,actual_owner_child=1,monitored_PIDs=8,positive_actual_pure_contract=True,positive_actual_engine_configure=True,positive_actual_observer_main=True,refusals=cases,mocked_unavailable_edges=sorted(set(edges)),fixture_stdout=output.getvalue(),fixture_observation=ref(o.OUTPUT/'observation.json'),no_fixture_execution_release=ref(o.OUTPUT/'cleanup-release-draft.json'),guard_recovery_branches_preserved=True,root_operations=0,Docker_commands=0,censuses=0,cleanup=False,physical_clearance=False,runtime_release=None,native_acceptance=False)
 (D/'ACTUAL-CONTROLLER-CONSUMER-TESTS.json').write_text(json.dumps(result_report,indent=2,sort_keys=True)+'\n');print(json.dumps(dict(status=result_report['status'],refusals=len(cases),Docker_clients=7,owner_children=1,root_operations=0,cleanup=False)))
if __name__=='__main__':main()
