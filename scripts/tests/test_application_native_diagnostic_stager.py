import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

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
        self.cpio = Path("/usr/bin/cpio"); self.gzip = self.d / "gzip"
        # Keep gzip fake and use the installed cpio for real archive-member checks.
        self.gzip.write_text("#!/bin/sh\nprintf 'GZIP-FAKE'\n")
        self.gzip.chmod(0o755)

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

    def _replacement_map(self, include_mcexec=False):
        result = {}
        paths = S.MCEEXEC_REPLACEMENT_PATHS if include_mcexec else S.REPLACEMENT_PATHS
        for index, rel in enumerate(sorted(paths)):
            source = self.d / ("replacement-%d.bin" % index)
            source.write_bytes(("replacement-%d\n" % index).encode("ascii"))
            source.chmod(0o755)
            result[rel] = {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                           "size": source.stat().st_size, "mode": source.stat().st_mode & 0o7777}
        return result

    def test_five_artifact_mode_replaces_stale_mcexec_exactly(self):
        replacements = self._replacement_map(include_mcexec=True)
        launcher = Path(replacements["bin/mcexec"]["path"])
        corrected_hash = hashlib.sha256(launcher.read_bytes()).hexdigest()
        stale = self.base / "bin/mcexec"
        stale.write_bytes(b"stale-launcher"); stale.chmod(0o755)
        before = (stale.read_bytes(), stale.stat().st_mode, stale.stat().st_mtime_ns)
        out = self.d / "five-artifact"
        with mock.patch.object(S, "MCEEXEC_SHA256", corrected_hash), \
             mock.patch.object(S, "MCEEXEC_SIZE", launcher.stat().st_size):
            manifest = S.stage(self.base, self.payload, self.collector, out,
                               cpio=str(self.cpio), gzip=str(self.gzip),
                               replacements=replacements)
        self.assertEqual((out / "root/bin/mcexec").read_bytes(), launcher.read_bytes())
        self.assertEqual(manifest["replacements"]["bin/mcexec"]["final_sha256"], corrected_hash)
        self.assertEqual((stale.read_bytes(), stale.stat().st_mode, stale.stat().st_mtime_ns), before)

    def test_mcexec_replacement_requires_corrected_hash_size_and_mode(self):
        replacements = self._replacement_map(include_mcexec=True)
        launcher = Path(replacements["bin/mcexec"]["path"])
        corrected_hash = hashlib.sha256(launcher.read_bytes()).hexdigest()
        for field in ("hash", "size", "mode"):
            with self.subTest(field=field):
                expected_hash = corrected_hash if field != "hash" else "0" * 64
                expected_size = launcher.stat().st_size if field != "size" else launcher.stat().st_size + 1
                expected_mode = 0o755 if field != "mode" else 0o700
                with mock.patch.object(S, "MCEEXEC_SHA256", expected_hash), \
                     mock.patch.object(S, "MCEEXEC_SIZE", expected_size):
                    if field == "mode":
                        launcher.chmod(expected_mode)
                        replacements["bin/mcexec"]["mode"] = expected_mode
                    try:
                        with self.assertRaisesRegex(S.StagerError, "exact corrected executable"):
                            S.stage(self.base, self.payload, self.collector,
                                    self.d / ("bad-mcexec-" + field),
                                    cpio=str(self.cpio), gzip=str(self.gzip),
                                    replacements=replacements)
                    finally:
                        launcher.chmod(0o755)
                        replacements["bin/mcexec"]["mode"] = 0o755

    def test_stale_base_still_rejected_without_mcexec_replacement(self):
        (self.base / "bin/mcexec").write_bytes(b"stale-launcher")
        with self.assertRaisesRegex(S.StagerError, "hash mismatch: bin/mcexec"):
            S.stage(self.base, self.payload, self.collector, self.d / "stale-four",
                    cpio=str(self.cpio), gzip=str(self.gzip),
                    replacements=self._replacement_map())

    def test_authenticated_four_artifact_replacements_are_staged_and_recorded(self):
        replacements = self._replacement_map()
        out = self.d / "replacement-out"
        manifest = S.stage(self.base, self.payload, self.collector, out, cpio=str(self.cpio), gzip=str(self.gzip),
                           replacements=replacements)
        self.assertEqual(set(manifest["replacements"]), set(S.REPLACEMENT_PATHS))
        for rel, descriptor in replacements.items():
            target = out / "root" / rel
            self.assertEqual(target.read_bytes(), Path(descriptor["path"]).read_bytes())
            self.assertEqual(manifest["replacements"][rel]["final_sha256"], descriptor["sha256"])
            self.assertEqual(manifest["replacements"][rel]["final_size"], descriptor["size"])
            self.assertEqual(manifest["replacements"][rel]["final_mode"], descriptor["mode"])
        self.assertEqual((out / "root/bin/mcexec").read_bytes(), b"exec")
        self.assertEqual((out / "root/init").stat().st_mode & 0o7777, 0o755)
        self.assertEqual((out / "root/apps/app").stat().st_mode & 0o7777, 0o755)
        self.assertEqual((out / "root/init").stat().st_mtime_ns, 0)
        self.assertEqual((out / "root/apps/app").stat().st_mtime_ns, 0)

    def test_replacement_map_is_exact_and_sources_are_authenticated(self):
        replacements = self._replacement_map()
        with self.assertRaises(S.StagerError):
            S.stage(self.base, self.payload, self.collector, self.d / "missing", cpio=str(self.cpio), gzip=str(self.gzip),
                    replacements={k: v for k, v in replacements.items() if k != "images/mckernel.img"})
        replacements["extra"] = replacements["images/mckernel.img"]
        with self.assertRaises(S.StagerError):
            S.stage(self.base, self.payload, self.collector, self.d / "extra", cpio=str(self.cpio), gzip=str(self.gzip), replacements=replacements)
        replacements = self._replacement_map()
        source = Path(replacements["images/mckernel.img"]["path"])
        source.write_bytes(b"drift")
        with self.assertRaises(S.StagerError):
            S.stage(self.base, self.payload, self.collector, self.d / "drift", cpio=str(self.cpio), gzip=str(self.gzip), replacements=replacements)
        source.unlink(); source.symlink_to(self.payload)
        with self.assertRaises(S.StagerError):
            S.stage(self.base, self.payload, self.collector, self.d / "symlink", cpio=str(self.cpio), gzip=str(self.gzip), replacements=replacements)

    def test_replacement_inode_substitution_and_parent_symlink_are_rejected(self):
        replacements = self._replacement_map()
        rel = "images/mckernel.img"; source = Path(replacements[rel]["path"])
        original = source.read_bytes(); real_copy = S._copy_replacement; changed = [False]
        def substitute(src, target, descriptor):
            if not changed[0] and descriptor["path"] == str(source):
                changed[0] = True
                replacement = source.with_name(source.name + ".new")
                replacement.write_bytes(original); replacement.chmod(0o755)
                os.replace(str(replacement), str(source))
            return real_copy(src, target, descriptor)
        with mock.patch.object(S, "_copy_replacement", side_effect=substitute):
            with self.assertRaises(S.StagerError):
                S.stage(self.base, self.payload, self.collector, self.d / "substituted", cpio=str(self.cpio), gzip=str(self.gzip), replacements=replacements)
        replacements = self._replacement_map()
        source = Path(replacements[rel]["path"]); real_parent = source.parent
        alias_parent = self.d / "alias-parent"; alias_parent.symlink_to(real_parent, target_is_directory=True)
        replacements[rel]["path"] = str(alias_parent / source.name)
        with self.assertRaises(S.StagerError):
            S.stage(self.base, self.payload, self.collector, self.d / "parent-link", cpio=str(self.cpio), gzip=str(self.gzip), replacements=replacements)

    def test_parent_substitution_after_validation_rejected_even_for_same_inode(self):
        for use_symlink in (False, True):
            with self.subTest(use_symlink=use_symlink):
                replacements = self._replacement_map()
                parent = self.d / ("sources-" + str(use_symlink)); parent.mkdir()
                rel = "images/mckernel.img"
                source = Path(replacements[rel]["path"])
                relocated = parent / source.name; source.rename(relocated)
                replacements[rel]["path"] = str(relocated)
                real_copy = S._copy_tree
                def substitute(*args):
                    old_parent = parent.with_name(parent.name + "-original")
                    parent.rename(old_parent)
                    if use_symlink:
                        parent.symlink_to(old_parent, target_is_directory=True)
                    else:
                        parent.mkdir()
                        os.link(old_parent / source.name, relocated)
                    return real_copy(*args)
                out = self.d / ("parent-substituted-" + str(use_symlink))
                with mock.patch.object(S, "_copy_tree", side_effect=substitute):
                    with self.assertRaises(S.StagerError):
                        S.stage(self.base, self.payload, self.collector, out,
                                cpio=str(self.cpio), gzip=str(self.gzip), replacements=replacements)
                self.assertFalse(out.exists())

    def test_final_replacement_drift_before_inventory_is_rejected(self):
        for field in ("content", "size", "mode"):
            with self.subTest(field=field):
                replacements = self._replacement_map()
                real_normalize = S._normalize
                def drift(tree):
                    real_normalize(tree)
                    target = tree / "images/mckernel.img"
                    if field == "content":
                        data = target.read_bytes(); target.write_bytes(bytes([data[0] ^ 1]) + data[1:])
                    elif field == "size": target.write_bytes(b"short")
                    else: target.chmod(0o644)
                out = self.d / ("drift-" + field)
                with mock.patch.object(S, "_normalize", side_effect=drift):
                    with self.assertRaisesRegex(S.StagerError, "final replacement drift"):
                        S.stage(self.base, self.payload, self.collector, out,
                                cpio=str(self.cpio), gzip=str(self.gzip), replacements=replacements)
                self.assertFalse(out.exists())

    @staticmethod
    def _member_offsets(data):
        pos = 0; result = {}
        while True:
            size = int(data[pos + 54:pos + 62], 16)
            namesize = int(data[pos + 94:pos + 102], 16)
            end = pos + 110 + namesize; body = (end + 3) & ~3
            name = bytes(data[pos + 110:end - 1]).decode()
            result[name] = (pos, body, size)
            if name == "TRAILER!!!": return result
            pos = (body + size + 3) & ~3

    def test_same_size_archive_content_mutation_is_rejected_during_stage(self):
        real_fsync = S._fsync
        def corrupt(path):
            if Path(path).name == "initramfs.cpio":
                data = bytearray(Path(path).read_bytes())
                _, body, _ = self._member_offsets(data)["images/mckernel.img"]
                data[body] ^= 1; Path(path).write_bytes(data)
            return real_fsync(path)
        out = self.d / "corrupt-archive"
        with mock.patch.object(S, "_fsync", side_effect=corrupt):
            with self.assertRaisesRegex(S.StagerError, "archive member content mismatch"):
                S.stage(self.base, self.payload, self.collector, out,
                        cpio=str(self.cpio), gzip=str(self.gzip), replacements=self._replacement_map())
        self.assertFalse(out.exists())

    def test_newc_rejects_malformed_metadata_names_padding_and_truncation(self):
        out = self.d / "archive-tests"
        manifest = S.stage(self.base, self.payload, self.collector, out,
                           cpio=str(self.cpio), gzip=str(self.gzip))
        archive = out / "initramfs.cpio"; original = bytearray(archive.read_bytes())
        offsets = self._member_offsets(original)
        pos, body, size = offsets["images/mckernel.img"]
        trailer, _, _ = offsets["TRAILER!!!"]
        mutations = {}
        for field, start, value in (("mode", 14, 0o100644), ("type", 14, 0o120755),
                                    ("uid", 22, 1), ("gid", 30, 1), ("size", 54, size + 1),
                                    ("link", 38, 2), ("huge-name", 94, 0xffffffff),
                                    ("checksum", 102, 1)):
            data = original.copy(); data[pos + start:pos + start + 8] = ("%08x" % value).encode()
            mutations[field] = data
        data = original.copy(); data[pos + 110] = ord("/"); mutations["path"] = data
        data = original.copy(); data[pos + 6] = ord("x"); mutations["hex"] = data
        data = original.copy(); data[body + size] = 1; mutations["alignment"] = data
        data = original.copy(); data[trailer + 54:trailer + 62] = b"00000001"; mutations["trailer"] = data
        mutations["truncated-body"] = original[:body + size - 1]
        mutations["missing-trailer"] = original[:trailer]
        mutations["extra-zero-block"] = original + bytes(512)
        mutations["trailing-data"] = original + b"x"
        for label, data in mutations.items():
            with self.subTest(label=label):
                archive.write_bytes(data)
                with self.assertRaises(S.StagerError):
                    S._archive_members(archive, manifest["staged_inventory"])

if __name__ == "__main__": unittest.main()
