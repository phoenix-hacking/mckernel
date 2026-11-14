"""Functional OS only; no security testing. Exact initializer/runtime role join and TEMP production producer."""
import contextlib,copy,hashlib,importlib.util,io,json,os,shutil,stat,subprocess,tempfile,unittest
from pathlib import Path
from unittest import mock
HERE=Path(__file__).parent.parent
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
 def bootstrap_to_transport_boundary(self,mutate_initialized=None,mutate_context=None,mutate_config=None):
  class BoundaryReached(Exception):pass
  with tempfile.TemporaryDirectory() as temporary:
   temp=Path(temporary);capture=temp/'disposable-caller-capture';original_capture=Path(self.cfg['capture_root']);config=Path(R['config']['path']);checksum=R['config']['sha256']
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
   calls=[];writes=[]
   def boundary(argv,root,name):
    self.assertEqual(argv,self.cfg['commands']['five_observations']['argv']);self.assertEqual(root,original_capture);self.assertEqual(name,'five');self.assertFalse(original_capture.exists());self.assertTrue((capture/'PREPARATION-GRANT-REFERENCE.json').is_file());self.assertEqual(writes,[('mkdir',original_capture),('publish',original_capture/'PREPARATION-GRANT-REFERENCE.json')]);calls.append(name);raise BoundaryReached()
   real_mkdir=Path.mkdir;real_publish=self.caller.publish;real_getrlimit=self.caller.resource.getrlimit
   def virtual_getrlimit(which):return (self.caller.resource.RLIM_INFINITY,self.caller.resource.RLIM_INFINITY) if which==self.caller.resource.RLIMIT_CPU else real_getrlimit(which)
   def disposable_mkdir(path,*args,**kwargs):
    self.assertEqual(path,original_capture,'only exact disposable capture-root mkdir is allowed');writes.append(('mkdir',path));return real_mkdir(capture,*args,**kwargs)
   def disposable_publish(path,value):
    self.assertEqual(path,original_capture/'PREPARATION-GRANT-REFERENCE.json','only exact disposable grant-reference publish is allowed');writes.append(('publish',path));return real_publish(capture/path.name,value)
   before=[(Path(row['path']).stat().st_dev,Path(row['path']).stat().st_ino,sorted(Path(row['path']).iterdir())) for row in self.initialized['identities']]
   with contextlib.ExitStack() as guards:
    guards.enter_context(mock.patch.object(Path,'mkdir',new=disposable_mkdir));guards.enter_context(mock.patch.object(self.caller,'publish',side_effect=disposable_publish));guards.enter_context(mock.patch.object(self.caller,'captured',side_effect=boundary));lock=guards.enter_context(mock.patch.object(self.caller,'lock_functions',side_effect=AssertionError('no permanent lock')));guards.enter_context(mock.patch.object(self.caller.fcntl,'flock',side_effect=AssertionError('no flock')));guards.enter_context(mock.patch.object(self.caller.os,'sched_getaffinity',return_value={7}));guards.enter_context(mock.patch.object(self.caller.resource,'getrlimit',side_effect=virtual_getrlimit))
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
if __name__=='__main__':unittest.main(verbosity=2)
