#!/usr/bin/env python3
"""Focused source-stager tests. Author has not imported or run this file.

Root supplies STABILITY_PUBLISHED_HOLD_COMPOSED_SOURCE: the actual flat, fully
composed ORIGINAL mode-2 tree, before published-hold staging. No fake Rust tree
is treated as a native build. Every scenario/source/output remains under TMPDIR.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import traceback
import unittest


EXPECTED_HELPER = "80b6b4fe90a5ac42f187f08e1056867b06776a83102cf59196011790c6b2e563"
REPO = Path(__file__).resolve().parents[2]
CAPTURE = Path(tempfile.mkdtemp(prefix="stability-published-hold-stage-tests-"))
SUBJECT = None
BASE = None


def ident(data):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def journal(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def read_tree(path):
    result = {}
    names = []
    with os.scandir(path) as entries:
        for entry in entries:
            if len(names) >= 128 or not entry.name.endswith(".rs") or not entry.is_file(follow_symlinks=False):
                raise ValueError("expected bounded flat Rust-only real composed source")
            names.append(entry.name)
    for name in sorted(names):
        item = path / name
        descriptor = os.open(str(item), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 8 * 1024 * 1024:
                raise ValueError("expected bounded real composed source member: " + str(item))
            data = stream.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise ValueError("source member grew beyond bound")
        result[name] = data
        if sum(map(len, result.values())) > 64 * 1024 * 1024:
            raise ValueError("composed source exceeds fixed source budget")
    return result


def load_subject():
    global SUBJECT, BASE
    supplied = os.environ.get("STABILITY_PUBLISHED_HOLD_COMPOSED_SOURCE")
    if not supplied:
        raise RuntimeError("required actual original mode-2 COMPOSED_SOURCE was not supplied; do not skip")
    BASE = read_tree(Path(supplied))
    base_copy = CAPTURE / "original-composed-source"
    base_copy.mkdir()
    for name, data in BASE.items():
        (base_copy / name).write_bytes(data)
    helper = REPO / "scripts/tests/prepare_stability_published_hold.py"
    data = helper.read_bytes()
    if ident(data)["sha256"] != EXPECTED_HELPER:
        raise RuntimeError("reviewed stager source hash changed")
    retained = CAPTURE / "subject/scripts/tests/prepare_stability_published_hold.py"
    retained.parent.mkdir(parents=True)
    retained.write_bytes(data)
    # Package paths must stay relative to the retained helper, not the live repo.
    for package in ("stability-owner-phase", "stability-transport-fault", "stability-published-hold-v1"):
        source = REPO / "scripts/tests/fixtures" / package
        destination = retained.parent / "fixtures" / package
        destination.mkdir(parents=True)
        for item in sorted(source.glob("*.rs")):
            if item.is_symlink() or item.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("invalid source fixture")
            (destination / item.name).write_bytes(item.read_bytes())
    (CAPTURE / "test-source.py").write_bytes(Path(__file__).read_bytes())
    journal(CAPTURE / "inputs.json", {"helper": ident(data), "original_composed_source": supplied,
            "source_files": {name: ident(data) for name, data in BASE.items()},
            "scope": "stager metadata tests only; no native compilation or execution"})
    spec = importlib.util.spec_from_file_location("retained_published_hold_stager", retained)
    SUBJECT = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(SUBJECT)
    expected_send = (retained.parent / "fixtures/stability-transport-fault/send.append.rs").read_bytes().replace(b"@MODE@", b"2")
    if BASE.get("smp_application_syscall.rs", b"").count(expected_send) != 1:
        raise RuntimeError("supplied composed source is not original mode2")


class StageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            load_subject()
        except BaseException:
            (CAPTURE / "setup-failure.txt").write_text(traceback.format_exc())
            raise

    def setUp(self):
        self.directory = CAPTURE / self._testMethodName
        self.directory.mkdir()
        self.source = self.directory / "source"
        self.source.mkdir()
        for name, data in BASE.items():
            (self.source / name).write_bytes(data)
        self.output = self.directory / "staged"
        self.mode = "postpublish-notify"
        self.observed = None

    def invoke(self, expected_error=None):
        journal(self.directory / "invocation.json", {"method": "prepare", "source": str(self.source),
                "output": str(self.output), "mode": self.mode, "expected_error_substring": expected_error,
                "compiled": False, "guest_executed": False, "application_acceptance": False})
        try:
            SUBJECT.prepare(self.source, self.output, self.mode)
        except Exception as error:
            self.observed = {"exception": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
            journal(self.directory / "actual.json", self.observed)
            if expected_error is None:
                raise
            self.assertIsInstance(error, (ValueError, OSError, UnicodeError))
            self.assertIn(expected_error, str(error))
            if (self.output / "record.json").exists():
                self.assertEqual(json.loads((self.output / "record.json").read_text())["status"], "FAIL")
            return
        self.observed = {"result": "returned", "record": json.loads((self.output / "record.json").read_text())}
        journal(self.directory / "actual.json", self.observed)
        self.assertIsNone(expected_error, "negative fixture unexpectedly staged successfully")

    def unchanged(self):
        self.assertEqual(read_tree(self.source), BASE)

    def test_positive_mode2_preserves_complete_source(self):
        self.invoke()
        self.unchanged()
        record = self.observed["record"]
        self.assertEqual(record["status"], "PREPARED_NOT_COMPILED_NOT_EXECUTED")
        for field in ("compiled", "executed", "execution_authorized", "application_acceptance",
                      "production_gate_credit", "physical_full_ring_verified", "compiled_stack_bound_verified"):
            self.assertIs(record[field], False)
        self.assertEqual({entry["name"] for entry in record["files"]}, set(BASE))
        self.assertEqual(read_tree(self.output / "originals"), BASE)
        changed = {entry["name"] for entry in record["files"] if entry["original"] != entry["staged"]}
        self.assertEqual(changed, {"stability_phase.rs", "smp_application.rs", "smp_application_syscall.rs", "smp_memory.rs", "smp_service.rs"})
        for entry in record["files"]:
            self.assertIs(entry["inverse_restoration_byte_equal"], True)
            self.assertEqual(entry["original"], ident(BASE[entry["name"]]))
            self.assertEqual(entry["staged"], ident((self.output / "source" / entry["name"]).read_bytes()))

    def test_positive_mode3_uses_exact_other_send_appendix(self):
        path = self.source / "smp_application_syscall.rs"
        old = b"// 2 is replaced with the frozen mode 1..4 by the isolated stager.\nconst STABILITY_FAULT_MODE: u32 = 2;"
        new = b"// 3 is replaced with the frozen mode 1..4 by the isolated stager.\nconst STABILITY_FAULT_MODE: u32 = 3;"
        self.assertEqual(path.read_bytes().count(old), 1)
        path.write_bytes(path.read_bytes().replace(old, new, 1))
        expected = read_tree(self.source)
        self.mode = "recoverable-backpressure"
        self.invoke()
        self.assertEqual(read_tree(self.source), expected)
        self.assertIn(b"pub(crate) const MODE: u32 = 3;", (self.output / "source/stability_phase.rs").read_bytes())
        self.assertEqual(self.observed["record"]["mode_number"], 3)

    def test_mode1_is_rejected_before_output(self):
        self.mode = "prepublish-hard"
        self.invoke("only published modes")
        self.assertFalse(self.output.exists())
        self.unchanged()

    def test_mode4_is_rejected_before_output(self):
        self.mode = "permanent-backpressure"
        self.invoke("only published modes")
        self.assertFalse(self.output.exists())

    def test_wrong_mode_source(self):
        self.mode = "recoverable-backpressure"
        self.invoke("unchanged exact-mode send appendix")
        self.unchanged()

    def test_changed_original_phase_is_retained(self):
        data = BASE["stability_phase.rs"] + b"// changed original\n"
        (self.source / "stability_phase.rs").write_bytes(data)
        self.invoke("exact original phase module")
        self.assertEqual((self.output / "originals/stability_phase.rs").read_bytes(), data)

    def test_duplicate_hook_is_rejected(self):
        target = self.source / "smp_service.rs"
        target.write_bytes(target.read_bytes() + b"        self.verification_accepted_phase();\n")
        self.invoke("one original end-pump")

    def test_crlf_triggering_bytes_are_retained(self):
        data = b"// deliberate\r\n"
        (self.source / "aaa_trigger.rs").write_bytes(data)
        self.invoke("exact LF bytes")
        self.assertEqual((self.output / "originals/aaa_trigger.rs").read_bytes(), data)
        self.assertEqual(json.loads((self.output / "record.json").read_text())["source_inputs"], [{"name": "aaa_trigger.rs", **ident(data)}])

    def test_invalid_utf8_triggering_bytes_are_retained(self):
        data = b"//\xff\n"
        (self.source / "aaa_trigger.rs").write_bytes(data)
        self.invoke("utf-8")
        self.assertEqual((self.output / "originals/aaa_trigger.rs").read_bytes(), data)

    def test_file_byte_limit(self):
        path = self.source / "aaa_large.rs"
        with path.open("wb") as stream:
            stream.truncate(8 * 1024 * 1024 + 1)
        self.invoke("bounded regular file")
        self.assertFalse((self.output / "originals/aaa_large.rs").exists())

    def test_total_budget_retains_one_triggering_file(self):
        for index in range(9):
            (self.source / ("aaa_large_%02d.rs" % index)).write_bytes(b" " * (8 * 1024 * 1024))
        self.invoke("combined source byte budget")
        record = json.loads((self.output / "record.json").read_text())
        self.assertEqual(len(record["source_inputs"]), 9)
        self.assertEqual(sum(entry["size"] for entry in record["source_inputs"]), 72 * 1024 * 1024)
        self.assertEqual((self.output / "originals/aaa_large_08.rs").stat().st_size, 8 * 1024 * 1024)
        self.assertEqual(list((self.output / "source").iterdir()), [])

    def test_member_count(self):
        for index in range(129 - len(BASE)):
            (self.source / ("extra_%03d.rs" % index)).write_bytes(b"// extra\n")
        self.invoke("flat bounded Rust-only")

    def test_symlink_member_rejected(self):
        path = self.source / "aaa_link.rs"
        target = self.source / "stability_phase.rs"
        path.symlink_to(target)
        journal(self.directory / "special-fixture.json", {"type": "symlink", "path": str(path),
                "literal_target": os.readlink(path), "mode": path.lstat().st_mode,
                "retained_in_place": True})
        self.invoke("bounded regular file")
        self.assertTrue(path.is_symlink())
        self.assertEqual(os.readlink(path), str(target))
        self.assertEqual(target.read_bytes(), BASE["stability_phase.rs"])

    def test_fifo_member_rejected_without_read(self):
        path = self.source / "aaa_fifo.rs"
        os.mkfifo(path)
        journal(self.directory / "special-fixture.json", {"type": "fifo", "path": str(path),
                "mode": path.lstat().st_mode, "written_bytes": 0, "retained_in_place": True})
        self.invoke("bounded regular file")
        self.assertTrue(stat.S_ISFIFO(path.lstat().st_mode))

    def test_nonrust_member_rejected(self):
        (self.source / "unexpected.json").write_bytes(b"{}")
        self.invoke("flat bounded Rust-only")

    def test_nested_output_rejected(self):
        self.output = self.source / "nested"
        self.invoke("disjoint trees")
        self.assertFalse(self.output.exists())

    def test_existing_output_is_preserved(self):
        self.output.mkdir()
        marker = self.output / "owned-marker"
        marker.write_bytes(b"preserve existing bytes\n")
        self.invoke("File exists")
        self.assertEqual(marker.read_bytes(), b"preserve existing bytes\n")

    def test_actual_input_drift_is_detected_and_retained(self):
        path = self.source / "stability_observer.rs"
        original_reader = SUBJECT.read_regular
        changed = []
        def racing_reader(candidate):
            data = original_reader(candidate)
            if candidate == path and not changed:
                path.write_bytes(data + b"// controlled source drift\n")
                changed.append(True)
            return data
        SUBJECT.read_regular = racing_reader
        try:
            self.invoke("source changed during staging")
        finally:
            SUBJECT.read_regular = original_reader
        self.assertEqual(changed, [True])
        self.assertEqual((self.output / "originals/stability_observer.rs").read_bytes(), BASE["stability_observer.rs"])
        self.assertEqual(path.read_bytes(), BASE["stability_observer.rs"] + b"// controlled source drift\n")


if __name__ == "__main__":
    print("retained_capture=" + str(CAPTURE), flush=True)
    unittest.main(failfast=True)
