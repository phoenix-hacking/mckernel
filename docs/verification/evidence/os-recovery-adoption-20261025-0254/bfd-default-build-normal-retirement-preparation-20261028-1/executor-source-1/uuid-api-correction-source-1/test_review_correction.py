"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The two independent review families; substituted spawn/clock/writer effects only.
"""
from pathlib import Path
import importlib.util,os,tempfile,types,unittest
from unittest.mock import patch
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('BFD_two_family_correction',D/'retire_exact_bfd_stopped_container.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
B=m.bindings();ARGV=m.PREFIX+['rm','--',B['cid']]

class Wrapped:
 def __init__(self,process,capture):
  self.process=process;self.pid=process.pid;self.capture=capture;self.returncode=None
  self.record=dict(pid=self.pid,birth=12345,process_group=self.pid,started_epoch=1793218000.,started_monotonic=1.,positive_wait4=False)
 def wait(self,timeout):
  self.returncode=0;self.record.update(positive_wait4=True,wait4_pid=self.pid,wait4_status=0,returncode=0,finished_epoch=1793218001.,wall_seconds=1.,user_cpu_seconds=.01,system_cpu_seconds=.01,peak_rss_kib=12);return 0
 def poll(self):return self.returncode

class ReviewCorrection(unittest.TestCase):
 def make(self,T):
  cls,ns=m.transport(B);client=cls(T,m.Stop());process=types.SimpleNamespace(pid=999997,returncode=None)
  return client,ns,process
 def fake_actual(self,T,now,events):
  pre=m.write_new(T/'TEST_ONLY_PREPROOF.json',dict(TEST_ONLY=True,present=True,label='PREINSPECT-2',clocks=list(now)))
  claim=m.write_new(T/'TEST_ONLY_CLAIM.json',dict(TEST_ONLY=True,preproof=pre))
  fake=types.SimpleNamespace(b=B,rm_claimed=True,rm_invoked=True,rm_claim_reference=claim,rm_preproof_reference=pre,stop=m.Stop(),guard=types.SimpleNamespace(guard=lambda:events.append('guard_io')))
  fake.safe=lambda:events.append('protected_and_source_io')
  return fake
 def test_stall_after_durable_log_refuses_actual_spawn(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_BFD_final_spawn_') as tmp:
   T=Path(tmp);client,ns,process=self.make(T);now=[1793218000.,1000000.,1015000.];events=[];fake=self.fake_actual(T,now,events)
   class Log:
    parent=T
    def open(self,mode):
     stream=(T/'commands.log').open(mode)
     class Context:
      def __enter__(self):return self
      def write(self,data):return stream.write(data)
      def flush(self):stream.flush();events.append('log_flush_stall');now[0]+=121
      def fileno(self):return stream.fileno()
      def __exit__(self,*args):stream.close()
     return Context()
   client.log=Log();client.before_popen=lambda argv:m.Actual.before_spawn(fake,argv)
   with patch.object(m.time,'time',side_effect=lambda:now[0]),patch.object(m.time,'monotonic',side_effect=lambda:now[1]),patch.object(m.time,'clock_gettime',side_effect=lambda clock:now[2]),patch.object(m.subprocess,'Popen',return_value=process) as spawn,patch.object(os,'killpg') as kill:
    with self.assertRaisesRegex(m.Refusal,'final pre-Popen original120s'):client.exact(ARGV)
    spawn.assert_not_called();kill.assert_not_called()
   self.assertEqual(events,['log_flush_stall','protected_and_source_io','guard_io'])
   self.assertIsNone(client.raw_child);self.assertFalse(client.client_retirement_unproven)
 def test_final_clock_check_follows_protected_io_and_checks_earliest_cap(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_BFD_final_clock_') as tmp:
   T=Path(tmp);now=[1793218000.,1000000.,1015000.];events=[];fake=self.fake_actual(T,now,events)
   def stalled_safe():events.append('protected_and_source_io');now[1]=B['cutoffs'][1]
   fake.safe=stalled_safe
   with patch.object(m.time,'time',side_effect=lambda:now[0]),patch.object(m.time,'monotonic',side_effect=lambda:now[1]),patch.object(m.time,'clock_gettime',side_effect=lambda clock:now[2]),self.assertRaisesRegex(m.Refusal,'final pre-Popen earliest'):m.Actual.before_spawn(fake,ARGV)
   self.assertEqual(events,['protected_and_source_io','guard_io'])
 def test_successful_spawn_birth_failure_retains_raw_child_and_custody(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_BFD_birth_failure_') as tmp:
   T=Path(tmp);client,ns,process=self.make(T)
   with patch.object(m.subprocess,'Popen',return_value=process) as spawn,patch.object(m,'Wait4Child',side_effect=OSError('TEST_ONLY birth read failure')),patch.object(os,'killpg') as kill:
    with self.assertRaises(OSError):client.exact(ARGV)
    spawn.assert_called_once();kill.assert_not_called()
   self.assertIs(client.raw_child,process);self.assertTrue(client.client_retirement_unproven);self.assertTrue(m.must_retain_custody(types.SimpleNamespace(mutated=False,commands=client)))
   self.assertEqual(client.unresolved_spawn['pid'],process.pid);self.assertIsNone(client.unresolved_spawn['birth'])
   with patch.object(m.subprocess,'Popen') as again,self.assertRaisesRegex(m.Refusal,'prior command uncertainty'):client.exact(ARGV)
   again.assert_not_called()
 def test_successful_spawn_wrapper_failure_after_birth_keeps_latch(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_BFD_wrapper_failure_') as tmp:
   T=Path(tmp);client,ns,process=self.make(T);raw=b'999997 (TEST_ONLY) '+b' '.join([b'S',b'1',b'999997',b'999997']+[b'0']*15+[b'12345']+[b'0']*35)
   original=Path.read_bytes
   def read(path):return raw if str(path)=='/proc/999997/stat' else original(path)
   with patch.object(m.subprocess,'Popen',return_value=process),patch.object(Path,'read_bytes',read),patch.object(m.time,'time',side_effect=OSError('TEST_ONLY wrapper record initialization failure')),patch.object(os,'killpg') as kill:
    with self.assertRaises(OSError):client.exact(ARGV)
    kill.assert_not_called()
   self.assertIs(client.raw_child,process);self.assertTrue(client.client_retirement_unproven);self.assertTrue(m.must_retain_custody(types.SimpleNamespace(mutated=False,commands=client)))
 def test_successful_spawn_status_or_receipt_publication_failure_keeps_custody(self):
  for stage in ('running_status','joined_receipt'):
   with self.subTest(stage=stage),tempfile.TemporaryDirectory(prefix='TEST_ONLY_BFD_writer_failure_') as tmp:
    T=Path(tmp);client,ns,process=self.make(T);atomic=ns['atomic']
    def writer(path,value):
     if (stage=='running_status' and value.get('state')=='running') or (stage=='joined_receipt' and path.name=='JOIN-WAIT4.json'):raise OSError('TEST_ONLY writer failure after spawn')
     return atomic(path,value)
    ns['atomic']=writer
    with patch.object(m.subprocess,'Popen',return_value=process) as spawn,patch.object(m,'Wait4Child',Wrapped),patch.object(client,'_surviving_group_members',return_value=[]),patch.object(os,'killpg') as kill:
     with self.assertRaises(OSError):client.exact(ARGV)
     spawn.assert_called_once();kill.assert_not_called()
    self.assertIs(client.raw_child,process);self.assertTrue(client.client_retirement_unproven);self.assertEqual(client.unresolved_spawn['birth'],12345)
    self.assertTrue(m.must_retain_custody(types.SimpleNamespace(mutated=False,commands=client)))

if __name__=='__main__':unittest.main(verbosity=2)
