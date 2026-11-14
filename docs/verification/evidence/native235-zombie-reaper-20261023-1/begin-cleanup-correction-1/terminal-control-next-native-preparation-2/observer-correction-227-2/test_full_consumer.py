# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Full consumer replay: retained227 native bytes + explicitly modeled host-time
# envelope (actual failed writer omitted original observation timestamps).
from pathlib import Path
import copy,hashlib,importlib.util,json,re,unittest
P=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2')
W5=P.parent
M227=W5/'next-stage-preparation-1/source-ready-1/case-227/ACTUAL-V3-NATIVE227-MANIFEST.json'
M235=W5/'next-stage-preparation-1/source-ready-1/case-235/ACTUAL-V3-NATIVE235-MANIFEST.json'
G=ROOT/'failed-native-227-451c-raw-1/guest'
D227=json.loads(M227.read_text());D235=json.loads(M235.read_text())
raw=json.loads((G/'result.json').read_text());qmp=json.loads((G/'qmp.transcript.json').read_text())
assert raw['failure']['error']=='child ordinary RET coverage' and raw['cleanup']=={'reaped':True,'errors':[]} and raw['capture_errors']==[]
assert any('"status": "shutdown"' in bytes.fromhex(r['raw_hex']).decode(errors='replace') or '"status":"shutdown"' in bytes.fromhex(r['raw_hex']).decode(errors='replace')for r in qmp if r['direction']=='received')
q=raw['qemu_evidence'];identity={k:q[k]for k in ['pid','pgid','sid','starttime_ticks']}
O227=dict(serial=(G/'serial.log').read_text(),debugcon=(G/'debugcon.log').read_text(),qmp={'status':'shutdown'},teardown=True,started_at=qmp[0]['monotonic'],finished_at=qmp[-1]['monotonic'],deadline=qmp[0]['monotonic']+300,process_identity=identity,qemu_evidence=q)
O235=json.loads((ROOT/'actual-post-physical-1/decoded-root/inner-result.json').read_text())['observation']
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
OLD=module('original_full_consumer',P/'original_full_consumer.f368.py');NEW=module('corrected_full_consumer',P/'native_diagnostic.py')
def remove(o,match):
 lines=o['serial'].splitlines();found=[x for x in lines if re.search(match,x)];assert len(found)==1,(match,found);o['serial']='\n'.join(x for x in lines if not re.search(match,x))+'\n'
def change(o,match,replace):
 lines=o['serial'].splitlines();found=[x for x in lines if re.search(match,x)];assert len(found)==1,(match,found);o['serial']='\n'.join(re.sub(match,replace,x)if x==found[0]else x for x in lines)+'\n'
def drop_return(o,pid,worker,delivery):
 remove(o,rf'application_syscall=returned os=0 generation=1 pid={pid} worker={worker} delivery={delivery} ')
 lines=o['serial'].splitlines();o['serial']='\n'.join(x for x in lines if f'application_syscall=return_route os=0 generation=1 pid={pid} worker={worker} delivery={delivery} 'not in x)+'\n'
class FullConsumer(unittest.TestCase):
 def reject(self,alter,manifest=None,observation=None):
  m=copy.deepcopy(D227 if manifest is None else manifest);o=copy.deepcopy(O227 if observation is None else observation);alter(m,o)
  with self.assertRaises(NEW.DiagnosticError):NEW.evaluate(m,o)
 def test_original_full227_fails_at_original_exact_RET_guard(self):
  with self.assertRaisesRegex(OLD.DiagnosticError,'child ordinary RET coverage'):OLD.evaluate(copy.deepcopy(D227),copy.deepcopy(O227))
 def test_corrected_full227_retained_actual_bytes_protocol_pass_only(self):
  r=NEW.evaluate(copy.deepcopy(D227),copy.deepcopy(O227));self.assertEqual(r['status'],'PROTOCOL_PASS');self.assertFalse(r['application_acceptance']);self.assertFalse(r['mckernel_application_executed']);self.assertEqual(r['guest_report']['raw_wait_status'],0)
 def test_unchanged_full235_actual_observation_still_passes(self):
  self.assertEqual(OLD.evaluate(copy.deepcopy(D235),copy.deepcopy(O235))['status'],'PROTOCOL_PASS');self.assertEqual(NEW.evaluate(copy.deepcopy(D235),copy.deepcopy(O235))['status'],'PROTOCOL_PASS')
 def test_missing_real_child_ACK_refused(self):self.reject(lambda m,o:remove(o,r'application cleanup ACK os=0 generation=1 pid=258 '))
 def test_wrong_child_ACK_PID_refused(self):self.reject(lambda m,o:change(o,r'application cleanup ACK os=0 generation=1 pid=258 ', 'application cleanup ACK os=0 generation=1 pid=259 '))
 def test_wrong_child_ACK_generation_refused(self):self.reject(lambda m,o:change(o,r'application cleanup ACK os=0 generation=1 pid=258 ', 'application cleanup ACK os=0 generation=2 pid=258 '))
 def test_error_ACK_refused(self):self.reject(lambda m,o:change(o,r'application cleanup ACK os=0 generation=1 pid=258 token=32 errno=0', 'application cleanup ACK os=0 generation=1 pid=258 token=32 errno=-16'))
 def test_missing_child_intent_refused(self):self.reject(lambda m,o:remove(o,r'application_process=cleanup_requested os=0 generation=1 pid=258 '))
 def test_wrong_child_procfs_delete_refused(self):self.reject(lambda m,o:change(o,r'application procfs deleted os=0 generation=1 pid=258 tid=258', 'application procfs deleted os=0 generation=1 pid=258 tid=259'))
 def test_wrong_parent_reap_identity_refused(self):self.reject(lambda m,o:change(o,r'pid=255 worker=7 delivery=57 cpu=0 value=258', 'pid=255 worker=7 delivery=57 cpu=0 value=259'))
 def test_missing_terminal_refused(self):self.reject(lambda m,o:remove(o,r'application_syscall=delivered os=0 generation=1 pid=258 worker=34 delivery=50 '))
 def test_terminal_same_worker_refused(self):self.reject(lambda m,o:change(o,r'pid=258 worker=34 delivery=50 cpu=0 number=231','pid=258 worker=33 delivery=50 cpu=0 number=231'))
 def test_wrong_missing_call_number_refused(self):self.reject(lambda m,o:change(o,r'pid=258 worker=33 delivery=49 cpu=0 number=7','pid=258 worker=33 delivery=49 cpu=0 number=0'))
 def test_second_missing_ordinaryRET_refused(self):self.reject(lambda m,o:drop_return(o,258,33,44))
 def test_missing_recovery_childRET_refused(self):self.reject(lambda m,o:drop_return(o,261,67,126))
 def test_235_missing_childRET_stays_strict(self):self.reject(lambda m,o:drop_return(o,258,34,37),D235,O235)
 def test_wrong_existing_route_refused(self):self.reject(lambda m,o:change(o,r'pid=258 worker=34 delivery=47 launcher_cpu=1 guest_cpu=0','pid=258 worker=34 delivery=47 launcher_cpu=1 guest_cpu=1'))
 def test_fabricated_missing_poll_route_refused(self):
  def mutate(m,o):o['serial']=o['serial'].replace('ND_PAYLOAD ','<6> mcctrl: application_syscall=return_route os=0 generation=1 pid=258 worker=33 delivery=49 launcher_cpu=0 guest_cpu=0\nND_PAYLOAD ')
  self.reject(mutate)
 def test_wrong_frozen_payload_refused(self):self.reject(lambda m,o:m['artifacts']['payload'].__setitem__('sha256','0'*64))
 def test_wrong_case_has_no_cancellation_exception(self):self.reject(lambda m,o:m.__setitem__('case_id','P-M06-01-process-exec-wait-235B'))
 def test_original_app_SIGTERM_bytes_still_required(self):self.reject(lambda m,o:o.__setitem__('serial',o['serial'].replace('7369676e616c3d3135','7369676e616c3d3039')))
 def test_parent_final_retirement0_still_required(self):self.reject(lambda m,o:remove(o,r'application retirement os=0 generation=1 pid=255 token=147 errno=0'))
 def test_no_missingRET_without_cancel_lifecycle(self):
  def mutate(m,o):
   remove(o,r'application cleanup ACK os=0 generation=1 pid=258 ')
   remove(o,r'application procfs deleted os=0 generation=1 pid=258 ')
  self.reject(mutate)
class FailureEvidenceWriter(unittest.TestCase):
 def test_real_exercise_lifecycle_retains_collected_observation_on_observer_failure(self):
  import tempfile,time
  class Process:
   def terminate(self):pass
   def kill(self):pass
   def wait(self,timeout):return 0
   def communicate(self,timeout):return b'',b''
   def process_identity(self):return dict(identity)
   def qemu_evidence(self):return dict(q,returncode=0)
  class Qmp:
   def negotiate(self,timeout):pass
   def resume(self,timeout):pass
   def wait_shutdown(self,timeout):return {'status':'shutdown'}
   def terminate(self,timeout):pass
   def close(self,timeout):pass
  for mod,expected in [(OLD,False),(NEW,True)]:
   with tempfile.TemporaryDirectory(prefix='failure-writer-fixture-',dir=P)as temp:
    t=Path(temp);(t/'serial.log').write_text(O227['serial']);(t/'debugcon.log').write_text(O227['debugcon'])
    actual=mod.evaluate
    def refuse(manifest,observation):raise mod.DiagnosticError('fixture observer refusal')
    mod.evaluate=refuse
    try:
     with self.assertRaisesRegex(mod.DiagnosticError,'fixture observer refusal'):
      mod.exercise_lifecycle(copy.deepcopy(D227),t,lambda timeout:Process(),lambda timeout:Qmp(),timeout=10)
    finally:mod.evaluate=actual
    result=json.loads((t/'result.json').read_text());self.assertEqual('observation'in result,expected);self.assertEqual(result['status'],'FAIL');self.assertFalse(result['application_acceptance']);self.assertFalse(result['mckernel_application_executed']);self.assertEqual(result['failure']['error'],'fixture observer refusal');self.assertEqual(json.loads((t/'first-failure.jsonl').read_text())['error'],'fixture observer refusal')
    if expected:
     self.assertEqual(result['observation']['serial'],O227['serial']);self.assertLess(result['observation']['started_at'],result['observation']['finished_at']);self.assertLess(result['observation']['finished_at'],result['observation']['deadline'])
    before=(t/'result.json').read_bytes()
    with self.assertRaisesRegex(mod.DiagnosticError,'final record already published'):mod.write_record(t,{'status':'replacement'})
    self.assertEqual((t/'result.json').read_bytes(),before)

# New actual observation uses its real collected host envelope; no modeled fields.
ACTUAL227_PATH=ROOT/'failed-native-227-5b643-raw-1/guest/result.json'
ACTUAL227=json.loads(ACTUAL227_PATH.read_text());O227_REAL=ACTUAL227['observation']
E1B=module('expert_correction_preimage_e1b',P/'native_diagnostic.preimage.py')
class RealSlotOneObservation(unittest.TestCase):
 def reject(self,alter):
  m=copy.deepcopy(D227);o=copy.deepcopy(O227_REAL);alter(m,o)
  with self.assertRaises(NEW.DiagnosticError):NEW.evaluate(m,o)
 def test_e1b_fullconsumer_reproduces_real_slot1_failure(self):
  with self.assertRaisesRegex(E1B.DiagnosticError,'cancelled worker route history'):E1B.evaluate(copy.deepcopy(D227),copy.deepcopy(O227_REAL))
 def test_expert_correction_fullconsumer_real_envelope_passes(self):
  m=copy.deepcopy(D227);o=copy.deepcopy(O227_REAL);r=NEW.evaluate(m,o)
  self.assertEqual(r['status'],'PROTOCOL_PASS');self.assertFalse(r['application_acceptance']);self.assertFalse(r['mckernel_application_executed']);self.assertEqual(r['observation']['started_at'],ACTUAL227['observation']['started_at']);self.assertEqual(r['observation']['deadline'],ACTUAL227['observation']['deadline']);self.assertEqual(r['guest_report']['raw_wait_status'],0)
 def test_missing_prior_worker_history_refused(self):
  def mutate(m,o):
   lines=o['serial'].splitlines();o['serial']='\n'.join(l for l in lines if not(re.search(r'application_syscall=(delivered|returned|return_route) os=0 generation=1 pid=258 worker=33 delivery=(39|41|46) ',l)))+'\n'
  self.reject(mutate)
 def test_switching_prior_worker_slots_refused(self):self.reject(lambda m,o:remove(o,r'application_syscall=return_route os=0 generation=1 pid=258 worker=33 delivery=41 '))
 def test_wrong_canceled_worker_refused(self):self.reject(lambda m,o:change(o,r'pid=258 worker=33 delivery=48 cpu=0 number=7','pid=258 worker=99 delivery=48 cpu=0 number=7'))
 def test_wrong_route_PID_domain_refused(self):self.reject(lambda m,o:change(o,r'pid=258 worker=33 delivery=39 launcher_cpu=1 guest_cpu=0','pid=259 worker=33 delivery=39 launcher_cpu=1 guest_cpu=0'))
 def test_wrong_route_generation_domain_refused(self):self.reject(lambda m,o:change(o,r'generation=1 pid=258 worker=33 delivery=39 launcher_cpu=1 guest_cpu=0','generation=2 pid=258 worker=33 delivery=39 launcher_cpu=1 guest_cpu=0'))
 def test_wrong_route_guest_CPU_refused(self):self.reject(lambda m,o:change(o,r'pid=258 worker=33 delivery=39 launcher_cpu=1 guest_cpu=0','pid=258 worker=33 delivery=39 launcher_cpu=1 guest_cpu=1'))
 def test_invalid_launcher_slot_refused(self):self.reject(lambda m,o:change(o,r'pid=258 worker=33 delivery=39 launcher_cpu=1 guest_cpu=0','pid=258 worker=33 delivery=39 launcher_cpu=2 guest_cpu=0'))

 def test_prior_RET_after_canceled_poll_refused(self):
  def mutate(m,o):
   lines=o['serial'].splitlines();matches=[l for l in lines if 'application_syscall=returned os=0 generation=1 pid=258 worker=33 delivery=46 ' in l];assert len(matches)==1
   row=matches[0];lines.remove(row);index=next(i for i,l in enumerate(lines)if 'application_syscall=delivered os=0 generation=1 pid=258 worker=33 delivery=48 'in l);lines.insert(index+1,row);o['serial']='\n'.join(lines)+'\n'
  self.reject(mutate)

if __name__=='__main__':unittest.main(verbosity=2)
