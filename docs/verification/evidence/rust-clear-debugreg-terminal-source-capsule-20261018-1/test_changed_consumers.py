"""Actual configure/validator metadata checks, disposable ordinary fixtures only."""
from pathlib import Path
import copy,hashlib,importlib.util,json,unittest,contextlib,io,tempfile
P=Path(__file__).resolve().parent

def module(name):
 s=importlib.util.spec_from_file_location(name.replace('-','_').replace('.','_'),P/name);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=module('publication-cleanup-tests.py')
class Metadata(base.HostSplitConfigureTests):
 def setUp(self):
  super().setUp();self.m.IMAGE_CANDIDATE='a'*40
 def test_changed_author_actual_configure(self):
  r=self.release_fixture();self.m.configure(r)
  for author in (None,''):
   bad=copy.deepcopy(r);bad['author']=author
   with self.subTest(author=author),self.assertRaisesRegex(self.m.Refusal,'source-git-binding-required'):self.m.configure(bad)
 def test_real_producer_author_to_actual_configure(self):
  r=self.release_fixture();m=self.m
  draft=m.prepare_release(r['observation'],r['git_commit'],r['git_tree'])
  self.assertEqual(draft['author'],'clear_debugreg_terminal_prepare_1726');self.assertEqual(draft['status'],'NOT_RELEASED');self.assertIs(draft['fetched_source_verified'],False)
  produced=copy.deepcopy(draft)
  for key in ('status','source_review','execution_review','fetched_source_verified'):produced[key]=r[key]
  m.configure(produced)
  for author in (None,''):
   bad=copy.deepcopy(produced);bad['author']=author
   with self.subTest(author=author),self.assertRaisesRegex(m.Refusal,'source-git-binding-required'):m.configure(bad)
 def test_author_actual_entrypoint_before_effects(self):
  r=self.release_fixture();m=self.m;before={str(p):p.read_bytes() for p in (m.ATTEMPT,m.SHARED)};calls=[]
  def forbidden(*args,**kwargs):calls.append('forbidden');raise AssertionError('Git/root/recover reached before author refusal')
  self.patch('recover',forbidden)
  patch=base.mock.patch.object(m.subprocess,'check_output',forbidden);patch.start();self.addCleanup(patch.stop)
  for author in (None,''):
   bad=copy.deepcopy(r);bad['author']=author;release=m.NAMESPACE/'author-bad-release.json';release.write_bytes(m.canonical(bad));out=io.StringIO()
   with contextlib.redirect_stdout(out):rc=m.main(['--release',str(release),'--release-sha256',m.digest(release.read_bytes()),'--execute'])
   self.assertEqual(rc,1);self.assertEqual(json.loads(out.getvalue()),dict(status='REFUSED',reason='source-git-binding-required'));self.assertEqual(calls,[]);self.assertIsNone(m.RELEASE)
   self.assertEqual({str(p):p.read_bytes() for p in (m.ATTEMPT,m.SHARED)},before)
 def test_changed_profile_actual_configure(self):
  r=self.release_fixture();self.m.configure(r)
  for key,value in [('CpusetCpus','0-7'),('Memory',21474836480),('MemorySwap',0),('PidsLimit',1024),('NetworkMode','host')]:
   bad=copy.deepcopy(r);bad['observation']['container_inspect']['HostConfig'][key]=value
   with self.subTest(field=key),self.assertRaises(self.m.Refusal):self.m.configure(bad)
 def test_changed_publication_actual_configure(self):
  r=self.release_fixture();self.m.configure(r)
  for key,value in [('fetched_source_verified',False),('git_commit','bad'),('git_tree','bad')]:
   bad=copy.deepcopy(r);bad[key]=value
   with self.subTest(field=key),self.assertRaises(self.m.Refusal):self.m.configure(bad)
 def test_full_source_actual_configure(self):
  r=self.release_fixture();self.m.configure(r)
  request=json.loads(self.m.REQUEST.read_bytes())
  for key in ('host_owner_path','driver_path','provenance_path','source_manifest','toolchain_manifest'):
   for missing in (True,False):
    bad=copy.deepcopy(r);rows=bad['observation']['selected_files'];path=request[key]
    if missing:bad['observation']['selected_files']=[row for row in rows if row['path']!=path]
    else:next(row for row in rows if row['path']==path)['sha256']='0'*64
    with self.subTest(field=key,missing=missing),self.assertRaises(self.m.Refusal):self.m.configure(bad)
class Entrypoints(unittest.TestCase):
 def test_no_effect_pending(self):
  m=module('cleanup.py');o=module('observe_reset_image_retirement.py');r=module('retention_observer.py');ordinary=module('ordinary_readback.py')
  with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(m.main([]),1)
  with self.assertRaisesRegex(RuntimeError,'pending actual source bindings'):o.main([])
  with self.assertRaisesRegex(RuntimeError,'not released'):r.validate({'status':'NOT_RELEASED'})
  self.assertEqual(ordinary.observe(ordinary.module())['status'],'PENDING_ORDINARY_READABILITY')
  self.assertEqual(r.ENGINE,P/'retention-engine-frozen.py');self.assertEqual(hashlib.sha256(r.ENGINE.read_bytes()).hexdigest(),'f7a35968f510c60791ac6604cdaaa6a2abbd1a991d04f6afb4ad61c84cb76ef8')
  self.assertEqual(len(r.ARTIFACT_PATHS),15);self.assertEqual(sum(v['action']=='reuse' for v in r.ARTIFACT_PATHS.values()),4)
  self.assertEqual(r.ARTIFACT_PATHS['process.c.o']['action'],'reuse')
 def test_retention_actual_validator(self):
  r=module('retention_observer.py');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  with tempfile.TemporaryDirectory(dir=P) as d:
   d=Path(d);source=d/'source.json';execution=d/'execution.json'
   sources={k:dict(path=str(p),sha256=sha(p)) for k,p in [('observer',P/'retention_observer.py'),('engine',r.ENGINE),('join',r.JOIN)]}
   review=dict(status='PASS',reviewer='independent-fixture-reviewer',implementation_ownership=False,source_map=sources);source.write_text(json.dumps(review))
   release=dict(schema='mckernel.rust-image.finite-retention-release.v1',status='PASS_EXECUTION_RELEASE',author='clear-debugreg-terminal-author',boot_id=r.BOOT,output=str(r.DEST),resource_profile=r.PROFILE,source_review=dict(path=str(source),sha256=sha(source)),**sources)
   execution.write_text(json.dumps(dict(review,reviewed_retention_payload_sha256=hashlib.sha256(r.canonical(release)).hexdigest())));release['execution_review']=dict(path=str(execution),sha256=sha(execution))
   self.assertEqual(r.validate(release),release)
   for field,value in [('author',None),('resource_profile',{}),('engine',{}),('output','wrong')]:
    bad=copy.deepcopy(release);bad[field]=value
    with self.subTest(field=field),self.assertRaises(RuntimeError):r.validate(bad)
   rows=[dict(kind=k,action=v['action'],original=dict(path=v['original'],size=1),retained=v['retained'],retained_authority=dict(path=v['retained'])) for k,v in r.ARTIFACT_PATHS.items()]
   self.assertEqual(r.validate_artifact_rows(rows),rows)
   self.assertEqual(set(k for k,v in r.ARTIFACT_PATHS.items() if v['action']=='reuse'),{'syscall.c.o','process.c.o','mckernel_rust.o','mckernel.img'})
   for key in ('process.c.o','syscall.c.o'):
    bad=copy.deepcopy(rows);next(row for row in bad if row['kind']==key)['retained']='wrong'
    with self.subTest(kind=key),self.assertRaises(RuntimeError):r.validate_artifact_rows(bad)
 def test_raw5_export_actual_validator(self):
  e=module('export_raw_five.py');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  with tempfile.TemporaryDirectory(dir=P) as d:
   p=Path(d)/'joined.json';p.write_text(json.dumps(dict(returncode=0,direct_child_joined=True)))
   r=dict(schema='mckernel.reset-image.raw-five-export-release.v1',status='PASS_EXECUTION_RELEASE',author='clear-debugreg-terminal-author',helper_sha256=sha(P/'export_raw_five.py'),summary_sha256=e.SUMMARY_SHA,output=str(e.OUTPUT),argv=e.COMMAND,names=list(e.NAMES),max_archive_bytes=e.CAP,file_sha256={n:'0'*64 for n in e.NAMES},observer_status=dict(path=str(p),sha256=sha(p)),summary_status=dict(path=str(p),sha256=sha(p)))
   review=dict(status='PASS',reviewer='independent-fixture-reviewer',implementation_ownership=False,helper_sha256=r['helper_sha256'],summary_sha256=r['summary_sha256']);r['source_review']=review;r['execution_review']=dict(review,reviewed_payload_sha256=e.sha(e.canonical(r)))
   self.assertEqual(e.validate_release(r),r)
   for key,value in [('author',None),('argv',[]),('output','wrong'),('names',list(reversed(e.NAMES))),('helper_sha256','0'*64),('observer_status',None)]:
    bad=copy.deepcopy(r);bad[key]=value
    with self.subTest(field=key),self.assertRaises(RuntimeError):e.validate_release(bad)
   for field,value in [('reviewer',r['author']),('implementation_ownership',True),('reviewed_payload_sha256','0'*64)]:
    bad=copy.deepcopy(r);bad['execution_review'][field]=value
    with self.subTest(field=field),self.assertRaises(RuntimeError):e.validate_release(bad)
# Only changed checks: inherited canonical39 unaffected tests are deliberately excluded.
if __name__=='__main__':
 suite=unittest.TestSuite([Metadata(n) for n in ['test_real_producer_author_to_actual_configure','test_author_actual_entrypoint_before_effects','test_changed_author_actual_configure','test_changed_profile_actual_configure','test_changed_publication_actual_configure','test_full_source_actual_configure']]+[Entrypoints(n) for n in ['test_no_effect_pending','test_raw5_export_actual_validator','test_retention_actual_validator']])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 (P/'changed-consumers-result.json').write_text(json.dumps(dict(status='PASS' if result.wasSuccessful() else 'FAIL_PRESERVED',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),actual_configure=True,physical_cleanup=False,root=False,docker=False,builds=0,guests=0),indent=2)+'\n')
 raise SystemExit(not result.wasSuccessful())
