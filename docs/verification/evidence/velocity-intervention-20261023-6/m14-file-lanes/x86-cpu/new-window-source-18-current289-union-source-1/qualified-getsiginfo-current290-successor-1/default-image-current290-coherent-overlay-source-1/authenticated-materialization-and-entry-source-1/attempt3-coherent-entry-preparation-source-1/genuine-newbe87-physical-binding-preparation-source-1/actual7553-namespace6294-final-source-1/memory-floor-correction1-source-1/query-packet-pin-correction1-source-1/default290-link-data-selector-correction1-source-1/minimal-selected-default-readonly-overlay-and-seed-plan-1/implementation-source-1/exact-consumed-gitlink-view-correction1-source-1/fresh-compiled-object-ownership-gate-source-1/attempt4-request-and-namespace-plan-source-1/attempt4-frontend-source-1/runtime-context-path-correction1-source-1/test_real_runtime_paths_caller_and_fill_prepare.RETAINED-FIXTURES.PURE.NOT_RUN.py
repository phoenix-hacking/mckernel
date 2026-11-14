"""Functional OS only; no security testing. Real producer/argument regressions; retained fixtures, no admission."""
import contextlib,copy,hashlib,importlib.util,io,json,os,resource,shutil,tempfile,unittest
from pathlib import Path
from unittest import mock
HERE=Path(__file__).parent
R=json.loads((HERE/'READY-RUNTIME-CONTEXT-PATH-CORRECTION1.SOURCE-ONLY.json').read_bytes())
def load(name,row):
 p=Path(row['path']) if isinstance(row,dict) else Path(row);spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def reference(path):path=Path(path);return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.caller=load('real_runtime_caller',R['caller']);cls.fill=load('real_runtime_fill',R['fill']);cls.cleanup=load('real_runtime_cleanup',R['cleanup']);cls.protocol=cls.cleanup.current230_contract();cls.cfg=json.loads(Path(R['config']['path']).read_bytes());cls.check=load('real_runtime_roles',HERE/'check_actual_runtime_command_output_bindings.PURE.py');cls.C=Path(R['retained_actual_five_fixture']['path']).parent;cls.context=Path(R['retained_context_fixture']['path']);cls.roles=cls.check.validate(cls.caller,cls.fill,cls.cfg,cls.cleanup,cls.protocol)
 def test_exact_producer_consumer_paths_before_query(self):
  self.assertTrue(self.caller.command_output_paths(self.cfg));self.assertEqual(self.roles['context_output'],self.cfg['commands']['prepare_metadata']['argv'][-1]);self.assertFalse(Path(self.roles['context_output']).exists());self.assertFalse(Path(self.roles['caller_capture_root']).exists());bad=copy.deepcopy(self.cfg);bad['commands']['prepare_metadata']['argv'][-1]=str(Path(R['original_F'])/'ROOT-CURRENT290-ACTUAL-FETCH-AND-DEVFLOCK-CONTEXT.ACTUAL.json')
  with self.assertRaisesRegex(RuntimeError,'before five'):self.check.validate(self.caller,self.fill,bad,self.cleanup,self.protocol)
  with self.assertRaisesRegex(RuntimeError,'before five'):self.caller.command_output_paths(bad)
 def test_all_other_output_role_mismatches_refuse(self):
  for mutate in [lambda x:x.update(P='/wrong'),lambda x:x.update(capture_root='/wrong'),lambda x:x['commands']['compact_census']['argv'].__setitem__(4,'/wrong'),lambda x:x['commands']['finish_metadata']['source'].update(path='/wrong'),lambda x:x['context_template'].update(path=self.roles['context_output'])]:
   bad=copy.deepcopy(self.cfg);mutate(bad)
   with self.assertRaises(RuntimeError):self.check.validate(self.caller,self.fill,bad,self.cleanup,self.protocol)
 def test_real_fill_prepare_retained_sealed_five_fixture(self):
  self.assertEqual(reference(R['retained_actual_five_fixture']['path']),R['retained_actual_five_fixture']);self.assertEqual(reference(self.context),R['retained_context_fixture'])
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary)
   for name in ['ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json','COMPACT-C252-CENSUS-REQUEST.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json']:shutil.copyfile(HERE/name,root/name)
   shutil.copytree(self.C,root/'actual-readonly-admission-capture-1');fixture_context=root/'ROOT-CURRENT290-ACTUAL-FETCH-AND-DEVFLOCK-CONTEXT.ACTUAL.json';shutil.copyfile(self.context,fixture_context)
   # Original timestamps/holder bytes stay retained fixture facts; outputs are TEMP only.
   with mock.patch.object(self.fill,'D',root),contextlib.redirect_stdout(io.StringIO()):self.fill.prepare(Path(self.fill.FETCHED_ORIGIN_PROOF['path']),self.fill.FETCHED_ORIGIN_PROOF['sha256'],fixture_context)
   compact=root/'COMPACT-C252-CENSUS-REQUEST.ACTUAL-FIVE-BOUND.NOT-GRANTED.json';prepared=root/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.ACTUAL-FIVE-BOUND.NOT-RELEASED.json';self.assertTrue(compact.is_file() and prepared.is_file());p=json.loads(prepared.read_bytes());self.assertEqual(p['root_fill_context'],reference(fixture_context));self.assertEqual(p['actual_five_query']['sha256'],R['retained_actual_five_fixture']['sha256']);self.assertEqual(p['source']['request'],R['request']);self.assertNotEqual(p['root_fill_context']['path'],self.roles['context_output'])
 def test_real_caller_to_prepare_transport_uses_created_context(self):
  m=self.caller
  class Prepared(BaseException):pass
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);cfg=copy.deepcopy(self.cfg);cfg['P']=str(root);cfg['capture_root']=str(root/'entry');cfg['commands']['prepare_metadata']['argv'][-1]=str(root/'ROOT-CURRENT290-ACTUAL-FETCH-AND-DEVFLOCK-CONTEXT.ACTUAL.json')
   # Mirror real code bytes only into TEMP so early source/output guards remain real.
   for slot in ('five_observations','prepare_metadata','finish_metadata'):
    old=cfg['commands'][slot]['source'];new=root/Path(old['path']).name
    if not new.exists():shutil.copyfile(old['path'],new)
    cfg['commands'][slot]['source']=reference(new);cfg['commands'][slot]['argv']=[str(new) if arg==old['path'] else arg for arg in cfg['commands'][slot]['argv']]
   cfg['fill']=cfg['commands']['prepare_metadata']['source'];cfg['commands']['compact_census']['argv'][4]=str(root/'COMPACT-C252-CENSUS-REQUEST.ACTUAL-FIVE-BOUND.NOT-GRANTED.json');shutil.copytree(self.C,root/'actual-readonly-admission-capture-1');ctx=root/'precursor.json';shutil.copyfile(self.context,ctx);review=root/'fixture-source-review.json';review.write_text(json.dumps(dict(decision='PASS_SOURCE_EXISTING_SAME_OFD_IMAGE_CLEANUP',implementation_ownership=False,reviewer='unit-fixture-only-not-actual-review',source=R['cleanup'],same_OFD_transport='STDIN_FD0_SUDO_A')));prep=root/'fixture-preparation-grant.json';prep.write_text(json.dumps(dict(author='/root',decision='GRANT_CURRENT290_READONLY_PREPARATION',caller_sha256=m.digest(m.__file__),config_sha256=R['config']['sha256'],census_observer=R['corrected_census_observer'],existing_cleanup_source=R['cleanup'],existing_cleanup_source_review=reference(review),context=reference(ctx),namespace_initialization=R['actual_namespace_initialization'])));guard=root/'disposable-fd';guard.write_bytes(b'');fd=os.open(guard,os.O_RDONLY);calls=[];originallimit=resource.getrlimit
   def captured(argv,capture,label,**kwargs):
    calls.append((label,argv))
    if label=='five':return dict(returncode=0)
    if label=='prepare':
     self.assertEqual(argv[-1],cfg['commands']['prepare_metadata']['argv'][-1]);self.assertTrue(Path(argv[-1]).is_file());actual=json.loads(Path(argv[-1]).read_bytes());self.assertEqual(actual['actual_devflock_holder']['pid'],os.getpid());self.assertEqual(actual['actual_devflock_holder']['fd'],fd);raise Prepared()
    raise AssertionError('unreviewed later transport')
   try:
    with mock.patch.object(m,'D',root),mock.patch.object(m,'actual_config',return_value=cfg),mock.patch.object(m.os,'sched_getaffinity',return_value={7}),mock.patch.object(m.resource,'getrlimit',side_effect=lambda key:(resource.RLIM_INFINITY,resource.RLIM_INFINITY) if key==resource.RLIMIT_CPU else originallimit(key)),mock.patch.object(m,'captured',side_effect=captured),mock.patch.object(m,'lock_functions',return_value={'identity':lambda st:{},'acquire_development_lock':lambda arg:fd}),mock.patch.object(m,'check_held'),mock.patch.object(m.fcntl,'flock'),mock.patch('signal.signal'),mock.patch('subprocess.Popen',side_effect=AssertionError('Popen forbidden')):
     with self.assertRaises(Prepared):m.execute(prep,Path(R['config']['path']),R['config']['sha256'])
   finally:
    try:os.close(fd)
    except OSError:pass
   self.assertEqual([row[0] for row in calls],['five','prepare']);self.assertFalse(Path(self.roles['context_output']).exists());self.assertFalse(Path(self.roles['caller_capture_root']).exists())
if __name__=='__main__':unittest.main(verbosity=2)
