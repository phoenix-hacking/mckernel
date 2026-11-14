"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,copy,hashlib,json,os,re,stat,unittest
N=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/image-receipt-identity-successor-source-1')
READY=json.loads((N/'READY-IMAGE-RECEIPT-IDENTITY-SUCCESSOR.SOURCE-ONLY.json').read_bytes())
def auth(row):
 p=Path(row['path']);b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==row['sha256'] and len(b)==row['bytes'];return p
def extract(row):
 p=auth(row);tree=ast.parse(p.read_bytes(),str(p));functions={x.name:x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))};selected=set();pending=['_validate_v2_image_tools']
 while pending:
  name=pending.pop()
  if name in selected:continue
  selected.add(name)
  for x in ast.walk(functions[name]):
   if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id in functions:pending.append(x.func.id)
 allowed={'OwnerError','_canonical','_fail','_load_json','_no_symlink_parents','_regular','_safe_regular','_sha256','_validate_library_closure','_validate_v2_image_tools'}
 assert selected==allowed
 constants={'REQUIRED_TOOLS','REQUIRED_LIBRARIES','LIBRARY_SPECS','PREPARER_BASE_IMAGE','PINNED_CMAKE_RPM','PINNED_RUST_RPM','_PREPARATION_EVIDENCE'}
 nodes=[x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.ClassDef)) and x.name in selected or isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in x.targets)]
 ns=dict(Path=Path,json=json,hashlib=hashlib,os=os,re=re,stat=stat);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),ns);return ns
class ActualProductionReceipt(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.old=extract(READY['original_owner']);cls.new=extract(READY['successor_owner']);cls.request=json.loads(auth(READY['successor_request']).read_bytes());cls.original=json.loads(auth(READY['original_request']).read_bytes());cls.tc=json.loads(auth(READY['toolchain']).read_bytes());auth(READY['receipt'])
 def call(self,r=None,t=None):return self.new['_validate_v2_image_tools'](copy.deepcopy(r if r is not None else self.request),copy.deepcopy(t if t is not None else self.tc))
 def reject(self,r=None,t=None):
  with self.assertRaises(self.new['OwnerError']):self.call(r,t)
 def test_01_actual_original_failure_retained(self):
  with self.assertRaisesRegex(self.old['OwnerError'],'image receipt identity differs'):self.old['_validate_v2_image_tools'](self.original,self.tc)
 def test_02_actual_full_production_function_passes(self):
  image,mounted=self.call();self.assertEqual(image,self.tc['image_tools']);self.assertEqual(mounted,self.tc['mounted_tools']);self.assertNotEqual(self.request['candidate_sha'],self.request['image_receipt_candidate_sha'])
 def test_03_missing_image_candidate_rejected(self):
  r=copy.deepcopy(self.request);r.pop('image_receipt_candidate_sha');self.reject(r)
 def test_04_source_candidate_substitution_rejected(self):
  r=copy.deepcopy(self.request);r['image_receipt_candidate_sha']=r['candidate_sha'];self.reject(r)
 def test_05_malformed_candidate_rejected(self):
  r=copy.deepcopy(self.request);r['image_receipt_candidate_sha']='x'*40;self.reject(r)
 def test_06_receipt_hash_rejected(self):
  r=copy.deepcopy(self.request);r['image_receipt_sha256']='0'*64;self.reject(r)
 def test_07_image_id_rejected(self):
  r=copy.deepcopy(self.request);r['image_id']='sha256:'+'0'*64;self.reject(r)
 def test_08_lock_rejected(self):
  r=copy.deepcopy(self.request);r['toolchain_lock_sha256']='0'*64;self.reject(r)
 def test_09_tool_partition_rejected(self):
  t=copy.deepcopy(self.tc);t['image_tools']['rustc']=t['mounted_tools']['rustc'];self.reject(t=t)
 def test_10_image_tool_hash_rejected(self):
  t=copy.deepcopy(self.tc);key=next(iter(t['image_tools']));t['image_tools'][key]['sha256']='0'*64;self.reject(t=t)
 def test_11_library_closure_rejected(self):
  t=copy.deepcopy(self.tc);t['libraries']['libnuma']['linker']['sha256']='0'*64;self.reject(t=t)
if __name__=='__main__':unittest.main(verbosity=2)
