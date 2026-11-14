"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Production helper module on disposable ordinary files only. No actual shared file,
root query, flock, signal or archive/unlink_one call. Actual shared_phase(True)
AST extracted to exercise its real helper join using disposable data.
"""
from pathlib import Path
import ast,copy,hashlib,json,os,stat,tempfile,types,unittest
C=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt2-coherent-entry-preparation-source-1/genuine-postshared-binding-successor-source-1/owner904301-parent903729-recovery-source-1/new-be87-shared-archival-preparation-source-1/actual1937-process-bound-shared-source-1/transitive-record-owner-correction1-source-1');READY=json.loads((C/'READY-NEWBE87-TRANSITIVE-RECORD-OWNER-CORRECTION1.SOURCE-ONLY.json').read_bytes())
def auth(row):
 raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes'];return raw
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.mod=types.ModuleType('production_real_record_helper');exec(compile(auth(READY['archive_primitives']),READY['archive_primitives']['path'],'exec'),cls.mod.__dict__)
  cls.profile=json.loads(auth(READY['profile']));cls.tree=ast.parse(auth(READY['source']))
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='disposable-be87-bind-node-',dir=str(C));self.path=Path(self.temp.name)/'owned.json';self.record=copy.deepcopy(self.profile['shared_value'])
 def tearDown(self):self.temp.cleanup()
 def create(self,change_record=None):
  if change_record:change_record(self.record)
  # Disposable inode/device stand in for the real node while all ownership,
  # request/schema values are exact. No actual shared record is opened.
  with self.path.open('xb') as f:f.write(b'{}')
  self.path.chmod(0o600);st=self.path.stat();self.record['inode']=st.st_ino;self.record['device']=st.st_dev;raw=(json.dumps(self.record,sort_keys=True,separators=(',',':'))+'\n').encode();self.path.write_bytes(raw);st=self.path.stat();self.identity=dict(path=str(self.path),device=st.st_dev,inode=st.st_ino,size=len(raw),mode=0o600,uid=st.st_uid,gid=st.st_gid,nlink=1,sha256=hashlib.sha256(raw).hexdigest());return raw
 def reject_record(self,key,value):
  self.create(lambda r:r.update({key:value}))
  with self.assertRaises(self.mod.Refusal):self.mod.bind_node(self.path,self.record,self.identity)
 def test_01_real_bind_node_new_owner(self):
  raw=self.create();row,read,meta,snapshot=self.mod.bind_node(self.path,self.record,self.identity);self.assertEqual(row,self.identity);self.assertEqual(read,raw);self.assertEqual(snapshot['record'],self.record)
 def test_02_real_shared_phase_to_bind_node_join(self):
  raw=self.create();node=next(n for n in self.tree.body if isinstance(n,ast.FunctionDef) and n.name=='shared_phase');ns=dict(archive_ops=self.mod,SHARED=self.path,r=dict(shared_value=self.record,shared_identity=self.identity),OUT=Path(self.temp.name),m=types.SimpleNamespace(Refusal=self.mod.Refusal),os=os);exec(compile(ast.Module(body=[node],type_ignores=[]),'production_shared_phase','exec'),ns);result=ns['shared_phase'](True);self.assertEqual(result['raw_hex'],raw.hex());self.assertEqual(result['original_identity'],self.identity)
 def test_03_old_owner_rejected(self):self.reject_record('pid',867329)
 def test_04_wrong_birth_rejected(self):self.reject_record('starttime','76715862')
 def test_05_wrong_request_rejected(self):self.reject_record('request_sha256','c05b1ad24ece9fa4dec6107394fa8f42437deaacf42f3b209fc8d8087e170e1f')
 def test_06_wrong_inode_rejected(self):
  self.create();self.identity['inode']+=1
  with self.assertRaises(self.mod.Refusal):self.mod.bind_node(self.path,self.record,self.identity)
 def test_07_wrong_hash_rejected(self):
  self.create();self.identity['sha256']='0'*64
  with self.assertRaises(self.mod.Refusal):self.mod.bind_node(self.path,self.record,self.identity)
 def test_08_wrong_device_rejected(self):
  self.create();self.identity['device']+=1
  with self.assertRaises(self.mod.Refusal):self.mod.bind_node(self.path,self.record,self.identity)
 def test_09_wrong_schema_rejected(self):self.reject_record('schema','old.schema')
 def test_10_durability_and_engine_AST_unchanged(self):
  a={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(auth(READY['archive_primitives'])).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};b={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(auth(READY['original_archive_primitives'])).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};self.assertEqual([k for k in a if a[k]!=b[k]],['record_snapshot'])
  a={n.name:ast.dump(n,include_attributes=False) for n in self.tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};b={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(auth(READY['predecessor_source'])).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};self.assertEqual(a,b)
if __name__=='__main__':unittest.main(verbosity=2)
