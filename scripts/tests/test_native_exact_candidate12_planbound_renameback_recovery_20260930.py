"""Disposable adversarial tests for the source-only candidate12 recovery."""
import hashlib, importlib.util, json, os, signal, tempfile, unittest
from pathlib import Path
from unittest import mock

PATH=Path(__file__).resolve().parents[2]/'docs/verification/evidence/native-exact-candidate12-planbound-renameback-recovery-20260930.py'
S=importlib.util.spec_from_file_location('r12',PATH); m=importlib.util.module_from_spec(S); S.loader.exec_module(m)

class Recovery(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.addCleanup(self.t.cleanup); b=Path(self.t.name); self.root=b/'candidate'; self.q=self.root/'.q'; self.e=self.root/'docs/verification/evidence'; self.e.mkdir(parents=True); self.q.mkdir(); self.rows=[]
  for i in range(3):
   data=('data%d'%i).encode(); x=self.q/str(i); x.write_bytes(data); x.chmod(0o644); s=x.stat(); self.rows.append(dict(path=str(self.e/('x%d'%i)),sha256=hashlib.sha256(data).hexdigest(),dev=s.st_dev,ino=s.st_ino,mode=0o644,nlink=1,size=len(data),mtime_ns=s.st_mtime_ns,allocated_bytes=s.st_blocks*512))
  qfd=m.dirfd(self.q); self.qns=m.scan(qfd); os.close(qfd)
  for i,row in enumerate(self.rows): os.rename(self.q/str(i),row['path'])
  rfd=m.dirfd(self.root); self.rns=m.scan(rfd); os.close(rfd)
  for i,row in enumerate(self.rows): os.rename(row['path'],self.q/str(i))
  self.old={x:getattr(m,x) for x in ('QROOT','DEFAULT_Q','DEFAULT_RECEIPT','EXPECTED_COUNT','RECEIPT_SIZE','RECEIPT_SHA256','SCRATCH')}; m.QROOT=str(self.root);m.DEFAULT_Q=str(self.q);m.DEFAULT_RECEIPT=str(b/'in.json');m.EXPECTED_COUNT=3;m.SCRATCH=str(b)
  self.receipt=Path(m.DEFAULT_RECEIPT); value=dict(status='FAIL',phase='staged-admission',interrupted=False,quarantine=str(self.q),states=['staged']*3,restoration=self.rows,quarantine_namespace=self.qns,restored_namespace=self.rns); raw=json.dumps(value,separators=(',',':')).encode();self.receipt.write_bytes(raw);m.RECEIPT_SIZE=len(raw);m.RECEIPT_SHA256=hashlib.sha256(raw).hexdigest()
  self.out={k:str(b/(k+'.json')) for k in ('journal','receipt','status','lock')};self.out['quarantine']=str(self.q)
 def tearDown(self):
  for k,v in self.old.items():setattr(m,k,v)
 def recover_fixture(self,**kw):
  out=dict(self.out);out.update(kw)
  with mock.patch.object(m,'validate_attempt_journal'),mock.patch.object(m,'validate_release'):return m.recover(str(self.receipt),out,str(Path(self.t.name)/'release.json'))
 def test_success_is_exact_namespace_transaction(self):
  r=self.recover_fixture();self.assertEqual(r['status'],'PASS');self.assertEqual(list(self.q.iterdir()),[]);self.assertTrue(all(Path(x['path']).is_file() for x in self.rows));self.assertEqual(len([x for x in Path(self.out['journal']).read_text().splitlines() if 'rename-intent' in x]),3)
 def test_all_outputs_precreated_before_mutation(self):
  Path(self.out['status']).write_text('collision')
  with self.assertRaises(m.Refusal):self.recover_fixture()
  self.assertEqual(len(list(self.q.iterdir())),3)
 def test_short_write_never_false_passes(self):
  with mock.patch.object(m.os,'write',side_effect=lambda fd,b: 0):
   with self.assertRaises(m.Refusal):m.write_all(7,b'bytes')
 def test_partial_interrupt_reconciles_every_row(self):
  real=m.rename_noreplace
  def hit(a,b,c,d):
   if b=='1':os.kill(os.getpid(),signal.SIGTERM)
   return real(a,b,c,d)
  with mock.patch.object(m,'rename_noreplace',side_effect=hit):r=self.recover_fixture()
  self.assertEqual(r['status'],'FAIL');self.assertEqual(len([x for x in Path(self.out['journal']).read_text().splitlines() if 'reconciled' in x]),3);self.assertTrue(Path(self.rows[0]['path']).exists())
 def test_parent_swap_before_rename_is_refused(self):
  real=m.check_at; calls=[]
  def race(fd,name,row):
   if name=='0' and not calls:
    calls.append(1); saved=self.e.with_name('e.saved');self.e.rename(saved);self.e.symlink_to(saved,target_is_directory=True)
   return real(fd,name,row)
  with mock.patch.object(m,'check_at',side_effect=race):r=self.recover_fixture()
  self.assertEqual(r['status'],'FAIL');self.assertTrue(r['uncertain'])
 def test_namespace_rejects_fifo_symlink_and_empty_dir(self):
  for kind in ('fifo','symlink','directory'):
   with self.subTest(kind=kind):
    p=self.q/'evil'
    if kind=='fifo':os.mkfifo(p)
    elif kind=='symlink':p.symlink_to('/tmp')
    else:p.mkdir()
    with self.assertRaises(m.Refusal):m.namespace(m.dirfd(self.q),self.qns)
    if kind=='directory':p.rmdir()
    else:p.unlink()
 def test_metadata_and_content_drift_rejected(self):
  (self.q/'0').write_bytes(b'changed')
  with self.assertRaises(m.Refusal):m.check_at(m.dirfd(self.q),'0',self.rows[0])
 def test_duplicate_and_nested_outputs_refused(self):
  with self.assertRaises(m.Refusal):self.recover_fixture(status=self.out['journal'])
  self.out['status']=str(Path(self.out['journal'])/'nested')
  with self.assertRaises(m.Refusal):self.recover_fixture()
 def test_reconcile_never_guesses_mixed_state(self):
  Path(self.rows[0]['path']).write_bytes(b'other')
  q=m.dirfd(self.q)
  try:self.assertEqual(m.reconcile(self.rows[0],q,0),'uncertain')
  finally:os.close(q)
 def test_release_requires_distinct_source_and_fetched_commit(self):
  # A self-supplied release has no separate source/release commits and cannot pass.
  p=Path(self.t.name)/'r.json';p.write_text(json.dumps({'schema':'mckernel.candidate12.renameback.recovery.v2','status':'PASS','source_commit':'a'*40,'release_commit':'a'*40,'upstream_commit':'a'*40,'fetched_commit':'a'*40}))
  with self.assertRaises(m.Refusal):m.validate_release(str(p))
 def test_journal_requires_final_failure_and_no_deletion(self):
  old=(m.JOURNAL_SIZE,m.JOURNAL_SHA256,m.EXPECTED_COUNT);p=Path(self.t.name)/'old';p.write_text('{"event":"deleted"}\n');m.JOURNAL_SIZE=p.stat().st_size;m.JOURNAL_SHA256=hashlib.sha256(p.read_bytes()).hexdigest();m.EXPECTED_COUNT=0
  try:
   with self.assertRaises(m.Refusal):m.validate_attempt_journal(str(p))
  finally:m.JOURNAL_SIZE,m.JOURNAL_SHA256,m.EXPECTED_COUNT=old
if __name__=='__main__':unittest.main()
