import gzip, hashlib, importlib.util, os, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("overlay", ROOT / "scripts/application-tests/native_diagnostic_overlay.py")
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)

def tiny(entries):
    return M._archive(entries)

class OverlayTests(unittest.TestCase):
    def test_parser_and_deterministic_overlay(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); base_raw=gzip.compress(tiny((("init",b"old",0o100755),)),mtime=0)
            # Authenticate fixture through the public replay path, then use a patched constant.
            old=M.BASE_SHA256; oldp=M.PAYLOAD_SHA256
            M.BASE_SHA256=hashlib.sha256(base_raw).hexdigest(); M.PAYLOAD_SHA256=hashlib.sha256(b"app").hexdigest()
            try:
                (d/"base.gz").write_bytes(base_raw); (d/"app").write_bytes(b"app"); (d/"collector").write_bytes(b"collector")
                a=M.build_overlay(d/"base.gz",d/"app",d/"collector",d/"one.gz")
                b=M.build_overlay(d/"base.gz",d/"app",d/"collector",d/"two.gz")
                self.assertEqual(a["output_sha256"],b["output_sha256"])
                self.assertEqual(M.parse_newc(gzip.decompress((d/"one.gz").read_bytes()))[0][-1]["name"],"case/work")
            finally: M.BASE_SHA256=old; M.PAYLOAD_SHA256=oldp

    def test_rejects_duplicate_overlay_and_path_escape(self):
        with self.assertRaises(M.OverlayError): M.parse_newc(tiny((("../x",b"x",0o100644),)))
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); base=tiny((("x",b"x",0o100644),)); raw=gzip.compress(base,mtime=0)
            old=M.BASE_SHA256; M.BASE_SHA256=hashlib.sha256(raw).hexdigest()
            try:
                with self.assertRaises(M.OverlayError): M.replay(raw,tiny((("init",b"a",0o100755),("init",b"b",0o100755),("case/work",b"",0o40755))))
            finally: M.BASE_SHA256=old

    def test_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); (d/"out").write_bytes(b"x")
            with self.assertRaises(M.OverlayError): M.build_overlay(d/"missing",d/"missing",d/"missing",d/"out")

if __name__ == "__main__": unittest.main()
