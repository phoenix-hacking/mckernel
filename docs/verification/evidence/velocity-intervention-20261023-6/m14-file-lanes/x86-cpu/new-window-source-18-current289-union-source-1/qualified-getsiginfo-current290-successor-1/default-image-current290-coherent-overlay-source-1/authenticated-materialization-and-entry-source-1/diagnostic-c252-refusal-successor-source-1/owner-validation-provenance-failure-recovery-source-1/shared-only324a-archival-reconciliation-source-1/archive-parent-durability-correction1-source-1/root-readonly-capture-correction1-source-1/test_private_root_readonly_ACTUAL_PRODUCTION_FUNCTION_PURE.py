"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual private production function with mocked subprocess, real disposable captures.
No observer import, live query, root/shared action or credential-helper invocation.
"""
from pathlib import Path
import ast,errno,hashlib,importlib.util,json,os,subprocess,tempfile,unittest
from unittest import mock
N=Path(__file__).parent;r=json.loads((N/'READY-SHARED-ONLY324A-ROOT-READONLY-CAPTURE-CORRECTION1.SOURCE.json').read_bytes());p=json.loads(Path(r['profile']['path']).read_bytes())
def load(row,name):
 raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes'];spec=importlib.util.spec_from_file_location(name,row['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
c=load(r['private_root_readonly_capture'],'actual_private_production_root_readonly');m=load(p['primitive'],'existing_durable_publish_functions_only')
class CaptureTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=N,prefix='disposable-root-capture-');self.addCleanup(self.tmp.cleanup);self.out=Path(self.tmp.name);c.CAPTURE_DIRECTORY=self.out;c.CALL_COUNT=0;c.SMALL_LIMIT=m.SMALL_LIMIT;self.events=[]
  owner=self
  class OriginalRefusal(RuntimeError):
   def __init__(self,message):
    owner.assertTrue((owner.out/'root-readonly-000001.status.json').is_file());owner.events.append('original-guard-refusal');super().__init__(message)
  c.Refusal=OriginalRefusal
  def publish(path,raw):self.events.append(path.suffix);return m.publish(path,raw)
  c.PUBLISH=publish
  self.argv=['/usr/bin/python3','-I','-B','-c','print("functional fixture")','fixture-challenge','101','202']
 def status(self):return json.loads((self.out/'root-readonly-000001.status.json').read_bytes())
 def assert_streams(self,stdout,stderr):
  s=self.status();self.assertEqual((self.out/'root-readonly-000001.stdout.raw').read_bytes(),stdout);self.assertEqual((self.out/'root-readonly-000001.stderr.raw').read_bytes(),stderr);self.assertEqual(s['stdout']['sha256'],hashlib.sha256(stdout).hexdigest());self.assertEqual(s['stderr']['sha256'],hashlib.sha256(stderr).hexdigest());self.assertEqual(s['stdout']['bytes'],len(stdout));self.assertEqual(s['stderr']['bytes'],len(stderr));self.assertEqual(s['argv'],self.argv);self.assertEqual(s['sudo_argv'],['/usr/bin/sudo','-A','--',*self.argv]);self.assertEqual(s['challenge'],'fixture-challenge');return s
 def run_result(self,result):
  with mock.patch.dict(os.environ,{'SUDO_ASKPASS':'fixture-helper-never-invoked'},clear=True),mock.patch.object(c.subprocess,'run',return_value=result) as run:
   try:return c.root_readonly(self.argv)
   finally:
    run.assert_called_once_with(['/usr/bin/sudo','-A','--',*self.argv],env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','SUDO_ASKPASS':'fixture-helper-never-invoked'},stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=False)
 def test_success_exact_capture_before_return(self):
  self.assertEqual(self.run_result(subprocess.CompletedProcess([],0,b'exact stdout',b'')),b'exact stdout');s=self.assert_streams(b'exact stdout',b'');self.assertEqual(s['returncode'],0);self.assertEqual(s['state'],'COMPLETED_BEFORE_UNCHANGED_GUARD');self.assertNotIn('original-guard-refusal',self.events);self.assertNotIn('fixture-helper-never-invoked',json.dumps(s))
 def test_rc1_capture_before_unchanged_refusal(self):
  with self.assertRaises(c.Refusal) as error:self.run_result(subprocess.CompletedProcess([],1,b'partial stdout',b'actual child failure'))
  self.assertEqual(str(error.exception),'approved root read-only observation failed');s=self.assert_streams(b'partial stdout',b'actual child failure');self.assertEqual(s['returncode'],1);self.assertEqual(self.events[-1],'original-guard-refusal')
 def test_nonempty_stderr_capture_before_unchanged_refusal(self):
  with self.assertRaises(c.Refusal):self.run_result(subprocess.CompletedProcess([],0,b'exact stdout',b'unexpected stderr'))
  self.assert_streams(b'exact stdout',b'unexpected stderr');self.assertEqual(self.events[-1],'original-guard-refusal')
 def test_oversize_exact_raw_retained_before_unchanged_refusal(self):
  data=b'x'*(m.SMALL_LIMIT+1)
  with self.assertRaises(c.Refusal):self.run_result(subprocess.CompletedProcess([],0,data,b''))
  s=self.assert_streams(data,b'');self.assertGreater(s['stdout']['bytes'],s['SMALL_LIMIT']);self.assertEqual(self.events[-1],'original-guard-refusal')
 def test_capture_failure_stops_before_guard_or_return(self):
  def publish(path,raw):
   if path.name.endswith('.status.json'):raise OSError('disposable capture writer failure')
   return m.publish(path,raw)
  c.PUBLISH=publish
  with self.assertRaises(OSError):self.run_result(subprocess.CompletedProcess([],0,b'complete stdout',b''))
  self.assertEqual((self.out/'root-readonly-000001.stdout.raw').read_bytes(),b'complete stdout');self.assertNotIn('original-guard-refusal',self.events)
 def test_timeout_partial_bytes_status_and_same_exception(self):
  error=subprocess.TimeoutExpired(['/fixture'],30,output=b'partial timeout stdout',stderr=b'partial timeout stderr')
  with mock.patch.object(c.subprocess,'run',side_effect=error),self.assertRaises(subprocess.TimeoutExpired) as caught:c.root_readonly(self.argv)
  self.assertIs(caught.exception,error);s=self.assert_streams(b'partial timeout stdout',b'partial timeout stderr');self.assertEqual(s['state'],'TIMEOUT_BEFORE_ORIGINAL_EXCEPTION_RERAISE');self.assertEqual(s['error']['type'],'TimeoutExpired');self.assertEqual(s['error']['timeout'],30);self.assertTrue(s['stdout']['available']);self.assertTrue(s['stderr']['available']);self.assertIsNone(s['returncode'])
 def test_startup_error_unavailable_streams_and_same_exception(self):
  error=OSError(errno.ENOENT,'disposable startup failure')
  with mock.patch.object(c.subprocess,'run',side_effect=error),self.assertRaises(OSError) as caught:c.root_readonly(self.argv)
  self.assertIs(caught.exception,error);s=self.assert_streams(b'',b'');self.assertEqual(s['state'],'ERROR_BEFORE_ORIGINAL_EXCEPTION_RERAISE');self.assertEqual(s['error']['errno'],errno.ENOENT);self.assertFalse(s['stdout']['available']);self.assertFalse(s['stderr']['available'])
 def test_original_call_env_timeout_bound_guard_AST_identical(self):
  original=next(n for n in ast.parse(Path(p['primitive']['path']).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='root_readonly');new=next(n for n in ast.parse(Path(r['private_root_readonly_capture']['path']).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='root_readonly')
  guard=lambda f:next(n for n in f.body if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp));call=lambda f:next(n for n in ast.walk(f) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess' and n.func.attr=='run')
  self.assertEqual(ast.dump(guard(original),include_attributes=False),ast.dump(guard(new),include_attributes=False));self.assertEqual(ast.dump(call(original),include_attributes=False),ast.dump(call(new),include_attributes=False));self.assertFalse(Path(p['archive_directory']).exists())
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CaptureTests));print(json.dumps({'scope':__doc__,'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'actual_root_queries':0,'observer_imported':False,'actual_shared_action':False,'original_subprocess_call_and_guard_AST_identical':True},sort_keys=True));raise SystemExit(0 if result.wasSuccessful() else 1)
