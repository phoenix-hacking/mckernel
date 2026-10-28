"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure retained-data routing regression. All guard effects substituted; no live guard.
"""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,shutil,sys,tempfile,types,unittest
from unittest.mock import patch
D=Path(__file__).resolve().parent;C=D/'cohort';H=D/'entry'
E=D.parent
sys.path.insert(0,str(H))

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def put(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n');return ref(p)
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class Routing(unittest.TestCase):
 def test_retained_typed_data_validators_follow_private_observer_chain(self):
  top=load('TEST_ONLY_actual_top_observer',H/'observe_bfd_current61.py')
  self.assertEqual(top.PINS['current60_source'],ref(H/'observe_bfd_current60_history.py'))
  actual=read(H/'ACTUAL-PINS.json');self.assertEqual(actual['common'],ref(H/'observe_bfd_root59_history.py'))
  ledger,free,extension,actors=top.validate_current(top.CURRENT)
  self.assertEqual(len(ledger['consumed_nonces']),70)
  self.assertEqual(ref(top.CURRENT['latest_free']['path'])['sha256'],'6c83eee41b7e90d0f055034b9bbd30cfc9e32efac9e8285a90fc8948f7b82e7d')
  self.assertEqual(len(actors),61) # 51 prior + holder/runner + seven HOST + capture2.
 def test_production_commands_export_and_resource_implementations_unchanged(self):
  old=E/'m15-bfd-default-next-integration-source-20261028-1/new-window-producer-cohort-source-1/latest-root61-consumer-successor-source-1'
  for n in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','REQUEST.SOURCE-ONLY.json','ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json']:
   self.assertEqual((C/n).read_bytes(),(old/'root-adopted-dispatch-1'/n).read_bytes())
  for n in ['capture_resources.py','finite_review.py','publish_approved_ready.py','publish_after_independent_pass_once.py','root_capture_once.py','prepare_entry_inputs.py','bfd_guard_facade.py','observe_bfd_root59_history.py','observe_bfd_current60_history.py']:
   self.assertEqual((H/n).read_bytes(),(old/'actual-entry-coupling-source-1'/n).read_bytes())
  self.assertEqual(read(C/'PROFILE.SOURCE-ONLY.json')['exact_commands'],read(old/'root-adopted-dispatch-1/PROFILE.SOURCE-ONLY.json')['exact_commands'])
  self.assertEqual(read(C/'PROFILE.SOURCE-ONLY.json')['inputs'],read(old/'root-adopted-dispatch-1/PROFILE.SOURCE-ONLY.json')['inputs'])
 def routed(self,mutate=None):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_BFD_restart_route_') as tmp:
   T=Path(tmp);A=T/'cohort';B=T/'entry';A.mkdir();B.mkdir()
   for p in C.iterdir():shutil.copyfile(p,A/p.name)
   shutil.copyfile(H/'bfd_guard_facade.py',B/'bfd_guard_facade.py')
   pins=read(H/'FROZEN-COHORT-PINS.json');pins['admission']=str(A);put(B/'FROZEN-COHORT-PINS.json',pins)
   runtime=load('TEST_ONLY_relocated_runtime',A/'runtime_guard.py');shared=load('TEST_ONLY_shared_for_fixture',A/'operation_window_guard.py');subjects=runtime.subjects()
   self.assertEqual(len(subjects),12)
   successor=dict(TEST_ONLY=True,schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',operation=runtime.OPERATION,decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',window_sha256=shared.WINDOW_SHA256,credit_run_id=shared.RUN,credit_ceiling=shared.CEILING,predecessor_cutoffs=list(shared.PREDECESSOR_CUTOFFS[runtime.OPERATION]),operation_cutoffs=list(shared.CUTOFFS),subjects=subjects,source_owners=['/root','/root/bfd_route','/root/restart_guard'],minimum_cumulative_spent='22812.3311',guardian=dict(source=shared.GUARDIAN_SOURCE,entrypoint='guard'))
   review=dict(TEST_ONLY=True,schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,reviewer='/root/independent_fixture',operation=runtime.OPERATION,successor=copy.deepcopy(successor))
   if mutate:mutate(successor,review)
   sr=put(T/'TEST_ONLY_SUCCESSOR.json',successor);rr=put(T/'TEST_ONLY_REVIEW.json',review)
   put(A/'ROOT-OPERATION-BINDINGS.json',dict(TEST_ONLY=True,author='/root',operation=runtime.OPERATION,successor=sr,independent_review=rr,expected_subjects=subjects,runtime_authority=None))
   config=put(T/'TEST_ONLY_FACADE.json',dict(TEST_ONLY=True,author='/root',operation=runtime.OPERATION,runtime_guard=ref(A/'runtime_guard.py'),operation_bindings=ref(A/'ROOT-OPERATION-BINDINGS.json'),authorized_clamps=pins['clamps'],runtime_authority=None))
   facade=load('TEST_ONLY_private_facade',B/'bfd_guard_facade.py');facade.configure(config)
   # Account state and times are retained fixture facts, never current live clearance.
   predecessor=shared.load_predecessor();state=read(shared.PREDECESSOR.parent/'ACCOUNT-FIXTURE.json');state['thread_id']=shared.THREAD
   wall=datetime.datetime.fromisoformat(state['heartbeat_at']).timestamp()+1
   now=[wall,950000.,965000.];statepath=T/'TEST_ONLY_ACCOUNT.json';put(statepath,state)
   predecessor.STATE=statepath;predecessor.time=types.SimpleNamespace(time=lambda:now[0],monotonic=lambda:now[1],clock_gettime=lambda clock:now[2],CLOCK_BOOTTIME=7)
   oldspec=importlib.util.spec_from_file_location;oldmodule=importlib.util.module_from_spec;seen=[]
   class GuardianLoader:
    def exec_module(self,m):pass
   def spec(name,path):
    if name=='new_window_reviewed_guardian':
     self.assertEqual(ref(path),shared.GUARDIAN_SOURCE);return types.SimpleNamespace(name=name,loader=GuardianLoader())
    s=oldspec(name,path)
    if name=='bfd_disjoint_operation_window':
     original=s.loader.exec_module
     def execute(m):
      original(m);self.assertEqual(m.THREAD,'01a183ec-72e5-7400-8f48-b4efb8725520');self.assertEqual(m.CUTOFFS,tuple(pins['clamps']))
      m.load_predecessor=lambda:predecessor
      realpath=m.Path
      m.Path=lambda p:types.SimpleNamespace(read_text=lambda:shared.BOOT) if str(p)=='/proc/sys/kernel/random/boot_id' else realpath(p)
      seen.append('restart_shared_guard')
     s.loader.exec_module=execute
    return s
   def module(s):
    if s.name=='new_window_reviewed_guardian':
     return types.SimpleNamespace(guard=lambda:(seen.append('restart_guardian_effect') or list(now)))
    return oldmodule(s)
   with patch.object(importlib.util,'spec_from_file_location',side_effect=spec),patch.object(importlib.util,'module_from_spec',side_effect=module):
    result=facade.guard()
   self.assertEqual(result,now);self.assertEqual(facade.current_cutoffs(),pins['clamps']);self.assertEqual(seen,['restart_shared_guard','restart_guardian_effect'])
   return result
 def test_facade_runtime_12subjects_shared_guard_guardian_account_route(self):self.routed()
 def test_route_rejects_retired_guardian(self):
  def mutate(s,r):s['guardian']['source']=dict(path='/retired/guardian.py',bytes=1,sha256='0'*64);r['successor']=copy.deepcopy(s)
  with self.assertRaisesRegex(ValueError,'exact actual restart guardian'):self.routed(mutate)
 def test_route_rejects_looser_monotonic(self):
  def mutate(s,r):s['operation_cutoffs'][1]+=1;r['successor']=copy.deepcopy(s)
  with self.assertRaisesRegex(ValueError,'only within NEW window'):self.routed(mutate)
 def test_route_rejects_changed_subject(self):
  def mutate(s,r):s['subjects']=copy.deepcopy(s['subjects']);s['subjects']['BFD_contract']['sha256']='0'*64;r['successor']=copy.deepcopy(s)
  with self.assertRaisesRegex(ValueError,'exact consumer source closure'):self.routed(mutate)

if __name__=='__main__':unittest.main(verbosity=2)
