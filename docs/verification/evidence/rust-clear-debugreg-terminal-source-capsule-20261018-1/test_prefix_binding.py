"""One bounded prefix-family correction: actual metadata consumers, no transaction."""
from pathlib import Path
import importlib.util,json,copy,unittest,hashlib
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('changed',P/'test_changed_consumers.py');changed=importlib.util.module_from_spec(s);s.loader.exec_module(changed)
FRESH='rust-clear-debugreg-terminal-preparation-20261018-1'
OLD='rust-scheduler-debug-terminal-preparation-20261018-1'
SUFFIXES=('.mutex','.plan.json','.journal.jsonl','.docker-logs.capture','.quarantine.json','.attempt.archive','.shared.archive')
class Prefix(changed.Metadata):
 def test_fresh_fixed_paths_and_hash_pins(self):
  m=changed.module('cleanup.py');o=changed.module('observe_reset_image_retirement.py');post=changed.module('postjoin_readback.py')
  expected=[str(m.ROOT/(FRESH+x)) for x in SUFFIXES[:5]]+[str(m.ATTEMPT.parent/(FRESH+SUFFIXES[5])),str(m.SHARED.parent/(FRESH+SUFFIXES[6]))]
  self.assertEqual(m.PREFIX,FRESH);self.assertEqual(m.transaction_paths(),expected);self.assertEqual(len(set(expected)),7)
  self.assertTrue(all(OLD not in p for p in expected));draft=m.prepare_release({},'c'*40,'d'*40);self.assertEqual(draft['transaction_paths'],expected);self.assertEqual(draft['author'],'clear_debugreg_terminal_prepare_1726')
  sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  self.assertEqual(o.SOURCE_SHA,sha(P/'cleanup.py'));self.assertEqual(post.ENGINE_SHA,o.SOURCE_SHA);self.assertEqual(post.OBSERVER_SHA,sha(P/'observe_reset_image_retirement.py'))
 def test_actual_configure_rejects_each_stale_path(self):
  r=self.release_fixture();m=self.m
  for name,suffix in zip(('MUTEX','PLAN','JOURNAL','CAPTURE','QUARANTINE'),SUFFIXES):setattr(m,name,m.ROOT/(FRESH+suffix))
  m.ARCHIVE_NAMES=(FRESH+SUFFIXES[5],FRESH+SUFFIXES[6]);r['transaction_paths']=m.prepare_release(r['observation'],r['git_commit'],r['git_tree'])['transaction_paths'];m.configure(r)
  before={str(p):p.read_bytes() for p in (m.ATTEMPT,m.SHARED)}
  for i in range(7):
   bad=copy.deepcopy(r);bad['transaction_paths'][i]=bad['transaction_paths'][i].replace(FRESH,OLD)
   with self.subTest(index=i),self.assertRaisesRegex(m.Refusal,'transaction-path-binding'):m.configure(bad)
   self.assertIsNone(m.RELEASE);self.assertEqual({str(p):p.read_bytes() for p in (m.ATTEMPT,m.SHARED)},before)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([Prefix('test_fresh_fixed_paths_and_hash_pins'),Prefix('test_actual_configure_rejects_each_stale_path')]))
 (P/'prefix-correction-result.json').write_text(json.dumps(dict(status='PASS' if result.wasSuccessful() else 'FAIL_ESCALATE',family='privatecloneprefix',finding=1,bounded_correction=1,tests=result.testsRun,stale_path_refusals=7,actual_configure=True,transaction=False,root=False,docker=False),indent=2)+'\n')
 raise SystemExit(not result.wasSuccessful())
