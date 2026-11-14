"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure finalization/source-binding checks only; no live/query/workload imports.
"""
import ast,json,unittest
from pathlib import Path
import finalize_sdk7_static as f
D=Path(__file__).resolve().parent
class Static(unittest.TestCase):
 def test_exact_current_owner_paths_and_literals_keep_all_live_fields_unset(self):
  values=f.prepare(D/'PURE-FUTURE-OUTPUT-NOT-WRITTEN');ready=values['READY.POSTGROWTH.STATIC-NOT-RELEASED.json'];bundle=values['SDK7-BUNDLE.STATIC.NOT-RELEASED.json'];request=values['SDK7-REQUEST.TEMPLATE.NOT-RELEASED.json']
  origin=f.bound(f.ref(f.ORIGIN))
  self.assertEqual(ready['seven_commands'],origin['seven_commands']);self.assertEqual(ready['provider'],origin['provider']);self.assertEqual(ready['profile'],origin['profile'])
  self.assertEqual(ready['selected_owner']['sha256'],'999713a7b4dafa034232d997872132642358aa80029244ad27e571efbf1664ee')
  self.assertTrue(request['request_path'].endswith('PURE-FUTURE-OUTPUT-NOT-WRITTEN/SDK7-REQUEST.TEMPLATE.NOT-RELEASED.json'))
  for key in ('nonce','backing_identity','candidate_root','candidate_identity','owner_evidence_root'):self.assertIsNone(request[key])
  for key in ('growth_closure','accepted_growth_stage','latest_operation','operation_head','live_observation','query','query_join','reservation','root_admission_review','current_source_publication','current_source_review'):self.assertIsNone(bundle[key])
  self.assertIsNone(values['CURRENT-CONSUMER-PUBLICATION.TEMPLATE.NOT-RELEASED.json']['status']);self.assertIsNone(values['CURRENT-CONSUMER-REVIEW.TEMPLATE.NOT-RELEASED.json']['decision']);self.assertFalse(ready['execution_authority'])
 def test_partial_growth_or_old_single_hop_publication_cannot_finalize(self):
  with self.assertRaisesRegex(ValueError,'matching-accepted-growth-physical'):
   f.prepare(D/'PURE-NOT-WRITTEN',dict(growth_closure=dict(path='/not-read',bytes=1,sha256='0'*64)))
  old=f.C
  with self.assertRaisesRegex(ValueError,'current source publication'):
   f.prepare(D/'PURE-NOT-WRITTEN',dict(current_source_publication=f.ref(old/'CURRENT-CONSUMER-SOURCE-PUBLICATION.json'),current_source_review=f.ref(old/'CURRENT-CONSUMER-SOURCE-REVIEW.json')))
 def test_adapter_keeps_runtime_query_owner_operations_and_only_adds_stage_bindings(self):
  parent=D.parent/'scratch-growth-postcheck-custody-recovery-source-1/sdk7_authority_adapter.RECOVERED-GROWTH.SOURCE-ONLY.py'
  current=D/'sdk7_authority_adapter.POSTGROWTH-CHAIN.SOURCE-ONLY.py'
  def funcs(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef)}
  a,b=funcs(parent),funcs(current);self.assertEqual(set(a),set(b))
  self.assertEqual({n:a[n] for n in a if n not in {'adapt','validate_query_release','readonly_query'}},{n:b[n] for n in b if n not in {'adapt','validate_query_release','readonly_query'}})
  self.assertEqual(a['context'],b['context'])
  for name in ('adapt','validate_query_release','readonly_query'):self.assertNotEqual(a[name],b[name])
if __name__=='__main__':unittest.main(verbosity=2)
