"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Changed native2-success metadata only; no replay of parent/runtime tests or workload.
"""
import copy,unittest
from pathlib import Path
import prepare_native2_sdk7_bindings as p
D=Path(__file__).resolve().parent
class Projection(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.v={name:p.bound(ref) for name,ref in p.INPUTS.items() if name!='adapter'}
  cls.v['original_request']=p.bound(cls.v['origin']['request'])
 def compose(self,v=None):return p.compose(self.v if v is None else v,p.INPUTS,D/'NATIVE2-PURE-FIXTURE-NOT-WRITTEN')
 def test_actual_success_keeps_protocol_false_flags_separate_from_independent_case_acceptance(self):
  outputs=self.compose();closure=outputs['LATEST-NATIVE2-CLOSURE.PROJECTION.json'];terminal=outputs['LATEST-NATIVE2-TERMINAL.PROJECTION.json']
  self.assertEqual(closure['original_workload_status'],'PROTOCOL_PASS');self.assertEqual(terminal['state']['ExitCode'],0)
  self.assertEqual(closure['container'],self.v['post']['exact_container_absent']);self.assertEqual(closure['nonce'],self.v['owner']['nonce'])
  self.assertFalse(closure['application_acceptance']);self.assertFalse(closure['native_acceptance'])
  self.assertFalse(closure['protocol_observation']['application_acceptance']);self.assertFalse(closure['protocol_observation']['mckernel_application_executed'])
  self.assertTrue(closure['accepted_native_diagnostic_case']);self.assertEqual(closure['independent_protocol_acceptance'],p.INPUTS['protocol_acceptance'])
  self.assertEqual(closure['protocol_observation']['stdout_bytes'],91);self.assertEqual(closure['protocol_observation']['raw_wait_status'],0)
  self.assertIn('token=514 errno=-11',closure['protocol_observation']['retirement_lines'][0]);self.assertIn('token=515 errno=0',closure['protocol_observation']['retirement_lines'][-1])
 def test_original_failed_shape_or_broken_protocol_and_review_are_refused(self):
  cases=[('owner_result',['status'],'FAIL'),('owner_result',['failure'],'OwnerError'),('caller_join',['returncode'],1),('terminal_inspection',[0,'State','ExitCode'],1),('post',['commands_actual_reaped'],[]),('inner',['application_acceptance'],True),('inner',['mckernel_application_executed'],True),('inner',['guest_report','procfs_empty'],False),('inner',['guest_report','raw_wait_status'],1),('inner',['guest_report','streams','stdout','truncated'],True),('inner',['guest_report','streams','stderr','observed'],1),('acceptance',['decision'],'PASS_ACTUAL_FAILED_NATIVE_POSTJOIN_CURRENT_PHYSICAL'),('protocol_acceptance',['runner_protocol_false_flags_unchanged'],False),('protocol_acceptance',['accepted_native_diagnostic_case'],False)]
  for name,path,value in cases:
   v=copy.deepcopy(self.v);target=v[name]
   for key in path[:-1]:target=target[key]
   target[path[-1]]=value
   with self.subTest(name=name,path=path),self.assertRaises((ValueError,KeyError)):self.compose(v)
 def test_sdk_literals_stay_unchanged_and_future_live_authority_stays_null(self):
  outputs=self.compose();bundle=outputs['SDK7-BUNDLE.STATIC.NOT-RELEASED.json'];head=outputs['OPERATION-HEAD.TEMPLATE.NOT-RELEASED.json'];live=outputs['LIVE-OBSERVATION.TEMPLATE.NOT-RELEASED.json'];request=outputs['SDK7-REQUEST.TEMPLATE.NOT-RELEASED.json'];command=outputs['NEXT-UNPRIVILEGED-SDK7-OWNER.COMMAND.NOT-RELEASED.json']
  self.assertIsNone(head['no_intervening_operation']);self.assertIsNone(head['consumed_nonces']);self.assertIsNone(live['clock']);self.assertIsNone(request['nonce'])
  for key in ('query','query_join','reservation','root_admission_review'):self.assertIsNone(bundle[key])
  self.assertEqual(command['commands'],self.v['origin']['seven_commands']);self.assertEqual(command['profile'],self.v['origin']['profile']);self.assertEqual(command['provider'],self.v['origin']['provider']);self.assertEqual(command['owner'],self.v['origin']['owner'])
  self.assertIn('LATEST-NATIVE2-CLOSURE',bundle['latest_operation']['path']);self.assertEqual(outputs['SDK7-FILL.STATIC.NOT-RELEASED.json']['historical_sdk21_artifact'],self.v['origin']['SDK21_artifact_behavior'])
if __name__=='__main__':unittest.main(verbosity=2)
