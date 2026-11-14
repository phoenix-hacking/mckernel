"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure static/API controls; no nonce creation, live clock, target or Root authority.
"""
from pathlib import Path
from types import SimpleNamespace
import tempfile,unittest
import finalize_repro_batch as batch

class Pure(unittest.TestCase):
 def test_real_frozen_source_api_and_latest_actual_boundary(self):
  mapping,known=batch.preflight()
  self.assertEqual(len(mapping['source_sha256']),25)
  self.assertEqual(len(set(known)),18)
  self.assertIn(batch.FAILED_NONCE,known);self.assertIn(batch.NEXT_NONCE,known)
 def test_consumed_nonce_stops_before_any_static_copy(self):
  mapping,known=batch.preflight()
  for nonce in [batch.FAILED_NONCE,batch.NEXT_NONCE,'not-a-nonce',None]:
   with self.subTest(nonce=nonce),self.assertRaises(ValueError):batch.static(SimpleNamespace(nonce=nonce),mapping,known)
 def test_incomplete_or_substituted_root_ledger_refused_without_outputs(self):
  _,known=batch.preflight()
  with tempfile.TemporaryDirectory(prefix='PURE-NO-RUNTIME-',dir=batch.HERE) as temporary:
   p=Path(temporary)/'PURE-NOT-AUTHORITY.json'
   base=dict(author='/root',complete_within_declared_current_boundary=False,root_attests_no_unlisted_post_boundary_execution_or_custody_operation=True,consumed_nonces=known,latest_accepted_free_boundary=batch.mc.ref(batch.LATEST),fixture_only=True,runtime_authority=None)
   for mutation in ['incomplete','extra','stale-boundary']:
    value=dict(base)
    if mutation=='extra':value.update(complete_within_declared_current_boundary=True,consumed_nonces=known+['c'*32])
    elif mutation=='stale-boundary':value.update(complete_within_declared_current_boundary=True,latest_accepted_free_boundary=None)
    p.write_bytes(batch.mc.canonical(value));reference=batch.mc.ref(p)
    args=SimpleNamespace(ledger=str(p),ledger_sha256=reference['sha256'])
    with self.subTest(mutation=mutation),self.assertRaises(ValueError):batch.root_static_refs(args,known)
if __name__=='__main__':unittest.main(verbosity=2)
