"""Parity checks for detached compatibility metadata and runtime reconstruction."""

import copy
from pathlib import Path
import unittest

from scripts import native_rust_runtime_evidence as evidence
from scripts.tests import test_native_rust_kbuild_link_closure as link_fixtures
from scripts.tests import test_native_rust_runtime_evidence as runtime_fixtures


class NativeRustRuntimeLinkMetadataTests(unittest.TestCase):
    def setUp(self):
        self.fixture = link_fixtures.NativeRustKbuildLinkClosureTests(
            "test_valid_closure_is_exact_canonical_and_credit_forbidden"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.closure = evidence._link_closure_module
        self.raw = {
            name: Path(self.fixture.path(name)).read_bytes()
            for name in evidence.EXPECTED_RAW_RECORD_NAMES
        }
        self.stage_raw = Path(self.fixture.stage_lock_path).read_bytes()

    def test_bound_byte_reconstruction_matches_filesystem_closure(self):
        expected = self.closure.validate_kbuild_link_closure(
            self.fixture.records, stage_lock_path=self.fixture.stage_lock_path
        )
        actual = evidence._validate_kbuild_link_closure_bytes(self.raw, self.stage_raw)
        self.assertEqual(self.closure.canonical_bytes(expected), self.closure.canonical_bytes(actual))
        self.assertEqual(
            self.fixture.stage_lock["compatibility_build_identity"],
            actual["stage_lock"]["compatibility_build_identity"],
        )
        self.assertEqual(
            [self.closure.COMPATIBILITY_BUILD_ID_PATH],
            [item["path"] for item in actual["generated_metadata_inputs"]],
        )
        self.assertTrue(all(item["path"].endswith(".rs") for item in actual["source_closure"]))
        self.assertFalse(any(actual["claims"].values()))

    def test_compatibility_change_preserves_separate_native_source_identity(self):
        original = evidence._validate_kbuild_link_closure_bytes(self.raw, self.stage_raw)
        identity = self.fixture.make_compatibility_identity(
            "v1.2-rc_3+test", "ihk-version-fallback"
        )
        self.fixture.write_stage_identity(identity)
        changed = evidence._validate_kbuild_link_closure_bytes(
            self.raw, Path(self.fixture.stage_lock_path).read_bytes()
        )
        expected = self.closure.validate_kbuild_link_closure(
            self.fixture.records, stage_lock_path=self.fixture.stage_lock_path
        )
        self.assertEqual(expected, changed)
        self.assertEqual(original["source_closure"], changed["source_closure"])
        self.assertEqual(
            original["stage_lock"]["manifest_sha256"],
            changed["stage_lock"]["manifest_sha256"],
        )
        self.assertNotEqual(original["generated_metadata_inputs"], changed["generated_metadata_inputs"])
        self.assertNotEqual(original["stage_lock"]["sha256"], changed["stage_lock"]["sha256"])

    def test_bound_stage_metadata_must_match_payload_and_file_digest(self):
        original = self.fixture.stage_lock
        mutations = []
        for field, value in (
            ("bytes", 7),
            ("value", "a1b2c3e"),
            ("sha256", self.closure._sha256(b"a1b2c3d")),
            ("source_rule_path", "CMakeLists.txt"),
            ("origin", "native-module-source-digest"),
        ):
            changed = copy.deepcopy(original)
            changed["compatibility_build_identity"][field] = value
            mutations.append(changed)
        changed = copy.deepcopy(original)
        del changed["compatibility_build_identity"]
        mutations.append(changed)
        changed = copy.deepcopy(original)
        for item in changed["files"]:
            if item["path"] == self.closure.COMPATIBILITY_BUILD_ID_PATH:
                item["sha256"] = "d" * 64
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["files"] = [
            item for item in changed["files"]
            if item["path"] != self.closure.COMPATIBILITY_BUILD_ID_PATH
        ]
        mutations.append(changed)
        for index, stage_lock in enumerate(mutations):
            with self.subTest(index=index):
                raw = self.closure.canonical_bytes(stage_lock)
                with self.assertRaises(evidence.LinkClosureError):
                    evidence._validate_kbuild_link_closure_bytes(self.raw, raw)

    def test_bound_record_metadata_must_be_exact_and_smp_owned(self):
        metadata = (link_fixtures.SOURCE_PREFIX + self.closure.COMPATIBILITY_BUILD_ID_PATH).encode("ascii")
        smp_name = ".ihk_smp_x86_64.o.cmd"
        for replacement in (b"/tmp/unbound.bin", metadata + b".extra", b""):
            with self.subTest(replacement=replacement):
                raw = dict(self.raw)
                self.assertIn(metadata, raw[smp_name])
                raw[smp_name] = raw[smp_name].replace(metadata, replacement, 1)
                with self.assertRaises(evidence.LinkClosureError):
                    evidence._validate_kbuild_link_closure_bytes(raw, self.stage_raw)
        for name, target in ((".ihk.o.cmd", "ihk.o"), (".mcctrl.o.cmd", "mcctrl.o")):
            with self.subTest(module=name):
                raw = dict(self.raw)
                head = ("deps_drivers/misc/mckernel/{0} := \\\n".format(target)).encode("ascii")
                self.assertIn(head, raw[name])
                raw[name] = raw[name].replace(head, head + b"  " + metadata + b" \\\n", 1)
                with self.assertRaises(evidence.LinkClosureError):
                    evidence._validate_kbuild_link_closure_bytes(raw, self.stage_raw)

    @staticmethod
    def _capture():
        return runtime_fixtures.NativeRustRuntimeEvidenceTests().valid_capture_unsigned()

    @staticmethod
    def _seal(unsigned):
        value = copy.deepcopy(unsigned)
        value["capture_sha256"] = evidence._sha256_bytes(evidence._canonical_bytes(unsigned))
        return value

    def _serial(self, text):
        path = Path(self.fixture.path("buildid-serial.log"))
        path.write_text(text, encoding="utf-8")
        return evidence.validate_serial(path, runtime_fixtures.KERNEL_RELEASE)

    def test_capture_and_serial_keep_compatibility_identity_bound_without_credit(self):
        unsigned = self._capture()
        evidence.validate_capture(self._seal(unsigned))
        serial = self._serial(runtime_fixtures.valid_serial())
        self.assertEqual(unsigned["runtime"]["mcd0"], serial["mcd0"])
        self.assertEqual(
            unsigned["build"]["kbuild_link_closure"]["compatibility_build_identity"]["value"],
            serial["mcd0"]["compatibility_build_id"],
        )
        self.assertEqual(["IHK_DEVICE_GET_BUILDID", "IHK_DEVICE_CREATE_OS", "IHK_DEVICE_DESTROY_OS"], serial["mcd0"]["valid_ioctl_commands"])
        self.assertTrue(serial["mcd0"]["get_buildid_nul_and_guards_observed"])
        self.assertFalse(serial["mcd0"]["runtime_behavior_proven"])
        self.assertFalse(serial["mcd0"]["credit_eligible"])

    def test_resealed_capture_rejects_build_and_runtime_identity_divergence(self):
        for side in ("runtime", "build"):
            with self.subTest(side=side):
                unsigned = self._capture()
                if side == "runtime":
                    unsigned["runtime"]["mcd0"]["compatibility_build_id"] = "a1b2c3e"
                else:
                    identity = unsigned["build"]["kbuild_link_closure"]["compatibility_build_identity"]
                    identity["value"] = "a1b2c3e"
                    identity["sha256"] = self.closure._sha256(b"a1b2c3e\0")
                with self.assertRaisesRegex(evidence.EvidenceError, "mcd0|compatibility"):
                    evidence.validate_capture(self._seal(unsigned))

    def test_resealed_capture_rejects_corrupt_metadata_and_scope_escalation(self):
        for field, value in (
            ("bytes", 7),
            ("bytes", True),
            ("sha256", self.closure._sha256(b"a1b2c3d")),
            ("value", "a1b2c3d\0"),
            ("source_rule_path", "CMakeLists.txt"),
            ("native_source_provenance", True),
        ):
            with self.subTest(metadata_field=field):
                unsigned = self._capture()
                unsigned["build"]["kbuild_link_closure"]["compatibility_build_identity"][field] = value
                with self.assertRaisesRegex(evidence.EvidenceError, "compatibility"):
                    evidence.validate_capture(self._seal(unsigned))
        for field, value in (
            ("get_buildid_command", "0x112900"),
            ("get_buildid_fault_errno", -22),
            ("get_buildid_nul_and_guards_observed", False),
            ("valid_ioctl_commands", ["IHK_DEVICE_GET_BUILDID", "IHK_DEVICE_CREATE_OS"]),
            ("os_operations_reachable", False),
            ("resource_operations_reachable", True),
            ("runtime_behavior_proven", True),
            ("credit_eligible", True),
        ):
            with self.subTest(runtime_field=field):
                unsigned = self._capture()
                unsigned["runtime"]["mcd0"][field] = value
                with self.assertRaisesRegex(evidence.EvidenceError, "mcd0"):
                    evidence.validate_capture(self._seal(unsigned))

    def test_serial_requires_one_safe_compatibility_identity_record(self):
        text = runtime_fixtures.valid_serial()
        marker = evidence.PROTOCOL + " MCD0 BUILDID expected=a1b2c3d\n"
        self.assertEqual(1, text.count(marker))
        mutations = [text.replace(marker, ""), text.replace(marker, marker * 2)]
        for value in ("", "a" * 41, "../a1b2c3d", "a1 b2c3d", "a1b2c3d\0", "a1b2c3d;extra"):
            replacement = evidence.PROTOCOL + " MCD0 BUILDID expected=" + value + "\n"
            mutations.append(text.replace(marker, replacement))
            mutations.append(text.replace(marker, marker + replacement))
        for index, changed in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(evidence.EvidenceError):
                    self._serial(changed)

    def test_serial_requires_buildid_error_markers_and_identity_before_ioctl_results(self):
        text = runtime_fixtures.valid_serial()
        prefix = evidence.PROTOCOL + " MCD0 "
        buildid = prefix + "BUILDID expected=a1b2c3d\n"
        native = prefix + "IOCTL abi=x86_64 buildid=exact_nul expected_errno=EFAULT unknown_errno=EINVAL status=ok\n"
        compat = prefix + "IOCTL abi=i386 buildid=exact_nul expected_errno=EFAULT unknown_errno=EINVAL status=ok\n"
        mutations = []
        for marker in (native, compat):
            self.assertEqual(1, text.count(marker))
            mutations.append(text.replace(marker, ""))
            mutations.append(text.replace(marker, marker.replace("buildid=exact_nul ", "")))
            mutations.append(text.replace(marker, marker.replace("expected_errno=EFAULT", "expected_errno=EINVAL")))
            mutations.append(text.replace(marker, marker.replace("unknown_errno=EINVAL", "unknown_errno=ENOTTY")))
        mutations.append(text.replace(buildid, "").replace(native, native + buildid))
        mutations.append(text.replace(native, "NATIVE_PLACEHOLDER\n").replace(compat, native).replace("NATIVE_PLACEHOLDER\n", compat))
        for index, changed in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(evidence.EvidenceError):
                    self._serial(changed)


if __name__ == "__main__":
    unittest.main()
