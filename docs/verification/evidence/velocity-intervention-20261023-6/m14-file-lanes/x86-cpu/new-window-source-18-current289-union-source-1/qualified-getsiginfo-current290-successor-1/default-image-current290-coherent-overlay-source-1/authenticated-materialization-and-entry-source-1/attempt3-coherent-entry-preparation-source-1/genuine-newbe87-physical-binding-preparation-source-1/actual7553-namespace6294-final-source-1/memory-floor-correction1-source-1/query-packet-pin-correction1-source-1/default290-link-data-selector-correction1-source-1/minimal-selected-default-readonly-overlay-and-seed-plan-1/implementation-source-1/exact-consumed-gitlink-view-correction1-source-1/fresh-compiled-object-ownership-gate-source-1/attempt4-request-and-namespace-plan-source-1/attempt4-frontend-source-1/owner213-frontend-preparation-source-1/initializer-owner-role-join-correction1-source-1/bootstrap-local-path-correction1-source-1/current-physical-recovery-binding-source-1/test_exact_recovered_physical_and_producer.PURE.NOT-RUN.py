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
 def bootstrap_to_transport_boundary(self,mutate_initialized=None,mutate_context=None,mutate_config=None):
  class BoundaryReached(Exception):pass
  with tempfile.TemporaryDirectory() as temporary:
   temp=Path(temporary);capture=temp/'disposable-caller-capture';config=Path(R['config']['path']);checksum=R['config']['sha256']
   if mutate_config is not None:
    bad=copy.deepcopy(self.cfg);mutate_config(bad);config=temp/'DISPOSABLE-CONFIG.json';config.write_text(json.dumps(bad));checksum=reference(config)['sha256']
   context=json.loads(Path(R['context_template']['path']).read_bytes());context.update(author='/root',disposable_fixture_only_no_authority=True);context['aggregate']['actual_no_other_heavy']=True;context['continuity']['no_heavy_since_latest_physical']=True
   if mutate_context is not None:mutate_context(context)
   cp=temp/'DISPOSABLE-CONTEXT.json';cp.write_text(json.dumps(context))
   initialized=copy.deepcopy(self.initialized);ir=self.cfg['namespace_initialization']
   if mutate_initialized is not None:
    mutate_initialized(initialized);ip=temp/'DISPOSABLE-INITIALIZER.json';ip.write_text(json.dumps(initialized));ir=reference(ip)
   review=temp/'DISPOSABLE-CLEANUP-REVIEW.json';review.write_text(json.dumps(dict(decision='PASS_SOURCE_EXISTING_SAME_OFD_IMAGE_CLEANUP',implementation_ownership=False,reviewer='/disposable-fixture-reviewer',source=R['cleanup'],same_OFD_transport='STDIN_FD0_SUDO_A',disposable_fixture_only_no_authority=True)))
   grant=temp/'DISPOSABLE-PREPARATION-GRANT.json';grant.write_text(json.dumps(dict(author='/root',decision='GRANT_CURRENT290_READONLY_PREPARATION',caller_sha256=R['caller']['sha256'],config_sha256=checksum,census_observer=R['corrected_census_observer'],existing_cleanup_source=R['cleanup'],existing_cleanup_source_review=reference(review),context=reference(cp),namespace_initialization=ir,disposable_fixture_only_no_authority=True)))
   calls=[]
   def boundary(argv,root,name):
    self.assertEqual(argv,self.cfg['commands']['five_observations']['argv']);self.assertEqual(root,capture);self.assertEqual(name,'five');calls.append(name);raise BoundaryReached()
   real_path=Path;real_getrlimit=self.caller.resource.getrlimit
   def virtual_getrlimit(which):return (self.caller.resource.RLIM_INFINITY,self.caller.resource.RLIM_INFINITY) if which==self.caller.resource.RLIMIT_CPU else real_getrlimit(which)
   def disposable_path(value,*args,**kwargs):return capture if str(value)==self.cfg['capture_root'] else real_path(value,*args,**kwargs)
   before=[(Path(row['path']).stat().st_dev,Path(row['path']).stat().st_ino,sorted(Path(row['path']).iterdir())) for row in self.initialized['identities']]
   with contextlib.ExitStack() as guards:
    guards.enter_context(mock.patch.object(self.caller,'Path',side_effect=disposable_path));guards.enter_context(mock.patch.object(self.caller,'captured',side_effect=boundary));lock=guards.enter_context(mock.patch.object(self.caller,'lock_functions',side_effect=AssertionError('no permanent lock')));guards.enter_context(mock.patch.object(self.caller.fcntl,'flock',side_effect=AssertionError('no flock')));guards.enter_context(mock.patch.object(self.caller.os,'sched_getaffinity',return_value={7}));guards.enter_context(mock.patch.object(self.caller.resource,'getrlimit',side_effect=virtual_getrlimit))
    if mutate_initialized is None and mutate_context is None and mutate_config is None:
     with self.assertRaises(BoundaryReached):self.caller.execute(grant,config,checksum)
     self.assertEqual(calls,['five']);self.assertTrue((capture/'PREPARATION-GRANT-REFERENCE.json').is_file())
    else:
     with self.assertRaises(RuntimeError):self.caller.execute(grant,config,checksum)
     self.assertEqual(calls,[])
    lock.assert_not_called()
   after=[(Path(row['path']).stat().st_dev,Path(row['path']).stat().st_ino,sorted(Path(row['path']).iterdir())) for row in self.initialized['identities']];self.assertEqual(before,after);self.assertFalse(Path(self.cfg['capture_root']).exists());self.assertFalse((HERE/'actual-readonly-admission-capture-1').exists())
 def test_real_new_runtime_physical_consumer_positive(self):
  self.assertTrue(self.helper.require_new_runtime_facts(self.cfg));self.bootstrap_to_transport_boundary()
  self.assertEqual(self.cfg['physical']['sha256'],'468813ec41d54d6549345a909ffd8ccbb0b25448ee31ac3d1f611870b6784cc3')
  self.assertEqual(self.cfg['postjoin']['sha256'],'11b6c7764641dfac0b63f09b0fef049fdab3326f2ee40aa9c72962962b402fd3')
 def test_old_only_wrong_binding_missing_join_and_mutated_recovery_refused(self):
  spec=json.loads(Path(self.b['physical_consumer_spec']['path']).read_bytes());adapter=load('exact_recovery_adapter',spec['physical_validator']);old=json.loads(Path(spec['historical_baseline_spec']['path']).read_bytes())
  for key,value in [('physical',old['actual_acceptance']),('postjoin',old['actual_postjoin']),('postjoin',self.cfg['physical'])]:
   bad=copy.deepcopy(self.cfg);bad[key]=value
   with self.subTest(binding=key),self.assertRaises(RuntimeError):self.helper.require_new_runtime_facts(bad)
  with self.assertRaises(RuntimeError):adapter.validate(old['actual_acceptance'],old['actual_postjoin'])
  self.bootstrap_to_transport_boundary(mutate_initialized=lambda d:d.update(owner=R['owner']))
  self.bootstrap_to_transport_boundary(mutate_context=lambda d:d.update(actual_current_physical=old['actual_acceptance']))
  self.bootstrap_to_transport_boundary(mutate_config=lambda d:d['pins'].update(owner=self.initialized['owner']))
  records=[adapter.auth(adapter.R[k]) for k in ['completion','postjoin','action','helper_join','metadata']];records+=[adapter.raw(adapter.R['archive'])];records +=[adapter.auth(adapter.R[k]) for k in ['signal_budget','unlink_budget','source_order','failed_references']]
  for index,mutate in [(1,lambda d:d.update(helper_join=None)),(0,lambda d:d.update(action_result_sha256='0'*64)),(2,lambda d:d.update(action_budget_consumed=dict(pidfd_sigkill=2,shared_unlink=1))),(4,lambda d:d['value'].update(pid=1)),(1,lambda d:d['retired_groups'].update({'998188':[1]}))]:
   bad=copy.deepcopy(records);mutate(bad[index])
   with self.subTest(record=index),self.assertRaises((RuntimeError,KeyError,TypeError)):adapter.validate_records(*bad)
if __name__=='__main__':unittest.main(verbosity=2)
