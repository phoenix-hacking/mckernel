import importlib.util
import io
import contextlib
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).parents[2]
PACKET = ROOT / "docs/verification/evidence/native-exact-candidate-retention-relocation-8b5056f8-20260930.py"


def load():
    spec = importlib.util.spec_from_file_location("retention_packet", PACKET)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RetentionRelocationPacketTests(unittest.TestCase):
    def test_syntax_and_side_effect_free_default(self):
        subprocess.run(["/usr/bin/python3", "-m", "py_compile", str(PACKET)], check=True)
        before = set(pathlib.Path(tempfile.gettempdir()).glob("native-exact-build-failure-8b5056f8*"))
        result = subprocess.run(["/usr/bin/python3", str(PACKET)], check=True, text=True, capture_output=True)
        after = set(pathlib.Path(tempfile.gettempdir()).glob("native-exact-build-failure-8b5056f8*"))
        self.assertEqual(before, after)
        self.assertIn('"status": "NOT_EXECUTED"', result.stdout)

    def test_frozen_identity_bindings_and_no_source_archive(self):
        text = PACKET.read_text()
        for token in ("8b5056f836ecd3e6916625696750c4dfadbaaf9f", "1831:5111816", "1831:6553623", "1831:6553638", "92b2f3fed0376933f6d703ecfe5245da5a3f19be63aa9712d4713792b5c245e9", "f234ca2cb443f0014f626bbbf1e72991dd1c6a51598c5b675f895354847300d4", "c1ad79ea8b0bba63e41b9a1e34d43b32e008ee97dec357ad6a3295b972bdd719", "dd243ae0f14025bccafeab21654478780f102ddc64668770820d79b5a0379b95", "4f3f3ec96b1366cdbac384ff70d54f0576f99308a33ad7986dc804ca5f8511ee", "ec4768c91f1719647cdf806dbd1a192da119b990", "SOURCE_DEVICE = 1831", "DESTINATION_DEVICE = 66306"):
            self.assertIn(token, text)
        self.assertIn("ARCHIVE_INPUTS = (OUTPUT, EVIDENCE, REQUEST, MANIFEST, PREP_TERMINAL, EXCLUSION, FAILURE)", text)
        self.assertIn('"source_excluded": True', text)
        self.assertNotIn("shutil.rmtree", text)
        self.assertIn("os.O_EXCL", text)
        self.assertIn("os.link(temp, destination)", text)
        self.assertNotIn("shutil.rmtree", text)
        self.assertNotIn("qemu", text.lower())
        self.assertIn("RETENTION_PREPARE_RELEASE", text)

    def test_inventory_rejects_external_hardlinks(self):
        m = load()
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "root"
            root.mkdir()
            (root / "payload").write_bytes(b"payload")
            os.link(root / "payload", root / "alias")
            with self.assertRaisesRegex(ValueError, "external-hardlink"):
                m.inventory(root)

    def test_top_level_file_rejects_external_hardlink(self):
        m = load()
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "input"
            path.write_text("payload")
            os.link(path, pathlib.Path(td) / "outside")
            m.SOURCE_DEVICE = path.stat().st_dev
            with self.assertRaisesRegex(RuntimeError, "external-hardlink"):
                m._validate_input(path)

    def test_inventory_rejects_escape_and_special_file(self):
        m = load()
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "root"
            root.mkdir()
            (root / "escape").symlink_to("/etc/passwd")
            with self.assertRaisesRegex(ValueError, "unsafe-symlink"):
                m.inventory(root)
            (root / "escape").unlink()
            os.mkfifo(root / "fifo")
            with self.assertRaisesRegex(ValueError, "special-file"):
                m.inventory(root)

    def test_archive_rejects_existing_destination_and_temp(self):
        m = load()
        with tempfile.TemporaryDirectory() as td:
            destination = pathlib.Path(td) / "archive.tar"
            destination.write_bytes(b"existing")
            with mock.patch.dict(os.environ, {"RETENTION_PREPARE_RELEASE": "1"}):
                with self.assertRaisesRegex(FileExistsError, "archive-exists"):
                    m.prepare_archive(destination)

    def test_audit_rejects_stale_snapshot(self):
        m = load()
        with mock.patch.object(m, "_expected_members", return_value={"live": "snapshot"}):
            with self.assertRaisesRegex(RuntimeError, "audited-snapshot-changed"):
                m.audit_inputs({"stale": "snapshot"})

    def test_temp_ownership_is_captured_and_required_for_cleanup(self):
        text = PACKET.read_text()
        self.assertIn("os.fstat(fd)", text)
        self.assertIn("temp_identity = (stat_result.st_dev, stat_result.st_ino)", text)
        self.assertIn("(current.st_dev, current.st_ino) == temp_identity", text)

    def test_main_requires_audit_for_prepare_and_keeps_default_read_only(self):
        m = load()
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(m, "audit_inputs") as audit, mock.patch.object(m, "prepare_archive") as prepare:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(m.main(), 0)
            self.assertIn("AUDIT_NOT_REQUESTED", output.getvalue())
            audit.assert_not_called()
            prepare.assert_not_called()
        with mock.patch.dict(os.environ, {"RETENTION_PREPARE_RELEASE": "1"}, clear=True):
            with self.assertRaisesRegex(SystemExit, "PREPARATION_REQUIRES_AUDIT"):
                m.main()

    def test_main_explicit_release_calls_audited_archive(self):
        m = load()
        with mock.patch.dict(os.environ, {"RETENTION_AUDIT": "1", "RETENTION_PREPARE_RELEASE": "1"}, clear=True), mock.patch.object(m, "audit_inputs", return_value={"status": "AUDIT_ONLY"}) as audit, mock.patch.object(m, "prepare_archive", return_value={"archive": "/tmp/exact.tar"}) as prepare:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(m.main(), 0)
            audit.assert_called_once_with()
            prepare.assert_called_once_with()
            self.assertIn("/tmp/exact.tar", output.getvalue())
    def test_archive_requires_release_and_excludes_candidate(self):
        m = load()
        with self.assertRaisesRegex(RuntimeError, "PREPARATION_RELEASE_REQUIRED"):
            m.prepare_archive(pathlib.Path(tempfile.gettempdir()) / "unused-8b5056f8.tar")
        plan = m.relocation_plan()
        self.assertEqual(plan["status"], "NOT_EXECUTED")
        self.assertTrue(plan["preserve_source_until_verified"])
        self.assertTrue(plan["no_replace"])
        self.assertEqual(plan["host_free_floor"], 16 * 1024**3)
        self.assertEqual(plan["emergency_reserve"], 512 * 1024**2)

    def test_archive_fixture_contains_only_declared_inputs(self):
        m = load()
        with tempfile.TemporaryDirectory() as td:
            paths = []
            for name in ("output", "evidence", "request", "manifest", "prep", "exclusion", "failure"):
                path = pathlib.Path(td) / name
                path.write_text('{"candidate_sha":"8b5056f836ecd3e6916625696750c4dfadbaaf9f","execution":{"exit_code":1,"terminal_pid":0,"oom_killed":false,"container_id":"92b2f3fed0376933f6d703ecfe5245da5a3f19be63aa9712d4713792b5c245e9"},"retained_evidence":{"output_identity":"1831:6553623","evidence_identity":"1831:6553638","operational_exclusion_identity":"1831:57597","operational_exclusion_sha256":""}}' if name == "failure" else name)
                paths.append(path)
            for path in paths[:2]:
                path.unlink()
                (path / "nested").mkdir(parents=True)
                (path / "nested" / "payload").write_text(path.name)
            (paths[0] / "receipt.json").write_text("owner")
            (paths[1] / "build").mkdir()
            (paths[1] / "build" / "receipt.json").write_text("build")
            (paths[1] / "build" / "driver.log").write_text("driver")
            original = (m.ARCHIVE_INPUTS, m.SOURCE_DEVICE, m.OUTPUT, m.EVIDENCE, m.OUTPUT_IDENTITY, m.EVIDENCE_IDENTITY, m.EXCLUSION_IDENTITY, m.REFERENCED_EVIDENCE, m.REQUEST, m.MANIFEST, m.PREP_TERMINAL, m.EXCLUSION, m.FAILURE, m.REQUEST_SHA, m.MANIFEST_SHA, m.PREP_TERMINAL_SHA, m.EXCLUSION_SHA, m.FAILURE_SHA)
            m.ARCHIVE_INPUTS = tuple(paths)
            m.SOURCE_DEVICE = paths[0].stat().st_dev
            m.OUTPUT, m.EVIDENCE = paths[:2]
            m.OUTPUT_IDENTITY = f"{paths[0].stat().st_dev}:{paths[0].stat().st_ino}"
            m.EVIDENCE_IDENTITY = f"{paths[1].stat().st_dev}:{paths[1].stat().st_ino}"
            m.EXCLUSION_IDENTITY = f"{paths[5].stat().st_dev}:{paths[5].stat().st_ino}"
            m.REFERENCED_EVIDENCE = {paths[0] / "receipt.json": m.digest(paths[0] / "receipt.json"), paths[1] / "build/receipt.json": m.digest(paths[1] / "build/receipt.json"), paths[1] / "build/driver.log": m.digest(paths[1] / "build/driver.log")}
            m.REQUEST, m.MANIFEST, m.PREP_TERMINAL, m.EXCLUSION = paths[2:6]
            m.FAILURE = paths[-1]
            m.REQUEST_SHA = m.digest(paths[2])
            m.MANIFEST_SHA = m.digest(paths[3])
            m.PREP_TERMINAL_SHA = m.digest(paths[4])
            m.EXCLUSION_SHA = m.digest(paths[5])
            m.FAILURE_SHA = m.digest(paths[-1])
            failure_data = __import__("json").loads(paths[-1].read_text())
            failure_data["retained_evidence"]["output_identity"] = m.OUTPUT_IDENTITY
            failure_data["retained_evidence"]["evidence_identity"] = m.EVIDENCE_IDENTITY
            failure_data["retained_evidence"]["operational_exclusion_identity"] = m.EXCLUSION_IDENTITY
            failure_data["retained_evidence"]["operational_exclusion_sha256"] = m.EXCLUSION_SHA
            paths[-1].write_text(__import__("json").dumps(failure_data))
            m.FAILURE_SHA = m.digest(paths[-1])
            destination = pathlib.Path(td) / "archive.tar"
            try:
                with mock.patch.dict(os.environ, {"RETENTION_PREPARE_RELEASE": "1"}):
                    result = m.prepare_archive(destination)
                self.assertTrue(result["source_excluded"])
                import tarfile
                with tarfile.open(destination) as archive:
                    names = archive.getnames()
                self.assertIn("output/nested/payload", names)
                self.assertIn("evidence/nested/payload", names)
                self.assertIn("retention-manifest.json", names)
                self.assertNotIn("mckernel-exact-candidate-8b5056f8-scratch-6", names)
            finally:
                (m.ARCHIVE_INPUTS, m.SOURCE_DEVICE, m.OUTPUT, m.EVIDENCE,
                 m.OUTPUT_IDENTITY, m.EVIDENCE_IDENTITY, m.EXCLUSION_IDENTITY, m.REFERENCED_EVIDENCE,
                 m.REQUEST, m.MANIFEST, m.PREP_TERMINAL, m.EXCLUSION, m.FAILURE,
                 m.REQUEST_SHA, m.MANIFEST_SHA, m.PREP_TERMINAL_SHA,
                 m.EXCLUSION_SHA, m.FAILURE_SHA) = original


if __name__ == "__main__":
    unittest.main()
