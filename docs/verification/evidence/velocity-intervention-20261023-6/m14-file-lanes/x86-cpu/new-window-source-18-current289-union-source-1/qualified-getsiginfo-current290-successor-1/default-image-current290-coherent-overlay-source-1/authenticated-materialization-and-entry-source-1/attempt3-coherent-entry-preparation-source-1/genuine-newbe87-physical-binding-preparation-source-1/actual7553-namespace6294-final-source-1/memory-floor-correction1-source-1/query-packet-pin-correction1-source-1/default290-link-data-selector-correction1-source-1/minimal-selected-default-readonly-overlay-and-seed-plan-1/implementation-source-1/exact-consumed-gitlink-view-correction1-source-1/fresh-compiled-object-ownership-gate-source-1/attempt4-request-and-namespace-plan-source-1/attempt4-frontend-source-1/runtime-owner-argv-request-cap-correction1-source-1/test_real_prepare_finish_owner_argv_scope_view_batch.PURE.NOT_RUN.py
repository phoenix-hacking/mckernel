"""Functional OS only; no security testing. Real producer argv/view regression; TEMP retained fixtures only."""
import contextlib,copy,hashlib,importlib.util,io,json,os,shutil,stat,tempfile,unittest
from pathlib import Path
from unittest import mock
HERE=Path(__file__).parent
R=json.loads((HERE/'READY-OWNER-ARGV-SCOPE-VIEW-BATCH-CORRECTION1.SOURCE-ONLY.json').read_bytes())
def load(name,row):
 path=Path(row['path']) if isinstance(row,dict) else Path(row);spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def reference(path):path=Path(path);return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.caller=load('actual_batch_caller',R['caller']);cls.fill=load('actual_batch_fill',R['fill']);cls.cfg=json.loads(Path(R['config']['path']).read_bytes());cls.template_path=HERE/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json';cls.template=json.loads(cls.template_path.read_bytes());cls.fixed=json.loads(Path(cls.cfg['readonly_reuse_inputs']['path']).read_bytes());cls.request=json.loads(Path(R['request']['path']).read_bytes());cls.effective=next(row['postimage'] for row in cls.fixed['postimages'] if row['relative']=='kernel/CMakeLists.txt')
 def assert_bindings(self,p):
  self.assertEqual(p['argv'],self.cfg['commands']['owner_entry_unchanged']['argv'])
  for key in ('owner','request','driver'):self.assertEqual(p['source'][key],self.cfg['pins'][key])
  self.assertEqual(p['readonly_reuse_inputs'],self.cfg['readonly_reuse_inputs']);self.assertEqual(p['readonly_reuse_inputs']['path'],self.request['readonly_reuse_inputs']);self.assertEqual(p['operation_scope'],self.cfg['operation_scope']);self.assertEqual(p['execution_scope'],self.cfg['metadata_template_execution_scope']);self.assertIs(p['fresh_full_configure'],False);self.assertIs(p['native_fork_owned_transaction'],False);self.assertIs(p['wholefile_retirement'],False);self.assertEqual(p['native_apps'],0);self.assertEqual(p['native_executor_pair_acceptance'],'OPEN');c=p['canonical_cfg_source'];self.assertEqual(c['selected_CMake'],self.cfg['metadata_retained_base_CMake']);self.assertEqual(c['CMake_after'],self.cfg['metadata_retained_base_CMake_after']);self.assertEqual(c['selected_CMake_scope'],'RETAINED_BASE_SOURCE_ONLY');self.assertEqual(c['effective_readonly_postimages'],self.fixed['postimages']);self.assertEqual(c['effective_selected_CMake'],self.effective);self.assertEqual(c['effective_CMake_after'],self.effective['sha256']);self.assertIs(c['fresh_source_copy'],False);self.assertIs(c['fresh_full_configure'],False);self.assertNotEqual(c['CMake_after'],c['effective_CMake_after'])
 def test_actual_prequery_template_guard_and_old_argv_failure(self):
  self.assertGreater(R['request']['bytes'],1<<20);self.assertLessEqual(R['request']['bytes'],32<<20)
  with self.assertRaises(RuntimeError):self.caller.strict(Path(R['request']['path']))
  with tempfile.TemporaryDirectory() as temporary:
   boundary=Path(temporary)/'strict-boundary.json';boundary.write_bytes(b'{}'+b' '*30);self.assertEqual(self.caller.strict(boundary,maximum=32),{});boundary.write_bytes(b'{}'+b' '*31)
   with self.assertRaisesRegex(RuntimeError,'bounded unique regular metadata'):self.caller.strict(boundary,maximum=32)
  self.assertTrue(self.caller.command_output_paths(self.cfg));self.assert_bindings(self.template);old=json.loads(Path(R['predecessor_payload_template']['path']).read_bytes());self.assertNotEqual(old['argv'],self.template['argv']);m=self.caller;original=m.strict
  with mock.patch.object(m,'strict',side_effect=lambda path,*args,**kwargs:old if Path(path)==self.template_path else original(path,*args,**kwargs)),mock.patch.object(m,'captured',side_effect=AssertionError('query forbidden')) as query:
   with self.assertRaisesRegex(RuntimeError,'exact payload template owner argv before five'):m.execute(HERE/'NOT-A-GRANT',Path(R['config']['path']),R['config']['sha256'])
   query.assert_not_called()
 def test_prequery_batch_mismatches_refused(self):
  m=self.caller;original=m.strict
  mutations=[lambda x:x['source']['owner'].update(sha256='0'*64),lambda x:x['source']['request'].update(path='/wrong'),lambda x:x['source']['driver'].update(sha256='0'*64),lambda x:x['readonly_reuse_inputs'].update(sha256='0'*64),lambda x:x.update(operation_scope='wrong'),lambda x:x.update(execution_scope='configure old476 reused0'),lambda x:x.update(fresh_full_configure=True),lambda x:x.update(native_apps=1),lambda x:x.update(native_executor_pair_acceptance='PASS'),lambda x:x['canonical_cfg_source'].update(effective_CMake_after=x['canonical_cfg_source']['CMake_after']),lambda x:x['canonical_cfg_source'].update(selected_CMake_scope='CURRENT_EFFECTIVE'),lambda x:x['canonical_cfg_source'].update(effective_readonly_postimages=[])]
  for mutate in mutations:
   bad=copy.deepcopy(self.template);mutate(bad)
   with self.subTest(case=mutations.index(mutate)),mock.patch.object(m,'strict',side_effect=lambda path,*args,**kwargs:bad if Path(path)==self.template_path else original(path,*args,**kwargs)),self.assertRaises(RuntimeError):m.command_output_paths(self.cfg)
 def test_REAL_prepare_and_finish_output_bindings_retained_TEMP_fixture(self):
  for key in ('retained_five','retained_context','retained_census'):
   self.assertEqual(reference(R[key]['path']),R[key])
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary)
   for name in ('ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json','COMPACT-C252-CENSUS-REQUEST.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json'):shutil.copyfile(HERE/name,root/name)
   shutil.copytree(Path(R['retained_five']['path']).parent,root/'actual-readonly-admission-capture-1');context=root/'ROOT-CURRENT290-ACTUAL-FETCH-AND-DEVFLOCK-CONTEXT.ACTUAL.json';shutil.copyfile(R['retained_context']['path'],context)
   with mock.patch.object(self.fill,'D',root),contextlib.redirect_stdout(io.StringIO()):self.fill.prepare(Path(self.fill.FETCHED_ORIGIN_PROOF['path']),self.fill.FETCHED_ORIGIN_PROOF['sha256'],context)
   prepared=root/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.ACTUAL-FIVE-BOUND.NOT-RELEASED.json';self.assert_bindings(json.loads(prepared.read_bytes()));compact=root/'COMPACT-C252-CENSUS-REQUEST.ACTUAL-FIVE-BOUND.NOT-GRANTED.json';compactdoc=json.loads(compact.read_bytes());census=json.loads(Path(R['retained_census']['path']).read_bytes());st=compact.stat();census['request']=dict(path=str(compact),sha256=reference(compact)['sha256'],normalized_sha256=hashlib.sha256(json.dumps(compactdoc,sort_keys=True).encode()).hexdigest(),device=st.st_dev,inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=oct(stat.S_IMODE(st.st_mode)));census['disposable_fixture_only_not_current_query']=True;fixture=root/'RETAINED-CENSUS-DERIVED-FIXTURE.json';fixture.write_text(json.dumps(census,sort_keys=True)+'\n')
   # Original rawEquery/census files are untouched. Only TEMP requestbinding is derived.
   with mock.patch.object(self.fill,'D',root),contextlib.redirect_stdout(io.StringIO()):self.fill.finish(fixture,reference(fixture)['sha256'])
   final=root/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FINAL.NOT-RELEASED.json';p=json.loads(final.read_bytes());self.assert_bindings(p);self.assertEqual(p['actual_compact_census'],reference(fixture));self.assertEqual(p['actual_five_query']['sha256'],R['retained_five']['sha256']);self.assertIsNone(p['independent_review'])
 def test_fresh_outputs_scope_and_immutable_base_origin(self):
  self.assertFalse((HERE/'actual-entry-1').exists());self.assertFalse((HERE/'actual-readonly-admission-capture-1').exists());self.assertFalse((HERE/'ROOT-CURRENT290-ACTUAL-FETCH-AND-DEVFLOCK-CONTEXT.ACTUAL.json').exists());self.assertEqual(self.template['canonical_cfg_source']['selected_CMake']['sha256'],'f54e9093abf7850e3c14afef4932b7ad9e67b92a395cf8e031b8e5366e170b7b');self.assertEqual(reference(self.effective['path']),self.effective);self.assertTrue(all(value is None for value in R['future_runtime_PID_CID_holder_clock_query_grants'].values()));self.assertEqual(R['request']['sha256'],'31a38f75dea33c1b280270ce9d3e8ce25fd6ae354c0bf4808a7ada5def3ca435')
if __name__=='__main__':unittest.main(verbosity=2)
