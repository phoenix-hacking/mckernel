"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure metadata projection checks only; no runtime owner import or observation.
"""
import copy,json,unittest
from pathlib import Path
import prepare_native1_sdk7_bindings as p
D=Path(__file__).resolve().parent
class Projection(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.v={name:p.bound(ref) for name,ref in p.INPUTS.items() if name!='adapter'}
  cls.v['original_request']=p.bound(cls.v['origin']['request'])
 def compose(self,v=None):return p.compose(self.v if v is None else v,p.INPUTS,D/'PURE-FIXTURE-NOT-WRITTEN')
 def test_actual_failed_native_retirement_projects_without_native_acceptance(self):
  result=self.compose();closure=result['LATEST-NATIVE1-CLOSURE.PROJECTION.json'];terminal=result['LATEST-NATIVE1-TERMINAL.PROJECTION.json']
  self.assertEqual(closure['container'],self.v['post']['exact_container_absent'])
  self.assertEqual(closure['nonce'],self.v['owner']['nonce']);self.assertEqual(closure['original_workload_status'],'FAIL')
  self.assertFalse(closure['native_acceptance']);self.assertFalse(closure['application_acceptance'])
  self.assertEqual(terminal['state']['ExitCode'],1);self.assertEqual(terminal['state'],self.v['terminal_inspection'][0]['State'])
  self.assertTrue(closure['source_only_projection']);self.assertTrue(closure['projection_adds_no_independent_acceptance'])
  self.assertEqual(closure['terminal'],p.document_ref(D/'PURE-FIXTURE-NOT-WRITTEN/LATEST-NATIVE1-TERMINAL.PROJECTION.json',terminal))
 def test_new_live_authority_stays_null_and_old_source_provenance_unchanged(self):
  result=self.compose();request=result['SDK7-REQUEST.TEMPLATE.NOT-RELEASED.json'];head=result['OPERATION-HEAD.TEMPLATE.NOT-RELEASED.json'];live=result['LIVE-OBSERVATION.TEMPLATE.NOT-RELEASED.json'];bundle=result['SDK7-BUNDLE.STATIC.NOT-RELEASED.json'];fill=result['SDK7-FILL.STATIC.NOT-RELEASED.json'];command=result['NEXT-UNPRIVILEGED-SDK7-OWNER.COMMAND.NOT-RELEASED.json']
  for key in ('nonce','request_path','candidate_root','candidate_identity','owner_evidence_root','output_parent_identity','input_identity','basis_identity','backing_identity'):self.assertIsNone(request[key],key)
  self.assertIsNone(head['no_intervening_operation']);self.assertIsNone(head['consumed_nonces']);self.assertIsNone(live['clock'])
  for key in ('query','query_join','reservation','root_admission_review'):self.assertIsNone(bundle[key],key)
  self.assertEqual(command['commands'],self.v['origin']['seven_commands']);self.assertEqual(command['provider'],self.v['origin']['provider']);self.assertEqual(command['owner'],self.v['origin']['owner'])
  self.assertEqual(fill['historical_sdk21_artifact'],self.v['origin']['SDK21_artifact_behavior']);self.assertEqual(fill['historical_source_approval'],self.v['origin']['source_approval'])
  self.assertNotEqual(bundle['latest_operation'],self.v['origin']['current_physical'])
 def test_broken_retirement_or_failed_scope_never_produces_projection(self):
  cases=[('acceptance',['decision'],'PASS_SDK_SUPPORTED_TOOLS_ARTIFACTS_ONLY'),('acceptance',['independent'],False),('acceptance',['native_acceptance'],True),('caller_join',['joined'],False),('caller_join',['returncode'],0),('owner_result',['absence_verified'],False),('terminal_inspection',[0,'State','Running'],True),('terminal_inspection',[0,'State','ExitCode'],0),('post',['group_membership_observation','errors'],['unresolved']),('post',['commands_actual_reaped',0,'command','reaped'],False),('post',['closed_exclusive_probes'],[]),('post',['docker_observations',1,'stdout'],'foreignCID\n')]
  for name,path,value in cases:
   v=copy.deepcopy(self.v);target=v[name]
   for key in path[:-1]:target=target[key]
   target[path[-1]]=value
   with self.subTest(name=name,path=path),self.assertRaises((ValueError,KeyError)):self.compose(v)
if __name__=='__main__':unittest.main(verbosity=2)
