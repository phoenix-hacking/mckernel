"""Functional OS only; no security testing. Actual helper/protocol regression; retainedquery bytes only."""
import copy,hashlib,importlib.util,json,sys,unittest
from pathlib import Path
S=Path(__file__).parent/'produce_actual_owner935300_cleanup_observation.READONLY.SELECTED-CLOSURE-CORRECTION1.NOT_RELEASED.py'
spec=importlib.util.spec_from_file_location('real_corrected_producer',S);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
MANIFEST=Path(sys.argv.pop(1))
class ActualProtocol(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p,cls.e=a.bootstrap();fixtures=json.loads(MANIFEST.read_bytes());cls.raw={}
  for key in ('inspect','findmnt'):
   row=fixtures[key];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes'];cls.raw[key]=raw
  # ACTUAL production branch; only queryfn is replaced by exact retained raw bytes.
  cls.obs=a.produce(cls.p,cls.e,lambda label:cls.raw[label]);cls.selected={r['path']:r for r in cls.obs['selected_files']};cls.protocol=cls.e.current230_contract();cls.receipt=cls.e.parse(a.pinned(cls.p['owner_receipt']));cls.join=cls.e.parse(a.pinned(cls.p['join']));cls.request=cls.e.parse(cls.e.read_bounded(cls.e.REQUEST))
 def normal(self,selected):return self.protocol.normal_owner_join_binding(self.receipt,self.join,self.obs['target'],self.obs['container_inspect'],self.p['owner_receipt']['sha256'],self.request,self.obs,selected)
 def test_actual_production_fullpath(self):
  self.assertEqual(set(self.obs),a.REQUIRED);self.assertEqual(len(self.obs['client_ledger']),7);self.assertTrue(self.normal(self.selected));self.assertTrue(self.protocol.typed_source_binding(self.request,self.obs,self.selected));self.assertEqual(self.obs['ownership_case'],'FAIL_COMMON_AND_SHARED')
 def test_remove_grant_payload_or_origin_refused(self):
  contract=self.e.parse(a.pinned(self.p['contract']));paths=[r['path'] for r in self.p['dynamic_selected_proof_refs']]+[contract['fetched_origin_proof']['path']]
  for path in paths:
   selected=copy.deepcopy(self.selected);selected.pop(path)
   with self.subTest(path=path),self.assertRaises(ValueError):self.normal(selected)
 def test_tamper_grant_payload_or_origin_identity_refused(self):
  contract=self.e.parse(a.pinned(self.p['contract']));paths=[r['path'] for r in self.p['dynamic_selected_proof_refs']]+[contract['fetched_origin_proof']['path']]
  for path in paths:
   selected=copy.deepcopy(self.selected);selected[path]['sha256']='0'*64
   with self.subTest(path=path),self.assertRaises(ValueError):self.normal(selected)
if __name__=='__main__':unittest.main(verbosity=2)
