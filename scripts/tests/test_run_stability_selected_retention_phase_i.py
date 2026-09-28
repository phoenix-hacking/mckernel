import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("driver", HERE / "run_stability_selected_retention_phase_i.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def pin(path):
    data = path.read_bytes()
    return {"path": str(path), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class Fixture:
    """Two distinct mode trees and ten archive mappings; disposable only.

    A real subprocess stages sources/originals/diffs, templates and records.
    This small driver fixture grants no production staging acceptance.
    """
    def __init__(self, base, *, tail="", candidate_data=b"fn fixture() {}\n"):
        self.base, self.c, self.d = base, base / "candidate", base / "diagnostics"
        self.python = str(Path(sys.executable).resolve())
        self.files, self.mapping = {}, {}
        archive_path = base / "source.tar"
        with tarfile.open(archive_path, "w") as archive:
            for mode in ("mode2", "mode3"):
                for name in ("adapter.rs", "runner.rs", "source/application_syscall.rs", "source/smp_application_syscall.rs", "source/stability_phase.rs"):
                    rel = mode + "/" + name
                    self.files[rel] = candidate_data
                    member = "retained/" + rel
                    info = tarfile.TarInfo(member)
                    info.size = len(candidate_data)
                    archive.addfile(info, io.BytesIO(candidate_data))
                    self.mapping[rel] = {"archive": str(archive_path), "member": member}
                for name in ("originals/application_syscall.rs", "diffs/application_syscall.rs.diff", "inputs/template.rs", "record.json"):
                    self.files[mode + "/" + name] = b"preserved fixture\n"
        source = base / "source.json"
        source.write_text(json.dumps({k: v.hex() for k, v in self.files.items()}))
        stager = base / "stager.py"
        stager.write_text("import json, sys\nfrom pathlib import Path\nr = Path(sys.argv[1])\n"
                          "for name, data in json.loads(Path(sys.argv[2]).read_text()).items():\n"
                          "    p = r / name\n    p.parent.mkdir(parents=True, exist_ok=True)\n"
                          "    p.write_bytes(bytes.fromhex(data))\n"
                          "print('PREPARED_NOT_COMPILED_NOT_EXECUTED')\n" + tail + "\n")
        self.command = [self.python, str(stager), str(self.c), str(source)]
        inputs = [pin(Path(self.python)), pin(stager), pin(source), pin(archive_path)]
        self.contract = {
            "command_argv": self.command, "cwd": str(base),
            "candidate_root": str(self.c), "diagnostics_root": str(self.d),
            "authenticated_inputs": inputs, "required_inputs": [i["path"] for i in inputs],
            "command_inputs": [str(stager), str(source)], "archive_mapping": self.mapping,
            "expected_membership": {k: {"size": len(v), "sha256": hashlib.sha256(v).hexdigest()} for k, v in self.files.items()},
            "expected_directories": sorted({str(p) for name in self.files for p in Path(name).parents if str(p) != "."}),
            "validator_members": sorted(self.mapping), "timeout_seconds": 5,
        }
        self.save()

    def save(self):
        self.manifest = self.base / "manifest.json"
        self.manifest.write_text(json.dumps(self.contract))
        self.reviewed = {"manifest": pin(self.manifest)}

    def run(self, **kwargs):
        return driver.run_phase_i(self.c, self.d, self.command, cwd=self.base, reviewed=self.reviewed, **kwargs)

    def records(self, name):
        return [json.loads(line) for line in (self.d / name).read_text().splitlines()]

    def failure(self, root=None):
        lines = ((root or self.c) / "phase-i-failure.txt").read_text().splitlines()
        if len(lines) != 6:
            raise AssertionError(lines)
        return dict(line.split("=", 1) for line in lines)


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def test_real_two_mode_positive_candidate_and_five_controls(self):
        f = Fixture(self.base)
        result = f.run()
        self.assertEqual(result["status"], "PASS_PHASE_I")
        self.assertEqual(len(result["candidate"]["files"]), 18)
        self.assertEqual(result["controls"], 5)
        installed = f.records("installation.json")[1]
        self.assertEqual(installed["argv"], f.command)
        self.assertEqual(installed["returncode"], 0)
        self.assertEqual(bytes.fromhex(installed["stdout"]["bytes_hex"]), b"PREPARED_NOT_COMPILED_NOT_EXECUTED\n")
        validation = f.records("validation.json")
        self.assertEqual(validation[0]["returncode"], 0)
        self.assertEqual(validation[0]["stdout"]["bytes_hex"], b"PASS_WHITESPACE\n".hex())
        self.assertEqual(validation[0]["stderr"]["size"], 0)
        self.assertEqual(len(validation[0]["argv"][4:]), 10)
        controls = f.records("controls.json")
        self.assertEqual(len(controls), 5)
        for record, (name, payload, prefix) in zip(controls, driver.CONTROL_CASES):
            self.assertEqual(record["returncode"], 1)
            self.assertEqual(record["stdout"]["size"], 0)
            self.assertEqual(bytes.fromhex(record["stderr"]["bytes_hex"]), (prefix + ":" + str(f.d / name) + "\n").encode())
            self.assertEqual((f.d / name).read_bytes(), payload)
        self.assertFalse((f.c / "phase-i-failure.txt").exists())

    def test_validator_self_tests_execute_and_detect_corruption(self):
        path = self.base / "valid"
        path.write_bytes(b"x\n\ny\n")
        cp = subprocess.run([sys.executable, "-B", "-c", driver.VALIDATOR, str(path)], capture_output=True)
        self.assertEqual((cp.returncode, cp.stdout, cp.stderr), (0, b"PASS_WHITESPACE\n", b""))
        bad = driver.VALIDATOR.replace('assert check(b"x\\ny\\n") is None', 'assert check(b"x\\ny\\n") == "CR"')
        cp = subprocess.run([sys.executable, "-B", "-c", bad, str(path)], capture_output=True)
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn(b"AssertionError", cp.stderr)
        cp = subprocess.run([sys.executable, "-B", "-O", "-c", driver.VALIDATOR, str(path)], capture_output=True)
        self.assertEqual((cp.returncode, cp.stdout, cp.stderr), (1, b"", b"SELF_TESTS_DISABLED\n"))

    def test_bad_whitespace_authenticates_but_actual_validator_rejects(self):
        f = Fixture(self.base, candidate_data=b"fn fixture() {} \n")
        with self.assertRaises(driver.PhaseIFailure):
            f.run()
        self.assertEqual(f.failure()["stage"], "candidate-validator")
        record = f.records("validation.json")[0]
        self.assertEqual(record["returncode"], 1)
        self.assertTrue(bytes.fromhex(record["stderr"]["bytes_hex"]).startswith(b"TRAILING:"))
        self.assertFalse((f.d / "controls.json").exists())

    def test_mandatory_manifest_mapping_and_closure(self):
        for defect in ("manifest", "mapping", "inputs", "closure", "command-input", "validator", "directory"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                f = Fixture(Path(tmp))
                if defect == "mapping":
                    f.contract["archive_mapping"] = {}
                elif defect == "inputs":
                    f.contract["authenticated_inputs"] = []
                elif defect == "closure":
                    f.contract["required_inputs"].append(str(f.base / "omitted"))
                elif defect == "command-input":
                    f.contract["command_inputs"] = []
                elif defect == "validator":
                    f.contract["validator_members"] = []
                elif defect == "directory":
                    f.contract["expected_directories"].append("unprescribed")
                f.save()
                if defect == "manifest":
                    f.reviewed["manifest"]["sha256"] = "0" * 64
                with self.assertRaises(ValueError):
                    f.run()
                self.assertFalse(f.c.exists())
                self.assertFalse(f.d.exists())

    def test_archive_mapping_wrong_bytes(self):
        f = Fixture(self.base)
        first = next(iter(f.contract["expected_membership"]))
        f.contract["expected_membership"][first]["sha256"] = "0" * 64
        f.save()
        with self.assertRaisesRegex(ValueError, "mapping bytes"):
            f.run()
        self.assertFalse(f.c.exists())

    def test_malformed_archive_mapping_rejects_missing_duplicate_and_link_members(self):
        for kind in ("missing", "duplicate", "link", "unbound"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                f = Fixture(Path(tmp))
                mapping = f.contract["archive_mapping"]["mode2/adapter.rs"]
                if kind == "missing":
                    mapping["member"] = "retained/missing.rs"
                elif kind == "unbound":
                    mapping["archive"] = str(f.base / "unbound.tar")
                else:
                    archive_path = Path(mapping["archive"])
                    with tarfile.open(archive_path, "a") as archive:
                        member = tarfile.TarInfo(mapping["member"])
                        if kind == "link":
                            member.name = "retained/link.rs"
                            member.type = tarfile.SYMTYPE
                            member.linkname = mapping["member"]
                            mapping["member"] = member.name
                        archive.addfile(member, io.BytesIO(b""))
                    for item in f.contract["authenticated_inputs"]:
                        if item["path"] == str(archive_path):
                            item.update(pin(archive_path))
                f.save()
                with self.assertRaises(ValueError):
                    f.run()
                self.assertFalse(f.c.exists())

    def test_duplicate_manifest_key_and_changed_input_are_rejected(self):
        f = Fixture(self.base)
        raw = f.manifest.read_text()
        f.manifest.write_text('{"timeout_seconds":5,' + raw[1:])
        f.reviewed = {"manifest": pin(f.manifest)}
        with self.assertRaisesRegex(ValueError, "duplicate manifest"):
            f.run()
        f.save()
        (f.base / "source.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "input hash/size"):
            f.run()
        self.assertFalse(f.c.exists())

    def test_missing_review_and_disabled_controls_rejected(self):
        with self.assertRaises(ValueError):
            driver.run_phase_i(self.base / "c", self.base / "d", ["true"])
        f = Fixture(self.base)
        with self.assertRaises(ValueError):
            f.run(controls=False)
        self.assertFalse(f.c.exists())

    def test_unprescribed_directory_and_outside_hardlink(self):
        for tail in ("(r / 'extra-directory').mkdir()", "import os\nos.link(r / 'mode2/adapter.rs', r.parent / 'outside-link')"):
            with self.subTest(tail=tail), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                f = Fixture(Path(tmp), tail=tail)
                with self.assertRaises(driver.PhaseIFailure):
                    f.run()
                self.assertEqual(f.failure()["stage"], "membership")

    def test_missing_extra_symlink_and_changed_candidate_file(self):
        for tail in ("(r / 'mode2/adapter.rs').unlink()", "(r / 'extra.rs').write_bytes(b'extra\\n')",
                     "(r / 'mode2/adapter.rs').write_bytes(b'wrong\\n')",
                     "(r / 'mode2/adapter.rs').unlink()\n(r / 'mode2/adapter.rs').symlink_to(r / 'mode3/adapter.rs')"):
            with self.subTest(tail=tail), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                f = Fixture(Path(tmp), tail=tail)
                with self.assertRaises(driver.PhaseIFailure):
                    f.run()
                self.assertEqual(f.failure()["stage"], "membership")

    def test_candidate_and_diagnostic_root_renames_to_symlinks(self):
        for which in ("candidate", "diagnostics"):
            with self.subTest(which=which), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                base = Path(tmp)
                outside = base / "outside"
                outside.mkdir()
                tail = f"target = Path({str(base / which)!r})\ntarget.rename(target.with_name('retained'))\ntarget.symlink_to({str(outside)!r}, target_is_directory=True)"
                f = Fixture(base, tail=tail)
                with self.assertRaises(driver.PhaseIFailure):
                    f.run()
                self.assertEqual(list(outside.iterdir()), [])
                failure = f.failure(base / "retained" if which == "candidate" else None)
                self.assertIn("root identity", failure["observed"])
                diagnostic = base / "retained" if which == "diagnostics" else f.d
                rows = [json.loads(x) for x in (diagnostic / "installation.json").read_text().splitlines()]
                self.assertEqual(rows[1]["returncode"], 0)

    def test_diagnostic_symlink_directory_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        f = Fixture(self.base, tail=f"Path({str(self.base / 'diagnostics' / 'foreign')!r}).symlink_to({str(outside)!r}, target_is_directory=True)")
        with self.assertRaises(driver.PhaseIFailure):
            f.run()
        self.assertEqual(f.failure()["stage"], "membership")
        self.assertEqual(list(outside.iterdir()), [])

    def test_first_process_failure_survives_bad_membership(self):
        f = Fixture(self.base, tail="(r / 'extra').mkdir()\nraise SystemExit(7)")
        with self.assertRaises(driver.PhaseIFailure):
            f.run()
        failure = f.failure()
        self.assertEqual(failure["stage"], "installation-process")
        self.assertIn('"returncode": 7', failure["observed"])
        self.assertEqual(f.records("installation.json")[1]["returncode"], 7)

    def test_failed_child_still_checks_root_identity(self):
        f = Fixture(self.base, tail="r.rename(r.with_name('retained'))\nr.mkdir()\nraise SystemExit(9)")
        with self.assertRaises(driver.PhaseIFailure) as raised:
            f.run()
        self.assertIn('"returncode": 9', str(raised.exception))
        self.assertIn("post-child authentication", str(raised.exception))
        self.assertEqual(f.failure(self.base / "retained")["stage"], "installation-process")

    def test_input_and_prior_evidence_changes_after_child_are_detected(self):
        for tail in ("Path(sys.argv[2]).write_bytes(b'changed')",
                     f"Path({str(self.base / 'diagnostics' / 'authentication.json')!r}).write_bytes(b'changed')",
                     f"Path({str(self.base / 'diagnostics' / 'installation.json')!r}).write_bytes(b'changed')"):
            # Each scenario needs its own literal diagnostic paths.
            with self.subTest(tail=tail), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                rewritten = tail.replace(str(self.base / 'diagnostics'), str(Path(tmp) / 'diagnostics'))
                f = Fixture(Path(tmp), tail=rewritten)
                with self.assertRaises(driver.PhaseIFailure):
                    f.run()
                self.assertNotIn("PASS_PHASE_I", f.failure()["observed"])

    def test_control_result_status_stdout_stderr_are_exact(self):
        real = subprocess.run
        for field, value in (("returncode", 0), ("stdout", b"unexpected"), ("stderr", b"wrong rejection")):
            with self.subTest(field=field), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                f = Fixture(Path(tmp))
                def launch(argv, **kw):
                    cp = real(argv, **kw)
                    if argv[-1] == str(f.d / "cr.bin"):
                        setattr(cp, field, value)
                    return cp
                with mock.patch.object(driver.subprocess, "run", side_effect=launch):
                    with self.assertRaises(driver.PhaseIFailure):
                        f.run()
                self.assertEqual(f.failure()["stage"], "control-cr.bin")
                self.assertEqual(len(f.records("controls.json")), 1)

    def test_each_control_launch_failure_is_immediately_journaled(self):
        real = subprocess.run
        for index, (name, _, _) in enumerate(driver.CONTROL_CASES):
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                f = Fixture(Path(tmp))
                def launch(argv, **kw):
                    if argv[-1] == str(f.d / name):
                        raise OSError("launch failure\nwith newline")
                    return real(argv, **kw)
                with mock.patch.object(driver.subprocess, "run", side_effect=launch):
                    with self.assertRaises(driver.PhaseIFailure):
                        f.run()
                rows = f.records("controls.json")
                self.assertEqual(len(rows), index + 1)
                self.assertIn("launch_error", rows[-1])
                self.assertEqual(f.failure()["stage"], "control-" + name)

    def test_installation_and_validator_launch_failures(self):
        real = subprocess.run
        for target in ("installation-process", "candidate-validator"):
            with self.subTest(target=target), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                f = Fixture(Path(tmp))
                def launch(argv, **kw):
                    if (argv == f.command) == (target == "installation-process"):
                        raise OSError("cannot launch")
                    return real(argv, **kw)
                with mock.patch.object(driver.subprocess, "run", side_effect=launch):
                    with self.assertRaises(driver.PhaseIFailure):
                        f.run()
                self.assertEqual(f.failure()["stage"], target)
                log = "installation.json" if target == "installation-process" else "validation.json"
                self.assertIn("launch_error", f.records(log)[-1])

    def test_stream_collision_is_not_overwritten_and_process_is_retained(self):
        f = Fixture(self.base, tail=f"Path({str(self.base / 'diagnostics' / 'mode2-stage.stdout')!r}).write_bytes(b'collision')")
        with self.assertRaises(driver.PhaseIFailure):
            f.run()
        self.assertEqual((f.d / "mode2-stage.stdout").read_bytes(), b"collision")
        self.assertEqual(f.failure()["stage"], "installation-streams")
        self.assertEqual(f.records("installation.json")[1]["returncode"], 0)

    def test_authentication_write_failure_retains_first_failure(self):
        f = Fixture(self.base)
        with mock.patch.object(driver, "_json_at", side_effect=OSError("authentication write failed")):
            with self.assertRaises(driver.PhaseIFailure):
                f.run()
        self.assertEqual(f.failure()["stage"], "authentication")
        self.assertFalse((f.c / "mode2").exists())

    def test_each_journal_write_failure_retains_process_and_prior_records(self):
        real = driver.Journal.append
        for event in ("installation-process", "candidate-validator", "control-cr.bin", "control-extra-blank.bin", "complete"):
            with self.subTest(event=event), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                f = Fixture(Path(tmp))
                def append(journal, record):
                    if record["event"] == event:
                        raise OSError("journal write failed")
                    return real(journal, record)
                with mock.patch.object(driver.Journal, "append", append):
                    with self.assertRaises(driver.PhaseIFailure):
                        f.run()
                failure = f.failure()
                self.assertIn("journal write failed", failure["observed"])
                if event != "complete":
                    self.assertIn('"returncode":', failure["observed"])
                if event == "control-extra-blank.bin":
                    self.assertEqual(len(f.records("controls.json")), 4)

    def test_journal_creation_and_control_file_write_failures(self):
        for name in ("installation.json", "validation.json", "controls.json", "cr.bin", "extra-blank.bin"):
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                f = Fixture(Path(tmp))
                real = os.open
                def opening(path, flags, *args, **kw):
                    if path == name and flags & os.O_CREAT:
                        raise OSError("create evidence failed")
                    return real(path, flags, *args, **kw)
                with mock.patch.object(driver.os, "open", side_effect=opening):
                    with self.assertRaises(driver.PhaseIFailure):
                        f.run()
                self.assertIn("create evidence failed", f.failure()["observed"])

    def test_failed_finalization_close_preserves_first_failure(self):
        real = driver.Journal.close
        for fail_child in (False, True):
            with self.subTest(fail_child=fail_child), tempfile.TemporaryDirectory(dir=self.base) as tmp:
                f = Fixture(Path(tmp), tail="raise SystemExit(29)" if fail_child else "")
                def close(log):
                    real(log)
                    raise OSError("close fault")
                with mock.patch.object(driver.Journal, "close", close):
                    with self.assertRaises(driver.PhaseIFailure) as raised:
                        f.run()
                self.assertIn("close fault", str(raised.exception))
                if fail_child:
                    self.assertIn('"returncode": 29', str(raised.exception))
                    self.assertEqual(f.failure()["stage"], "installation-process")
                else:
                    self.assertEqual(f.failure()["stage"], "finalization")

    def test_nonzero_and_result_write_failure_keep_original_exit(self):
        f = Fixture(self.base, tail="raise SystemExit(19)")
        real = driver.Journal.append
        def append(journal, record):
            if record["event"] == "installation-process":
                raise OSError("disk failure")
            return real(journal, record)
        with mock.patch.object(driver.Journal, "append", append):
            with self.assertRaises(driver.PhaseIFailure) as raised:
                f.run()
        self.assertIn('"returncode": 19', str(raised.exception))
        self.assertIn('"returncode": 19', f.failure()["observed"])
        self.assertIn("disk failure", f.failure()["observed"])

    def test_failure_persistence_failure_is_exposed_without_erasing_original(self):
        f = Fixture(self.base, tail="raise SystemExit(23)")
        with mock.patch.object(driver, "_failure", side_effect=OSError("failure evidence unavailable")):
            with self.assertRaises(driver.PhaseIFailure) as raised:
                f.run()
        self.assertIn('"returncode": 23', str(raised.exception))
        self.assertIn("failure evidence unavailable", str(raised.exception))
        self.assertEqual(f.records("installation.json")[1]["returncode"], 23)

    def test_existing_diagnostic_root_leaves_both_roots_untouched(self):
        f = Fixture(self.base)
        f.d.mkdir()
        (f.d / "sentinel").write_bytes(b"untouched")
        with self.assertRaises(ValueError):
            f.run()
        self.assertFalse(f.c.exists())
        self.assertEqual((f.d / "sentinel").read_bytes(), b"untouched")

    def test_short_writes_are_completed(self):
        f = Fixture(self.base)
        real = os.write
        with mock.patch.object(driver.os, "write", side_effect=lambda fd, data: real(fd, data[:7])):
            self.assertEqual(f.run()["status"], "PASS_PHASE_I")
        self.assertEqual(len(f.records("controls.json")), 5)

    def test_zero_write_reports_failure_and_persistence_error(self):
        f = Fixture(self.base)
        with mock.patch.object(driver.os, "write", return_value=0):
            with self.assertRaises(driver.PhaseIFailure) as raised:
                f.run()
        self.assertIn("short write", str(raised.exception))
        self.assertIn("failure-record", str(raised.exception))

    def test_all_failure_fields_are_newline_free(self):
        fd = os.open(str(self.base), driver.DIR_FLAGS)
        try:
            driver._failure(fd, "mode2\nattack", "stage\r\nattack", "expected\nattack", "observed\nattack\u2028more\x85more")
        finally:
            os.close(fd)
        lines = (self.base / "phase-i-failure.txt").read_text().splitlines()
        self.assertEqual(len(lines), 6)
        self.assertEqual(lines[1], "mode=global")
        self.assertIn("stage=stage\\r\\nattack", lines)

    def test_root_parent_fsync_failure_routes_to_first_failure(self):
        f = Fixture(self.base)
        real = os.fsync
        calls = 0
        def fsync(fd):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("parent fsync failed")
            return real(fd)
        with mock.patch.object(driver.os, "fsync", side_effect=fsync):
            with self.assertRaises(driver.PhaseIFailure):
                f.run()
        self.assertEqual(f.failure()["stage"], "root-create")
        self.assertFalse(f.d.exists())


if __name__ == "__main__":
    unittest.main()
