"""Functional OS only; no security testing. Exact initializer/runtime role join and TEMP production producer."""
import contextlib,copy,hashlib,importlib.util,io,json,os,shutil,stat,subprocess,tempfile,unittest
from pathlib import Path
from unittest import mock
HERE=Path(__file__).parent
R=json.loads((HERE/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json').read_bytes())
F=json.loads(Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/EXACT-ROLEJOIN-PRODUCER-FIXTURES.SOURCE-ONLY.json').read_bytes())
def reference(path):p=Path(path);return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def load(name,row):
 p=Path(row['path']);assert reference(p)==row;spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.guards=contextlib.ExitStack()
  for obj,name in [(subprocess,'Popen'),(subprocess,'run'),(os,'system'),(os,'kill')]:cls.guards.enter_context(mock.patch.object(obj,name,side_effect=AssertionError('no query/action transport '+name)))
  cls.addClassCleanup(cls.guards.close);cls.helper=load('exact_role_join_helper',R['origin_helper']);cls.b=cls.helper.data();cls.initialized=json.loads(Path(cls.b['actual_namespace_initialization']['path']).read_bytes());cls.cfg=json.loads(Path(R['config']['path']).read_bytes());cls.caller=load('actual_role_join_caller',R['caller']);cls.fill=load('actual_role_join_fill',R['fill'])
 def test_REAL_prepare_finish_emits_runtime213_and_retains_initializer15(self):
  for row in F.values():self.assertEqual(reference(row['path']),row)
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary)
   for name in ('ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json','COMPACT-C252-CENSUS-REQUEST.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json'):shutil.copyfile(HERE/name,root/name)
   shutil.copytree(Path(F['five']['path']).parent,root/'actual-readonly-admission-capture-1');context=root/'ROOT-CURRENT290-ACTUAL-FETCH-AND-DEVFLOCK-CONTEXT.ACTUAL.json';doc=json.loads(Path(F['context']['path']).read_bytes());doc['actual_current_physical']=self.cfg['physical'];doc['actual_current_live_postjoin']=self.cfg['postjoin'];context.write_text(json.dumps(doc))
   with mock.patch.object(self.fill,'D',root),contextlib.redirect_stdout(io.StringIO()):self.fill.prepare(Path(self.fill.FETCHED_ORIGIN_PROOF['path']),self.fill.FETCHED_ORIGIN_PROOF['sha256'],context)
   prepared=json.loads((root/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.ACTUAL-FIVE-BOUND.NOT-RELEASED.json').read_bytes());self.assertEqual(prepared['argv'],self.cfg['commands']['owner_entry_unchanged']['argv']);self.assertEqual(prepared['source']['owner'],R['owner']);self.assertEqual(prepared['source']['request'],R['request'])
   compact=root/'COMPACT-C252-CENSUS-REQUEST.ACTUAL-FIVE-BOUND.NOT-GRANTED.json';doc=json.loads(compact.read_bytes());census=json.loads(Path(F['census']['path']).read_bytes());st=compact.stat();census['request']=dict(path=str(compact),sha256=reference(compact)['sha256'],normalized_sha256=hashlib.sha256(json.dumps(doc,sort_keys=True).encode()).hexdigest(),device=st.st_dev,inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=oct(stat.S_IMODE(st.st_mode)));census['disposable_fixture_only_not_current_query']=True;p=root/'RETAINED-CENSUS-DERIVED-FIXTURE.json';p.write_text(json.dumps(census))
   with mock.patch.object(self.fill,'D',root),contextlib.redirect_stdout(io.StringIO()):self.fill.finish(p,reference(p)['sha256'])
   final=json.loads((root/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FINAL.NOT-RELEASED.json').read_bytes());self.assertEqual(final['argv'],self.cfg['commands']['owner_entry_unchanged']['argv']);self.assertEqual(final['source']['owner'],R['owner']);self.assertEqual(final['source']['request'],R['request']);self.assertEqual(self.b['namespace_initializer_owner'],self.initialized['owner']);self.assertTrue(self.helper.require_initializer_runtime_owner_roles(self.initialized,self.b));self.assertEqual(final['current_physical'],self.cfg['physical']);self.assertEqual(final['current_live_postjoin'],self.cfg['postjoin']);self.assertTrue(self.caller.command_output_paths(self.cfg))
if __name__=='__main__':unittest.main(verbosity=2)
