#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Temporary synthetic role receipts prove parser semantics, never actual initialization.
No owner/initializer import, namespace mutation, subprocess or current proof creation.
"""
import ast,copy,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest import mock
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('attempt5_role',D/'attempt5_exact_source_origin_binding.SOURCE-ONLY.NOT-RELEASED.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
class Roles(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.b=helper.data()
  def put(name,value):
   p=self.root/name;p.write_text(json.dumps(value));return helper.ref(p)
  self.put=put
  self.b['namespace_initializer_source']=put('synthetic-initializer-source.json',{'synthetic_fixture_only':True})
  self.b['namespace_initializer_inputs']=put('synthetic-inputs.json',{'synthetic_fixture_only':True})
  self.grant=dict(author='/root',decision='GRANT_ONE_ORDINARY_ATTEMPT5_THREE_NAMESPACE_INITIALIZATION',maximum_invocations=1,source=self.b['namespace_initializer_source'],inputs=self.b['namespace_initializer_inputs'],request=self.b['current_request'],image_entry_owner=self.b['image_entry_owner'],host_control_owner=self.b['host_control_owner'],synthetic_fixture_only=True)
  self.b['ordinary_namespace_grant']=put('synthetic-grant.json',self.grant)
  ns=Path(self.b['planned_namespace']);rows=[dict(path=str(path),device=1,inode=i+1,uid=1000,gid=1000,mode=0o700,entries=['owner-evidence','owner-work'] if i==0 else []) for i,path in enumerate([ns,ns/'owner-work',ns/'owner-evidence'])]
  self.receipt=dict(status='PASS_ACTUAL_ORDINARY_SOURCE_PREPARATION_NAMESPACE_INITIALIZATION_ONLY',request=self.b['current_request'],owner=self.b['image_entry_owner'],host_control_owner=self.b['host_control_owner'],source=self.b['namespace_initializer_source'],grant=self.b['ordinary_namespace_grant'],identities=rows,synthetic_fixture_only=True)
  self.b['actual_namespace_identities']=rows;self.save()
 def save(self):self.b['actual_namespace_initialization']=self.put('synthetic-receipt.json',self.receipt)
 def test_positive_real_helper_accepts_same_owner735_roles(self):
  self.assertTrue(helper.require_initializer_runtime_owner_roles(self.receipt,self.b))
 def test_negative_historical_attempt4_actual_receipt(self):
  predecessor=json.loads((D/'SOURCE-SUCCESSOR-ROLE-BINDING.NOT-RELEASED.json').read_bytes())
  old=json.loads(Path(predecessor['predecessor_data']['path']).read_bytes());self.b['actual_namespace_initialization']=old['actual_namespace_initialization'];receipt=json.loads(helper.auth(old['actual_namespace_initialization']).read_bytes())
  with self.assertRaisesRegex(RuntimeError,'attempt5 request'):helper.require_initializer_runtime_owner_roles(receipt,self.b)
 def test_negative_stale_owner213_in_fresh_shape(self):
  predecessor=json.loads((D/'SOURCE-SUCCESSOR-ROLE-BINDING.NOT-RELEASED.json').read_bytes());old=json.loads(Path(predecessor['predecessor_data']['path']).read_bytes());self.receipt['owner']=old['image_entry_owner'];self.save()
  with self.assertRaisesRegex(RuntimeError,'initializer/runtime owner'):helper.require_initializer_runtime_owner_roles(self.receipt,self.b)
 def test_negative_changed_namespace_path(self):
  self.receipt['identities'][1]['path']='/synthetic-wrong-attempt/owner-work';self.save()
  with self.assertRaisesRegex(RuntimeError,'attempt5 paths'):helper.require_initializer_runtime_owner_roles(self.receipt,self.b)
 def test_pending_production_data_cannot_accept_fixture(self):
  with self.assertRaisesRegex(RuntimeError,'receipt pending'):helper.require_initializer_runtime_owner_roles(self.receipt,helper.data())
 def test_preserved_source_materialization_semantics_with_real_inputs(self):
  spec=importlib.util.spec_from_file_location('metadata_only',D.parent/'materialize_successor_request.SOURCE-ONLY.NOT-RELEASED.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);raw=m.request_bytes();current=json.loads(raw);b=helper.data();retention=json.loads(helper.auth(b['source_retention']).read_bytes());original_auth=helper.auth
  class InMemoryRequest:
   def read_bytes(self):return raw
  def auth(row):return InMemoryRequest() if row==b['current_request'] else original_auth(row)
  with mock.patch.object(helper,'auth',side_effect=auth):
   self.assertTrue(helper.validate_source_origin(current,retention))
   changed=copy.deepcopy(current);changed['source_derivative_sha256']='0'*64
   with self.assertRaises(RuntimeError):helper.validate_source_origin(changed,retention)
 def test_original_source_checks_and_physical_checks_unchanged(self):
  successor=json.loads((D/'SOURCE-SUCCESSOR-ROLE-BINDING.NOT-RELEASED.json').read_bytes());old=ast.parse(Path(successor['predecessor_helper']['path']).read_bytes());new=ast.parse((D/'attempt5_exact_source_origin_binding.SOURCE-ONLY.NOT-RELEASED.py').read_bytes())
  for name in ['validate_source_origin','require_new_runtime_facts']:
   pick=lambda tree:next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
   self.assertEqual(ast.dump(pick(old)),ast.dump(pick(new)))
if __name__=='__main__':unittest.main(verbosity=2)
