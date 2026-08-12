import ast
import json
import os
import sys
import unittest
from unittest import mock


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import x86_64_shared_abi as abi


def read_bytes(relative_path):
    with open(os.path.join(REPO_ROOT, relative_path), "rb") as stream:
        return stream.read()


class X8664SharedAbiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rust = read_bytes(abi.RUST_PATH)
        cls.contract = read_bytes(abi.CONTRACT_PATH)
        cls.sources = abi.load_sources(REPO_ROOT)

    def rejected_rust_mutation(self, old, new):
        self.assertIn(old, self.rust)
        mutated = self.rust.replace(old, new, 1)
        with self.assertRaises(abi.ContractError):
            abi.check(REPO_ROOT, rust_override=mutated, contract_override=self.contract)

    def test_repository_contract_is_bounded_and_fail_closed(self):
        contract = abi.check(REPO_ROOT)
        self.assertEqual(145, contract["capture"]["constant_count"])
        self.assertEqual(28, contract["capture"]["layout_count"])
        self.assertEqual(13, len(contract["capture"]["sources"]))
        self.assertEqual(abi.READINESS_BLOCKERS, tuple(contract["readiness"]["blockers"]))
        self.assertFalse(contract["readiness"]["credit_eligible"])
        self.assertFalse(contract["coverage"]["complete_rs003_catalog"])
        self.assertEqual("TODO", contract["readiness"]["status"])

    def test_checker_and_tests_parse_as_python_3_6(self):
        for relative in (
                "scripts/x86_64_shared_abi.py",
                "scripts/tests/test_x86_64_shared_abi.py"):
            source = read_bytes(relative).decode("utf-8")
            try:
                ast.parse(source, filename=relative, feature_version=(3, 6))
            except TypeError:
                ast.parse(source, filename=relative, feature_version=6)

    def test_queue_head_is_reusable_and_fully_asserted(self):
        contract = abi.check(REPO_ROOT)
        queue = next(item for item in contract["layouts"]
                     if item["rust_name"] == "IhkIkcQueueHead")
        self.assertEqual(64, queue["size"])
        self.assertEqual(8, queue["alignment"])
        self.assertEqual(13, len(queue["offsets"]))
        self.assertEqual(60, queue["offsets"]["reserved"])

    def test_frozen_source_single_byte_mutation_is_rejected(self):
        for source_id in sorted(self.sources):
            with self.subTest(source_id=source_id):
                source = self.sources[source_id]
                mutated = bytes(bytearray(source[:-1]) + bytearray([source[-1] ^ 1]))
                with self.assertRaises(abi.ContractError):
                    abi.derive_contract(REPO_ROOT, source_overrides={source_id: mutated})

    def test_git_reads_use_only_the_resolved_repository_safe_directory(self):
        for owner, expected_root in (
                ("root", os.path.realpath(REPO_ROOT)),
                ("ihk", os.path.realpath(os.path.join(REPO_ROOT, "ihk")))):
            process = mock.Mock()
            process.returncode = 0
            process.communicate.return_value = (b"locked blob", b"")
            with self.subTest(owner=owner):
                with mock.patch.object(abi.subprocess, "Popen", return_value=process) as popen:
                    self.assertEqual(
                        b"locked blob",
                        abi._git_blob(REPO_ROOT, owner, "a" * 40, "locked/path"),
                    )
                popen.assert_called_once_with(
                    [
                        "git",
                        "-c",
                        "safe.directory=" + expected_root,
                        "-C",
                        expected_root,
                        "show",
                        "{}:locked/path".format("a" * 40),
                    ],
                    cwd=expected_root,
                    stdout=abi.subprocess.PIPE,
                    stderr=abi.subprocess.PIPE,
                )

    def test_git_reads_succeed_under_assumed_different_ownership(self):
        selected = (abi.SOURCE_LOCKS[0], abi.SOURCE_LOCKS[9])
        with mock.patch.dict(
                os.environ, {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}):
            for source_id, owner, ref, path, size, digest in selected:
                with self.subTest(source_id=source_id):
                    data = abi._git_blob(REPO_ROOT, owner, ref, path)
                    self.assertEqual(size, len(data))
                    self.assertEqual(digest, abi._sha(data))

    def test_constant_value_mutation_is_rejected(self):
        self.rejected_rust_mutation(
            b"pub const IKC_FLAG_NO_COPY: u32 = 0x10;",
            b"pub const IKC_FLAG_NO_COPY: u32 = 0x20;",
        )

    def test_queue_field_mutation_is_rejected_even_when_layout_is_unchanged(self):
        self.rejected_rust_mutation(
            b"    pub packet_count: u32,",
            b"    pub packet_count_mutated: u32,",
        )

    def test_size_assertion_mutation_is_rejected(self):
        self.rejected_rust_mutation(
            b"assert_layout!(IhkIkcQueueHead, 64, 8,",
            b"assert_layout!(IhkIkcQueueHead, 72, 8,",
        )

    def test_offset_assertion_mutation_is_rejected(self):
        self.rejected_rust_mutation(
            b"write_cpu => 56, reserved => 60",
            b"write_cpu => 52, reserved => 60",
        )

    def test_target_and_endian_assertion_removal_is_rejected(self):
        self.rejected_rust_mutation(
            b'#[cfg(not(target_endian = "little"))]',
            b'#[cfg(target_endian = "little")]',
        )

    def test_unreviewed_public_constant_or_layout_is_rejected(self):
        self.rejected_rust_mutation(
            b"pub const ABI_POINTER_BITS: u32 = 64;",
            b"pub const UNREVIEWED_ABI_VALUE: u32 = 1;\npub const ABI_POINTER_BITS: u32 = 64;",
        )
        self.rejected_rust_mutation(
            b"#[repr(C)]\npub struct DumpMemChunk {",
            b"#[repr(C)]\npub struct UnreviewedLayout { pub value: u64 }\n\n#[repr(C)]\npub struct DumpMemChunk {",
        )

    def test_readiness_and_digest_self_attestation_is_rejected(self):
        contract = json.loads(self.contract.decode("utf-8"))
        contract["readiness"] = {
            "blockers": [],
            "credit_eligible": True,
            "status": "PASS",
        }
        with self.assertRaises(abi.ContractError):
            abi.check(REPO_ROOT, contract_override=abi.render_contract(contract))
        contract = json.loads(self.contract.decode("utf-8"))
        contract["capture"]["rust_sha256"] = "0" * 64
        with self.assertRaises(abi.ContractError):
            abi.check(REPO_ROOT, contract_override=abi.render_contract(contract))

    def test_duplicate_legacy_surfaces_are_cross_validated(self):
        contract = abi.check(REPO_ROOT)
        cross = contract["cross_validation"]
        self.assertEqual(2, len(cross["duplicate_declarations"]))
        self.assertGreaterEqual(cross["shared_scd_constant_count"], 30)


if __name__ == "__main__":
    unittest.main()
