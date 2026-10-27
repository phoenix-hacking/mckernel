"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure data/AST tests. No frontend, clock, Target, publication or observer execution.
"""
from pathlib import Path
import ast,copy,importlib.util,json,unittest
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pure_static_adoption_batch',P/'adopt_mock64_batch.py');batch=importlib.util.module_from_spec(spec);spec.loader.exec_module(batch)
class Data(unittest.TestCase):
 def envelope(self):
  payload=dict(nonce=batch.NONCE,request=batch.two(batch.BASIS['refs']['MOCK64-REQUEST.json']),author='/root',status='PASS_EXECUTION_RELEASE')
  return dict(status='PENDING_ACTUAL_INDEPENDENT_EXECUTION_REVIEW_NOT_A_RELEASE',proposed_release_payload=payload,reviewed_release_payload_sha256=batch.mc.sha(batch.mc.canonical(payload)))
 def test_exact_review_payload_and_two_key_reference(self):
  e=self.envelope();review=dict(decision='PASS_EXECUTION',reviewer=batch.REVIEWER,implementation_ownership=False,reviewed_release_payload_sha256=e['reviewed_release_payload_sha256']);reference=dict(path='/PURE-ONLY-NOT-A-RELEASE',bytes=123,sha256='a'*64)
  release=batch.build_release(e,review,reference);self.assertEqual(set(release['execution_review']),{'path','sha256'});self.assertEqual({k:v for k,v in release.items() if k!='execution_review'},e['proposed_release_payload'])
 def test_no_approval_missing_wrong_hash_reviewer_or_mutation_refused(self):
  e=self.envelope();r=dict(decision='PASS_EXECUTION',reviewer=batch.REVIEWER,implementation_ownership=False,reviewed_release_payload_sha256=e['reviewed_release_payload_sha256']);ref=dict(path='/PURE',sha256='a'*64)
  for key,value in [('decision',None),('reviewer','/root'),('implementation_ownership',True),('reviewed_release_payload_sha256','0'*64)]:
   wrong=dict(r);wrong[key]=value
   with self.assertRaises(ValueError):batch.build_release(e,wrong,ref)
  e['proposed_release_payload']['author']='mutated'
  with self.assertRaises(ValueError):batch.validated_payload(e)
 def test_parent_tool_requires_actual_completed_return(self):
  batch.tool_completed(dict(exit_code=0,session_id=None,fixture_only=True))
  for d in [dict(exit_code=1),dict(exit_code=0,session_id=123),dict(function_returned=True,returncode=0,process_joined=False)]:
   with self.assertRaises(ValueError):batch.tool_completed(d)
 def test_propose_frontend_is_metadata_only_and_bootstrap_closed(self):
  tree=ast.parse((P/'adopt_mock64_batch.py').read_bytes());funcs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)};propose=funcs['propose'];front=[n for n in ast.walk(propose) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='frontend']
  self.assertEqual(len(front),1);self.assertEqual(ast.literal_eval(front[0].args[0]),'prepare_mock64_release_proposal.py')
  src=ast.get_source_segment((P/'adopt_mock64_batch.py').read_text(),funcs['publish']);self.assertNotIn("frontend(",src);self.assertIn('owner.authenticate(',src)
 def test_no_frozen_source_or_request_changed_and_only_D_added(self):
  batch.verify_static();src=(P/'adopt_mock64_batch.py').read_text();self.assertEqual(src.count('sys.path.insert('),1);self.assertIn('sys.path.insert(0,str(D))',src)
if __name__=='__main__':unittest.main(verbosity=2)
