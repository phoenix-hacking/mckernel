"""Actual focused driver/owner consumers; synthetic authority stays fixture-only."""
import copy,hashlib,importlib.util,json,os,stat,struct,unittest,shutil,sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
O=Path(__file__).resolve().parents[2]
I=O/"prepared-inputs"
sys.path.insert(0,str(O/"scripts"))

def load(name):
 s=importlib.util.spec_from_file_location('kmsg_'+name,O/'scripts'/({'driver':'native_running_external_modules_offline.py','owner':'native_running_external_modules_owner.py'}[name]));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
D=load('driver')
W=load('owner')
P=json.loads((O/'preparation.json').read_text())
class Consumers(unittest.TestCase):
 def test_target_plan_exact_and_pipe_probe_pending(self):
  plan=D.plan(P);self.assertEqual(plan['argv'][-1],'ihk.ko');self.assertIn('--jobserver-style=pipe',plan['argv']);self.assertIn('-j2',plan['argv'])
  for bad in ('modules','mcctrl.ko','ihk.o'):
   q=copy.deepcopy(P);q['proposed_external_command'][-1]=bad
   with self.assertRaises(ValueError):D.plan(q)
  q=copy.deepcopy(P);q['proposed_external_command'].remove('--jobserver-style=pipe')
  with self.assertRaises(ValueError):D.plan(q)
  D.pipe_probe(P,I)
  q=copy.deepcopy(P);q['make_pipe_probe']=None
  with self.assertRaisesRegex(ValueError,'pending'):D.pipe_probe(q,I)
  q=copy.deepcopy(P);q['make_pipe_probe']['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'drift'):D.pipe_probe(q,I)
 def test_actual_source_command_strict_controls(self):
  source=Path('/home/holden/mckernel-work/scratch/nsd-c-a7d84db0d8b54b9b94347fd0aff57594/modules/.ihk.o.cmd').read_text()
  class F:
   def __init__(self,txt):self.txt=txt
   def read_text(self):return self.txt
  class Root:
   def __init__(self,text):self.text=text
   def __truediv__(self,n):return F(self.text)
  with patch.object(D,'plain',side_effect=lambda x:x),patch.object(D,'digest',return_value='fixture'):
   self.assertEqual(len(D.source_bindings(Root(source),Root(source),P)['sources']),13)
   for before,after in [('-Dwarnings','-Awarnings'),('rustc --edition','echo --edition'),('--module /candidate','--module /foreign'),('source_/candidate/modules/ihk.o := /candidate/modules/ihk.rs','source_/candidate/modules/ihk.o := /candidate/modules/mcctrl.rs'),('deps_/candidate/modules/ihk.o :=','notdeps :=')]:
    self.assertIn(before,source)
    with self.assertRaises(ValueError):D.source_bindings(Root(source.replace(before,after)),Root(source),P)
   with self.assertRaises(ValueError):D.source_bindings(Root(source+'\n  /candidate/modules/extra.rs \\\n'),Root(source),P)
 def test_foreign_specialfile_inventory_is_rejected(self):
  # No filesystem FIFO is created. Actual files() receives its lstat identity.
  class Entry:
   def lstat(self):return type('St',(),{'st_mode':stat.S_IFIFO|0o600})()
   def __str__(self):return 'synthetic-only FIFO'
  class Root:
   def rglob(self,p):return [Entry()]
  with self.assertRaisesRegex(ValueError,'nonregular'):D.files(Root())
 def test_actual_elf_imports_and_exact_export_boundary(self):
  accepted=Path('/home/holden/mckernel-work/scratch/nsd-c-a7d84db0d8b54b9b94347fd0aff57594/modules/ihk.ko')
  imports,namespaces=D.elf_imports(accepted);self.assertTrue(imports)
  kernel={}
  for line in Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output/build/Module.symvers').read_text().splitlines():
   row=line.split();kernel[row[1]]=row
  D.check_imports(imports,namespaces,kernel)
  with self.assertRaises(ValueError):D.check_imports(['invented'],set(),kernel)
  with self.assertRaises(ValueError):D.check_imports(['x'],set(),{'x':['0','x','othermodule','EXPORT_SYMBOL']})
  with self.assertRaises(ValueError):D.check_imports(['x'],set(),{'x':['0','x','vmlinux','EXPORT_SYMBOL','NS']})
  D.check_imports(['x'],{'NS'},{'x':['0','x','vmlinux','EXPORT_SYMBOL','NS']})
  exports=(accepted.parent/'Module.symvers').read_text();self.assertEqual(len(D.export_rows(exports)),21)
  for bad in [exports+exports.splitlines()[0]+'\n',exports.replace('/candidate/modules/ihk','/foreign/ihk')]:
   with self.assertRaises(ValueError):D.export_rows(bad)
 def test_actual_driver_refuses_pending_probe_before_make(self):
  root=Path(os.environ['MCKERNEL_KMSG_FIXTURE_DATA']+'-driver');root.mkdir(exist_ok=False)
  for n in ('modules','home','tmp'):(root/n).mkdir()
  missing=copy.deepcopy(P);missing['make_pipe_probe']=None
  with patch.object(D,'load_preparation',return_value=missing),patch.object(D,'validate',return_value={r['path']:r['sha256'] for r in P['closure']}),patch.object(D.subprocess,'run',side_effect=AssertionError('forbidden make')):
   receipt=D.execute(Path('synthetic-preparation'),root/'basis',root,root/'inputs',run=True)
  self.assertEqual(receipt['status'],'FAIL');self.assertIn('pending',receipt['error']);self.assertIsNone(receipt['make_returncode'])
 def test_owner_only_narrow_function_changes(self):
  import ast
  baseline=Path('/home/holden/mckernel-work/scratch/native-cpu-reacquire-module-preparation-20261017-1/final/capsule/scripts/native_running_external_modules_owner.py')
  def funcs(s):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  before=funcs(baseline.read_text());after=funcs((O/'scripts/native_running_external_modules_owner.py').read_text())
  self.assertEqual(set(before),set(after));changed={n for n in before if before[n]!=after[n]};self.assertEqual(changed,{'validate_request','run_owner'})
 def test_actual_owner_admission_includes_authenticated_pipe_proof(self):
  # Private ordinary fixture identities; no live admission, resource or lease effect.
  root=Path(os.environ['MCKERNEL_KMSG_FIXTURE_DATA']+'-owner-admission');root.mkdir(mode=0o700)
  nonce='a1'*16;inputs=root/('nsd-i-'+nonce);candidate=root/('nsd-c-'+nonce)
  shutil.copytree(I,inputs);shutil.copytree(O/'prepared-candidate',candidate);(root/'basis').mkdir(mode=0o700)
  request_path=root/'request.json'
  req=dict(schema='mckernel.native-running-external-modules-request.v1',candidate_sha=W.CANDIDATE,image_id=W.IMAGE,nonce=nonce,request_path=str(request_path),preparation=dict(path=str(W.PREPARATION),sha256=W.PREPARATION_SHA),driver=dict(path=str(W.DRIVER),sha256=D.digest(W.DRIVER)),input_root=str(inputs),candidate_root=str(candidate),owner_evidence_root=str(root/('nsd-o-'+nonce)),lease_path=str(root/'lease.json'),common_exclusion_path=str(root/'common.json'),basis_identity=W.node(root/'basis'),candidate_identity=W.node(candidate),input_identity=W.node(inputs),boot_id=W.BOOT,timeout=1800,disk_budget_bytes=512*2**20,capture_budget_bytes=64*2**20,terminal_policy='remove-owned-terminal')
  request_path.write_text(json.dumps(req));os.chmod(request_path,0o600)
  with ExitStack() as stack:
   for module,name,value in [(W,'ROOT',root),(W,'BASIS',root/'basis'),(W,'LEASE',root/'lease.json'),(W,'COMMON',root/'common.json'),(W.shared,'SHARED_HEAVY_LOCK_PATH',str(root/'shared.lock')),(W.image,'COMMON_EXCLUSION',str(root/'image-common')),(W.host,'OPERATIONAL_EXCLUSION_PATH',str(root/'host-common'))]:stack.enter_context(patch.object(module,name,value))
   stack.enter_context(patch.object(W,'live_admission',return_value={'fixture_only':True}))
   stack.enter_context(patch.object(W,'measure',return_value={'fixture_only':True}))
   stack.enter_context(patch.object(W,'validate_historical_report',return_value={'fixture_only':True}))
   result=W.validate_request(req,request_path,historical_observe=lambda:{'fixture_only':True})
   self.assertIn('historical_leases',result)
   proof=inputs/P['make_pipe_probe']['input_name'];self.assertTrue(proof.is_file());proof.unlink()
   with self.assertRaisesRegex(W.Refusal,'complete exact RO input directory'):W.validate_request(req,request_path,historical_observe=lambda:{'fixture_only':True})
 def test_actual_owner_authenticate_exact_capsule_source_and_review_joins(self):
  # Synthetic review documents exist only inside this no-effect fixture tree.
  root=Path(os.environ['MCKERNEL_KMSG_FIXTURE_DATA']+'-owner-auth');root.mkdir(mode=0o700)
  def save(n,value):
   p=root/n;p.write_bytes(W.canonical(value));os.chmod(p,0o600);return dict(path=str(p),sha256=D.digest(p))
  sources={n:D.digest(O/n) for n in W.SOURCES}
  request=save('request.json',dict(nonce='b2'*16,driver={'sha256':sources['scripts/native_running_external_modules_offline.py']}))
  source_review=save('source-review.json',dict(decision='PASS_SOURCE',implementation_ownership=False,reviewer='fixture-independent',source_sha256=sources,fixture_only=True))
  release=dict(schema='mckernel.native-running-external-modules-release.v1',status='PASS_EXECUTION_RELEASE',execution_count=1,author='fixture-author',request=request,nonce='b2'*16,boot_id=W.BOOT,fetched_source_verified=True,terminal_policy=None,historical_observer=dict(path=str(W.HISTORICAL_OBSERVER),sha256=W.HISTORICAL_OBSERVER_SHA,prefix=list(W.HISTORICAL_PREFIX),timeout_seconds=30),source_sha256=sources,source_review=source_review)
  release['execution_review']=save('execution-review.json',dict(decision='PASS_EXECUTION',implementation_ownership=False,reviewer='fixture-independent',reviewed_release_payload_sha256=W.sha(W.canonical(release)),fixture_only=True))
  final=save('release.json',release)
  self.assertEqual(W.authenticate(Path(request['path']),request['sha256'],Path(final['path']),final['sha256'])[1],release)
  bad=copy.deepcopy(release);bad['source_sha256'].pop('scripts/tests/test_native_running_external_modules_owner.py');negative=save('negative-release.json',bad)
  with self.assertRaisesRegex(W.Refusal,'complete runtime source closure'):W.authenticate(Path(request['path']),request['sha256'],Path(negative['path']),negative['sha256'])
if __name__=='__main__':unittest.main(verbosity=2)

