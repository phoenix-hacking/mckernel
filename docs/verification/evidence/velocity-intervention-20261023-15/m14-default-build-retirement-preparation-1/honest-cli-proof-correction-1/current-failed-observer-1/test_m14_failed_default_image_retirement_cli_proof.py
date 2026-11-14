"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure selected actual receipt-gate regressions. No cleanup, Docker, root, process factory or compiled-artifact change.
"""
import ast,copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actual_failed_image_cleanup',D/'cleanup_failed_default_image.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
OWNER=json.loads(Path(m.SOURCE_REFS['owner_receipt']['path']).read_bytes())
DRIVER=json.loads(Path(m.SOURCE_REFS['driver_receipt']['path']).read_bytes())
RECEIPT_SHA=m.SOURCE_REFS['owner_receipt']['sha256']
TARGET=dict(m.KNOWN_TARGET,image_id=OWNER['terminal_container_info']['Image'])
GUARD=json.loads((D/'ROOT-CLOSED-CLI-PROOF.TEMPLATE.NOT-ACTUAL.json').read_bytes())['future_exact_payload']
def testonly_process_report():
 rows=[[1,0,'1'],[999998,1,'1']]
 return dict(schema='fp-save-image.proc.v2',uid=0,boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb',challenge='TESTONLY-NOT-HOST-OBSERVATION',caller=[999998,'1'],publishers=[],snapshots=[copy.deepcopy(rows),copy.deepcopy(rows)],status='COMPLETE',failure=None,acquisition=dict(max_sweeps=8,window_ns=5_000_000_000,elapsed_ns=1,attempts=[dict(number=i,listed=[1,999998],identities=copy.deepcopy(rows),confirmed=[1,999998],failure=None) for i in (1,2)],observed=copy.deepcopy(rows)))
class ReceiptGate(unittest.TestCase):
 def gate(self,owner=None,driver=None,target=None,item=None,guard=None,terminal=None,process=None,identity_drift=False):
  owner=copy.deepcopy(OWNER if owner is None else owner);driver=copy.deepcopy(DRIVER if driver is None else driver);target=copy.deepcopy(TARGET if target is None else target);item=copy.deepcopy(OWNER['terminal_container_info'] if item is None else item);guard=copy.deepcopy(GUARD if guard is None else guard)
  terminal=copy.deepcopy(m.KNOWN_CLI_TERMINAL if terminal is None else terminal);process=copy.deepcopy(testonly_process_report() if process is None else process)
  old=m.SOURCE_REFS['driver_receipt']
  try:
   with tempfile.TemporaryDirectory(prefix='TESTONLY-m14-failed-receipt-') as td:
    td=Path(td)
    def fixture_file(name,value):
     p=td/name;raw=(json.dumps(value,sort_keys=True)+'\n').encode();p.write_bytes(raw);return p,raw
    p,raw=fixture_file('driver.json',driver);m.SOURCE_REFS['driver_receipt']=dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    terminal_path,_=fixture_file('TESTONLY-tool-terminal.json',terminal)
    process_path,_=fixture_file('TESTONLY-process-report.json',process)
    guard['tool_terminal']=m.observe_identity(terminal_path)
    guard['fresh_process_observation']=m.observe_identity(process_path)
    if identity_drift:guard['fresh_process_observation']['sha256']='0'*64
    return m.image_receipt_binding(owner,guard,target,item,RECEIPT_SHA)
  finally:m.SOURCE_REFS['driver_receipt']=old
 def test_genuine_failed_owner_and_compiled_linked_driver(self):self.gate()
 def test_PASS_owner_refused(self):
  o=copy.deepcopy(OWNER);o['status']='PASS'
  with self.assertRaises(m.Refusal):self.gate(owner=o)
 def test_owner_exit0_refused(self):
  o=copy.deepcopy(OWNER);o['exit_code']=0
  with self.assertRaises(m.Refusal):self.gate(owner=o)
 def test_other_owner_error_refused(self):
  o=copy.deepcopy(OWNER);o['error']='other failure'
  with self.assertRaises(m.Refusal):self.gate(owner=o)
 def test_unretired_refused(self):
  o=copy.deepcopy(OWNER);o['retired']=False
  with self.assertRaises(m.Refusal):self.gate(owner=o)
 def test_not_retained_refused(self):
  o=copy.deepcopy(OWNER);o['terminal_container_retained']=False
  with self.assertRaises(m.Refusal):self.gate(owner=o)
 def test_uncertain_client_refused(self):
  o=copy.deepcopy(OWNER);o['client_retirement_unproven']=True
  with self.assertRaises(m.Refusal):self.gate(owner=o)
 def test_retirement_error_refused(self):
  o=copy.deepcopy(OWNER);o['retirement_error']='unproven'
  with self.assertRaises(m.Refusal):self.gate(owner=o)
 def test_driver_PASS_refused(self):
  d=copy.deepcopy(DRIVER);d['status']='PASS'
  with self.assertRaises(m.Refusal):self.gate(driver=d)
 def test_driver_non_artifact_phase_refused(self):
  d=copy.deepcopy(DRIVER);d['phase']='build'
  with self.assertRaises(m.Refusal):self.gate(driver=d)
 def test_other_artifact_error_refused(self):
  d=copy.deepcopy(DRIVER);d['error']='other validator'
  with self.assertRaises(m.Refusal):self.gate(driver=d)
 def test_failed_compile_command_refused(self):
  d=copy.deepcopy(DRIVER);d['commands'][0]['exit_code']=1
  with self.assertRaises(m.Refusal):self.gate(driver=d)
 def test_missing_link_command_refused(self):
  d=copy.deepcopy(DRIVER);d['commands']=[x for x in d['commands'] if x['phase']!='build']
  with self.assertRaises(m.Refusal):self.gate(driver=d)
 def test_missing_Rust_command_refused(self):
  d=copy.deepcopy(DRIVER);d['commands']=[x for x in d['commands'] if x['phase']!='production-rust-object']
  with self.assertRaises(m.Refusal):self.gate(driver=d)
 def test_wrong_container_target_refused(self):
  t=copy.deepcopy(TARGET);t['container_id']='0'*64
  with self.assertRaises(m.Refusal):self.gate(target=t)
 def test_wrong_nonce_refused(self):
  o=copy.deepcopy(OWNER);o['owner_nonce']='0'*32
  with self.assertRaises(m.Refusal):self.gate(owner=o)
 def test_changed_terminal_inspect_refused(self):
  i=copy.deepcopy(OWNER['terminal_container_info']);i['State']['Running']=True
  with self.assertRaises(m.Refusal):self.gate(item=i)
 def test_relabelled_proof_PASS_refused(self):
  g=copy.deepcopy(GUARD);g['owner_status']='PASS'
  with self.assertRaises(m.Refusal):self.gate(guard=g)
 def test_fabricated_outer_identity_refused(self):
  g=copy.deepcopy(GUARD);g['unrecorded_outer_identity']={'pid':1,'starttime':'1'}
  with self.assertRaises(m.Refusal):self.gate(guard=g)
 def test_fabricated_direct_join_refused(self):
  t=copy.deepcopy(m.KNOWN_CLI_TERMINAL);t['direct_child_joined']=True
  with self.assertRaises(m.Refusal):self.gate(terminal=t)
 def test_fabricated_group_absence_refused(self):
  t=copy.deepcopy(m.KNOWN_CLI_TERMINAL);t['group_absent']=True
  with self.assertRaises(m.Refusal):self.gate(terminal=t)
 def test_wrong_tool_session_refused(self):
  t=copy.deepcopy(m.KNOWN_CLI_TERMINAL);t['tool_session']=73314
  with self.assertRaises(m.Refusal):self.gate(terminal=t)
 def test_wrong_tool_exit_refused(self):
  t=copy.deepcopy(m.KNOWN_CLI_TERMINAL);t['exit_code']=0
  with self.assertRaises(m.Refusal):self.gate(terminal=t)
 def test_wrong_owner_birth_refused(self):
  t=copy.deepcopy(m.KNOWN_CLI_TERMINAL);t['owner_starttime']='62249678'
  with self.assertRaises(m.Refusal):self.gate(terminal=t)
 def test_incomplete_process_acquisition_refused(self):
  p=testonly_process_report();p['status']='REFUSED'
  with self.assertRaises(m.Refusal):self.gate(process=p)
 def test_wrong_process_boot_refused(self):
  p=testonly_process_report();p['boot_id']='TESTONLY-wrong-boot'
  with self.assertRaises(m.Refusal):self.gate(process=p)
 def test_known_owner_present_refused(self):
  p=testonly_process_report();rows=[[1,0,'1'],[999998,1,'1'],[4166629,1,'62249677']]
  for a in p['acquisition']['attempts']:a.update(listed=[r[0] for r in rows],identities=copy.deepcopy(rows),confirmed=[r[0] for r in rows])
  p['snapshots']=[copy.deepcopy(rows),copy.deepcopy(rows)];p['acquisition']['observed']=copy.deepcopy(rows)
  with self.assertRaises(m.Refusal):self.gate(process=p)
 def test_known_saved_client_present_refused(self):
  p=testonly_process_report();rows=[[1,0,'1'],[999998,1,'1'],[4168062,1,'1']]
  for a in p['acquisition']['attempts']:a.update(listed=[r[0] for r in rows],identities=copy.deepcopy(rows),confirmed=[r[0] for r in rows])
  p['snapshots']=[copy.deepcopy(rows),copy.deepcopy(rows)];p['acquisition']['observed']=copy.deepcopy(rows)
  with self.assertRaises(m.Refusal):self.gate(process=p)
 def test_current_publisher_present_refused(self):
  p=testonly_process_report();p['publishers']=[[999998,'1','TESTONLY publisher']]
  with self.assertRaises(m.Refusal):self.gate(process=p)
 def test_process_descriptor_drift_refused(self):
  with self.assertRaises(m.Refusal):self.gate(identity_drift=True)
if __name__=='__main__':unittest.main(verbosity=2)
