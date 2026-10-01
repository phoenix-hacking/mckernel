import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[2]; P=ROOT/'docs/verification/evidence/native-exact-candidate-delta-preparation-scratch21-20261001.py'; S=importlib.util.spec_from_file_location('s21',P); p=importlib.util.module_from_spec(S); S.loader.exec_module(p)
class Scratch21(unittest.TestCase):
 def test_fresh_names_owner_and_failed_scratch20_preserved(self):
  self.assertEqual(p.TARGET,'28a905bfc177627e338a3fd91f69329ac2e74046'); self.assertEqual(p._IMPL.EXCLUSION_NAME,'native-exact-candidate-operational-exclusion-scratch18.json'); self.assertEqual(p._IMPL.EXCLUSION_NAME,p.EXCLUSION_NAME)
  p.validate_owner_exclusion(ROOT)
  self.assertTrue((Path('/home/holden/mckernel-work/scratch')/'mckernel-exact-candidate-scratch-20').is_dir())
  for n in (p.CANDIDATE_NAME,p.MANIFEST_NAME,p.REQUEST_NAME,p.LOG_NAME,p.TERMINAL_NAME,p.LEASE_NAME): self.assertFalse((Path('/home/holden/mckernel-work/scratch')/n).exists())
 def test_execute_fails_closed(self):
  with self.assertRaisesRegex(p.Refusal,'forbids execute'): p.prepare(execute=True)
 def test_validate_only_authenticates_five_links(self):
  result=p.prepare(); self.assertEqual(result['status'],'PASS_VALIDATE_ONLY'); self.assertEqual(result['shared_files'],486)
  with self.assertRaisesRegex(p.Refusal,'five-link topology is pinned'): p.prepare(expected_initial_links=4)
  with self.assertRaisesRegex(p.Refusal,'shared aliases are pinned'): p.prepare(additional_shared_roots=())
 def test_small_five_to_six_link_contract_and_replaced_alias(self):
  with tempfile.TemporaryDirectory() as temporary:
   top=Path(temporary); roots=[top/str(i) for i in range(7)]
   for root in roots: root.mkdir()
   rel='evidence'; (roots[0]/rel).write_bytes(b'exact')
   for root in roots[1:5]: os.link(roots[0]/rel,root/rel)
   before=p._IMPL.snapshot(roots[0]/rel)
   self.assertEqual(before['nlink'],5)
   row={'path':rel,'before':before}
   os.link(roots[0]/rel,roots[5]/rel)
   p._IMPL.check_shared(roots[5],roots[0],roots[1],roots[2],[row],5,(roots[3],roots[4]))
   os.link(roots[0]/rel,roots[6]/rel)
   (roots[4]/rel).unlink(); (roots[4]/rel).write_bytes(b'exact')
   self.assertEqual((roots[0]/rel).stat().st_nlink,6)
   with self.assertRaisesRegex(p.Refusal,'shared evidence identity'):
    p._IMPL.check_shared(roots[5],roots[0],roots[1],roots[2],[row],5,(roots[3],roots[4]))
 def test_owner_exclusion_mismatch_precedes_mutation(self):
  candidate=Path('/home/holden/mckernel-work/scratch')/p.CANDIDATE_NAME
  self.assertFalse(candidate.exists())
  with mock.patch.object(p._IMPL,'git',return_value=b"OPERATIONAL_EXCLUSION_PATH = '/wrong'\n"), \
      mock.patch.object(p._IMPL,'prepare') as inherited:
   with self.assertRaisesRegex(p.Refusal,'active exclusion mismatch'): p.prepare()
   inherited.assert_not_called()
  self.assertFalse(candidate.exists())
if __name__=='__main__': unittest.main()
