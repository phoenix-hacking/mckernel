import importlib.util
import os
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]; P=ROOT/'docs/verification/evidence/native-exact-candidate-delta-preparation-scratch20-20261001.py'; S=importlib.util.spec_from_file_location('s20',P); p=importlib.util.module_from_spec(S); S.loader.exec_module(p)
class Scratch20(unittest.TestCase):
 def test_identity_and_fresh_names(self):
  self.assertEqual(p._IMPL.git(ROOT,'rev-parse',p.TARGET).decode().strip(),p.TARGET); self.assertEqual(p._IMPL.git(ROOT,'rev-parse',p.TARGET+'^{tree}').decode().strip(),p.TARGET_TREE)
  for n in (p.CANDIDATE_NAME,p.MANIFEST_NAME,p.REQUEST_NAME,p.LOG_NAME,p.TERMINAL_NAME,p.LEASE_NAME,p.EXCLUSION_NAME): self.assertIn('20',n); self.assertFalse((Path('/home/holden/mckernel-work/scratch')/n).exists())
 def test_explicit_identity(self):
  self.assertEqual(p.BASELINE,'5f063f75d7385a9763904d2f1a5888ea131c754d')
  self.assertEqual(len(p.EXACT_DELTA),3)

 def test_validate_only_and_four_link_census(self):
  result = p.prepare()
  self.assertEqual(result['status'], 'PASS_VALIDATE_ONLY')
  self.assertEqual(result['shared_files'], 486)
  roots = [
   Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-1e95abdc-scratch-15'),
   Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-ddb8d7d5-scratch-16'),
   Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-50b08432-scratch-17'),
   Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-18'),
  ]
  sizes = {}
  for row in p._IMPL.git(ROOT, 'ls-tree', '-rlz', p.TARGET).split(b'\0'):
   if row:
    metadata, rel = row.split(b'\t', 1)
    fields = metadata.split()
    if fields[1] == b'blob':
     sizes[rel.decode()] = int(fields[3])
  old_entries = {rel: (mode, kind, oid) for mode, kind, oid, rel in
                 p._IMPL.tree_entries(ROOT, p.BASELINE)}
  shared = []
  for mode, kind, oid, rel in p._IMPL.tree_entries(ROOT, p.TARGET):
   if (kind == 'blob' and sizes[rel] > 1 << 20 and
       rel.startswith('docs/verification/evidence/') and
       old_entries.get(rel) == (mode, kind, oid) and
       (roots[0] / rel).exists() and mode in ('100644', '100755')):
    shared.append((rel, mode))
  self.assertEqual(len(shared), 486)
  for rel, mode in shared:
   stats = [os.stat(root / rel) for root in roots]
   self.assertEqual(len({(s.st_dev, s.st_ino) for s in stats}), 1, rel)
   self.assertEqual({s.st_nlink for s in stats}, {4}, rel)
   self.assertEqual({s.st_mode & 0o777 for s in stats}, {int(mode, 8) & 0o777}, rel)

 def test_three_link_mutation_is_rejected(self):
  with self.assertRaisesRegex(p.Refusal, 'unauthenticated prior shared evidence'):
   p.prepare(expected_initial_links=3)
if __name__=='__main__': unittest.main()
