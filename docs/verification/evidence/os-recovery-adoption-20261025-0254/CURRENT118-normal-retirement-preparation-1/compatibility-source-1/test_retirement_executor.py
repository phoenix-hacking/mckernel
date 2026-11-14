"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Retained facts plus substituted effects only; no actual lock/process/Docker/guard calls.
"""
from pathlib import Path
import copy,importlib.util,json,os,subprocess,tempfile,time,types,unittest
from unittest.mock import patch
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('CURRENT118_retirement_candidate',D/'retire_exact_current118_stopped_container.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
B=m.bindings();P,PROTECTED,PROFILE,CLAIM,PLAN,TERMINAL=m.validate_retained(B)
NORMAL=m.load(B['normal'],'CURRENT118_retirement_existing_normal_for_pure_tests')

def fixture():
 # Independent OCI expectation parsed from the actual original CLI, not the
 # production profile-validator implementation. Immutable image defaults come
 # from the retained SDK full inspect of the same exact image.
 labels=copy.deepcopy(B['approved_image_labels'])
 image=dict(Id=PROFILE['inputs']['image'],Config=dict(Env=B['approved_image_environment'],Labels=labels))
 config=dict(Image=image['Id'],User='1000:1000',WorkingDir=B['working_directory'],Entrypoint=['/usr/bin/python3'],Cmd=['-I','-B','/build-only-worker.py','/build-only-plan.json'],Env=B['approved_image_environment'],Labels=labels,OpenStdin=False,StdinOnce=False,Tty=False)
 host=dict(ReadonlyRootfs=True,Privileged=False,AutoRemove=False,NetworkMode='none',CpusetCpus='2-5',CpusetMems='',Memory=12884901888,MemorySwap=12884901888,PidsLimit=512,CgroupParent='',PidMode='',IpcMode='private',UTSMode='',UsernsMode='',CpuShares=0,CpuPeriod=0,CpuQuota=0,NanoCpus=0,CapDrop=['ALL'],CapAdd=None,SecurityOpt=['no-new-privileges'],Tmpfs={'/tmp':'rw,nosuid,nodev,size=1073741824,mode=1777'})
 binds=[];declared=[];argv=CLAIM['argv']
 for n,arg in enumerate(argv):
  if arg!='--mount':continue
  options=argv[n+1].split(',');values=dict(x.split('=',1) for x in options if '=' in x);readonly='readonly' in options
  binds.append(dict(Type='bind',Source=values['source'],Destination=values['target'],RW=not readonly,Propagation='rprivate'))
  declared.append(dict(Type='bind',Source=values['source'],Target=values['target'],ReadOnly=readonly))
 host['Mounts']=declared
 item=dict(Id=B['cid'],Name='/'+B['name'],State=copy.deepcopy(TERMINAL['state']),Image=image['Id'],Config=config,HostConfig=host,Mounts=binds)
 return item,image

def check(item,image):return m.validate_profile(item,image,B,P,PROFILE,CLAIM,TERMINAL)

class FakeOps:
 def __init__(self,item=None,image=None,fail=None):self.item,self.image=fixture() if item is None else (item,image);self.events=[];self.fail=fail;self.mutated=False
 def event(self,name):
  self.events.append(name)
  if self.fail==name:raise m.Refusal('TEST_ONLY substituted '+name)
 def acquire(self):self.event('acquire')
 def safe(self):self.event('safe');return dict(clocks=[1793218000,1000000,1015000])
 def census(self,label,present):
  self.event(label)
  if present:check(self.item,self.image)
  return dict(clocks=[1793218000,1000000,1015000]),dict(TEST_ONLY=True)
 def logs(self):self.event('logs')
 def claim_once(self,proof):self.event('claim_once')
 def remove(self):self.event('rm');self.mutated=True
 def absence(self):self.event('absence')
 def finish(self):self.event('finish');return dict(TEST_ONLY=True,mutation_count=self.events.count('rm'))

class ProfileAndOrder(unittest.TestCase):
 def test_actual_retained_bindings_and_independent_OCI_expectation(self):
  self.assertTrue(check(*fixture()));self.assertEqual(len(PROTECTED['records']),46)
 def test_complete_preinspect_commit_postproof_order(self):
  ops=FakeOps();self.assertEqual(m.transaction(ops)['mutation_count'],1)
  self.assertEqual(ops.events,['acquire','safe','PREINSPECT-1','logs','PREINSPECT-2','claim_once','rm','absence','POSTPROOF','finish'])
 def test_profile_mismatches_never_reach_remove(self):
  changes=[('Id','0'*64),('Name','/other'),('Image','sha256:'+'0'*64)]
  for key,value in changes:
   item,image=fixture();item[key]=value;ops=FakeOps(item,image)
   with self.subTest(key=key),self.assertRaises(m.Refusal):m.transaction(ops)
   self.assertNotIn('rm',ops.events)
  fields=[('User','0:0'),('WorkingDir','/other'),('Cmd',['other']),('Env',['EXTRA=1']),('Labels',{'mckernel.owner':B['nonce']}),('Tty',True)]
  for key,value in fields:
   item,image=fixture();item['Config'][key]=value;ops=FakeOps(item,image)
   with self.subTest(config=key),self.assertRaises(m.Refusal):m.transaction(ops)
   self.assertNotIn('rm',ops.events)
  fields=[('Memory',12884901889),('MemorySwap',-1),('PidsLimit',513),('CpusetCpus','0-7'),('NetworkMode','host'),('ReadonlyRootfs',False),('Privileged',True),('CgroupParent','other'),('NanoCpus',4000000000),('Tmpfs',{}),('CapAdd',['SYS_ADMIN'])]
  for key,value in fields:
   item,image=fixture();item['HostConfig'][key]=value;ops=FakeOps(item,image)
   with self.subTest(host=key),self.assertRaises(m.Refusal):m.transaction(ops)
   self.assertNotIn('rm',ops.events)
  for mutate in [lambda i:i['Mounts'].pop(),lambda i:i['Mounts'][0].update(RW=False),lambda i:i['Mounts'][0].update(Source='/other'),lambda i:i['Mounts'].append(copy.deepcopy(i['Mounts'][0])),lambda i:i['State'].update(Pid=9),lambda i:i['State'].update(ExitCode=1)]:
   item,image=fixture();mutate(item);ops=FakeOps(item,image)
   with self.assertRaises(m.Refusal):m.transaction(ops)
   self.assertNotIn('rm',ops.events)
 def test_preproof_failures_have_no_remove(self):
  for phase in ['acquire','safe','PREINSPECT-1','logs','PREINSPECT-2','claim_once']:
   ops=FakeOps(fail=phase)
   with self.subTest(phase=phase),self.assertRaises(m.Refusal):m.transaction(ops)
   self.assertNotIn('rm',ops.events)
 def test_postproof_failure_stays_one_mutation_and_does_not_finish(self):
  for phase in ['absence','POSTPROOF','finish']:
   ops=FakeOps(fail=phase)
   with self.subTest(phase=phase),self.assertRaises(m.Refusal):m.transaction(ops)
   self.assertEqual(ops.events.count('rm'),1)
 def test_census_preserves_normal_and_adds_groups(self):
  code=m.process_source(NORMAL,P);compile(code,'TEST_ONLY_NOT_EXECUTED','exec')
  caller=[999999,'100'];rows=[[1,0,'1'],[999999,1,'100']];groups=[[1,0,'1',1,1],[999999,1,'100',999999,999999]]
  report=dict(schema='fp-save-image.proc.v1',uid=0,boot_id=B['boot'],challenge='c',caller=caller,publishers=[],snapshots=[rows,copy.deepcopy(rows)],groups=[groups,copy.deepcopy(groups)])
  self.assertTrue(m.validate_process(report,NORMAL,B,'c',caller,[]))
  for mutate in [lambda x:x.update(publishers=[[888,'1','gcc']]),lambda x:x['groups'][1][0].__setitem__(3,2124365),lambda x:x['groups'][1].pop(),lambda x:x['snapshots'][0].append([2124454,1,'101432667'])]:
   changed=copy.deepcopy(report);mutate(changed)
   with self.assertRaises((m.Refusal,NORMAL.Refusal)):m.validate_process(changed,NORMAL,B,'c',caller,[])
 def test_inventory_exact_presence_absence_and_active_overlap(self):
  row=dict(ID=B['cid'],Names=B['name'],Labels='name=rockylinux',State='exited')
  self.assertEqual(len(m.validate_inventory(json.dumps(row),B,True)),1);self.assertEqual(m.validate_inventory('',B,False),[])
  for raw,present in [(json.dumps(row),False),('',True),(json.dumps(dict(row,Names='other')),True),(json.dumps(dict(row,State='running')),True),(json.dumps(row)+'\n'+json.dumps(row),True)]:
   with self.assertRaises(m.Refusal):m.validate_inventory(raw,B,present)
 def test_postfsync_delay_prevents_commit(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_CURRENT118_claim_') as tmp:
   now=[1793218000,1000000,1015000];fake=types.SimpleNamespace(out=Path(tmp),b=B,r={'_reference':B['packet']},proofs=[B['packet']],safe=lambda:dict(clocks=now),rm_claimed=False)
   original=m.write_new
   def delayed(path,value):
    result=original(path,value);now[0]+=121;return result
   with patch.object(m,'write_new',side_effect=delayed),self.assertRaisesRegex(m.Refusal,'postfsync'):m.Actual.claim_once(fake,dict(clocks=[1793218000,1000000,1015000]))
   self.assertFalse(fake.rm_claimed)

class Transport(unittest.TestCase):
 def test_positive_wait4_metrics_without_spawning(self):
  process=types.SimpleNamespace(pid=999998,returncode=None);clock=types.SimpleNamespace(monotonic=lambda:10.,time=lambda:20.);raw=b'999998 (TEST_ONLY) '+b' '.join([b'S',b'1',b'999998',b'999998']+[b'0']*15+[b'1234']+[b'0']*35)
  usage=types.SimpleNamespace(ru_utime=.1,ru_stime=.2,ru_maxrss=44)
  with patch.object(Path,'read_bytes',return_value=raw):child=m.Wait4Child(process,Path('/TEST_ONLY'),clock=clock,wait4=lambda pid,flags:(pid,0,usage))
  self.assertEqual(child.wait(.1),0);self.assertTrue(child.record['positive_wait4']);self.assertEqual(child.record['birth'] if 'birth' in child.record else child.birth,1234);self.assertEqual(child.record['peak_rss_kib'],44)
 def transport_case(self,timeout=False):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_CURRENT118_transport_') as tmp:
   out=Path(tmp);cls,ns=m.transport(B);client=cls(out,m.Stop())
   fakeproc=types.SimpleNamespace(pid=999997,returncode=None)
   class Child:
    def __init__(self,process,capture):
     self.pid=process.pid;self.process=process;self.capture=capture;self.returncode=None;self.record=dict(pid=self.pid,birth=1234,process_group=self.pid,started_epoch=1.,started_monotonic=1.,positive_wait4=False)
    def wait(self,timeout):
     if timeout<.01:raise subprocess.TimeoutExpired('TEST_ONLY',timeout)
     self.returncode=0;self.record.update(positive_wait4=True,wait4_pid=self.pid,wait4_status=0,returncode=0,finished_epoch=2.,wall_seconds=1.,user_cpu_seconds=.1,system_cpu_seconds=.1,peak_rss_kib=12);return 0
    def poll(self):return self.returncode
   argv=m.PREFIX+['rm','--',B['cid']]
   with patch.object(m.subprocess,'Popen',return_value=fakeproc),patch.object(m,'Wait4Child',Child),patch.object(client,'_surviving_group_members',return_value=[]),patch.object(os,'killpg') as killed:
    if timeout:
     with self.assertRaises(RuntimeError):client.exact(argv,.001)
     self.assertTrue(client.client_retirement_unproven)
    else:
     self.assertEqual(client.exact(argv,30).returncode,0);self.assertFalse(client.client_retirement_unproven)
    killed.assert_not_called()
   receipt=m.authenticated(client.receipts[0],True);self.assertTrue(receipt['streams_closed']);self.assertEqual(receipt['signals_sent'],0);self.assertEqual(receipt['argv'],argv)
   return receipt
 def test_existing_capture_transport_positive_receipt(self):self.assertTrue(self.transport_case()['positive_wait4'])
 def test_existing_capture_transport_timeout_sends_no_signal_and_retains_uncertainty(self):self.assertTrue(self.transport_case(True)['client_retirement_unproven'])
 def test_argv_scope_and_once_guard_before_effect(self):
  fake=types.SimpleNamespace(b=B,p=P,profile=PROFILE,normal=NORMAL,m=types.SimpleNamespace(proc_stat=lambda pid:['0']*19+['1']),rm_claimed=False,rm_invoked=False,safe=lambda:(_ for _ in ()).throw(AssertionError('must reject argv before safe/effect')))
  for args in [['rm','--force',B['cid']],['rm','--','0'*64],['prune'],['rm','--',B['cid']]]:
   with self.assertRaises(m.Refusal):m.Actual.call(fake,args)
  fake.rm_claimed=True;fake.rm_invoked=True
  with self.assertRaises(m.Refusal):m.Actual.call(fake,['rm','--',B['cid']])

class ReleaseAndConsumer(unittest.TestCase):
 def release_fixture(self,T):
  files=dict(executor=m.reference(m.SELF),bindings=m.reference(D/'BINDINGS.json'))
  files.update({k:B[k] for k in ('primitive','normal','backend','guardian','prior_observer','packet','protected','base_reviewed_executor','wait_status_helper','pre_compatibility_executor')})
  ledger=json.loads((D/'ROOT-PENDING-LEDGER.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
  ledger.update(TEST_ONLY=True,author='/root',complete_within_declared_current_boundary=True,root_attests_no_unlisted_post_boundary_execution_or_custody_operation=True)
  ledger[B['ledger_key']]['actual_holder_tool_join_receipt']=B['parent_tool_join']
  lr=m.write_new(T/'TEST_ONLY_LEDGER.json',ledger)
  source=dict(TEST_ONLY=True,decision='PASS_SOURCE',independent=True,implementation_ownership=False,files=files,bindings=files['bindings'],reviewer='/root/independent_fixture',source_checkpoint='a'*40)
  sr=m.write_new(T/'TEST_ONLY_SOURCE.json',source)
  publication=dict(TEST_ONLY=True,status='PASS_FETCHED_TEST_ONLY_FIXTURE',commit='a'*40,runtime_authority=None,rows=[dict(actual=r) for r in files.values()]);pr=m.write_new(T/'TEST_ONLY_PUBLICATION.json',publication)
  r=dict(TEST_ONLY=True,schema='mckernel.current118-build.stopped-container-retirement.release.v1',author='/root',decision='GRANT_ONE_EXACT_STOPPED_CURRENT118_CONTAINER_RETIREMENT',maximum_invocations=1,bindings=files['bindings'],files=files,parent_tool_join=B['parent_tool_join'],cid=B['cid'],nonce=B['nonce'],signals_allowed=0,records_released=[],cutoffs=B['cutoffs'],credit_run_id='7f4af94a83b14cc08f97401f5891d965',credit_ceiling='57774.852125',minimum_cumulative_spent='22812.3311',Root_attests_no_unlisted_intervening_operation=True,actual_account_identity_operation_admission_accepted=True,current_ledger=lr,source_review=sr,source_checkpoint='a'*40,fetched_source_verified=True,source_publication=pr,output=str(D/'actual-retirement-TEST_ONLY_UNRUN'))
  er=m.write_new(T/'TEST_ONLY_EXECUTION.json',dict(TEST_ONLY=True,decision='PASS_EXECUTION',independent=True,implementation_ownership=False,reviewer='/root/independent_fixture',release_payload_sha256=m.hashlib.sha256(m.canonical(r)).hexdigest()));r['execution_review']=er
  return r,files
 def test_exact_release_consumer_static_only(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_CURRENT118_release_') as tmp:
   r,files=self.release_fixture(Path(tmp));self.assertEqual(m.validate_release(r,B,files),D/'actual-retirement-TEST_ONLY_UNRUN')
 def test_release_refuses_wrong_operation_budget_and_self_review_before_effect(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_CURRENT118_release_negative_') as tmp:
   r,files=self.release_fixture(Path(tmp))
   for key,value in [('cid','0'*64),('nonce','0'*32),('maximum_invocations',True),('signals_allowed',1),('records_released',['other']),('credit_run_id','reset'),('minimum_cumulative_spent','0'),('cutoffs',[1793253601,*B['cutoffs'][1:]]),('Root_attests_no_unlisted_intervening_operation',False),('fetched_source_verified',False)]:
    bad=copy.deepcopy(r);bad[key]=value
    with self.subTest(key=key),patch.object(m.subprocess,'Popen',side_effect=AssertionError('no effect allowed')),self.assertRaises(m.Refusal):m.validate_release(bad,B,files)
 def test_current_ledger_cannot_reuse_Root61_or_clear_physical_pending(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_CURRENT118_ledger_negative_') as tmp:
   T=Path(tmp);r,files=self.release_fixture(T);ledger=m.authenticated(r['current_ledger'],True)
   for n,mutate in enumerate([lambda x:x['consumed_nonces'].pop(),lambda x:x.update(current_physical_clearance_pending=False),lambda x:x[B['ledger_key']].update(container_id='0'*64),lambda x:x[B['ledger_key']].update(actual_holder_tool_join_receipt=None)]):
    bad=copy.deepcopy(r);value=copy.deepcopy(ledger);mutate(value);bad['current_ledger']=m.write_new(T/('TEST_ONLY_BAD_LEDGER_%d.json'%n),value)
    with self.assertRaises(m.Refusal):m.validate_release(bad,B,files)
 def test_success_result_still_requires_parent_join_and_fresh_current(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_CURRENT118_result_') as tmp:
   T=Path(tmp);release=m.write_new(T/'TEST_ONLY_RELEASE.json',dict(TEST_ONLY=True,runtime_authority=None));receipts=[];actor=dict(pid=999999,birth=100)
   rows=[[1,0,'1'],[actor['pid'],1,str(actor['birth'])]];groups=[[1,0,'1',1,1],[actor['pid'],1,str(actor['birth']),actor['pid'],actor['pid']]]
   code=m.process_source(NORMAL,P);report=dict(schema='fp-save-image.proc.v1',uid=0,boot_id=B['boot'],challenge='c'*32,caller=[actor['pid'],str(actor['birth'])],publishers=[],snapshots=[rows,copy.deepcopy(rows)],groups=[groups,copy.deepcopy(groups)])
   item,image=fixture();inventory=dict(ID=B['cid'],Names=B['name'],Labels='name=rockylinux',State='exited')
   process=['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',code,'c'*32,str(actor['pid']),str(actor['birth'])]
   commands=[(process,json.dumps(report)),(m.PREFIX+['ps','-a','--no-trunc','--format','{{json .}}'],json.dumps(inventory)),(m.PREFIX+['inspect','--type','container',B['cid']],json.dumps([item])),(m.PREFIX+['image','inspect',PROFILE['inputs']['image']],json.dumps([image])),(m.PREFIX+['logs','--',B['cid']],''),(process,json.dumps(report)),(m.PREFIX+['ps','-a','--no-trunc','--format','{{json .}}'],json.dumps(inventory)),(m.PREFIX+['inspect','--type','container',B['cid']],json.dumps([item])),(m.PREFIX+['image','inspect',PROFILE['inputs']['image']],json.dumps([image])),(m.PREFIX+['rm','--',B['cid']],B['cid']+'\n'),(m.PREFIX+['ps','--all','--quiet','--no-trunc','--filter','id='+B['cid']],''),(m.PREFIX+['ps','--all','--quiet','--no-trunc','--filter','name=^/'+B['name']+'$'],''),(process,json.dumps(report)),(m.PREFIX+['ps','-a','--no-trunc','--format','{{json .}}'],'')]
   for n,(argv,stdout) in enumerate(commands):
    c=T/('TEST_ONLY_command%d'%n);c.mkdir();raw={}
    for name,value in [('stdout',stdout.encode()),('stderr',b'')]:
     (c/name).write_bytes(value);raw[name]=m.reference(c/name)
    raw['status.json']=m.write_new(c/'status.json',dict(TEST_ONLY=True,state='exited',pid=999900+n,exit_code=0,argv=argv))
    receipt=dict(TEST_ONLY=True,pid=999900+n,birth=1234+n,positive_wait4=True,wait4_pid=999900+n,wait4_status=0,returncode=0,group_absent=True,group_members=[],streams_closed=True,client_retirement_unproven=False,signals_sent=0,started_epoch=1793218000,wall_seconds=.1,user_cpu_seconds=.01,system_cpu_seconds=.01,peak_rss_kib=12,argv=argv,raw=raw)
    receipts.append(m.write_new(c/'JOIN-WAIT4.json',receipt))
   proofs=[]
   for label,present,end in [('PREINSPECT-1',True,4),('PREINSPECT-2',True,9),('POSTPROOF',False,14)]:
    proof=dict(TEST_ONLY=True,schema='mckernel.current118-build.retirement-proof.v1',label=label,present=present,cid=B['cid'],nonce=B['nonce'],command_receipts=receipts[:end],process=report,inventory=[inventory] if present else [],container=[item] if present else None,image=[image] if present else None,clocks=[1793218000,1000000,1015000])
    proofs.append(m.write_new(T/('TEST_ONLY_'+label+'.json'),proof))
   value=dict(TEST_ONLY=True,schema='mckernel.current118-build.stopped-container-retirement.result.v1',status='PASS_EXACT_CURRENT118_STOPPED_CONTAINER_RETIRED_PENDING_POSTJOIN_CURRENT',scope=m.SCOPE,cid=B['cid'],nonce=B['nonce'],container_absent=True,signals_sent=0,records_released=[],bindings=m.reference(D/'BINDINGS.json'),protected_originals=B['protected'],native_acceptance=False,fullfile_acceptance=False,parent_positive_join_and_fresh_current_acceptance_required=True,release=release,command_receipts=receipts,proofs=proofs,cleanup_actor=actor)
   self.assertEqual(len(m.validate_result(value,B)),14)
   for key,replacement in [('parent_positive_join_and_fresh_current_acceptance_required',False),('native_acceptance',True),('fullfile_acceptance',True),('cid','0'*64),('command_receipts',receipts[:-1]),('proofs',proofs[:-1])]:
    bad=copy.deepcopy(value);bad[key]=replacement
    with self.subTest(key=key),self.assertRaises(m.Refusal):m.validate_result(bad,B)

if __name__=='__main__':unittest.main(verbosity=2)
