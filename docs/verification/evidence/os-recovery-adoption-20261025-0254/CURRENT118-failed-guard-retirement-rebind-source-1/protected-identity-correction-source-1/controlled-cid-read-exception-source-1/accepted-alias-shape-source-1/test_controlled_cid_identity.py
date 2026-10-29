"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Original identity algorithm, exact CID-only read flag; substituted file effects.
"""
from pathlib import Path
import ast,copy,importlib.util,os,stat,types,unittest
from unittest.mock import patch
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('exact_cid_identity_candidate',D/'retire_exact_failed_guard.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
CID=Path(m.B['controlled_cid_subject']['path'])
class ControlledIdentity(unittest.TestCase):
 def effects(self,change=None,shape=None):
  data=m.TB['cid'].encode();before=dict(st_dev=66306,st_ino=42,st_mode=stat.S_IFREG|0o644,st_uid=0,st_gid=0,st_nlink=1,st_size=len(data),st_mtime_ns=100,st_ctime_ns=101)
  if shape:before.update(shape)
  after=dict(before)
  if change:after[change]+=1
  calls=[];reads=[data,b''];stats=[types.SimpleNamespace(**before),types.SimpleNamespace(**after)]
  def opened(path,flags,dir_fd):
   calls.append(('open',path,flags,dir_fd))
   if flags&os.O_NOATIME:raise PermissionError(1,'TEST_ONLY original root-owned O_NOATIME EPERM',str(path))
   return 99
  fake=types.SimpleNamespace(**{k:getattr(os,k) for k in ['O_RDONLY','O_NOFOLLOW','O_NOATIME','O_CLOEXEC','O_NONBLOCK']},open=opened,fstat=lambda fd:stats.pop(0),read=lambda fd,count:reads.pop(0),stat=lambda *a,**kw:types.SimpleNamespace(**after),close=lambda fd:calls.append(('close',fd)))
  return fake,calls
 def test_original_root_owned_flag_failure_and_exact_corrected_read(self):
  fake,calls=self.effects()
  with patch.object(m.M,'os',fake),patch.object(m.M,'directory',return_value=55),self.assertRaises(PermissionError):m.M.file_identity(CID)
  fake,calls=self.effects()
  with patch.object(m.M,'os',fake),patch.object(m.M,'directory',return_value=55):row,raw=m.controlled_cid_identity(CID)
  self.assertIsNone(raw);self.assertEqual(row['sha256'],m.B['controlled_cid_subject']['sha256']);self.assertEqual(row['uid'],0)
  flags=calls[0][2];self.assertFalse(flags&os.O_NOATIME);self.assertTrue(flags&os.O_NOFOLLOW);self.assertTrue(flags&os.O_CLOEXEC);self.assertTrue(flags&os.O_NONBLOCK)
  self.assertEqual(calls[-2:],[('close',99),('close',55)])
 def test_every_original_stable_identity_time_field_still_refuses_drift(self):
  for field in ['st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns']:
   fake,calls=self.effects(change=field)
   with self.subTest(field=field),patch.object(m.M,'os',fake),patch.object(m.M,'directory',return_value=55),self.assertRaises(m.M.Refusal):m.controlled_cid_identity(CID)
   self.assertEqual(calls[-2:],[('close',99),('close',55)])
 def test_original_bounded_regular_single_link_shape_remains_required(self):
  for shape in [dict(st_mode=stat.S_IFDIR|0o755),dict(st_nlink=2),dict(st_size=m.M.FILE_LIMIT+1)]:
   fake,calls=self.effects(shape=shape)
   with patch.object(m.M,'os',fake),patch.object(m.M,'directory',return_value=55),self.assertRaises(m.M.Refusal):m.controlled_cid_identity(CID)
 def test_no_other_subject_or_shared_global_flag_exception(self):
  original=m.M.file_identity;flag=os.O_NOATIME
  for path in [CID.with_name('other.cid'),Path('/usr/bin/python3.8')]:
   with self.subTest(path=str(path)),self.assertRaises(RuntimeError):m.controlled_cid_identity(path)
  self.assertIs(m.M.file_identity,original);self.assertEqual(os.O_NOATIME,flag)
 def test_pidfd_lock_guard_transaction_units_unchanged_from_reviewed_rebind(self):
  before=ast.parse(m.T.authenticated(m.B['pre_alias_correction_executor']));after=ast.parse(Path(m.SELF).read_bytes())
  for name in ['guard_identity','safe','final_before_signal','process_code','validate_process_report','readonly','snapshot','bind_release','rebound_protocol','configure','validate_parent_join']:
   def unit(tree):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
   self.assertEqual(ast.dump(unit(before)),ast.dump(unit(after)),name)
 def test_original_failed_release_join_and_unknown_status_preserved(self):
  failed=m.T.authenticated(m.B['failed_rebind_attempt'],True);joined=m.T.authenticated(failed['parent_join'],True)
  self.assertEqual(joined['pid'],2247306);self.assertEqual(joined['returncode'],1);self.assertTrue(joined['positive_wait4_join'])
  self.assertEqual(m.PROFILE['first_readonly_client']['status'],'UNKNOWN');self.assertEqual(len(m.B['protected']),62)
if __name__=='__main__':unittest.main(verbosity=2)
