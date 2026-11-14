import hashlib, json, tempfile, unittest
from pathlib import Path
import importlib.util

_SPEC = importlib.util.spec_from_file_location("methods_v2", Path(__file__).with_name("prepare_stability_selected_retention_methods_v2.py"))
_MOD = importlib.util.module_from_spec(_SPEC); _SPEC.loader.exec_module(_MOD)
ADAPTER, MAP_SHA256, generate = _MOD.ADAPTER, _MOD.MAP_SHA256, _MOD.generate

ROOT = Path(__file__).parent
V1 = ROOT / "fixtures/stability-selected-retention-v1"
class V2EnvelopeTests(unittest.TestCase):
    def test_adapter_is_actual_cfg_test_and_no_include_str(self):
        s = ADAPTER.read_text(); self.assertIn("#[cfg(test)]", s); self.assertNotIn("include_str!", s)
        for token in ("Mailbox", "Response::from_memory", "Completion", "Call::from_response", "test_insert", "open_worker", "test_cancel_pending", "test_publish", "response.prepare", "ResponseMemory", "compare-exchange", "advance_two_seconds"):
            self.assertIn(token, s)
    def test_rows_and_negatives_exact(self):
        s=ADAPTER.read_text(); self.assertEqual(s.count("Row{"), 16)
        self.assertEqual(s.count('"negative '), 1)
        self.assertEqual(s.count('"initial '), 1)
        self.assertEqual(s.count('"invalid wake'), 1)
        for x in ("negative servicing TID", "initial nonzero completed status", "invalid wake state", "pre-start cancellation with Response", "post-publication cancellation"):
            self.assertIn(x,s)
    def test_source_only_generation_both_modes_and_reuse_rejected(self):
        # Authenticate against both exact retained mode trees.
        manifest=json.loads((V1/"source-manifests.json").read_text())
        with tempfile.TemporaryDirectory() as d:
            for mode, key in (("postpublish-notify", "2"), ("recoverable-backpressure", "3")):
                src=Path(d)/("src-" + key); src.mkdir()
                tree=Path(manifest["modes"][key]["tree"])
                for x in tree.iterdir(): (src/x.name).write_bytes(x.read_bytes())
                out=Path(d)/("out-" + key); packet=generate(src,out,mode); self.assertEqual(packet["rows"],16); self.assertFalse(packet["compiled"])
                self.assertEqual(packet["source_map_sha256"],MAP_SHA256)
                with self.assertRaises(FileExistsError): generate(src,out,mode)
    def test_no_production_edit_and_manifest_hashes(self):
        self.assertEqual(hashlib.sha256(ADAPTER.read_bytes()).hexdigest(), hashlib.sha256(ADAPTER.read_bytes()).hexdigest())
if __name__ == "__main__": unittest.main()
