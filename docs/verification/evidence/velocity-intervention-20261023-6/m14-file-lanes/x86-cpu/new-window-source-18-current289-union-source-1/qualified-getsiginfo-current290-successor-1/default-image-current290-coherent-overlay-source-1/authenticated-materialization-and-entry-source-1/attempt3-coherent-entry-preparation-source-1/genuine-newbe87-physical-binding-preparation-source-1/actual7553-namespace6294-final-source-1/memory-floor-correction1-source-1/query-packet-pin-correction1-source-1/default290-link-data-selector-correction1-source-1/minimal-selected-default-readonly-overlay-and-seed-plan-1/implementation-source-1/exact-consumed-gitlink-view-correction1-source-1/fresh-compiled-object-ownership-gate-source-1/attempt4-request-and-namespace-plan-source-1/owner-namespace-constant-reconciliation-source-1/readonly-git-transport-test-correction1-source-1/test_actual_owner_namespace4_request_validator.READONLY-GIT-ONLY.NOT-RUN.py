"""Functional OS only; no security testing. Real owner request validation, no entry/query/action."""
import ast,contextlib,copy,fcntl,hashlib,importlib.util,json,os,subprocess,unittest
from pathlib import Path
from unittest import mock
HERE=Path(__file__).parent
D=json.loads((HERE.parent/'EXACT-OWNER15-TO-NAMESPACE4-CONSTANT-DELTA.SOURCE-ONLY.json').read_bytes())
A=json.loads((HERE/'EXACT-READONLY-GIT-ARGV-ALLOWANCE.FIXTURE-ONLY.json').read_bytes())
ORIGINAL_RUN=subprocess.run
ORIGINAL_POPEN=subprocess.Popen
ALLOWED={tuple(argv) for argv in A['argv']}
GIT_COMMANDS=[]
def checked_argv(argv,kwargs):
 assert isinstance(argv,list) and tuple(argv) in ALLOWED,'non-allowlisted process argv'
 assert kwargs.get('env')==A['environment'],'Git environment differs'
 assert not kwargs.get('shell',False),'shell forbidden'
 assert kwargs.get('stdout')==subprocess.PIPE and kwargs.get('stderr')==subprocess.PIPE,'Git capture differs'
def readonly_git_run(argv,*args,**kwargs):
 checked_argv(argv,kwargs);assert not args and kwargs.get('timeout')==30 and kwargs.get('check') is False,'Git run profile differs'
 result=ORIGINAL_RUN(argv,**kwargs);GIT_COMMANDS.append(dict(argv=argv,returncode=result.returncode,stdout_bytes=len(result.stdout),stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),stderr_bytes=len(result.stderr)));return result
def readonly_git_popen(argv,*args,**kwargs):
 checked_argv(argv,kwargs);assert not args,'positional Popen options forbidden';return ORIGINAL_POPEN(argv,**kwargs)
def auth(row):
 p=Path(row['path']);raw=p.read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'];return raw
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.guards=contextlib.ExitStack()
  cls.guards.enter_context(mock.patch.object(subprocess,'run',side_effect=readonly_git_run));cls.guards.enter_context(mock.patch.object(subprocess,'Popen',side_effect=readonly_git_popen))
  for obj,name in [(subprocess,'check_output'),(os,'system'),(os,'kill'),(os,'unlink'),(fcntl,'flock')]:cls.guards.enter_context(mock.patch.object(obj,name,side_effect=AssertionError('no process/query/ownership mutation: '+name)))
  cls.addClassCleanup(cls.guards.close)
  self_git=Path(A['git']['path']);assert hashlib.sha256(self_git.read_bytes()).hexdigest()==A['git']['sha256'];auth(A['gitlink_manifest'])
  raw=auth(D['corrected_owner']);cls.request=json.loads(auth(D['request_fixture']));path=D['corrected_owner']['path'];spec=importlib.util.spec_from_file_location('actual_namespace_bound_owner_validator',path);cls.owner=importlib.util.module_from_spec(spec);exec(compile(raw,path,'exec'),cls.owner.__dict__)
 @classmethod
 def tearDownClass(cls):print(json.dumps({'actual_readonly_git_commands':GIT_COMMANDS,'no_workload_or_admission':True},sort_keys=True))
 def test_exact_wholefile_one_constant_only(self):
  old=ast.parse(auth(D['original_owner']));new=ast.parse(auth(D['corrected_owner']));oldassign=next(n for n in old.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='COMMON_EXCLUSION' for t in n.targets));newassign=next(n for n in new.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='COMMON_EXCLUSION' for t in n.targets));self.assertEqual(ast.literal_eval(newassign.value),self.request['common_exclusion_path']);oldassign.value=newassign.value;self.assertEqual(ast.dump(old,include_attributes=False),ast.dump(new,include_attributes=False))
 def test_real_owner_extended_request_validator_complete_no_transport(self):
  # Genuine31 is retained input to the ACTUAL corrected owner validator, not a new admission request.
  bound=self.owner._validate_request(copy.deepcopy(self.request))
  for key,field in [('work','work_root'),('owner_evidence','owner_evidence_root'),('attempt','attempt_root'),('output','output_root'),('evidence','evidence_root'),('lease','lease_path')]:self.assertEqual(str(bound[key]),self.request[field])
  self.assertEqual(self.owner.COMMON_EXCLUSION,self.request['common_exclusion_path']);self.assertEqual(str(bound['driver']),self.request['driver_path']);self.assertEqual(self.owner._REUSE_DRIVER_SHA256,D['driver']['sha256'])
 def test_real_base_validator_reproduces_old_constant_refusal(self):
  old=D['constant_changes'][0]['old']
  with mock.patch.object(self.owner,'COMMON_EXCLUSION',old):
   with self.assertRaisesRegex(self.owner.OwnerError,'common exclusion path differs or is retired'):self.owner._validate_request(copy.deepcopy(self.request))
if __name__=='__main__':unittest.main(verbosity=2)
