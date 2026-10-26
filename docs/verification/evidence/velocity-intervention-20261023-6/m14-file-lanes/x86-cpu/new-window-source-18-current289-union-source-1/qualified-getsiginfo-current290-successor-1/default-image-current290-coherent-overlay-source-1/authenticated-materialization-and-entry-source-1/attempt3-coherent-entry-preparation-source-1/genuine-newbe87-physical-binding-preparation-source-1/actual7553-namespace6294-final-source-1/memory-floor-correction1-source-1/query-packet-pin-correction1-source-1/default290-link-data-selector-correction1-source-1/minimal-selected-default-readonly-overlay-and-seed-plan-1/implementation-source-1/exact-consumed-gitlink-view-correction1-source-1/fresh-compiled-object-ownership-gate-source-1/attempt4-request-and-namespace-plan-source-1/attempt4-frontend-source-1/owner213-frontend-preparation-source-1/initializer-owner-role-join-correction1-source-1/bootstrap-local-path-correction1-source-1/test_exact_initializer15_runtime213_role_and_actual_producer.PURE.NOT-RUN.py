"""Functional OS only; no security testing. Exact initializer/runtime role join and TEMP production producer."""
import contextlib,copy,hashlib,importlib.util,io,json,os,shutil,stat,subprocess,tempfile,unittest
from pathlib import Path
from unittest import mock
HERE=Path(__file__).parent
R=json.loads((HERE/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json').read_bytes())
F=json.loads((HERE/'EXACT-ROLEJOIN-PRODUCER-FIXTURES.SOURCE-ONLY.json').read_bytes())
def reference(path):p=Path(path);return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def load(name,row):
 p=Path(row['path']);assert reference(p)==row;spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.guards=contextlib.ExitStack()
  for obj,name in [(subprocess,'Popen'),(subprocess,'run'),(os,'system'),(os,'kill')]:cls.guards.enter_context(mock.patch.object(obj,name,side_effect=AssertionError('no query/action transport '+name)))
  cls.addClassCleanup(cls.guards.close);cls.helper=load('exact_role_join_helper',R['origin_helper']);cls.b=cls.helper.data();cls.initialized=json.loads(Path(cls.b['actual_namespace_initialization']['path']).read_bytes());cls.cfg=json.loads(Path(R['config']['path']).read_bytes());cls.caller=load('actual_role_join_caller',R['caller']);cls.fill=load('actual_role_join_fill',R['fill'])
 def test_actual_qualified_owner_role_join_and_real_prequery(self):
  self.assertTrue(self.helper.require_initializer_runtime_owner_roles(self.initialized,self.b));self.assertTrue(self.caller.command_output_paths(self.cfg));self.assertEqual(self.initialized['owner']['sha256'],'15fe434d4e3ce8bea8ad280567b05ed35be4a99f590d695772d3917025ee8fe3');self.assertEqual(self.b['image_entry_owner'],R['owner']);self.assertNotEqual(self.initialized['owner'],R['owner']);self.assertEqual(self.initialized['identities'],self.b['actual_namespace_identities']);self.assertEqual(self.b['current_request'],R['request']);self.assertFalse((HERE/'actual-entry-1').exists());self.assertFalse((HERE/'actual-readonly-admission-capture-1').exists())
 def test_role_join_mutations_refused_before_transport(self):
  mutations=[lambda b:b['namespace_initializer_owner'].update(sha256='0'*64),lambda b:b['image_entry_owner'].update(sha256='0'*64),lambda b:b['current_request'].update(sha256='0'*64),lambda b:b['actual_namespace_identities'][0].update(inode=1),lambda b:b.update(initializer_owner_successor_join=None)]
  for mutate in mutations:
   b=copy.deepcopy(self.b);mutate(b)
   with self.subTest(mutation=mutations.index(mutate)),self.assertRaises(RuntimeError):self.helper.require_initializer_runtime_owner_roles(self.initialized,b)
  original=self.helper.NAMESPACE_OWNER_SUCCESSION;record=json.loads(Path(original['path']).read_bytes())
  mutations=[lambda j:j.update(changed_constant='OTHER'),lambda j:j.update(initializer_constant_value='/wrong'),lambda j:j.update(runtime_constant_value='/wrong'),lambda j:j['initializer_receipt'].update(sha256='0'*64),lambda j:j['namespace_identities'][0].update(inode=1),lambda j:j.update(validator_acceptance=None),lambda j:j.update(positive_only_join=None),lambda j:j['runtime_owner'].update(sha256='0'*64)]
  with tempfile.TemporaryDirectory() as temporary:
   for mutate in mutations:
    bad=copy.deepcopy(record);mutate(bad);p=Path(temporary)/'bad-role.json';p.write_text(json.dumps(bad));row=reference(p);b=copy.deepcopy(self.b);b['initializer_owner_successor_join']=row
    with self.subTest(record_mutation=mutations.index(mutate)),mock.patch.object(self.helper,'NAMESPACE_OWNER_SUCCESSION',row),self.assertRaises(RuntimeError):self.helper.require_initializer_runtime_owner_roles(self.initialized,b)
 def test_REAL_prepare_finish_emits_runtime213_and_retains_initializer15(self):
  for row in F.values():self.assertEqual(reference(row['path']),row)
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary)
   for name in ('ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json','COMPACT-C252-CENSUS-REQUEST.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json'):shutil.copyfile(HERE/name,root/name)
   shutil.copytree(Path(F['five']['path']).parent,root/'actual-readonly-admission-capture-1');context=root/'ROOT-CURRENT290-ACTUAL-FETCH-AND-DEVFLOCK-CONTEXT.ACTUAL.json';shutil.copyfile(F['context']['path'],context)
   with mock.patch.object(self.fill,'D',root),contextlib.redirect_stdout(io.StringIO()):self.fill.prepare(Path(self.fill.FETCHED_ORIGIN_PROOF['path']),self.fill.FETCHED_ORIGIN_PROOF['sha256'],context)
   prepared=json.loads((root/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.ACTUAL-FIVE-BOUND.NOT-RELEASED.json').read_bytes());self.assertEqual(prepared['argv'],self.cfg['commands']['owner_entry_unchanged']['argv']);self.assertEqual(prepared['source']['owner'],R['owner']);self.assertEqual(prepared['source']['request'],R['request'])
   compact=root/'COMPACT-C252-CENSUS-REQUEST.ACTUAL-FIVE-BOUND.NOT-GRANTED.json';doc=json.loads(compact.read_bytes());census=json.loads(Path(F['census']['path']).read_bytes());st=compact.stat();census['request']=dict(path=str(compact),sha256=reference(compact)['sha256'],normalized_sha256=hashlib.sha256(json.dumps(doc,sort_keys=True).encode()).hexdigest(),device=st.st_dev,inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=oct(stat.S_IMODE(st.st_mode)));census['disposable_fixture_only_not_current_query']=True;p=root/'RETAINED-CENSUS-DERIVED-FIXTURE.json';p.write_text(json.dumps(census))
   with mock.patch.object(self.fill,'D',root),contextlib.redirect_stdout(io.StringIO()):self.fill.finish(p,reference(p)['sha256'])
   final=json.loads((root/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FINAL.NOT-RELEASED.json').read_bytes());self.assertEqual(final['argv'],self.cfg['commands']['owner_entry_unchanged']['argv']);self.assertEqual(final['source']['owner'],R['owner']);self.assertEqual(final['source']['request'],R['request']);self.assertEqual(self.b['namespace_initializer_owner'],self.initialized['owner']);self.assertTrue(self.helper.require_initializer_runtime_owner_roles(self.initialized,self.b))
if __name__=='__main__':unittest.main(verbosity=2)
