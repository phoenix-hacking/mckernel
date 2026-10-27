"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure API/data tests: no guarded execution, clocks, compiler, Docker or daemon.
"""
from pathlib import Path
import ast,copy,json,tempfile,unittest
from unittest.mock import patch
import repro_contract as mc
import repro_owner as owner

def stat(pid,birth,state='R'):
 return str(pid)+' (joined worker) '+state+' '+' '.join(['0']*18+[str(birth)]+['0']*30)
def positive():
 def row(pid,birth):return dict(tid=pid,known_joined_or_main=True,stat_read=1,raw_stat=stat(pid,birth))
 def snapshot(rows):return dict(iteration=0,rows=rows,literal_threads=len(rows),unknown=False)
 return [snapshot([row(10,100),row(12,102)]),dict(status='OBSERVED_JOINED_TASK_ENUMERATION',iteration=0,immediate_literal_threads=2,real_pthread_join_returned_zero=True,workers=[dict(tid=11,initial_raw_stat=stat(11,101)),dict(tid=12,initial_raw_stat=stat(12,102))]),snapshot([row(10,100)]),snapshot([row(10,100)]),dict(status='FINAL_LITERAL_THREAD_CHECK',threads=1)]
def encode(records):return b''.join(mc.canonical(row) for row in records)
class Pure(unittest.TestCase):
 def test_exact_positive_and_not_reproduced(self):
  self.assertEqual(mc.validate_observation(encode(positive()),10,0),'OBSERVED_CURRENT_PLATFORM_JOIN_PROCFS_LAG')
  raw=encode([dict(status='NOT_REPRODUCED',iterations=256,historical_extra_task_identity=None)])
  self.assertEqual(mc.validate_observation(raw,10,2),'NOT_REPRODUCED')
  with self.assertRaises(ValueError):mc.validate_observation(raw,10,0)
 def test_unknown_unjoined_reused_or_nonsingleton_tasks_refused(self):
  for mutation in ['unknown','unjoined','reuse','singleton','missing','duplicate']:
   rows=positive()
   if mutation=='unknown':rows[0]['rows'][1]['tid']=13
   elif mutation=='unjoined':rows[1]['real_pthread_join_returned_zero']=False
   elif mutation=='reuse':rows[0]['rows'][1]['raw_stat']=stat(12,999)
   elif mutation=='singleton':rows[3]=copy.deepcopy(rows[0])
   elif mutation=='missing':rows.pop(2)
   else:rows[0]['rows'][1]=copy.deepcopy(rows[0]['rows'][0])
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):mc.validate_observation(encode(rows),10,0)
 def test_lifecycle_profile_account_and_source20_remain_exact(self):
  parent=ast.parse((mc.HERE.parents[1]/'mock64_owner.py').read_bytes());child=ast.parse(mc.OWNER.read_bytes())
  for name in ['run_owner','guarded_execute','ExternalDocker','BoundDocker','release_owned_records','create_args','profile','mounts','check_campaign','validate_runtime_source_bindings']:
   a=next(n for n in parent.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
   b=next(n for n in child.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
   self.assertEqual(ast.dump(a,include_attributes=False),ast.dump(b,include_attributes=False),name)
  self.assertEqual(mc.PREP['profile']['pids'],64);self.assertEqual(mc.PREP['observe_seconds'],8)
  self.assertEqual(mc.PREP['source_files'][0]['source']['sha256'],'290189d9d007ede5ba9d67b7b1fc06e05622aede89de342edccb976c23065820')
  self.assertEqual(mc.PREP['command_template'][0],'/usr/bin/cc');self.assertNotIn('rustc',' '.join(mc.PREP['command_template']))
  self.assertEqual(mc.PREP['execute_argv'],['/work/fixture-output/join-procfs-reproducer'])
  driver=(mc.HERE/'repro_driver.py').read_text();self.assertLess(driver.index('before=kernel_pids64.observe()'),driver.index("namespace['owned_capture']("))
 def test_actual_receipt_api_durable_stream_and_kernel_proofs(self):
  import kernel_pids64 as kp
  with tempfile.TemporaryDirectory(prefix='PURE-NO-RUNTIME-',dir=mc.HERE) as temporary:
   root=Path(temporary);evidence=root/'evidence';evidence.mkdir();output=root/'fixture-output';output.mkdir()
   captures=[]
   for label,data,rc in [('compile',b'',0),('observe',encode(positive()),0)]:
    directory=evidence/label;directory.mkdir();streams={}
    for stream,raw in [('stdout',data),('stderr',b'')]:
     (directory/stream).write_bytes(raw);streams[stream]=dict(path='/work/evidence/'+label+'/'+stream,size=len(raw),sha256=mc.sha(raw))
    capture=dict(pid=10,returncode=rc,direct_child_joined=True,group_absent=True,closed_streams=True,error=None,retirement_error=None,timed_out=False,unexpected_group_members=[],captures=streams)
    (directory/'whole-join.json').write_bytes(mc.canonical(capture));captures.append(capture)
   (output/'join-procfs-reproducer').write_bytes(b'PURE_FIXTURE_NO_EXECUTION')
   membership='7:pids:/docker/example\n';mount='10 2 0:30 /docker/example /sys/fs/cgroup/pids ro - cgroup cgroup ro,pids\n';controller,selected=kp.locate(membership,mount)
   proof=dict(schema='mckernel.daemon-mock.kernel-pids64.v1',pid=2,proc_self_cgroup=membership,proc_self_mountinfo=mount,controller_directory=controller,controller_identity=dict(device=30,inode=99),selected_mount=selected,maximum_raw='64\n',current_raw='2\n',maximum_identity=dict(path=controller+'/pids.max',sha256=mc.sha(b'64\n')),current_identity=dict(path=controller+'/pids.current',sha256=mc.sha(b'2\n')))
   for phase in ['before','after']:(evidence/('kernel-pids64-'+phase+'.json')).write_bytes(mc.canonical(proof))
   receipt=dict(schema='mckernel.daemon-join-procfs64-driver-receipt.v1',status='PASS_JOIN_PROCFS64_OBSERVATION_CAPTURE',scope=mc.PREP['scope'],nonce='a'*32,preparation_sha256=mc.PREPARATION_SHA,commands=[mc.PREP['command_template'],mc.PREP['execute_argv']],captures=captures,outcome='OBSERVED_CURRENT_PLATFORM_JOIN_PROCFS_LAG',production_main_executed=False,native_acceptance=False,provider_Rust_link_closure=False,M15_file_closure=False,daemon_acceptance=False,historical_extra_task_identity=None,executable=dict(mc.ref(output/'join-procfs-reproducer'),path='/work/fixture-output/join-procfs-reproducer'))
   for phase in ['before','after']:receipt['kernel_pids64_'+phase+'_sha256']=mc.ref(evidence/('kernel-pids64-'+phase+'.json'))['sha256']
   request=dict(nonce='a'*32,candidate_root=str(root));owner.validate_library_receipt(receipt,request)
   for mutation in ['hash','join','scope']:
    bad=copy.deepcopy(receipt)
    if mutation=='hash':bad['kernel_pids64_before_sha256']='0'*64
    elif mutation=='join':bad['captures'][1]['direct_child_joined']=False
    else:bad['daemon_acceptance']=True
    with self.subTest(mutation=mutation),self.assertRaises(ValueError):owner.validate_library_receipt(bad,request)
   (evidence/'observe/stdout').write_bytes(b'changed')
   with self.assertRaises(ValueError):owner.validate_library_receipt(receipt,request)
 def test_actual_authenticate_api_source_shape_hash_and_consumption(self):
  with tempfile.TemporaryDirectory(prefix='PURE-NO-RUNTIME-',dir=mc.HERE) as temporary:
   root=Path(temporary);nonce='a'*32;clocks=[1793057312.,839417.,854756.]
   def write(name,value):
    p=root/name;p.write_bytes(mc.canonical(value));return {k:v for k,v in mc.ref(p).items() if k!='bytes'}
   request=dict(nonce=nonce,boot_id=mc.BOOT,terminal_policy='remove-owned-terminal',driver=dict(path=str(mc.DRIVER),sha256=mc.sha(mc.DRIVER.read_bytes())))
   rr=write('SOURCE-ONLY-request.json',request);mapping={key:mc.sha(Path(owner.RUNTIME_SOURCE_PATHS[key]).read_bytes()) for key in owner.SOURCES}
   sr=write('SOURCE-ONLY-source-review.json',dict(decision='PASS_SOURCE',implementation_ownership=False,reviewer='PURE_FIXTURE_ONLY',source_sha256=mapping,runtime_authority=False))
   resource=write('SOURCE-ONLY-resources.json',dict(observed_clocks=clocks,boot_id=mc.BOOT,no_existing_heavy=True))
   extra=write('SOURCE-ONLY-extra.json',dict(fixture_only=True,runtime_authority=False))
   def three(ref):return mc.ref(Path(ref['path']))
   admission=dict(schema='mckernel.daemon-join-procfs64-current-admission.v1',status='ROOT_RESERVED_DAEMON_JOIN_PROCFS64_SOLE_HEAVY',author='/root',nonce=nonce,request=rr,boot_id=mc.BOOT,profile=mc.PREP['profile'],one_heavy=True,observed_clocks=clocks,expires_wall=clocks[0]+120,nonce_ledger_complete=True,consumed_nonces=['b'*32],resource_physical=three(resource),latest_postjoin_acceptance=three(extra),source_publication=three(extra))
   ar=write('SOURCE-ONLY-admission.json',admission)
   payload=dict(schema='mckernel.daemon-join-procfs64-release.v1',status='PASS_EXECUTION_RELEASE',execution_count=1,request=rr,nonce=nonce,boot_id=mc.BOOT,fetched_source_verified=True,terminal_policy=request['terminal_policy'],historical_observer=dict(path=str(owner.HISTORICAL_OBSERVER),sha256=owner.HISTORICAL_OBSERVER_SHA,prefix=list(owner.HISTORICAL_PREFIX),timeout_seconds=30),source_sha256=mapping,source_review=sr,current_admission=ar,author='/root')
   er=write('SOURCE-ONLY-execution-review.json',dict(decision='PASS_EXECUTION',implementation_ownership=False,reviewer='PURE_FIXTURE_ONLY',reviewed_release_payload_sha256=mc.sha(mc.canonical(payload)),runtime_authority=False))
   release=dict(payload,execution_review=er);lr=write('SOURCE-ONLY-release.json',release)
   def authenticate():
    with patch.object(owner,'check_campaign',return_value=clocks):return owner.authenticate(Path(rr['path']),rr['sha256'],Path(lr['path']),lr['sha256'])
   authenticate()
   for mutation in ['three-key-ref','wrong-source','consumed','stale']:
    bad=copy.deepcopy(release)
    if mutation=='three-key-ref':bad['source_review']['bytes']=1
    elif mutation=='wrong-source':bad['source_sha256']['repro/source.c']='0'*64
    elif mutation=='consumed':
     test=copy.deepcopy(admission);test['consumed_nonces'].append(nonce);bad['current_admission']=write('SOURCE-ONLY-consumed.json',test)
    else:
     test=copy.deepcopy(admission);test['observed_clocks']=[x-121 for x in clocks];bad['current_admission']=write('SOURCE-ONLY-stale.json',test)
    # A genuine fixture review binds each candidate payload, isolating its guard.
    newpayload={k:v for k,v in bad.items() if k!='execution_review'}
    bad['execution_review']=write('SOURCE-ONLY-exec-'+mutation+'.json',dict(decision='PASS_EXECUTION',implementation_ownership=False,reviewer='PURE_FIXTURE_ONLY',reviewed_release_payload_sha256=mc.sha(mc.canonical(newpayload)),runtime_authority=False))
    lr=write('SOURCE-ONLY-release.json',bad)
    with self.subTest(mutation=mutation),self.assertRaises(owner.Refusal):authenticate()
if __name__=='__main__':unittest.main(verbosity=2)
