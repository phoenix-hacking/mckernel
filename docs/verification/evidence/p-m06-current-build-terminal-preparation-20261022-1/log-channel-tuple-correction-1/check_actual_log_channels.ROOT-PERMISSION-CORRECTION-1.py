"""Actual source6 capture_logs + preflight_fresh, only physical edges mocked.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No root lock, Docker, mutations, cleanup, guest or build is executed.
"""
from pathlib import Path
from unittest.mock import patch
import ast,copy,hashlib,json,os,stat,types
E=Path(__file__).resolve().parent;D=E.parent;B=D/'bound-current-controller-source-6';S=D/'bound-current-controller-source-5'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def main():
 m=types.ModuleType('actual_source6_logging');m.__file__=str(B/'cleanup_launcher.py');exec(compile((B/'cleanup_launcher.py').read_bytes(),m.__file__,'exec'),m.__dict__)
 binding=json.loads((E/'ACTUAL-LOG-CHANNEL-BINDING.json').read_bytes());channels=copy.deepcopy(binding['channels']);assert m.PASS_LOG_CHANNELS==channels and set(channels)=={'status.json','stdout','stderr'}
 original=json.loads((D/'ROOT-CLEANUP-RELEASE-1.json').read_bytes());obs=original['observation'];m.RELEASE=original;m.PROTECTED=obs['selected_files'];m.DEVICE=obs['root']['device'];m.CANDIDATE=Path(obs['candidate_root']['path']);m.BOOT_ID=obs['boot_id'];m.CONTAINER=obs['target']['container_id'];m.ROOT_LOCK_BINDING=obs['root_lock']
 m.RECORDS={Path(r['path']):(r['sha256'],r['inode'],r['size'])for r in obs['retained_exclusions']};m.DIRS={Path(p):(rows[0]['device'],rows[0]['inode'],rows[0]['nlink'])for p,rows in obs['inventories'].items()};terminal=next(r for r in obs['selected_files']if r['path']==str(m.TERMINAL));m.TERMINAL_SHA,m.TERMINAL_INODE,m.TERMINAL_SIZE=terminal['sha256'],terminal['inode'],terminal['size']
 expected=Path(channels['stdout']['path']).read_bytes();assert expected==(m.EVIDENCE/'attempt/container.log').read_bytes();assert Path(channels['stderr']['path']).read_bytes()==b''
 calls=[]
 def logs(argv):
  assert argv==['/usr/bin/docker','--host=unix:///var/run/docker.sock','logs','--',m.CONTAINER];calls.append(argv);return expected
 assert not os.path.lexists(m.CAPTURE),'original planned capture must remain absent before mutation'
 cases=[]
 def refuse(name,fn,message):
  try:fn()
  except m.Refusal as exc:
   assert str(exc)==message,(name,str(exc));cases.append(dict(case=name,status='REFUSED',reason=str(exc)));return
  raise AssertionError('required refusal not observed: '+name)
 with patch.object(m,'run_privileged_large',logs):m.capture_logs(True,execute=False)
 assert len(calls)==1 and not os.path.lexists(m.CAPTURE)
 altered=copy.deepcopy(channels);altered['stdout']['sha256']='0'*64
 with patch.object(m,'PASS_LOG_CHANNELS',altered):refuse('changed-recorded-stdout-hash',lambda:m.capture_logs(True,False),'current-pass-log-channel-drift:stdout')
 altered=copy.deepcopy(channels);altered['status.json']['sha256']='0'*64
 with patch.object(m,'PASS_LOG_CHANNELS',altered):refuse('changed-recorded-Docker-status-hash',lambda:m.capture_logs(True,False),'current-pass-log-channel-drift:status.json')
 noisy=E/'TEST_ONLY-recorded-nonempty-stderr-correction-1';noisy.write_bytes(b'actual fixture stderr\n');noisy.chmod(0o600);altered=copy.deepcopy(channels);altered['stderr']=ref(noisy)
 with patch.object(m,'PASS_LOG_CHANNELS',altered):refuse('nonempty-recorded-log-stderr',lambda:m.capture_logs(True,False),'current-pass-recorded-log-stderr-not-empty')
 with patch.object(m,'run_privileged_large',lambda argv:b'wrong actual Docker body'):
  refuse('live-Docker-log-body-mismatch',lambda:m.capture_logs(True,False),'docker-log-mismatch')
 refuse('missing-live-container-and-capture',lambda:m.capture_logs(False,False),'docker-log-capture-missing')
 capture=E/'TEST_ONLY-existing-capture-correction-1';capture.write_bytes(expected);capture.chmod(0o600)
 with patch.object(m,'CAPTURE',capture),patch.object(m,'DEVICE',capture.stat().st_dev),patch.object(m,'run_privileged_large',lambda *a:(_ for _ in ()).throw(AssertionError('existing capture must not invoke Docker'))):m.capture_logs(False,False)
 capture.write_bytes(b'changed retained capture');capture.chmod(0o600)
 with patch.object(m,'CAPTURE',capture),patch.object(m,'DEVICE',capture.stat().st_dev):refuse('changed-retained-capture',lambda:m.capture_logs(False,False),'retained-capture-bytes')
 # Actual production preflight method and all ordinary protected byte/metadata,
 # preserved-directory/owner-record and lock(False) consumers execute unchanged.
 # Only inherited root-lock/namespace pin observation and live census/Docker
 # command edges are replaced; no Transaction constructor/root lock is entered.
 tx=object.__new__(m.Transaction);tx.fd=os.open(m.ROOT,os.O_RDONLY|os.O_DIRECTORY);tx.nfd=os.open(m.NAMESPACE,os.O_RDONLY|os.O_DIRECTORY);tx.rfd=None;tx.mfd=None;tx.root_locked=True;tx.mutation_started=False;pin_calls=[]
 tx.pinned=lambda:pin_calls.append('MOCK_ONLY_PERMANENT_ROOT_LOCK_AND_LIVE_NAMESPACE_PIN')
 # Exact root-owned observer metadata was already captured by the real root
 # observer and independently retained. Ordinary fixture cannot traverse its0700
 # directory; that permission/identity edge is the only protected row mocked.
 root_observation=S/'root-observation-p-m06-current-controller-observation-1'
 root_rows={r['path']:r for r in obs['selected_files']if Path(r['path']).is_relative_to(root_observation)}
 original_observe=m.observe_identity
 def observe_for_fixture(path):
  if str(path)in root_rows:return copy.deepcopy(root_rows[str(path)])
  return original_observe(path)
 m.observe_identity=observe_for_fixture
 print('PHASE actual preflight_fresh with actual capture_logs/ordinary preserved checks',flush=True)
 try:
  with patch.object(m,'census',lambda:True),patch.object(m,'run_privileged_large',logs):m.Transaction.preflight_fresh(tx)
  assert tx.mfd is None and tx.mutation_started is False and not os.path.lexists(m.CAPTURE)
  altered=copy.deepcopy(channels);altered['stdout']['sha256']='0'*64
  with patch.object(m,'census',lambda:True),patch.object(m,'run_privileged_large',logs),patch.object(m,'PASS_LOG_CHANNELS',altered):refuse('preflight-propagates-recorded-channel-drift',lambda:m.Transaction.preflight_fresh(tx),'current-pass-log-channel-drift:stdout')
  assert tx.mfd is None and tx.mutation_started is False
 finally:tx.close()
 # No function/class bodies changed, including old guard/recovery branches.
 unchanged=[]
 for name in ('cleanup_launcher.py','observe_current_launcher_retirement.py','check_launcher_fresh_preflight.py','postjoin_launcher.py','readback_observer.py','read_original_five_metadata.py','export_raw_five.py'):
  def bodies(p):return[(n.name,ast.dump(n,include_attributes=False))for n in ast.parse(p.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
  assert bodies(S/name)==bodies(B/name),name;unchanged.append(name)
 result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_ACTUAL_SOURCE6_LOG_CHANNELS_CAPTURE_AND_PREFLIGHT_COMPOSITION_ONLY',engine=ref(B/'cleanup_launcher.py'),source5_preserved=ref(S/'cleanup_launcher.py'),binding=ref(E/'ACTUAL-LOG-CHANNEL-BINDING.json'),actual_log_client_pid=binding['log_pid'],actual_channel_count=3,actual_stdout_bytes=len(expected),recorded_stderr_bytes=0,actual_production_capture_logs_positive=True,actual_existing_capture_positive=True,actual_production_preflight_fresh_positive=True,ordinary_protected_files_and_preserved_records_checks_real=True,refusals=cases,immutable_function_class_bodies=unchanged,root_live_edges_mocked=['permanent root-lock/live namespace pin observations','root process/container census','privileged Docker logs command only; actual saved log bytes returned','exact root-owned observer metadata identity row inaccessible to ordinary UID; genuine observation descriptor used'],root_operations=0,Docker_commands=0,mutations=0,cleanup=False,new_observation=None,physical_clearance=False,runtime_release=None)
 (E/'ACTUAL-LOG-CHANNEL-AND-PREFLIGHT-TESTS.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(dict(status=result['status'],refusals=len(cases),channel_count=3,stdout_bytes=len(expected),root_operations=0,mutations=0)))
if __name__=='__main__':main()
