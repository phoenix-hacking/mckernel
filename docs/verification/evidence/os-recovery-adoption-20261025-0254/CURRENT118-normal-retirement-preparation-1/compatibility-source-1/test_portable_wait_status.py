"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Execute under /usr/bin/python3; raw wait results and all effect leaves substituted.
No child process, signal, guard, lock, native workload or Docker command.
"""
from pathlib import Path
import ast,hashlib,importlib.util,os,sys,types,unittest
D=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('current118_wait_status_corrected',D/'retire_exact_current118_stopped_container.py')
old=load('current118_wait_status_failed',D.parent/'retire_exact_current118_stopped_container.py')
h=load('exact_portable_wait_status_subject',D/'wait_status_compat.py')
def child(module,status):
 c=module.Wait4Child.__new__(module.Wait4Child);c.pid=999999;c.returncode=None;c.process=types.SimpleNamespace(returncode=None)
 c.started=10.;c.clock=types.SimpleNamespace(time=lambda:20.,monotonic=lambda:11.)
 c.calls=[]
 def wait(pid,flags):
  c.calls.append((pid,flags));return pid,status,types.SimpleNamespace(ru_utime=.1,ru_stime=.2,ru_maxrss=44)
 c.wait4=wait;c.record=dict(pid=c.pid,birth=123,positive_wait4=False);return c
class PortableWaitStatus(unittest.TestCase):
 def test_actual_bound_python38_interpreter(self):
  self.assertEqual(sys.executable,'/usr/bin/python3');self.assertEqual(sys.version_info[:2],(3,8));self.assertFalse(hasattr(os,'waitstatus_to_exitcode'))
  self.assertEqual(m.WAIT_STATUS_SOURCE,m.bindings()['wait_status_helper'])
  self.assertEqual(m.WAIT_STATUS_SOURCE['sha256'],'c895898a0a0162d78e521f4ded5ea7c75b46bd47d7764003f31c09d2d2f31d0a')
 def test_normal_zero_and_nonzero_raw_wait_statuses(self):
  for code in [0,1,42,127,255]:
   with self.subTest(exit_code=code):self.assertEqual(h.waitstatus_to_exitcode(code<<8),code)
 def test_signal_and_core_flag_raw_statuses_without_sending_signal(self):
  for signal_number in [1,2,9,11,15]:
   for core_flag in [0,128]:
    with self.subTest(signal_number=signal_number,core_flag=core_flag):self.assertEqual(h.waitstatus_to_exitcode(signal_number|core_flag),-signal_number)
 def test_unsupported_stopped_and_continued_states_refused(self):
  for raw in [(19<<8)|127,(5<<8)|127,65535]:
   with self.subTest(raw_status=raw),self.assertRaises(ValueError):h.waitstatus_to_exitcode(raw)
 def test_real_wait4child_preserves_raw_status_usage_once_and_return_code(self):
  for raw,expected in [(0,0),(42<<8,42),(15,-15),(11|128,-11)]:
   c=child(m,raw);self.assertEqual(c.reap(),expected);self.assertEqual(c.process.returncode,expected)
   self.assertEqual(c.calls,[(c.pid,os.WNOHANG)]);self.assertEqual(c.reap(),expected);self.assertEqual(len(c.calls),1)
   self.assertTrue(c.record['positive_wait4']);self.assertEqual(c.record['wait4_status'],raw);self.assertEqual(c.record['wait4_pid'],c.pid)
   self.assertEqual(c.record['user_cpu_seconds'],.1);self.assertEqual(c.record['peak_rss_kib'],44)
 def test_unsupported_status_cannot_invent_positive_terminal_join(self):
  for raw in [(19<<8)|127,65535]:
   c=child(m,raw)
   with self.assertRaises(ValueError):c.reap()
   self.assertIsNone(c.returncode);self.assertIsNone(c.process.returncode);self.assertFalse(c.record['positive_wait4'])
 def test_exact_original_api_failure_reproduced_before_correction(self):
  self.assertEqual(m.reference(old.SELF)['sha256'],'4179233c5a604b2a5924b98469e0dba5fe782eb76e3ff54286767b69288e4488')
  c=child(old,0)
  with self.assertRaisesRegex(AttributeError,'waitstatus_to_exitcode'):c.reap()
  self.assertFalse(c.record['positive_wait4']);self.assertIsNone(c.returncode)
 def test_reap_body_changes_only_exact_converter_call(self):
  def node(module):return next(x for c in ast.parse(Path(module.SELF).read_text()).body if isinstance(c,ast.ClassDef) and c.name=='Wait4Child' for x in c.body if isinstance(x,ast.FunctionDef) and x.name=='reap')
  before=node(old);after=node(m)
  class Normalize(ast.NodeTransformer):
   def visit_Attribute(self,n):
    n=self.generic_visit(n)
    if isinstance(n.value,ast.Name) and n.value.id=='WAIT_STATUS_COMPAT' and n.attr=='waitstatus_to_exitcode':n.value.id='os'
    return n
  self.assertEqual(ast.dump(before),ast.dump(Normalize().visit(after)))
if __name__=='__main__':unittest.main(verbosity=2)
