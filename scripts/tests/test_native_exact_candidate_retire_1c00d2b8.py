#!/usr/bin/env python3
import importlib.util
import os, json, stat, tarfile, time
from datetime import datetime, timezone
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('retire',HERE/'native_exact_candidate_retire_1c00d2b8.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

class Tests(unittest.TestCase):
 def test_operation_failure_journal_and_close_survive_as_explicit_tree(self):
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);release=self.release(roots);write=M.Journal.write;close=M.Journal.close
   def journal_write(journal,phase,**kwargs):
    if phase=='terminal-failure':raise OSError('failure journal error')
    return write(journal,phase,**kwargs)
   def journal_close(journal):close(journal);raise OSError('journal close error')
   with mock.patch.object(M,'quarantine',side_effect=M.RetirementError('operation primary')),mock.patch.object(M.Journal,'write',new=journal_write),mock.patch.object(M.Journal,'close',new=journal_close):
    with self.assertRaises(M.RetirementCompositeError) as raised:self.execute(roots,release)
   record=M.failure_record(raised.exception)
   self.assertEqual(record['primary']['primary']['message'],'operation primary')
   self.assertEqual(record['primary']['cleanup']['message'],'failure journal error')
   self.assertEqual(record['cleanup']['message'],'journal close error')
   self.assertTrue(all(root.exists() for root in roots))
 def test_explicit_failure_record_is_bounded_cycle_safe_and_ignores_context(self):
  error=M.RetirementCompositeError(ValueError('primary'),OSError('cleanup'));error.primary=error
  error.__context__=ValueError('implicit context excluded')
  encoded=json.dumps(M.failure_record(error),sort_keys=True)
  self.assertIn('FailureTreeCycle',encoded);self.assertNotIn('implicit context excluded',encoded)
  error=ValueError('first')
  for unused in range(40):error=M.RetirementCompositeError(error,OSError('later'))
  self.assertIn('FailureTreeLimit',json.dumps(M.failure_record(error)))
 def trees(self,t):
  answer=[]
  for n in ('one','two'):
   r=Path(t)/n;(r/'d').mkdir(parents=True);(r/'d'/'f').write_text(n);(r/'safe').symlink_to('d/f');answer.append(r)
  return answer
 def release(self,roots):
  rows=[]
  for i,r in enumerate(roots): rows.append(dict(path=str(r),parent=M.root_identity(r.parent),root=M.root_identity(r),quarantine_name='.q%d'%i,quarantine_mode=0o700,quarantine_uid=os.getuid(),quarantine_gid=os.getgid(),members=M.inventory_root(r)['members']))
  base=roots[0].parent;archive=M._archive_module();entries=[]
  for label,row in zip(('candidate','metadata-backup'),rows):
   for member in row['members']:
    entry=dict(root=label,path=member['path'],type={'directory':'directory','file':'regular','symlink':'symlink'}[member['kind']],mode=member['mode'],uid=member['uid'],gid=member['gid'],size=member['size'],classification='capsule-required' if label=='candidate' and member['kind']=='file' else 'reconstructible')
    if member['kind']=='file':entry['sha256']=member['sha256']
    if member['kind']=='symlink':entry['target']=member['target']
    entries.append(entry)
  manifest=dict(format='native-exact-candidate-retention-v1',roots=[dict(name='candidate',path=str(roots[0]),identity={k:rows[0]['root'][{'dev':'device'}.get(k,k)] for k in ('dev','inode','uid','gid','mode')}),dict(name='metadata-backup',path=str(roots[1]),identity={k:rows[1]['root'][{'dev':'device'}.get(k,k)] for k in ('dev','inode','uid','gid','mode')})],revisions={},entries=entries,capsule_required=['candidate:'+x['path'] for x in entries if x['root']=='candidate' and x['classification']=='capsule-required'])
  mpath=base/'retention.json';mpath.write_text(json.dumps(manifest,sort_keys=True));capsule=base/'retained.tar';archive.build_archive(str(mpath),str(roots[0]),str(roots[1]),str(capsule))
  capsha=M.digest_bytes(capsule.read_bytes());msha=M.digest_bytes(mpath.read_bytes())
  msha=M.digest_bytes(mpath.read_bytes());host=dict(SecurityOpt=[],Privileged=False,ReadonlyRootfs=True,NanoCpus=0,Memory=0,PidsLimit=0,CpusetCpus='',RestartPolicy=dict(Name='no',MaximumRetryCount=0),AutoRemove=False);state=dict(Status='exited',Running=False,Paused=False,Restarting=False,Dead=False,Pid=0,ExitCode=1,OOMKilled=False);config=dict(Config=dict(Image='reviewed',User='',Cmd=['x']),HostConfig=host,Mounts=[])
  return dict(schema='mckernel.ordinary-retirement-release.v1',operational_exclusion='released operational exclusion spans observation and deletion',sealed=dict(retention_manifest_path=str(mpath),capsule_path=str(capsule),retention_manifest_sha256=msha,retention_manifest_pushed_sha256=msha,retention_manifest_fetched_sha256=msha,capsule_sha256=capsha,capsule_pushed_sha256=capsha,capsule_fetched_sha256=capsha),roots=rows,observer=dict(observer_sha256=M.digest_bytes((HERE.parent/'docs/verification/evidence/native-exact-candidate-live-reference-observer-1c00d2b8-1.py').read_bytes()),boot_id=M.current_boot_id()),docker=dict(terminal=dict(id=M.TERMINAL_CONTAINER_ID,state=state,exact_config=config)))
 def observer(self,r,mutate=None):
  def run(qs,members):
   rounds=[dict(round=i,target_references=[],permission_denials=[],tree_revalidation_failures=[],unscanned_final_identities=[],unresolved_churn=[],closure_nonconvergent=False,complete_mount_proofs=True,clean=True) for i in (1,2)]
   now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z');x=dict(schema='mckernel.read-only-live-reference-snapshot.v7-map-files-v3',status='PASS',scan_complete=True,failure=None,observer_sha256=r['observer']['observer_sha256'],boot_id=r['observer']['boot_id'],observer_pid=os.getpid(),observer_starttime='1',started_at_utc=now,ended_at_utc=now,persistent_tree_revalidation_failures=[],tree_observation_transients=[],roots=[dict(path=q,mode='0700',device_number=os.stat(q).st_dev,inode=os.stat(q).st_ino,uid=os.stat(q).st_uid,gid=os.stat(q).st_gid,tree_member_identities=m) for q,m in zip(qs,members)],rounds=rounds)
   if mutate:mutate(x)
   return x
  return run
 def terminal(self,r,mounts=None):
  x=dict(Id=M.TERMINAL_CONTAINER_ID,State=r['docker']['terminal']['state'],Config=r['docker']['terminal']['exact_config']['Config'],HostConfig=r['docker']['terminal']['exact_config']['HostConfig'],Mounts=mounts if mounts is not None else r['docker']['terminal']['exact_config']['Mounts']);return x
 def census(self,r,rows=None): return lambda:dict(ps_all=[x['Id'] for x in rows if x] if rows is not None else [M.TERMINAL_CONTAINER_ID],inspect=rows if rows is not None else [self.terminal(r)])
 def execute(self,roots,r,obs=None,census=None): return M.retire(roots,r,roots[0].parent/'claim',roots[0].parent/'journal',roots[0].parent/'evidence',obs or self.observer(r),census or self.census(r))
 def test_temp_tree_state_machine_safe_symlinks(self):
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);self.assertEqual(self.execute(roots,r)['status'],'PASS');self.assertFalse(roots[0].exists());self.assertFalse(roots[1].exists())
 def test_missing_extra_changed_and_hardlink_fail_seal(self):
  for op in (lambda x:(x[0]/'d'/'f').unlink(),lambda x:(x[0]/'extra').write_text('x'),lambda x:(x[0]/'d'/'f').write_text('changed'),lambda x:os.link(x[0]/'d'/'f',x[0]/'alias'),lambda x:os.mkfifo(str(x[0]/'pipe'))):
   with self.subTest(op=op),tempfile.TemporaryDirectory() as t:
    roots=self.trees(t);r=self.release(roots);op(roots)
    with self.assertRaises(M.RetirementError):self.execute(roots,r)
 def test_root_substitution_collision_and_release_mismatch(self):
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);roots[0].rename(Path(t)/'moved');roots[0].mkdir()
   with self.assertRaises(M.RetirementError):self.execute(roots,r)
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);(Path(t)/'.q0').mkdir()
   with self.assertRaises(M.RetirementError):self.execute(roots,r)
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);del r['sealed']['capsule_sha256']
   with self.assertRaises(M.RetirementError):self.execute(roots,r)
 def test_stale_pretransition_and_sticky_observer_fail_keep_quarantines(self):
  for m in (lambda x:x.update(boot_id='bad'),lambda x:x['rounds'][1].update(unresolved_churn=['x']),lambda x:x['rounds'][1].update(clean=False),lambda x:x.update(permission_denials=['x']),lambda x:x.update(target_references='bad'),lambda x:x.update(tree_revalidation_failures=['x']),lambda x:x.update(unscanned_final_identities='bad'),lambda x:x.update(complete_mount_proofs=False),lambda x:x.update(tree_observation_transients='bad')):
   with self.subTest(m=m),tempfile.TemporaryDirectory() as t:
    roots=self.trees(t);r=self.release(roots)
    with self.assertRaises(M.RetirementError):self.execute(roots,r,self.observer(r,m))
    self.assertTrue((Path(t)/'.q0').exists());self.assertIn('terminal-failure',(Path(t)/'journal').read_text())
 def test_each_container_config_mutation_and_unrelated(self):
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);unrelated=dict(Id='e'*64,Mounts=[dict(Source='/tmp/unrelated',Destination='/x')],Config=dict())
   self.assertEqual(self.execute(roots,r,census=self.census(r,[self.terminal(r),unrelated]))['status'],'PASS')
  for k,v in (('Id','d'*64),('State',dict(Status='running')),('Config',dict(Image='other'))):
   with self.subTest(k=k),tempfile.TemporaryDirectory() as t:
    roots=self.trees(t);r=self.release(roots);mounts=[dict(Source=str(Path(t)/'.q0'),Destination='/x')];r['docker']['terminal']['exact_config']['Mounts']=mounts;row=self.terminal(r,mounts);row[k]=v
    with self.assertRaises(M.RetirementError):self.execute(roots,r,census=self.census(r,[row]))
 def test_terminal_mount_order_is_canonical_but_mount_field_mutation_fails(self):
  mounts=[dict(Source='/srv/retirement-a',Destination='/mnt/a',Mode='ro',RW=False,Type='bind'),dict(Source='/srv/retirement-b',Destination='/mnt/b',Mode='rw',RW=True,Type='bind')]
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);r['docker']['terminal']['exact_config']['Mounts']=mounts
   self.assertEqual(self.execute(roots,r,census=self.census(r,[self.terminal(r,list(reversed(mounts)))]))['status'],'PASS')
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);r['docker']['terminal']['exact_config']['Mounts']=mounts
   mutated=[dict(mounts[1]),dict(mounts[0])];mutated[0]['Mode']='ro,delegated'
   with self.assertRaises(M.RetirementError):self.execute(roots,r,census=self.census(r,[self.terminal(r,mutated)]))
  with self.assertRaisesRegex(M.RetirementError,'not an object'):M.canonical_mounts([1])
 def test_short_zero_and_collision_writes_and_boundary_failure_survivor_record(self):
  with tempfile.TemporaryDirectory() as t:
   fd=os.open(str(Path(t)/'x'),os.O_CREAT|os.O_WRONLY,0o600)
   try:
    for w in (lambda fd,b:0,lambda fd,b:len(b)+1):
     with self.assertRaises(M.RetirementError):M.full_write(fd,b'abc',w)
   finally:os.close(fd)
   p=Path(t)/'claim';M.full_write_json(p,dict(x=1))
   with self.assertRaises(FileExistsError):M.full_write_json(p,dict(x=2))
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);old=M.rename_noreplace;M.rename_noreplace=lambda *x:(_ for _ in ()).throw(OSError('injected'))
   try:
    with self.assertRaises(OSError):self.execute(roots,r)
   finally:M.rename_noreplace=old
   self.assertTrue(roots[0].exists());self.assertIn('terminal-failure',(Path(t)/'journal').read_text())
 def test_unlink_and_rmdir_destructive_boundary_failures_keep_journal(self):
  for name in ('unlink','rmdir'):
   with self.subTest(name=name),tempfile.TemporaryDirectory() as t:
    roots=self.trees(t);r=self.release(roots);old=getattr(M.os,name)
    def boom(*args,**kwargs): raise OSError('injected '+name)
    setattr(M.os,name,boom)
    try:
     with self.assertRaises(OSError):self.execute(roots,r)
    finally:setattr(M.os,name,old)
    journal=(Path(t)/'journal').read_text();self.assertIn('terminal-failure',journal);self.assertTrue((Path(t)/'.q0').exists())
 def test_descriptor_closure_does_not_accumulate(self):
  if not Path('/proc/self/fd').is_dir():self.skipTest('no fd inventory')
  with tempfile.TemporaryDirectory() as t:
   before=len(list(Path('/proc/self/fd').iterdir()));roots=self.trees(t);r=self.release(roots);self.execute(roots,r);after=len(list(Path('/proc/self/fd').iterdir()))
   self.assertLessEqual(after,before+1)
 def test_arbitrary_hashes_empty_census_original_running_and_nested_roots_reject(self):
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);r['sealed']['capsule_sha256']='0'*64
   with self.assertRaises(M.RetirementError):self.execute(roots,r)
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);unknown=dict(Id='f'*64,Mounts=[dict(Source=str(roots[0]),Destination='/candidate')])
   with self.assertRaises(M.RetirementError):self.execute(roots,r,census=self.census(r,[self.terminal(r),unknown]))
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots)
   with self.assertRaises(M.RetirementError):self.execute([roots[0],roots[0]/'d'],r)
 def test_missing_terminal_stale_and_root_substitution_reject(self):
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots)
   with self.assertRaises(M.RetirementError):self.execute(roots,r,census=self.census(r,[]))
  for mutator in (lambda x:x.update(started_at_utc='2000-01-01T00:00:00Z'),lambda x:x['roots'][0].update(inode=x['roots'][0]['inode']+1)):
   with self.subTest(mutator=mutator),tempfile.TemporaryDirectory() as t:
    roots=self.trees(t);r=self.release(roots)
    with self.assertRaises(M.RetirementError):self.execute(roots,r,self.observer(r,mutator))
 def test_partial_capsule_and_path_replacement_cannot_change_verified_bytes(self):
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);cap=Path(r['sealed']['capsule_path']);cap.write_bytes(cap.read_bytes()[:128]);bad=M.digest_bytes(cap.read_bytes())
   for key in ('capsule_sha256','capsule_pushed_sha256','capsule_fetched_sha256'):r['sealed'][key]=bad
   with self.assertRaises(M.RetirementError):self.execute(roots,r)
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);cap=Path(r['sealed']['capsule_path']);old=M.verify_archive_bytes;seen=[]
   def swap(data,manifest):
    cap.write_bytes(b'not the accepted capsule');seen.append(data);return old(data,manifest)
   M.verify_archive_bytes=swap
   try:self.assertEqual(self.execute(roots,r)['status'],'PASS')
   finally:M.verify_archive_bytes=old
   self.assertTrue(seen)
 def test_replacement_after_delete_before_journal_is_revalidated(self):
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);old=M.Journal.write;replaced=[]
   def race(journal,phase,**kw):
    old(journal,phase,**kw)
    if phase=='delete-entry-before' and not replaced and kw.get('operation')=='unlink':
     target=Path(t)/'.q0'/kw['path'];target.unlink();target.write_text('replacement');replaced.append(target)
   M.Journal.write=race
   try:
    with self.assertRaises(M.RetirementError):self.execute(roots,r)
   finally:M.Journal.write=old
   self.assertTrue(replaced);self.assertIn('terminal-failure',(Path(t)/'journal').read_text())
 def test_quarantine_ownership_transition_is_explicit_and_revalidated(self):
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);self.assertEqual(self.execute(roots,r)['status'],'PASS')
   self.assertEqual(os.getuid(),r['roots'][0]['quarantine_uid']);self.assertEqual(os.getgid(),r['roots'][0]['quarantine_gid'])
   rows=[json.loads(line) for line in (Path(t)/'journal').read_text().splitlines()]
   before=[row for row in rows if row['phase']=='quarantine-before'][0];after=[row for row in rows if row['phase']=='quarantine-after'][0]
   target=dict(r['roots'][0]['root'],uid=r['roots'][0]['quarantine_uid'],gid=r['roots'][0]['quarantine_gid'],mode=0o700)
   self.assertEqual(before['released_root'],r['roots'][0]['root']);self.assertEqual(before['ownership_transition_target'],target)
   self.assertEqual(after['released_root'],r['roots'][0]['root']);self.assertEqual(after['ownership_transition_target'],target);self.assertEqual(after['observed_quarantine_root'],target)
 def test_transition_failure_or_changed_identity_records_no_after_and_cannot_retry(self):
  for name in ('fchown','fchmod'):
   with self.subTest(name=name),tempfile.TemporaryDirectory() as t:
    roots=self.trees(t);r=self.release(roots);old=getattr(M.os,name)
    if name=='fchown':M.os.fchown=lambda *a: (_ for _ in ()).throw(OSError('injected fchown'))
    else:M.os.fchmod=lambda fd,mode: old(fd,0o711)
    try:
     with self.assertRaises((OSError,M.RetirementError)):self.execute(roots,r)
    finally:setattr(M.os,name,old)
    rows=[json.loads(line) for line in (Path(t)/'journal').read_text().splitlines()]
    self.assertEqual(len([row for row in rows if row['phase']=='quarantine-before']),1);self.assertFalse([row for row in rows if row['phase']=='quarantine-after'])
    self.assertIn('terminal-failure',[row['phase'] for row in rows]);self.assertTrue((Path(t)/'.q0').exists())
    with self.assertRaises(Exception):self.execute(roots,r)
 def test_missing_or_changed_quarantine_owner_binding_rejects(self):
  for change in (lambda row: row.pop('quarantine_uid'),lambda row: row.update(quarantine_gid=-1)):
   with self.subTest(change=change),tempfile.TemporaryDirectory() as t:
    roots=self.trees(t);r=self.release(roots);change(r['roots'][0])
    with self.assertRaises(M.RetirementError):self.execute(roots,r)
 def test_post_transition_owner_change_and_observer_owner_mismatch_reject(self):
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots)
   def mutate(v):
    v['roots'][0]['uid'] += 1
   with self.assertRaises(M.RetirementError):self.execute(roots,r,self.observer(r,mutate))
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots)
   def mutate(v): v['roots'][0].pop('uid')
   with self.assertRaises(M.RetirementError):self.execute(roots,r,self.observer(r,mutate))
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots)
   def mutate(v):
    root=v['roots'][0];member=next(x for x in root['tree_member_identities'] if x[:2]==[root['device_number'],root['inode']]);member[2]+=1
   with self.assertRaises(M.RetirementError):self.execute(roots,r,self.observer(r,mutate))
 def test_bounded_artifact_and_streaming_candidate_reads_reject_oversize_short_and_growth(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'artifact';p.write_bytes(b'abcd')
   with self.assertRaisesRegex(M.RetirementError,'exceeds cap'):M.stable_read(p,3)
   fd=os.open(str(p),os.O_RDONLY)
   try:
    with self.assertRaisesRegex(M.RetirementError,'short read'):M.readfd(fd,8,5)
   finally:os.close(fd)
   fd=os.open(str(p),os.O_RDONLY)
   try:self.assertEqual(M.digest_fd(fd,4),M.digest_bytes(b'abcd'))
   finally:os.close(fd)
   fd=os.open(str(p),os.O_RDONLY)
   try:
    original=M.os.read;calls=[]
    def growing(which,count):
     b=original(which,count);calls.append(b)
     if len(calls)==1:p.write_bytes(b'abcdef')
     return b
    M.os.read=growing
    with self.assertRaisesRegex(M.RetirementError,'grew'):M.digest_fd(fd,4)
   finally:
    M.os.read=original;os.close(fd)
 def test_dirfd_output_api_never_uses_output_paths_and_rejects_bad_names(self):
  with tempfile.TemporaryDirectory() as t:
   roots=self.trees(t);r=self.release(roots);out=Path(t)/'out';out.mkdir();fd=os.open(str(out),os.O_RDONLY|os.O_DIRECTORY)
   try:
    result=M.retire(roots,r,'claim','journal','evidence',self.observer(r),self.census(r),output_dir_fd=fd)
    self.assertEqual(result['status'],'PASS')
    for n in ('claim','journal','evidence'):
     row=os.stat(n,dir_fd=fd,follow_symlinks=False);self.assertTrue(stat.S_ISREG(row.st_mode));self.assertGreater(row.st_size,0)
    with self.assertRaises(M.RetirementError):M.exclusive_fd_at(fd,'bad/name')
   finally:os.close(fd)
if __name__=='__main__':unittest.main()
