"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private pure source/API fixtures only: no guarded_execute, container, compiler or clock observation.
All synthetic review/clock documents live in deleted temporary fixture directories.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,tempfile,unittest
from unittest.mock import patch
import mock64_contract as mc
import kernel_pids64 as kp
import effective_profile64 as ep
import prepare_mock64_inputs as prepare
import mock64_owner as owner
N=Path(__file__).resolve().parent
PARENT=N.parents[1]/'sdk7-142g-consumer-successor-source-1/daemon_sdk_owner.142G-SOURCE-ONLY.py'
# N is E/daemon.../child, so the original owner is under E, two parents above N.
PARENT=N.parents[1]/'sdk7-142g-consumer-successor-source-1/daemon_sdk_owner.142G-SOURCE-ONLY.py'
NONCE='a'*32;CLOCK=[1793057312.,839417.,854756.]
def write(p,v):p.write_bytes(mc.canonical(v));return mc.ref(p)
def two(r):return {k:r[k] for k in ('path','sha256')}
def resources(leases=0):return dict(open_fds=0,duplicate_close=0,leases=leases,udev_ctx=0,udev_mon=0,udev_devices=0,threads=1,detect=1,get=1,syslog_messages=0,release_attempts=1,released=0)
def capture(rc=0):return dict(returncode=rc,direct_child_joined=True,group_absent=True,closed_streams=True,error=None,retirement_error=None,timed_out=False,unexpected_group_members=[],captures={s:dict(size=0,sha256=mc.sha(b'')) for s in ['stdout','stderr']})
def proof(kind='v1'):
 c='7:pids:/docker/example\n';m='10 2 0:30 /docker/example /sys/fs/cgroup/pids ro - cgroup cgroup ro,pids\n'
 if kind=='v2':c='0::/docker/example\n';m='10 2 0:30 /docker/example /sys/fs/cgroup ro - cgroup2 cgroup ro\n'
 path,mount=kp.locate(c,m)
 return dict(schema='mckernel.daemon-mock.kernel-pids64.v1',pid=2,proc_self_cgroup=c,proc_self_mountinfo=m,controller_directory=path,controller_identity=dict(device=30,inode=99),selected_mount=mount,maximum_raw='64\n',current_raw='2\n',maximum_identity=dict(path=path+'/pids.max',sha256=mc.sha(b'64\n')),current_identity=dict(path=path+'/pids.current',sha256=mc.sha(b'2\n')))
class Pure(unittest.TestCase):
 def using(self,context):
  value=context.start();self.addCleanup(context.stop);return value
 def tmp(self):
  t=tempfile.TemporaryDirectory(prefix='PURE-NO-RUNTIME-',dir=N);self.addCleanup(t.cleanup);return Path(t.name)
 def mirror(self):
  root=self.tmp();mirror=root/'mirror';mirror.mkdir(mode=0o700);self.using(patch.object(mc,'MIRROR',mirror));workspace=root/'workspace';workspace.mkdir(mode=0o700);self.using(patch.object(mc,'OUTPUT_PARENT',workspace))
  for row in mc.PREP['source_files']:prepare.copy_pinned(row,mirror/row['relative'])
  (mirror/mc.PREP['fixture_output_relative']).mkdir(mode=0o700)
  candidate=workspace/('native-running-modules-candidate-'+NONCE);candidate.mkdir(mode=0o700);(candidate/'fixture-output').mkdir(mode=0o700);prepdir=workspace/('preparation-'+NONCE);prepdir.mkdir(mode=0o700)
  (prepdir/'PREPARATION.SOURCE-ONLY.json').write_bytes(mc.PREPARATION.read_bytes())
  request=dict(nonce=NONCE,input_root=str(mirror),input_identity=mc.node(mirror),candidate_root=str(candidate),fixture_output_identity=mc.node(candidate/'fixture-output'),runtime_preparation_identity=mc.node(prepdir))
  r=write(prepdir/'OUTPUT-BINDING.ACTUAL.json',mc.output_binding(request));request['output_binding']=two(r);return root,request
 def test_writer_request_schema_matches_actual_owner_consumer(self):
  tree=ast.parse((N/'mock64_owner.py').read_bytes());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_request');required=next(ast.literal_eval(n.value) for n in function.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='required' for t in n.targets))
  writer=ast.parse((N/'prepare_mock64_inputs.py').read_bytes());calls=[n.value for n in ast.walk(writer) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='request' for t in n.targets)];self.assertEqual(len(calls),1);self.assertEqual({k.arg for k in calls[0].keywords},required)
 def test_frozen_lifecycle_functions_and_capture_classes_unchanged(self):
  def functions(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  old,new=functions(PARENT),functions(N/'mock64_owner.py')
  names=['run_owner','release_owned_records','record_snapshot','absence','BoundDocker','ExternalDocker','HistoricalObserverClient','DeferredSignals','output_namespace','live_admission','output_admission']
  for name in names:self.assertEqual(old[name],new[name],name)
 def test_same13_mirror_precreated_targets_and_output_identity(self):
  root,request=self.mirror();self.assertEqual(len(mc.verify_mirror(mc.MIRROR)),13);mc.verify_request_inputs(request);owner.validate_preparation(mc.PREP,request)
  target=mc.MIRROR/mc.PREP['source_files'][0]['relative'];target.write_bytes(b'wrong')
  with self.assertRaises(ValueError):mc.verify_mirror(mc.MIRROR)
 def test_output_wrong_inode_extra_or_nonempty_refused(self):
  root,request=self.mirror();bad=copy.deepcopy(request);bad['fixture_output_identity']['inode']+=1
  with self.assertRaises(ValueError):mc.verify_request_inputs(bad)
  (Path(request['candidate_root'])/'unexpected').write_text('retain')
  with self.assertRaises(ValueError):mc.verify_request_inputs(request)
 def test_only_exact_owned_invocation_symlink_allowed(self):
  root=self.tmp();out=root/'fixture-output';out.mkdir();(out/'ihkmond-Rust').write_bytes(b'fixture')
  link=out/'ihkmond';link.symlink_to(str(Path(mc.PREP['container_output'])/'ihkmond-Rust'));self.assertGreater(mc.output_tree_bytes(root,4096),0)
  link.unlink();link.symlink_to('/tmp/other')
  with self.assertRaises(ValueError):mc.output_tree_bytes(root,4096)
  link.unlink();(root/'foreign').symlink_to(out/'ihkmond-Rust')
  with self.assertRaises(ValueError):mc.output_tree_bytes(root,4096)
 def test_effective64_profile_rejects512_and_other_drift(self):
  info=dict(HostConfig=dict(ep.LIMITS,Privileged=False,ReadonlyRootfs=True,CapDrop=['ALL'],SecurityOpt=['no-new-privileges'],Init=True,PidMode='',IpcMode='private'),Image=mc.PREP['tool_image'],Config={'Labels':{'mckernel.owner':NONCE}},State={'Status':'created'})
  ep.check_profile(info,mc.PREP['tool_image'],NONCE)
  for key,value in [('PidsLimit',512),('PidsLimit',65),('NetworkMode','host'),('MemorySwap',-1)]:
   bad=copy.deepcopy(info);bad['HostConfig'][key]=value
   with self.assertRaises(RuntimeError):ep.check_profile(bad,mc.PREP['tool_image'],NONCE)
 def test_kernel_v1_v2_hybrid_controller_and_raw64(self):
  for kind in ['v1','v2']:kp.validate_proof(proof(kind))
  p=proof();p['proc_self_cgroup']+='0::/unified\n';p['controller_directory'],p['selected_mount']=kp.locate(p['proc_self_cgroup'],p['proc_self_mountinfo']);kp.validate_proof(p)
  for value in ['512\n','max\n','64','65\n']:
   p=proof();p['maximum_raw']=value
   with self.assertRaises(ValueError):kp.validate_proof(p)
  with self.assertRaises(ValueError):kp.locate('0::/unknown\n','10 2 0:30 /other /sys/fs/cgroup ro - cgroup2 cgroup ro\n')
 def test_driver_kernel_proof_before_compilers_and_frozen_case_body(self):
  source=(N/'mock64_driver.py').read_text();self.assertLess(source.index('proof=kernel_pids64.observe()'),source.index("namespace['owned_capture']("))
  old=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/m15-daemon-validation/read-errors-successor-1/fixture/run_fixture.py').read_text();new=(N/'run_fixture_precreated.py').read_text();suffix='    env={k:v for k,v in os.environ.items()';self.assertEqual(old[old.index(suffix):],new[new.index(suffix):])
 def summary(self):
  rows=[]
  for case in mc.cases():
   r=resources(case['expected_unreleased_leases'])
   for field,key in [('expected_gets','get'),('expected_syslog_messages','syslog_messages')]:
    if field in case:r[key]=case[field]
   rows.append(dict(name=case['name'],passed_contract=True,Rust_status=case['status'],Rust_resources=r,reference=dict(defined_output_status_diagnostic_equal=True) if case['reference_defined_compare'] else None))
  return dict(status='PASS_DEFINED_REFERENCE_AND_RUST_LIFECYCLE_MOCK_ONLY',daemon_cases=26,failed=[],normal_C_ring_parity=True,Rust_oversized_read_proposal=True,results=rows,production_daemon_fork_executed=False,real_udev_or_devices_executed=False,native_acceptance=False,provider_Rust_link_closure=False)
 def test_exact_summary_negative_status_and_real_resource_limits_preserved(self):
  s=self.summary();mc.validate_summary(s)
  negative=next(i for i,c in enumerate(mc.cases()) if c['status']!=0);bad=copy.deepcopy(s);bad['results'][negative]['Rust_status']=0
  with self.assertRaises(ValueError):mc.validate_summary(bad)
  bad=copy.deepcopy(s);bad['results'][0]['Rust_resources']['open_fds']=1
  with self.assertRaises(ValueError):mc.validate_summary(bad)
  bad=copy.deepcopy(s);bad['native_acceptance']=True
  with self.assertRaises(ValueError):mc.validate_summary(bad)
 def fixture_tree(self,root=None):
  root=self.tmp() if root is None else root;summary=self.summary();write(root/'summary.json',summary)
  statuses={label:0 for label in ['mock-build','C-reference-build','C-helper-build','Rust-daemon-build','ring-C','ring-Rust','oversize-Rust']}
  for i,(case,row) in enumerate(zip(mc.cases(),summary['results'])):
   label='%02d-Rust'%i;statuses[label]=case['status'];write(root/(label+'.resources.json'),row['Rust_resources']);trace=[]
   if case['name']=='configured-facility':trace.append('facility=144')
   if 'expected_event_read_fault' in case:trace.append('injected '+case['expected_event_read_fault'])
   (root/(label+'.trace')).write_text('\n'.join(trace)+'\n')
   if case['reference_defined_compare']:
    label='%02d-C'%i;statuses[label]=case['status'];(root/(label+'.trace')).write_text('')
  for label in ['ring-C','ring-Rust']:
   write(root/(label+'.resources.json'),resources());write(root/(label+'.files.json'),dict(kmsg0='00'));(root/(label+'.trace')).write_text('syslog same\n')
  write(root/'oversize-Rust.resources.json',dict(resources(),syslog_bytes=(1<<20)+16))
  for label,status in statuses.items():
   directory=root/label;directory.mkdir();write(directory/'whole-join.json',capture(status))
   for stream in ['stdout','stderr']:(directory/stream).write_bytes(b'')
  return root
 def test_complete_typed_fixture_tree_and_missing_join_wrong_trace_refused(self):
  root=self.fixture_tree();mc.validate_fixture_tree(root)
  target=root/'00-Rust/whole-join.json';value=mc.json_bytes(target.read_bytes());value['direct_child_joined']=False;write(target,value)
  with self.assertRaises(ValueError):mc.validate_fixture_tree(root)
  root=self.fixture_tree();i=next(i for i,c in enumerate(mc.cases()) if c['name']=='configured-facility');(root/('%02d-Rust.trace'%i)).write_text('wrong\n')
  with self.assertRaises(ValueError):mc.validate_fixture_tree(root)
 def test_actual_typed_driver_receipt_checks_all_artifacts_and_kernel_proof(self):
  work=self.tmp();output=work/'fixture-output';output.mkdir();self.fixture_tree(output);evidence=work/'evidence';evidence.mkdir()
  c=capture()
  for stream in ['stdout','stderr']:
   (evidence/stream).write_bytes(b'');c['captures'][stream]['path']='/work/evidence/'+stream
  before=write(evidence/'kernel-pids64-before.json',proof());after=write(evidence/'kernel-pids64-after.json',proof())
  receipt=dict(schema='mckernel.daemon-mock64-driver-receipt.v1',status='PASS_DAEMON_MOCK64_CAPTURE',scope=mc.PREP['scope'],preparation_sha256=mc.PREPARATION_SHA,nonce=NONCE,command=mc.fixture_command(NONCE),capture=c,summary_sha256=mc.ref(output/'summary.json')['sha256'],fixture_cases=26,kernel_pids64_before_sha256=before['sha256'],kernel_pids64_after_sha256=after['sha256'],production_main_executed=False,native_acceptance=False,provider_Rust_link_closure=False,M15_file_closure=False)
  owner.validate_library_receipt(receipt,dict(candidate_root=str(work),nonce=NONCE))
  bad=copy.deepcopy(receipt);bad['kernel_pids64_before_sha256']='0'*64
  with self.assertRaises(owner.Refusal):owner.validate_library_receipt(bad,dict(candidate_root=str(work),nonce=NONCE))
 def authfixture(self):
  root=self.tmp();request=dict(nonce=NONCE,boot_id=mc.BOOT,terminal_policy='remove-owned-terminal',driver=dict(path=str(mc.DRIVER),sha256=mc.sha(mc.DRIVER.read_bytes())))
  requestpath=root/'SOURCE-ONLY-request.json';rr=write(requestpath,request)
  mapping={key:mc.sha(Path(owner.RUNTIME_SOURCE_PATHS[key]).read_bytes()) for key in owner.SOURCES}
  sr=write(root/'SOURCE-ONLY-source-review.json',dict(decision='PASS_SOURCE',implementation_ownership=False,reviewer='PURE_FIXTURE_SOURCE_ONLY',source_sha256=mapping,fixture_only=True,runtime_authority=False))
  resourcesref=write(root/'SOURCE-ONLY-resources.json',dict(observed_clocks=CLOCK,boot_id=mc.BOOT,no_existing_heavy=True));postjoin=write(root/'SOURCE-ONLY-postjoin.json',dict(fixture_only=True,runtime_authority=False));pub=write(root/'SOURCE-ONLY-publication.json',dict(fixture_only=True,runtime_authority=False))
  admission=dict(schema='mckernel.daemon-mock64-current-admission.v1',status='ROOT_RESERVED_DAEMON_MOCK64_SOLE_HEAVY',author='/root',nonce=NONCE,request=two(rr),boot_id=mc.BOOT,profile=mc.PREP['profile'],one_heavy=True,observed_clocks=CLOCK,expires_wall=CLOCK[0]+120,nonce_ledger_complete=True,consumed_nonces=['b'*32],resource_physical=resourcesref,latest_postjoin_acceptance=postjoin,source_publication=pub)
  ar=write(root/'SOURCE-ONLY-admission.json',admission)
  payload=dict(schema='mckernel.daemon-mock64-release.v1',status='PASS_EXECUTION_RELEASE',execution_count=1,request=two(rr),nonce=NONCE,boot_id=mc.BOOT,fetched_source_verified=True,terminal_policy=request['terminal_policy'],historical_observer=dict(path=str(owner.HISTORICAL_OBSERVER),sha256=owner.HISTORICAL_OBSERVER_SHA,prefix=list(owner.HISTORICAL_PREFIX),timeout_seconds=30),source_sha256=mapping,source_review=two(sr),current_admission=two(ar),author='/root')
  er=write(root/'SOURCE-ONLY-execution-review.json',dict(decision='PASS_EXECUTION',implementation_ownership=False,reviewer='PURE_FIXTURE_SOURCE_ONLY',reviewed_release_payload_sha256=mc.sha(mc.canonical(payload)),fixture_only=True,runtime_authority=False));release=dict(payload,execution_review=two(er));releasepath=root/'SOURCE-ONLY-release.json';write(releasepath,release)
  return root,requestpath,rr,releasepath,release,admission
 def test_actual_new_owner_authenticate_api_refs_and_full_source_map(self):
  root,rp,rr,lp,release,admission=self.authfixture()
  with patch.object(owner,'check_campaign',return_value=CLOCK):owner.authenticate(rp,rr['sha256'],lp,mc.ref(lp)['sha256'])
  release['source_review']['bytes']=1;write(lp,release)
  with patch.object(owner,'check_campaign',return_value=CLOCK):
   with self.assertRaises(owner.Refusal):owner.authenticate(rp,rr['sha256'],lp,mc.ref(lp)['sha256'])
 def test_current_admission_wrong64_profile_stale_consumed_nonce_refused(self):
  root,rp,rr,lp,release,admission=self.authfixture()
  with patch.object(owner,'check_campaign',return_value=[CLOCK[0]+121,CLOCK[1]+121,CLOCK[2]+121]):
   with self.assertRaises(owner.Refusal):owner.check_current_admission(release,mc.json_bytes(rp.read_bytes()),rp,rr['sha256'])
  for change in ['profile','consumed']:
   bad=copy.deepcopy(admission)
   if change=='profile':bad['profile']['pids']=512
   else:bad['consumed_nonces'].append(NONCE)
   ar=write(root/('SOURCE-ONLY-'+change+'.json'),bad);test=dict(release,current_admission=two(ar))
   with patch.object(owner,'check_campaign',return_value=CLOCK):
    with self.assertRaises(owner.Refusal):owner.check_current_admission(test,mc.json_bytes(rp.read_bytes()),rp,rr['sha256'])
if __name__=='__main__':unittest.main(verbosity=2)
