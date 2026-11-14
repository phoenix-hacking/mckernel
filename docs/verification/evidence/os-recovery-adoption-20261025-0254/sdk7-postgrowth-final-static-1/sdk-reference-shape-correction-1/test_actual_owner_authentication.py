"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual owner999 authenticate API only. Never guarded_execute, locks, Docker or SDK.
Temporary re-signed review files are explicitly SOURCE_ONLY fixtures and are deleted.
"""
import ast,copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
N=Path(__file__).resolve().parent
E=N.parents[1]
A=E/'ROOT-DAEMON7-POSTGROWTH-SDK-ADMISSION-2'
OWNER=E/'sdk7-142g-consumer-successor-source-1/daemon_sdk_owner.142G-SOURCE-ONLY.py'
CANDIDATE=N/'sdk7_authority_adapter.OWNER-REFERENCE-SHAPE.SOURCE-ONLY.py'
BASE=N.parent/'sdk7_authority_adapter.POSTGROWTH-CHAIN.SOURCE-ONLY.py'

def ref(path):
 raw=Path(path).read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest())
def actual_owner():
 assert hashlib.sha256(OWNER.read_bytes()).hexdigest()=='999713a7b4dafa034232d997872132642358aa80029244ad27e571efbf1664ee'
 spec=importlib.util.spec_from_file_location('read_only_actual_sdk_owner',OWNER);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def projected_reference(bundle):
 # Evaluate the actual patched payload expression; no stale-clock bypass or mock.
 tree=ast.parse(CANDIDATE.read_bytes());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='adapt')
 expressions=[keyword.value for node in ast.walk(function) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='payload' and node.func.attr=='update' for keyword in node.keywords if keyword.arg=='source_review']
 assert len(expressions)==1
 return eval(compile(ast.Expression(expressions[0]),str(CANDIDATE),'eval'),{'bundle':bundle})

class ActualAPI(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.o=actual_owner();cls.argv=json.loads((A/'SDK-COMMAND.EXACT.json').read_bytes())['argv'];get=lambda name:cls.argv[cls.argv.index('--'+name)+1]
  cls.request=Path(get('request'));cls.requestsha=get('request-sha256');cls.releasepath=Path(get('release'));cls.releasesha=get('release-sha256')
  cls.release=json.loads(cls.releasepath.read_bytes());cls.bundle=json.loads((A/'FINAL-BUNDLE.PENDING-REVIEW.json').read_bytes())
 def authenticate(self,path,sha=None):return self.o.authenticate(self.request,self.requestsha,path,ref(path)['sha256'] if sha is None else sha)
 def fixture(self,mutate=None,review_mutate=None):
  tmp=tempfile.TemporaryDirectory(prefix='SOURCE-ONLY-AUTH-',dir=N);self.addCleanup(tmp.cleanup);folder=Path(tmp.name)
  candidate=copy.deepcopy(self.release);candidate['source_review']=projected_reference(self.bundle)
  candidate['fixture_scope']='PURE_AUTHENTICATE_SOURCE_ONLY_NEVER_EXECUTE';candidate['runtime_authority']=False
  if mutate:mutate(candidate)
  payload={k:v for k,v in candidate.items() if k!='execution_review'}
  review=dict(decision='PASS_EXECUTION',implementation_ownership=False,reviewer='independent-pure-fixture-not-runtime-authority',reviewed_release_payload_sha256=self.o.sha(self.o.canonical(payload)),fixture_only=True,source_only=True,runtime_authority=False)
  if review_mutate:review_mutate(review)
  reviewpath=folder/'SOURCE-ONLY-EXECUTION-REVIEW.FIXTURE.json';reviewpath.write_bytes(self.o.canonical(review));candidate['execution_review']=ref(reviewpath)
  path=folder/'SOURCE-ONLY-AUTHENTICATION-PAYLOAD.FIXTURE.json';path.write_bytes(self.o.canonical(candidate))
  return path,candidate,reviewpath
 def test_actual_failed_release_reproduces_exact_unmodified_signature(self):
  self.assertEqual(ref(self.releasepath)['sha256'],self.releasesha)
  self.assertEqual(set(self.release['source_review']),{'path','bytes','sha256'})
  with self.assertRaisesRegex(self.o.Refusal,'exact file reference required'):self.authenticate(self.releasepath,self.releasesha)
  self.assertIn('Refusal: exact file reference required',(A/'SDK-CAPTURE/stderr').read_text())
 def test_corrected_expression_and_full_genuine_authentication_pass(self):
  before=copy.deepcopy(self.bundle);path,candidate,_=self.fixture();request,release=self.authenticate(path)
  self.assertEqual(self.bundle,before);self.assertEqual(set(candidate['source_review']),{'path','sha256'})
  self.assertEqual(candidate['source_review'],{k:self.release['source_review'][k] for k in ('path','sha256')})
  self.assertEqual(request,json.loads(self.request.read_bytes()));self.assertEqual(release['source_sha256'],self.release['source_sha256'])
 def test_wrong_source_hash_missing_review_and_three_key_reviews_refused(self):
  path,_,_=self.fixture(lambda c:c['source_review'].update(sha256='0'*64))
  try:self.authenticate(path)
  except Exception as error:self.assertRegex(str(error).lower(),'hash|sha|digest')
  else:self.fail('actual bound accepted wrong source hash')
  path,_,_=self.fixture(lambda c:c.pop('source_review'))
  with self.assertRaises(KeyError):self.authenticate(path)
  path,_,_=self.fixture(lambda c:c.update(source_review=copy.deepcopy(self.release['source_review'])))
  with self.assertRaisesRegex(self.o.Refusal,'exact file reference required'):self.authenticate(path)
  path,candidate,reviewpath=self.fixture();candidate['execution_review']['bytes']=reviewpath.stat().st_size;path.write_bytes(self.o.canonical(candidate))
  with self.assertRaisesRegex(self.o.Refusal,'exact file reference required'):self.authenticate(path)
 def test_wrong_execution_payload_and_old_source_map_refused(self):
  path,_,_=self.fixture(review_mutate=lambda d:d.update(reviewed_release_payload_sha256='0'*64))
  with self.assertRaisesRegex(self.o.Refusal,'exact independent execution payload required'):self.authenticate(path)
  old=json.loads((A/'ACTUAL-REVIEWED-RELEASE.json').read_bytes())['historical_source_review']
  path,_,_=self.fixture(lambda c:c.update(source_review={k:old[k] for k in ('path','sha256')}))
  with self.assertRaisesRegex(self.o.Refusal,'exact independent source review required'):self.authenticate(path)
 def test_actual_owner_reference_consumers_all_have_expected_shape(self):
  request=json.loads(self.request.read_bytes())
  for key in ('driver','preparation'):self.assertEqual(set(request[key]),{'path','sha256'})
  prep=self.o.bound(request['preparation']);manifest=self.o.bound({k:prep['input_manifest'][k] for k in ('path','sha256')});self.assertIsInstance(manifest,dict)
  path,candidate,_=self.fixture()
  for key in ('request','source_review','execution_review'):self.assertEqual(set(candidate[key]),{'path','sha256'})
  self.authenticate(path)
 def test_only_payload_projection_and_private_import_placement_change(self):
  def funcs(path):return {n.name:n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef)}
  old,new=funcs(BASE),funcs(CANDIDATE);self.assertEqual(set(old),set(new))
  self.assertEqual({k:ast.dump(n,include_attributes=False) for k,n in old.items() if k!='adapt'},{k:ast.dump(n,include_attributes=False) for k,n in new.items() if k!='adapt'})
  for node in ast.walk(old['adapt']):
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='payload' and node.func.attr=='update':
    for keyword in node.keywords:
     if keyword.arg=='source_review':keyword.value=ast.parse("{k: bundle['current_source_review'][k] for k in ('path', 'sha256')}",mode='eval').body
  self.assertEqual(ast.dump(old['adapt'],include_attributes=False),ast.dump(new['adapt'],include_attributes=False))
if __name__=='__main__':unittest.main(verbosity=2)
