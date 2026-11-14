"""Functional OS/Rust only; no security testing. Actual controlled child lifecycle."""
from pathlib import Path
import base64,hashlib,importlib.util,json,signal,unittest
D=Path(__file__).resolve().parent
S=D/'cleanup_failed_retained_validator.py'
spec=importlib.util.spec_from_file_location('owned_logs_cleanup',S)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
LOG=Path(m.SOURCE_REFS['container_log']['path']).read_bytes()
OUT=D/'actual-owned-logs-lifecycle-captures-1'
PYTHON='/home/holden/anaconda3/bin/python3'
class Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):OUT.mkdir(mode=0o700)
    def child(self,name,code,wall=30):
        path=OUT/name;path.mkdir(mode=0o700)
        before={n:signal.getsignal(n) for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
        mask=signal.pthread_sigmask(signal.SIG_BLOCK,set())
        result=m.owned_log_transport([PYTHON,'-I','-B','-c',code],path,wall)
        self.assertEqual(before,{n:signal.getsignal(n) for n in before})
        self.assertEqual(mask,signal.pthread_sigmask(signal.SIG_BLOCK,set()))
        self.assertTrue(result['direct_child_joined']);self.assertTrue(result['group_absent'])
        self.assertTrue(result['closed_streams']);self.assertIsNone(result['retirement_error'])
        self.assertEqual(result['remaining_group_members'],[])
        self.assertTrue((path/'direct-wait.json').exists())
        self.assertTrue((path/'WHOLE-JOIN.json').exists())
        for n in ('stdout','stderr'):self.assertLessEqual((path/n).stat().st_size,1048576)
        return result,path
    def test_normal_exact_stderr(self):
        code='import os,base64;os.write(2,base64.b64decode('+repr(base64.b64encode(LOG))+'))'
        result,p=self.child('normal',code)
        self.assertTrue(m.owned_log_join_succeeded(result))
        self.assertEqual(m.validate_log_channels(0,(p/'stdout').read_bytes(),(p/'stderr').read_bytes()),LOG)
    def test_nonzero(self):
        result,p=self.child('nonzero','raise SystemExit(7)')
        self.assertEqual(result['returncode'],7);self.assertFalse(m.owned_log_join_succeeded(result))
    def test_full_file_and_oversize(self):
        result,p=self.child('full-file','import os;os.write(1,b"x"*1048576)')
        self.assertTrue(m.owned_log_join_succeeded(result));self.assertEqual((p/'stdout').stat().st_size,1048576)
        with self.assertRaises(m.Refusal):m.validate_log_channels(0,(p/'stdout').read_bytes(),b'')
        result,p=self.child('oversize','import os;os.write(1,b"x"*1048576);os.write(1,b"y")')
        self.assertNotEqual(result['returncode'],0);self.assertFalse(m.owned_log_join_succeeded(result))
    def test_timeout(self):
        result,p=self.child('timeout','import time;time.sleep(3)',0.05)
        self.assertTrue(result['timed_out']);self.assertFalse(m.owned_log_join_succeeded(result))
    def test_parent_TERM_cancellation(self):
        result,p=self.child('cancel','import os,signal,time;os.kill(os.getppid(),signal.SIGTERM);time.sleep(3)')
        self.assertIn('InterruptedError',result['error']);self.assertFalse(m.owned_log_join_succeeded(result))
    def test_unexpected_group_retired(self):
        code='''import os,signal,time
pid=os.fork()
if pid==0:
 signal.signal(signal.SIGTERM,lambda s,f:os._exit(0))
 time.sleep(3)
else:
 def done(s,f):
  os.kill(pid,signal.SIGTERM)
  os.waitpid(pid,0)
  os._exit(0)
 signal.signal(signal.SIGTERM,done)
 time.sleep(3)
'''
        result,p=self.child('group',code,0.15)
        self.assertTrue(result['unexpected_group_members']);self.assertFalse(m.owned_log_join_succeeded(result))
    def test_late_duplicate_channel_refused(self):
        code='import os,time,base64;b=base64.b64decode('+repr(base64.b64encode(LOG))+');os.write(2,b);time.sleep(.02);os.write(2,b)'
        result,p=self.child('duplicate',code)
        self.assertTrue(m.owned_log_join_succeeded(result))
        with self.assertRaises(m.Refusal):m.validate_log_channels(0,(p/'stdout').read_bytes(),(p/'stderr').read_bytes())
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Lifecycle))
    if not result.wasSuccessful():raise SystemExit(1)
    doc=dict(schema='mckernel.copy6.exact-owned-log-lifecycle.v1',status='PASS',tests_run=result.testsRun,source_sha256=hashlib.sha256(S.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with (D/'ACTUAL-OWNED-LOGS-LIFECYCLE-RESULT.json').open('x') as f:json.dump(doc,f,sort_keys=True);f.write('\n')
    print(json.dumps(doc,sort_keys=True))
