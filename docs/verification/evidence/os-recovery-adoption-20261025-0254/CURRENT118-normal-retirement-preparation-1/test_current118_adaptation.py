"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Current118-specific retained facts and substituted OCI effects; no runtime probes.
"""
from pathlib import Path
import ast,copy,importlib.util,json,unittest
from unittest.mock import patch
import test_retirement_executor as oracle
m=oracle.m;B=oracle.B;P=oracle.P

class Current118Applicability(unittest.TestCase):
 def test_original_claim_four_outputs_and_actor_frontier(self):
  packet,protected,profile,claim,plan,terminal=m.validate_retained(B)
  self.assertEqual([x['index'] for x in packet['actual_commands']],[0,1,2,3])
  self.assertEqual(len(packet['declared_build_outputs']),4)
  self.assertEqual(packet['declared_build_outputs'][-1]['sha256'],'7e5dca2b68d1e8c6da21c8be19e85d2fe28bf79d3451ece90146279b56551416')
  self.assertEqual((len(B['prior_actors']),len(B['new_known_actors'])),(99,10))
  self.assertEqual((B['holder_pid'],B['runner_pid'],B['finite_pid']),(2222137,2222194,2221500))
  self.assertEqual((B['cid'],B['nonce']),('d980474cc189c35f6d78132856be10b6903aac988808336e7d44efcca0f4108f','e984210ca59641b299cf42d392eb953b'))
  self.assertEqual(packet['shared_custody']['records_authorized_for_release'],[])
 def test_exact_claim_and_new_workdir_required_before_mutation(self):
  item,image=oracle.fixture();self.assertTrue(oracle.check(item,image))
  item['Config']['WorkingDir']='/work'
  ops=oracle.FakeOps(item,image)
  with self.assertRaises(m.Refusal):m.transaction(ops)
  self.assertNotIn('rm',ops.events)
  item,image=oracle.fixture();claim=copy.deepcopy(oracle.CLAIM);claim['argv'].insert(-1,'--env=container=other')
  with self.assertRaises(m.Refusal):m.validate_profile(item,image,B,P,oracle.PROFILE,claim,oracle.TERMINAL)
 def test_same_wrong_env_or_label_on_both_image_and_container_refused(self):
  for key,value in [('Env',['container=other']),('Labels',{'mckernel.owner':B['nonce']})]:
   item,image=oracle.fixture();item['Config'][key]=image['Config'][key]=value
   ops=oracle.FakeOps(item,image)
   with self.subTest(key=key),self.assertRaises(m.Refusal):m.transaction(ops)
   self.assertNotIn('rm',ops.events)
 def test_core_lock_clock_spawn_custody_transaction_is_unchanged(self):
  original=ast.parse(m.authenticated(B['base_reviewed_executor']))
  actual=ast.parse(Path(m.SELF).read_bytes())
  def unit(tree,name,parent=None):
   body=tree.body if parent is None else next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==parent).body
   return next(n for n in body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==name)
  for name in ['Wait4Child','transport','transaction','must_retain_custody','Stop','write_new']:
   self.assertEqual(ast.dump(unit(original,name)),ast.dump(unit(actual,name)),name)
  for name in ['acquire','safe','before_spawn','claim_once','remove','absence','close','uncertain']:
   self.assertEqual(ast.dump(unit(original,name,'Actual')),ast.dump(unit(actual,name,'Actual')),name)
 def test_retired_bfd_identity_cannot_be_removed_by_current118_adapter(self):
  fake=type('Fake',(),dict(b=B,profile=oracle.PROFILE,rm_claimed=False,rm_invoked=False,safe=lambda self:None))()
  oldcid='2460c49fbbbf8be6ee5ae931e7e769eec2f26e352937e7f4a4dcf5d2ebec8008'
  with patch.object(m.subprocess,'Popen',side_effect=AssertionError('no actual effect')),self.assertRaises(m.Refusal):m.Actual.call(fake,['rm','--',oldcid])

if __name__=='__main__':unittest.main(verbosity=2)
