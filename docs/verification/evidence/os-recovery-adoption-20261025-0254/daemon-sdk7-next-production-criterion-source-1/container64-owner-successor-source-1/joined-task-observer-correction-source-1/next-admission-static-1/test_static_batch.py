"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Two pure static-data checks; no clock, preparation effects or target command.
"""
from pathlib import Path
from types import SimpleNamespace
import tempfile,unittest
import finalize_suffix_batch as batch
class Pure(unittest.TestCase):
 def test_actual_frozen_source_api_and_retained_prefix(self):
  mapping,known=batch.preflight();self.assertEqual(len(mapping['sources']),28);self.assertEqual(len(known),21)
  self.assertIn('302eabc386ed259685d41fbec898b174',known)
 def test_pending_root_ledger_stops_before_any_binding_copy(self):
  mapping,known=batch.preflight()
  with tempfile.TemporaryDirectory(prefix='PURE-NO-RUNTIME-',dir=batch.HERE) as temporary:
   p=Path(temporary)/'PENDING-NOT-AUTHORITY.json';p.write_bytes(batch.mc.canonical(dict(author=None,complete_within_declared_current_boundary=None,root_attests_no_unlisted_post_boundary_execution_or_custody_operation=None,consumed_nonces=known,runtime_authority=None)))
   args=SimpleNamespace(latest_postjoin=str(batch.LATEST),latest_postjoin_sha256=batch.LATEST_SHA,ledger=str(p),ledger_sha256=batch.mc.ref(p)['sha256'])
   with self.assertRaises(ValueError):batch.bind(args,mapping,known)
if __name__=='__main__':unittest.main(verbosity=2)
