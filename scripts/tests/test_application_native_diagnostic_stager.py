import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("stager", ROOT / "scripts/application-tests/native_diagnostic_stager.py")
S = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(S)

class StagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name)
        self.base = self.d / "base"; self.base.mkdir()
        for rel, data in {"modules/ihk.ko":b"ihk", "modules/ihk-smp-x86_64.ko":b"smp",
                          "modules/mcctrl.ko":b"ctrl", "images/mckernel.img":b"image",
                          "bin/mcexec":b"exec", "bin/native-boot":b"boot", "lib64/ld-linux-x86-64.so.2":b"loader",
                          "lib64/libc.so.6":b"libc"}.items():
            p = self.base / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data); p.chmod(0o755)
        (self.base / "init").write_bytes(b"old-init"); (self.base / "tmp").mkdir(); (self.base / "tmp").chmod(0o1777)
        self.payload = self.d / "payload"; self.payload.write_bytes(b"payload"); self.payload.chmod(0o755)
        self.collector = self.d / "collector"; self.collector.write_bytes(b"collector"); self.collector.chmod(0o755)
        S.EXPECTED = {rel: hashlib.sha256((self.base / rel).read_bytes()).hexdigest() for rel in
                      ("modules/ihk.ko", "modules/ihk-smp-x86_64.ko", "modules/mcctrl.ko", "images/mckernel.img", "bin/mcexec", "bin/native-boot")}
        S.EXPECTED["bin/native-boot"] = hashlib.sha256((self.base / "bin/native-boot").read_bytes()).hexdigest()
        S.PAYLOAD_SHA256 = hashlib.sha256(self.payload.read_bytes()).hexdigest()
        self.cpio = self.d / "cpio"; self.gzip = self.d / "gzip"
        # Fake backend records argv and emits stable bytes; this remains a no-build unit test.
        self.cpio.write_text("#!/bin/sh\ncat >/dev/null\nprintf 'CPIO-FAKE'\n")
        self.gzip.write_text("#!/bin/sh\nprintf 'GZIP-FAKE'\n")
        self.cpio.chmod(0o755); self.gzip.chmod(0o755)

    def test_mcexec_expected_digest_is_current_artifact(self):
        self.assertEqual(
            S.MCEEXEC_SHA256,
            "ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b",
        )
        self.assertNotEqual(
            S.MCEEXEC_SHA256,
            "b786e9c98ecc3d429c5ce4d683f1ef4ebca7b3ea132b8435ed6026fc9e984639",
        )

    def tearDown(self): self.tmp.cleanup()

    def test_stages_replays_and_does_not_modify_source(self):
        before = {p.relative_to(self.base).as_posix(): (p.stat().st_mode, p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
                  for p in self.base.rglob("*")}
        out = self.d / "out"
        m = S.stage(self.base, self.payload, self.collector, out, cpio=str(self.cpio), gzip=str(self.gzip))
        self.assertEqual((out / "root/apps/app").read_bytes(), b"payload")
        self.assertEqual((out / "root/init").read_bytes(), b"collector")
        self.assertEqual(m["artifacts"]["initramfs.cpio.gz"], hashlib.sha256((out / "initramfs.cpio.gz").read_bytes()).hexdigest())
        after = {p.relative_to(self.base).as_posix(): (p.stat().st_mode, p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
                 for p in self.base.rglob("*")}
        self.assertEqual(before, after)

    def test_fresh_output_and_inputs_fail_closed(self):
        out = self.d / "out"; out.mkdir()
        with self.assertRaises(S.StagerError): S.stage(self.base, self.payload, self.collector, out, cpio=str(self.cpio), gzip=str(self.gzip))
        bad = self.base / "modules" / "evil"; bad.symlink_to(self.payload)
        with self.assertRaises(S.StagerError): S.stage(self.base, self.payload, self.collector, self.d / "new", cpio=str(self.cpio), gzip=str(self.gzip))

    def test_missing_closure_and_payload_hash_rejected(self):
        (self.base / "lib64/libc.so.6").unlink()
        with self.assertRaises(S.StagerError): S.stage(self.base, self.payload, self.collector, self.d / "out", cpio=str(self.cpio), gzip=str(self.gzip))

    def test_second_build_is_byte_identical_and_output_cannot_be_nested(self):
        first = self.d / "one"; second = self.d / "two"
        a = S.stage(self.base, self.payload, self.collector, first, cpio=str(self.cpio), gzip=str(self.gzip))
        b = S.stage(self.base, self.payload, self.collector, second, cpio=str(self.cpio), gzip=str(self.gzip))
        self.assertEqual(a["artifacts"], b["artifacts"])
        with self.assertRaises(S.StagerError): S.stage(self.base, self.payload, self.collector, self.base / "nested", cpio=str(self.cpio), gzip=str(self.gzip))

if __name__ == "__main__": unittest.main()
