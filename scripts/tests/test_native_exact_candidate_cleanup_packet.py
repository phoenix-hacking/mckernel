"""Pure source-contract checks for the unreleased exact-candidate cleanup."""

import hashlib
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
EVIDENCE = ROOT / "docs/verification/evidence"
PACKET = EVIDENCE / "native-exact-candidate-cleanup-execution-68cf089a-1.sh"
DELETER = EVIDENCE / "native-exact-candidate-delete-68cf089a-1.py"
BASIS = EVIDENCE / "native-exact-candidate-cleanup-release-basis-68cf089a-1.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_helper():
    spec = importlib.util.spec_from_file_location("cleanup_deleter_contract", DELETER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CleanupPacketContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell = PACKET.read_text(encoding="utf-8")
        cls.helper = DELETER.read_text(encoding="utf-8")
        cls.basis = json.loads(BASIS.read_text(encoding="utf-8"))

    def test_state_is_exact_draft_or_normalized_release(self):
        self.assertEqual(self.basis["schema_version"], 3)
        if self.basis["status"] == "DRAFT_NOT_RELEASED":
            self.assertEqual(self.basis["source_checkpoint"], "UNSET_REQUIRES_TEMPLATE_CHECKPOINT")
            self.assertIn("FINAL_DELETER_SHA=__REPLACE_WITH_FINAL_DELETER_SHA256__", self.shell)
            self.assertIn("RELEASE_SHA=__REPLACE_WITH_RELEASE_SHA256__", self.shell)
            self.assertEqual(self.basis["template_deleter"]["sha256"], digest(DELETER))
            self.assertEqual(self.basis["template_packet"]["sha256"], digest(PACKET))
        else:
            self.assertEqual(self.basis["status"], "PASS_ONE_SHOT_CLEANUP")
            self.assertRegex(self.basis["source_checkpoint"], r"^[0-9a-f]{40}$")
            helper_match = re.findall(r"(?m)^RELEASE_SHA = '([0-9a-f]{64})'$", self.helper)
            packet_match = re.findall(
                r"(?m)^FINAL_DELETER_SHA=([0-9a-f]{64}); RELEASE_SHA=([0-9a-f]{64})$",
                self.shell)
            self.assertEqual(len(helper_match), 1)
            self.assertEqual(len(packet_match), 1)
            self.assertEqual(helper_match[0], digest(BASIS))
            self.assertEqual(packet_match[0], (digest(DELETER), digest(BASIS)))
            helper_template = re.sub(
                r"(?m)^RELEASE_SHA = '[0-9a-f]{64}'$",
                "RELEASE_SHA = 'UNSET-REQUIRES-INDEPENDENT-RELEASE-SHA256'", self.helper)
            packet_template = re.sub(
                r"(?m)^FINAL_DELETER_SHA=[0-9a-f]{64}; RELEASE_SHA=[0-9a-f]{64}$",
                "FINAL_DELETER_SHA=__REPLACE_WITH_FINAL_DELETER_SHA256__; RELEASE_SHA=__REPLACE_WITH_RELEASE_SHA256__",
                self.shell)
            self.assertEqual(hashlib.sha256(helper_template.encode()).hexdigest(),
                             self.basis["template_deleter"]["sha256"])
            self.assertEqual(hashlib.sha256(packet_template.encode()).hexdigest(),
                             self.basis["template_packet"]["sha256"])

    def test_basis_is_acyclic_and_binds_full_scope(self):
        for prohibited in ("final_deleter_sha256", "final_packet_sha256",
                           "release_record_sha256", "preflight_sha256"):
            self.assertNotIn(prohibited, self.basis)
        self.assertIs(self.basis["one_shot"], True)
        self.assertIs(self.basis["retry"], False)
        self.assertIs(self.basis["rollback"], False)
        self.assertIs(self.basis["acceptance_credit"], False)
        self.assertEqual(self.basis["candidate"]["tree_inode_count"], 10462)
        self.assertEqual(self.basis["backup"]["tree_inode_count"], 87)
        self.assertEqual(set(self.basis["artifacts"]), {
            "inputs", "request", "preparation_archive", "preparation_record",
            "retention_capsule", "retention_record"})

    def test_helper_strictly_validates_release_and_receipt(self):
        for token in ("validate_release", "reject_duplicate_pairs", "require_exact_keys",
                      "final helper differs from reviewed template",
                      "final packet differs from reviewed template",
                      "type(receipt.get(key)) is not type(value)",
                      "preflight root field types mismatch"):
            self.assertIn(token, self.helper)
        for field in ("source_checkpoint", "packet_sha256", "candidate_git_clean",
                      "ihk_git_clean", "retention_capsule_sha256",
                      "preparation_archive_sha256", "release_record_sha256"):
            self.assertIn("'{}'".format(field), self.helper)
        self.assertLess(self.helper.index("release = validate_release()"),
                        self.helper.index("journal = Journal()"))
        self.assertIn("release_bytes = exact_regular_bytes(RELEASE)", self.helper)
        self.assertIn("signal.signal(signal.SIGTERM, request_termination)", self.helper)

    def test_packet_uses_direct_hashes_and_correct_artifact_paths(self):
        self.assertNotIn('${!p}', self.shell)
        for variable in ("INVENTORY", "INV_ARCHIVE", "RET", "PREP", "PREP_RECORD",
                         "RET_RECORD", "INPUTS", "REQUEST"):
            self.assertRegex(self.shell, r'check_hash "\$%s" "\$%s_SHA"' %
                             (variable, variable if variable != "INV_ARCHIVE" else "INV_ARCHIVE"))
        self.assertIn("docs/verification/stability-native-exact-prepared-candidate-retention-20260929-1.json", self.shell)
        self.assertNotIn("docs/verification/evidence/stability-native-exact-prepared-candidate-retention-20260929-1.json", self.shell)

    def test_capacity_git_process_and_zero_container_contracts(self):
        for floor in ("16 * 1024 * 1024 * 1024", "12 * 1024 * 1024 * 1024",
                      "4 * 1024 * 1024 * 1024"):
            self.assertIn(floor, self.shell)
        for token in ("GIT_OPTIONAL_LOCKS=0", "core.fsmonitor=false",
                      "core.hooksPath=/dev/null", "--ignored", "qemu-system(?:-[^ /]+)?"):
            self.assertIn(token, self.shell)
        self.assertIn("docker-inspect.jsonl", self.shell)
        self.assertRegex(self.shell, r"\(sys\.argv\[3\],b''\)")

    def test_release_and_preflight_are_exclusive_durable_and_exact(self):
        self.assertGreaterEqual(self.shell.count("os.O_EXCL"), 4)
        self.assertGreaterEqual(self.shell.count("os.fsync"), 6)
        self.assertIn("Copy the reviewed release bytes exactly", self.shell)
        self.assertNotIn("json.dumps(json.load(open(sys.argv[1]))", self.shell)
        for field in ("schema", "boot_id", "observer_sha256", "deleter_sha256",
                      "inventory_sha256", "retention_capsule_sha256",
                      "preparation_archive_sha256", "preparation_record_sha256",
                      "retention_record_sha256", "request_sha256", "inputs_sha256",
                      "release_record_path", "release_record_sha256", "candidate_sha",
                      "ihk_sha", "no_active_docker_binds", "source_checkpoint",
                      "packet_sha256", "candidate_git_clean", "ihk_git_clean",
                      "admission_started_boottime_ns", "observed_at_utc", "roots"):
            self.assertIn("'{}'".format(field), self.shell)
        self.assertIn("now-started>300*1_000_000_000", self.shell)

    def test_single_sanitized_attempt_and_terminal_checks(self):
        invocation = re.findall(r'/usr/bin/python3 -B "\$DELETER"', self.shell)
        self.assertEqual(len(invocation), 1)
        self.assertIn("sudo -A /usr/bin/env -i", self.shell)
        self.assertIn("/usr/bin/setsid /usr/bin/timeout", self.shell)
        for token in ("OUT=$E/deleter.stdout", "ERR=$E/deleter.stderr",
                      "RC=$E/deleter.rc", '[[ "$rc" -eq 0 ]]',
                      '! -e "$QC"', '! -e "$QB"', '! -e "$LEASE"',
                      "missing-success-journal", "targets_absent"):
            self.assertIn(token, self.shell)
        self.assertIn("Exactly one attempt", self.shell)
        self.assertNotRegex(self.shell, r"\b(retry|rerun)\b")

    def released_fixture(self, directory, mutation=None):
        release = json.loads(json.dumps(self.basis))
        release["status"] = "PASS_ONE_SHOT_CLEANUP"
        release["source_checkpoint"] = "1" * 40
        if mutation is not None:
            mutation(release)
        release_bytes = (json.dumps(release, sort_keys=True, separators=(",", ":")) + "\n").encode()
        release_hash = hashlib.sha256(release_bytes).hexdigest()
        helper_bytes = DELETER.read_bytes().replace(
            b"RELEASE_SHA = 'UNSET-REQUIRES-INDEPENDENT-RELEASE-SHA256'",
            ("RELEASE_SHA = '" + release_hash + "'").encode())
        helper_hash = hashlib.sha256(helper_bytes).hexdigest()
        packet_bytes, count = re.subn(
            rb"(?m)^FINAL_DELETER_SHA=__REPLACE_WITH_FINAL_DELETER_SHA256__; RELEASE_SHA=__REPLACE_WITH_RELEASE_SHA256__$",
            ("FINAL_DELETER_SHA=" + helper_hash + "; RELEASE_SHA=" + release_hash).encode(),
            PACKET.read_bytes())
        self.assertEqual(count, 1)
        release_path = directory / "release.json"
        helper_path = directory / "deleter.py"
        packet_path = directory / "packet.sh"
        release_path.write_bytes(release_bytes)
        helper_path.write_bytes(helper_bytes)
        packet_path.write_bytes(packet_bytes)
        module = load_helper()
        module.RELEASE = release_path
        module.RELEASE_SHA = release_hash
        module.PACKET = packet_path
        module.__file__ = str(helper_path)
        return module, release

    def test_validate_release_accepts_only_the_normalized_final_join(self):
        with tempfile.TemporaryDirectory() as raw:
            module, release = self.released_fixture(Path(raw))
            self.assertEqual(module.validate_release(), release)

    def test_validate_release_rejects_boolean_integer_alias(self):
        with tempfile.TemporaryDirectory() as raw:
            module, _ = self.released_fixture(Path(raw), lambda value: value.__setitem__("retry", 0))
            with self.assertRaisesRegex(RuntimeError, "release scalar contract mismatch"):
                module.validate_release()

    def test_validate_release_rejects_duplicate_keys_from_same_bytes(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            release_bytes = b'{"schema_version":3,"schema_version":3}\n'
            release_path = directory / "release.json"
            release_path.write_bytes(release_bytes)
            module = load_helper()
            module.RELEASE = release_path
            module.RELEASE_SHA = hashlib.sha256(release_bytes).hexdigest()
            with self.assertRaisesRegex(RuntimeError, "duplicate JSON key"):
                module.validate_release()


if __name__ == "__main__":
    unittest.main()
