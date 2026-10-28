"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
TEST_ONLY ephemeral full producer→resource→real guards→Hot→publisher integration.
All substituted effects use actual retained observations; no live guard or workload.
"""
from pathlib import Path
import contextlib,copy,importlib.util,json,os,sys,tempfile,types,unittest
from unittest.mock import patch
D=Path(__file__).resolve().parent;E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
sys.path.insert(0,str(D))

def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
import handoff_common as common
review=load('BFD_independent_finite',D/'finite_review.py');capture=load('BFD_actual_capture_producer',D/'capture_resources.py');publisher=load('BFD_actual_publisher',D/'publish_approved_ready.py');adapter=load('BFD_actual_once_adapter',D/'publish_after_independent_pass_once.py')
pins=common.read_json(D/'FROZEN-COHORT-PINS.json');profile=common.read_json_ref(pins['profile']);contract=common.read_json_ref(pins['contract'])

@contextlib.contextmanager
def scenario():
 with tempfile.TemporaryDirectory(prefix='TEST_ONLY_BFD_full_coupling_') as tmp:
  T=Path(tmp);A=T/'admission';H=T/'handoff';A.mkdir();H.mkdir()
  now=[1793169472.0,951578.0,966916.0]
  runner=load('actual_unchanged_BFD_runner',pins['runner']['path'])
  runner.current_operation_guard=lambda:list(now) # Substitute only effect; clamps untouched.
  refs={k:pins[k] for k in ['profile','runner','worker','holder_source','input_export','request_payload']}
  refs.update({f.name:common.reference(f) for f in D.glob('*.py')})
  gc=common.atomic_json(T/'TEST_ONLY_GUARD_CONFIGURATION.json',dict(TEST_ONLY=True,runtime_authority=None))
  b=dict(TEST_ONLY=True,reviewer=common.REVIEWER,Root_must_not_execute_approver=True,Root_capture_owner='/root',admission=str(A),nonce='f'*32,static_refs=refs,contract=pins['contract'],observer_source=common.reference(D/'observe_bfd_current61.py'),guard_facade=common.reference(D/'bfd_guard_facade.py'),guard_configuration=gc,finite_verifier=common.reference(D/'finite_review.py'),capture_source=common.reference(D/'capture_resources.py'),publisher_source=common.reference(D/'publish_approved_ready.py'),authorized_cutoffs=common.CUTOFFS)
  b['observer_schema']=common.reference(D/'OBSERVER-SCHEMA.BFD.SOURCE-ONLY.json');b['observer_schema_review']=common.atomic_json(T/'TEST_ONLY_SCHEMA_REVIEW.json',dict(TEST_ONLY=True,independent=True,decision='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING',reviewed_observer_schema=b['observer_schema']))
  rows=list(refs.values())+[b['observer_source'],b['guard_facade'],gc,b['finite_verifier'],b['capture_source'],b['publisher_source']]
  b['source_publication']=common.atomic_json(T/'TEST_ONLY_PUBLICATION.json',dict(TEST_ONLY=True,status='PASS_FETCHED_TEST_ONLY_FIXTURE',commit='a'*40,runtime_authority=None,rows=[dict(actual=r) for r in rows]))
  br=common.atomic_json(T/'TEST_ONLY_ENTRY_BINDINGS.json',b);b['_bindings']=br['path']
  original_load=review.load
  def safe_load(r,n):
   if r==pins['runner']:return runner
   return original_load(r,n)
  with patch.object(review,'load',side_effect=safe_load),patch.object(review,'clocks',side_effect=lambda:list(now)):
   c=review.cold(b,H)
  retained=common.read_json(E/'current116-actual-postjoin-current60-source-20261028-1/ACTUAL-POSTJOIN-OBSERVATION-2-CPU0.json')
  typed=load('retained35d5_shape',contract['Root61_observer_fragment']['current_observer_source']['path'])
  phy=typed.consumer_value(retained,[1793169467,951573,966911],[1793169470,951576,966914],common.CUTOFFS,common.BOOT)
  physical=capture.physical_value(b,phy,[1793169467,951573,966911],[1793169470,951576,966914]);pr=common.atomic_json(A/'ROOT-PREHOLDER-PHYSICAL-1.json',physical)
  (A/'HOLDER').mkdir()
  retainedready=common.read_json(E/'ROOT-CURRENT116-F03SEVEN-SHM-BUILD-ADMISSION-1/HOLDER/HOLDER.READY.json')
  bootstrap=common.read_json(E/'ROOT-CURRENT116-F03SEVEN-SHM-BUILD-ADMISSION-1/ROOT-HOLDER-BOOTSTRAP-GRANT.json');bootstrap.update(TEST_ONLY=True,nonce=b['nonce'],source=pins['holder_source'],runner=pins['runner'],worker=pins['worker'],profile=pins['profile'],native_custody_clearance=profile['native_custody_clearance'])
  bootstrap_ref=common.atomic_json(A/'ROOT-HOLDER-BOOTSTRAP-GRANT.json',bootstrap)
  ready=copy.deepcopy(retainedready);ready.update(TEST_ONLY=True,nonce=b['nonce'],bootstrap=bootstrap_ref);ready_ref=common.atomic_json(A/'HOLDER/HOLDER.READY.json',ready)
  inputs=dict(TEST_ONLY=True,author='/root',decision='BIND_BFD_ACTUAL_HELD_BUILD_RESOURCES',maximum_invocations=1,nonce=b['nonce'],root_attests_only_intervening_holder_preparation=True,actual_reservations_attested=True,profile=pins['profile'],nonce_ledger=contract['Root61_observer_fragment']['current_ledger'],native_custody_clearance=profile['native_custody_clearance'],physical_observation=pr,holder_ready=ready_ref,holder_bootstrap=bootstrap_ref,at_epoch=1793169471.0,other_reserved_memory_bytes=2<<30,other_reserved_pids=64,aggregate_pid_budget=576,fresh_output_root=profile['actual_output_root'])
  ir=common.atomic_json(A/'ROOT-ACTUAL-RESOURCE-INPUT-1.json',inputs);inputs['_input_ref']=ir
  oldresource=common.read_json(E/'ROOT-CURRENT116-F03SEVEN-SHM-BUILD-ADMISSION-1/ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json');obs=copy.deepcopy(oldresource['actual_observations']);obs.update(physical_ref=pr,holder_start=ready['holder']['starttime'],holder_fd_device_inode=[27,4],capture_profile=dict(affinity=[0],AS_bytes=2<<30,CPU_seconds=60));obs.pop('physical_observation',None)
  resource,pending=capture.held_values(b,inputs,physical,ready,bootstrap,obs,list(now));rr=common.atomic_json(A/'ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json',resource);pending['resource_authority']=rr;gr=common.atomic_json(A/'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json',pending)
  marker=dict(status='ROOT_HELD_CAPTURE_COMPLETE_ZERO_POSITIVE_JOIN',returncode=0,direct_child_joined=True,group_absent=True,closed_streams=True,prewarm_ready=c['ready_ref'],nonce=b['nonce'],admission=str(A),capture_source=b['capture_source'],pending_input=gr,resource=rr,physical=pr,root_resource_input=ir,holder_ready=ready_ref,holder_bootstrap=bootstrap_ref)
  common.atomic_json(H/'ROOT-HELD-CAPTURE.COMPLETE.json',marker)
  real_read=Path.read_text;real_stat=Path.stat
  def retained_text(path,*a,**k):
   p=str(path)
   if p=='/proc/locks':return obs['lock_rows']
   if p=='/proc/meminfo':return 'MemAvailable: %d kB\n'%(obs['memory']['MemAvailable']//1024)
   if p=='/proc/loadavg':return '0 0 0 1/%d 1\n'%obs['host_threads']
   if p=='/proc/sys/kernel/threads-max':return str(obs['thread_limit'])
   return real_read(path,*a,**k)
  def retained_stat(path,*a,**k):
   if str(path)=='/proc/%s/fd/3'%ready['holder']['pid']:return types.SimpleNamespace(st_dev=27,st_ino=4)
   return real_stat(path,*a,**k)
  with patch.object(Path,'read_text',retained_text),patch.object(Path,'stat',retained_stat),patch.object(review,'birth',return_value=ready['holder']['starttime']):
   yield dict(T=T,A=A,H=H,b=b,c=c,marker=marker,now=now,runner=runner,resource=resource,pending=pending)

class Coupling(unittest.TestCase):
 def test_full_real_producer_resource_guard_hot_postfsync_publisher(self):
  with scenario() as x:
   passed=review.hot(x['c'],x['marker']);review.publish_pass(x['c'],passed)
   self.assertTrue((x['H']/'INDEPENDENT-FINITE-REVIEW.PASS.json').exists())
   # Real publisher CLI adapter delegates to real publisher; substitute only
   # frozen runner import's live account guard and clock effect.
   original=publisher.importlib.util.module_from_spec
   def module(spec):
    if spec.name=='BFD_frozen_ready_runner':return x['runner']
    if spec.name=='existing_original_build_publisher':return publisher
    return original(spec)
   spec_loader=publisher.importlib.util.spec_from_file_location
   class Loader:
    def exec_module(self,m):pass
   def spec(name,path):
    if name in ['BFD_frozen_ready_runner','existing_original_build_publisher']:return types.SimpleNamespace(name=name,loader=Loader())
    return spec_loader(name,path)
   with patch.object(publisher.time,'time',return_value=x['now'][0]),patch.object(adapter,'clocks',side_effect=lambda:list(x['now'])),patch.object(publisher.importlib.util,'spec_from_file_location',side_effect=spec),patch.object(publisher.importlib.util,'module_from_spec',side_effect=module),patch.object(sys,'argv',['once','--bindings',x['b']['_bindings'],'--handoff',str(x['H'])]):
    adapter.main()
    with self.assertRaises(ValueError):adapter.main()
   self.assertTrue((x['A']/'HOLDER/ROOT-BUILD-GRANT.READY.json').exists())
   self.assertTrue((x['H']/'ROOT-PUBLICATION.ONCE-CLAIM.json').exists())
 def test_actual_capture_owner_prewarm_taskset_and_positive_join(self):
  with scenario() as x:
   owner=load('actual_Root_capture_owner',D/'root_capture_once.py');H=x['T']/'owner_handoff';H.mkdir()
   ready=common.read_json(x['H']/'PREWARM_READY.json');common.atomic_json(H/'PREWARM_READY.json',ready)
   common.atomic_json(H/'ROOT-PHYSICAL-CAPTURE.COMPLETE.json',dict(returncode=0,direct_child_joined=True,group_absent=True,closed_streams=True))
   class Child:
    pid=800001
    def wait(self,timeout):return 0
   seen=[]
   def popen(argv,**kwargs):seen.append(argv);return Child()
   with patch.object(owner,'birth',side_effect=lambda pid:ready['starttime'] if pid==ready['pid'] else 100),patch.object(owner,'clocks',side_effect=lambda:list(x['now'])),patch.object(owner.subprocess,'Popen',side_effect=popen),patch.object(owner.os,'killpg',side_effect=ProcessLookupError),patch.object(sys,'argv',['owner','--bindings',x['b']['_bindings'],'--handoff',str(H),'--phase','held']):owner.main()
   self.assertEqual(seen[0][:3],['/usr/bin/taskset','-c','0'])
   marker=common.read_json(H/'ROOT-HELD-CAPTURE.COMPLETE.json');self.assertTrue(marker['direct_child_joined'] and marker['group_absent'] and marker['closed_streams'])
 def test_actual_data_filler_and_common_physical_configuration_consumers(self):
  filler=load('actual_BFD_Root_data_filler',D/'prepare_entry_inputs.py')
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_BFD_configs_') as tmp:
   T=Path(tmp)
   import shutil
   for p in D.glob('*.py'):shutil.copyfile(p,T/p.name)
   for n in ['ACTUAL-PINS.json','FROZEN-COHORT-PINS.json','OBSERVER-SCHEMA.BFD.SOURCE-ONLY.json']:shutil.copyfile(D/n,T/n)
   def write(n,v):return common.atomic_json(T/n,v)
   facade=common.reference(T/'bfd_guard_facade.py');config=write('TEST_ONLY_FACADE.json',dict(TEST_ONLY=True,author='/root',runtime_authority=None))
   physical=common.read_json(D/'PHYSICAL-HISTORY-CONFIG.TEMPLATE.NOT-AUTHORITY.json');physical.update(TEST_ONLY=True,author='/root',guard_adapter=facade,guard_config=config)
   pv=common.read_json(D/'PHYSICAL-CONFIG-REVIEW.TEMPLATE.NOT-A-PASS.json');pv.update(TEST_ONLY=True,independent=True,implementation_ownership=False,decision='PASS_EXACT_NEW_WINDOW_PHYSICAL_HISTORY_SUCCESSOR',guard_adapter=facade,guard_config=config)
   physical['independent_review']=write('TEST_ONLY_PHYSICAL_REVIEW.json',pv);ph=write('TEST_ONLY_PHYSICAL.json',physical)
   cv=dict(TEST_ONLY=True,independent=True,implementation_ownership=False,decision='PASS_EXACT_ROOT59_CONFIGURED_NEW_WINDOW_OBSERVER_DEPENDENCIES',reviewed_observer=common.reference(T/'observe_bfd_root59_history.py'),reviewed_account_window_guard=facade,reviewed_account_window_guard_configuration=config,reviewed_physical_history_observer=physical['successor_source'],reviewed_physical_history_configuration=ph)
   tv=dict(TEST_ONLY=True,independent=True,implementation_ownership=False,decision='PASS_EXACT_ROOT61_BFD_OBSERVER_DEPENDENCIES',observer=common.reference(T/'observe_bfd_current61.py'),guard_adapter=facade,guard_configuration=config)
   q=common.read_json(D/'ROOT-ENTRY-DATA.TEMPLATE.NOT-AUTHORITY.json');q.update(TEST_ONLY=True,author='/root',Root_attests_latest_Root61_no_intervening_operation=True,nonce='f'*32,facade_configuration=config,physical_configuration=ph,physical_configuration_review=physical['independent_review'],common_dependency_review=write('TEST_ONLY_COMMON_REVIEW.json',cv),top_dependency_review=write('TEST_ONLY_TOP_REVIEW.json',tv),Root_authorizes_one_holder_only_bootstrap=False,observer_schema_review=write('TEST_ONLY_SCHEMA_REVIEW.json',dict(TEST_ONLY=True,independent=True,decision='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING',reviewed_observer_schema=common.reference(T/'OBSERVER-SCHEMA.BFD.SOURCE-ONLY.json'))))
   with patch.object(filler,'D',T):b=filler.fill(q)
   actual=load('actual_new_BFD_common_dependency_consumer',T/'observe_bfd_root59_history.py');original=actual.load;calls=[]
   fake=types.SimpleNamespace(configure=lambda r:calls.append(r))
   def configured(r,n):
    if n=='root59_configured_new_window_guard':return fake
    return original(r,n)
   with patch.object(actual,'load',side_effect=configured):g,phm=actual.configured_dependencies(common.read_json(T/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json'))
   self.assertEqual(calls,[config]);self.assertEqual(phm.binding()['guard_adapter'],facade);self.assertEqual(b['authorized_cutoffs'],common.CUTOFFS)
 def test_reject_full_resource_mutation(self):
  with scenario() as x:
   x['resource']['other_reserved_pids']=65
   # A changed byte subject cannot silently pass the actual marker chain.
   with self.assertRaises(ValueError):review.hot(x['c'],dict(x['marker'],resource=dict(x['marker']['resource'],sha256='0'*64)))
 def test_READY_postfsync_original120s(self):
  with scenario() as x:
   passed=review.hot(x['c'],x['marker']);original=publisher.importlib.util.module_from_spec;spec_loader=publisher.importlib.util.spec_from_file_location;write=publisher.atomic_json
   class Loader:
    def exec_module(self,m):pass
   def spec(name,path):
    if name=='BFD_frozen_ready_runner':return types.SimpleNamespace(name=name,loader=Loader())
    return spec_loader(name,path)
   def module(spec):
    if spec.name=='BFD_frozen_ready_runner':return x['runner']
    return original(spec)
   def delayed(path,value,before_publish=None):
    def callback():
     x['now'][0]+=121
     before_publish()
    return write(path,value,before_publish=callback if Path(path).name=='ROOT-BUILD-GRANT.READY.json' else before_publish)
   with patch.object(publisher.time,'time',return_value=x['now'][0]),patch.object(publisher,'atomic_json',side_effect=delayed),patch.object(publisher.importlib.util,'spec_from_file_location',side_effect=spec),patch.object(publisher.importlib.util,'module_from_spec',side_effect=module):
    with self.assertRaises(ValueError):publisher.publish(x['A'],passed['approved_input_sha256'])
   self.assertFalse((x['A']/'HOLDER/ROOT-BUILD-GRANT.READY.json').exists())
 def test_hot_original120s(self):
  with scenario() as x:
   x['now'][0]+=121
   with self.assertRaises(RuntimeError):review.hot(x['c'],x['marker'])
 def test_postfsync_original120s(self):
  with scenario() as x:
   passed=review.hot(x['c'],x['marker']);x['now'][0]+=121
   with self.assertRaises(ValueError):review.publish_pass(x['c'],passed)
   self.assertFalse((x['H']/'INDEPENDENT-FINITE-REVIEW.PASS.json').exists())

if __name__=='__main__':unittest.main(verbosity=2)
