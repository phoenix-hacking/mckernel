#!/usr/bin/env python3
"""Adversarial tests for the deterministic RK-001 response index."""

from __future__ import print_function

import copy
import fcntl
import hashlib
import importlib.util
import io
import json
import os
import errno
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(name, relative):
    path = REPO_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


indexer = load_module(
    "rk001_review_response_index",
    "scripts/rocky_kernel_license_review_response_index.py",
)
response = load_module(
    "rk001_review_response_for_index_tests",
    "scripts/rocky_kernel_license_review_response.py",
)


class ResponseIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.authority = indexer.load_authority(REPO_ROOT)
        with open(
            REPO_ROOT
            / "host-kernel/rocky/evidence/rk001-license-review-campaign-ef58-v1.json",
            "r",
        ) as source:
            cls.campaign = json.load(source)
        cls.packet_counts = indexer.packet_unit_records(cls.campaign)

    def entry(self, packet_id, unit_count, reviewer=1, unresolved=None):
        if unresolved is None:
            unresolved = unit_count
        root_digest = hashlib.sha256(("root:" + packet_id).encode("ascii")).hexdigest()
        package_digest = hashlib.sha256(
            ("package:" + packet_id).encode("ascii")
        ).hexdigest()
        return {
            "archive_expansion_complete": False,
            "durable_archive": False,
            "packet_id": packet_id,
            "response_package_sha256": package_digest,
            "review_completed_at": "2026-08-{0:02d}T12:34:56Z".format(
                1 + (int(packet_id) % 19)
            ),
            "reviewed_unit_count": unit_count,
            "reviewer_authority_id": "independent-reviewer-{0}".format(reviewer),
            "reviewer_identity": "reviewer{0}@example.invalid".format(reviewer),
            "reviewer_key_fingerprint": "SHA256:" + chr(64 + reviewer) * 43,
            "reviewer_registered": True,
            "signature_valid": True,
            "signed_response_root": "rk001-response-root:" + root_digest,
            "unresolved_unit_count": unresolved,
        }

    def entries(self, mixed=False, unresolved=None):
        return [
            self.entry(
                record["packet_id"],
                record["unit_count"],
                reviewer=(1 + (index % 2)) if mixed else 1,
                unresolved=(record["unit_count"] if unresolved is None else unresolved),
            )
            for index, record in enumerate(self.packet_counts)
        ]

    def build(self, entries=None):
        return indexer.build_index_data(
            self.authority,
            self.campaign,
            self.entries() if entries is None else entries,
        )

    def forge_live_handle(self, entry, seal=None):
        packet_type = indexer.LiveVerifiedPacket
        packet = object.__new__(packet_type)
        entry_slot = next(
            name for name in vars(packet_type) if name.endswith("__entry_bytes")
        )
        seal_slot = next(name for name in vars(packet_type) if name.endswith("__seal"))
        object.__setattr__(
            packet, entry_slot, indexer.canonical_json(entry, newline=True)
        )
        object.__setattr__(
            packet, seal_slot, b"\x00" * 32 if seal is None else seal
        )
        return packet

    def serialize(self, value):
        return indexer.index_bytes(self.authority, self.campaign, value)

    def test_production_authority_and_frozen_stack_check(self):
        indexer.validate_authority(self.authority)
        loaded = indexer.load_frozen_stack(REPO_ROOT, self.authority)
        self.assertEqual(loaded[1]["response_contract_id"], indexer.RESPONSE_CONTRACT_ID)
        self.assertEqual(loaded[3]["campaign_id"], indexer.CAMPAIGN_ID)
        self.assertEqual(loaded[1]["reviewer_authority_policy"]["registered_reviewers"], [])
        self.assertTrue(all(value is False for value in self.authority["claims"].values()))
        self.assertEqual(self.authority["gate"], indexer.EXPECTED_GATE)

    def test_check_mode_is_explicitly_non_crediting(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = indexer.main(["--repo", str(REPO_ROOT), "--check"])
        self.assertEqual(result, 0, stderr.getvalue())
        text = stdout.getvalue()
        self.assertIn("packets=219", text)
        self.assertIn("units=115265", text)
        self.assertIn("campaign_complete=false", text)
        self.assertIn("credit=false", text)

    def test_deterministic_pure_build_and_verify(self):
        first = self.build()
        second = self.build(copy.deepcopy(first["entries"]))
        self.assertEqual(first, second)
        self.assertEqual(self.serialize(first), self.serialize(second))
        parsed = indexer.parse_index_bytes(
            self.authority, self.campaign, self.serialize(first)
        )
        result = indexer.validate_structural_index_data(
            self.authority, self.campaign, parsed
        )
        self.assertEqual(result["packet_count"], 219)
        self.assertEqual(result["reviewed_unit_count"], 115265)
        self.assertFalse(result["campaign_complete"])
        self.assertFalse(result["durable_archive"])
        self.assertFalse(result["tracker_credit"])

    def test_fabricated_structural_rows_never_claim_live_verification(self):
        fabricated = self.build(self.entries(unresolved=0))
        self.assertFalse(fabricated["all_packet_responses_verified"])
        self.assertFalse(fabricated["structural_response_coverage_complete"])
        parsed = indexer.parse_index_bytes(
            self.authority, self.campaign, self.serialize(fabricated)
        )
        structural = indexer.validate_structural_index_data(
            self.authority, self.campaign, parsed
        )
        self.assertFalse(structural["all_packet_responses_verified"])
        self.assertFalse(structural["structural_response_coverage_complete"])
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.verify_index_data(self.authority, self.campaign, parsed)
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.verify_index_data(
                self.authority,
                self.campaign,
                parsed,
                verified_packets=copy.deepcopy(parsed["entries"]),
            )
        claimed = copy.deepcopy(parsed)
        claimed["all_packet_responses_verified"] = True
        claimed["structural_response_coverage_complete"] = True
        with self.assertRaises(indexer.ResponseIndexError):
            self.serialize(claimed)

    def test_live_provenance_exposes_no_token_or_arbitrary_factory(self):
        self.assertFalse(hasattr(indexer, "_LIVE_VERIFICATION_TOKEN"))
        self.assertFalse(hasattr(indexer, "_make_live_verified_packet"))
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.LiveVerifiedPacket(self.entries()[0])
        fabricated = self.build(self.entries(unresolved=0))
        forged = [
            self.forge_live_handle(entry) for entry in fabricated["entries"]
        ]
        with self.assertRaises(indexer.ResponseIndexError) as caught:
            indexer.verify_index_data(
                self.authority,
                self.campaign,
                fabricated,
                verified_packets=forged,
            )
        self.assertIn("seal differs", str(caught.exception))

    def test_live_provenance_type_is_exact_and_non_subclassable(self):
        with self.assertRaises(TypeError):
            class ForgedLivePacket(indexer.LiveVerifiedPacket):
                @property
                def entry(self):
                    return self.entries()[0]

        class EntryOverride(object):
            @property
            def entry(self):
                return self.entries()[0]

        with self.assertRaises(indexer.ResponseIndexError):
            indexer.verify_index_data(
                self.authority,
                self.campaign,
                self.build(),
                verified_packets=[EntryOverride()] * indexer.PACKET_COUNT,
            )

    def test_live_provenance_bytes_are_immutable_and_tamper_evident(self):
        packet = self.forge_live_handle(self.entries()[0])
        packet_type = indexer.LiveVerifiedPacket
        entry_slot = next(
            name for name in vars(packet_type) if name.endswith("__entry_bytes")
        )
        with self.assertRaises(indexer.ResponseIndexError):
            setattr(packet, entry_slot, b"mutated\n")
        object.__setattr__(packet, entry_slot, b'{"fabricated":true}\n')
        with self.assertRaises(indexer.ResponseIndexError) as caught:
            indexer._decode_live_verified_packet(packet)
        self.assertIn("seal differs", str(caught.exception))

    def test_zero_unresolved_still_never_completes_campaign(self):
        built = self.build(self.entries(unresolved=0))
        self.assertEqual(built["unresolved_unit_count"], 0)
        self.assertFalse(built["all_packet_responses_verified"])
        self.assertFalse(built["structural_response_coverage_complete"])
        self.assertTrue(built["successor_v2_archive_blockers_present"])
        self.assertTrue(all(value is False for value in built["claims"].values()))
        self.assertEqual(built["gate"]["points_awarded"], 0)
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.verify_index_data(self.authority, self.campaign, built)
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.verify_index_data(
                self.authority,
                self.campaign,
                built,
                verified_packets=copy.deepcopy(built["entries"]),
            )

    def test_exact_219_packet_order_count_and_total_are_enforced(self):
        original = self.entries()
        cases = [
            original[:-1],
            original + [copy.deepcopy(original[-1])],
            [original[1], original[0]] + original[2:],
        ]
        duplicate = copy.deepcopy(original)
        duplicate[1]["packet_id"] = duplicate[0]["packet_id"]
        cases.append(duplicate)
        wrong_count = copy.deepcopy(original)
        wrong_count[0]["reviewed_unit_count"] -= 1
        cases.append(wrong_count)
        for candidate in cases:
            with self.subTest(length=len(candidate)):
                with self.assertRaises(indexer.ResponseIndexError):
                    self.build(candidate)

    def test_duplicate_root_and_package_digest_are_rejected(self):
        for field in ("signed_response_root", "response_package_sha256"):
            candidate = self.entries()
            candidate[1][field] = candidate[0][field]
            with self.subTest(field=field):
                with self.assertRaises(indexer.ResponseIndexError):
                    self.build(candidate)

    def test_signature_registration_archive_and_durability_fail_closed(self):
        for field in (
            "signature_valid",
            "reviewer_registered",
            "archive_expansion_complete",
            "durable_archive",
        ):
            candidate = self.entries()
            candidate[0][field] = not candidate[0][field]
            with self.subTest(field=field):
                with self.assertRaises(indexer.ResponseIndexError):
                    self.build(candidate)
        candidate = self.entries()
        candidate[0]["signature_valid"] = 1
        with self.assertRaises(indexer.ResponseIndexError):
            self.build(candidate)

    def test_identity_aliases_and_malformed_identity_are_rejected(self):
        mutations = []
        authority_alias = self.entries()
        authority_alias[1]["reviewer_identity"] = "different@example.invalid"
        authority_alias[1]["reviewer_key_fingerprint"] = "SHA256:" + "B" * 43
        mutations.append(authority_alias)
        identity_alias = self.entries(mixed=True)
        identity_alias[1]["reviewer_identity"] = identity_alias[0]["reviewer_identity"]
        mutations.append(identity_alias)
        fingerprint_alias = self.entries(mixed=True)
        fingerprint_alias[1]["reviewer_key_fingerprint"] = fingerprint_alias[0][
            "reviewer_key_fingerprint"
        ]
        mutations.append(fingerprint_alias)
        malformed = self.entries()
        malformed[0]["reviewer_authority_id"] = "../reviewer"
        mutations.append(malformed)
        for candidate in mutations:
            with self.assertRaises(indexer.ResponseIndexError):
                self.build(candidate)

    def test_mixed_registered_reviewer_set_is_deterministic(self):
        built = self.build(self.entries(mixed=True))
        self.assertEqual(built["reviewer_count"], 2)
        self.assertEqual(sum(item["packet_count"] for item in built["reviewers"]), 219)
        self.assertEqual(
            built["reviewers"], sorted(built["reviewers"], key=lambda item: (
                item["reviewer_authority_id"],
                item["reviewer_identity"],
                item["reviewer_key_fingerprint"],
            ))
        )

    def test_time_is_real_utc_and_bounds_are_derived(self):
        built = self.build()
        completed = [entry["review_completed_at"] for entry in built["entries"]]
        self.assertEqual(built["earliest_review_completed_at"], min(completed))
        self.assertEqual(built["latest_review_completed_at"], max(completed))
        for timestamp in (
            "2026-02-30T00:00:00Z",
            "2026-08-01T00:00:00+00:00",
            "2026-08-01T00:00:00.1Z",
        ):
            candidate = self.entries()
            candidate[0]["review_completed_at"] = timestamp
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(indexer.ResponseIndexError):
                    self.build(candidate)

    def test_index_root_replay_rejects_claim_digest_and_live_binding_mutation(self):
        original = self.build()
        mutations = []
        claims = copy.deepcopy(original)
        claims["claims"]["campaign_complete"] = True
        mutations.append(claims)
        entry = copy.deepcopy(original)
        entry["entries"][0]["unresolved_unit_count"] -= 1
        mutations.append(entry)
        digest = copy.deepcopy(original)
        digest["entry_stream_sha256"] = "0" * 64
        mutations.append(digest)
        archive = copy.deepcopy(original)
        archive["successor_v2_archive_blockers_present"] = False
        mutations.append(archive)
        for candidate in mutations:
            with self.assertRaises(indexer.ResponseIndexError):
                indexer.validate_structural_index_data(
                    self.authority, self.campaign, candidate
                )
        live = copy.deepcopy(original["entries"])
        live[0]["response_package_sha256"] = "f" * 64
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.verify_index_data(
                self.authority,
                self.campaign,
                original,
                verified_packets=live,
            )

    def test_canonical_duplicate_key_float_and_oversize_json_fail(self):
        built = self.build()
        canonical = self.serialize(built)
        noncanonical = json.dumps(built, indent=2, sort_keys=True).encode("ascii")
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.parse_index_bytes(self.authority, self.campaign, noncanonical)
        duplicate = b'{"a":1,"a":2}\n'
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.read_json_bytes(duplicate, "duplicate")
        floating = b'{"a":1.0}\n'
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.read_json_bytes(floating, "floating")
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.read_json_bytes(b"{" + b" " * indexer.MAX_INDEX_BYTES, "large")
        self.assertLessEqual(len(canonical), indexer.MAX_INDEX_BYTES)

    def test_authority_binding_path_and_false_claim_types_fail(self):
        for mutate in ("path", "digest", "size", "claim"):
            authority = copy.deepcopy(self.authority)
            if mutate == "path":
                authority["inputs"]["campaign_checker"]["path"] = "../escape.py"
            elif mutate == "digest":
                authority["inputs"]["campaign_checker"]["sha256"] = "A" * 64
            elif mutate == "size":
                authority["inputs"]["campaign_checker"]["size"] = True
            else:
                authority["claims"]["campaign_complete"] = 0
            with self.subTest(mutate=mutate):
                with self.assertRaises(indexer.ResponseIndexError):
                    indexer.validate_authority(authority)

    def test_every_input_descriptor_and_ordered_blocker_is_exact_frozen(self):
        self.assertEqual(
            self.authority["inputs"], indexer.EXPECTED_INPUT_DESCRIPTORS
        )
        self.assertEqual(
            self.authority["remaining_blockers"], indexer.EXPECTED_BLOCKERS
        )
        for key in sorted(indexer.EXPECTED_INPUT_DESCRIPTORS):
            for field, replacement in (
                ("path", "synthetic/" + key),
                ("sha256", "0" * 64),
                ("size", 0),
            ):
                authority = copy.deepcopy(self.authority)
                authority["inputs"][key][field] = replacement
                with self.subTest(key=key, field=field):
                    with self.assertRaises(indexer.ResponseIndexError):
                        indexer.validate_authority(authority)
                    with self.assertRaises(indexer.ResponseIndexError):
                        indexer.build_index_data(
                            authority, self.campaign, self.entries()
                        )
        coherent = copy.deepcopy(self.authority)
        for descriptor in coherent["inputs"].values():
            descriptor["sha256"] = "0" * 64
            descriptor["size"] = 0
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.validate_campaign(coherent, self.campaign)
        for blockers in (
            list(reversed(indexer.EXPECTED_BLOCKERS)),
            indexer.EXPECTED_BLOCKERS[:-1],
            indexer.EXPECTED_BLOCKERS + ["synthetic blocker"],
        ):
            authority = copy.deepcopy(self.authority)
            authority["remaining_blockers"] = blockers
            with self.assertRaises(indexer.ResponseIndexError):
                indexer.validate_authority(authority)

    def test_campaign_packet_count_stream_binding_rejects_mutation(self):
        stream = indexer.canonical_stream(indexer.packet_unit_records(self.campaign))
        self.assertEqual(len(stream), 8321)
        self.assertEqual(
            hashlib.sha256(stream).hexdigest(),
            "3f50a8e9cad00d8d7d8b88bdebea332e3051fbd086bf56e30720ac6fed17d365",
        )
        for field in ("packet_id", "unit_count"):
            campaign = copy.deepcopy(self.campaign)
            campaign["packets"][0][field] = (
                "9999" if field == "packet_id" else campaign["packets"][0][field] + 1
            )
            with self.subTest(field=field):
                with self.assertRaises(indexer.ResponseIndexError):
                    indexer.validate_campaign(self.authority, campaign)
        synthetic = copy.deepcopy(self.campaign)
        synthetic["gate"]["status"] = "DONE"
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.validate_campaign(self.authority, synthetic)

    def test_package_digest_binds_paths_bytes_sizes_and_signature(self):
        files = {
            "response-root.json": b"root\n",
            "response-root.sig": b"signature\n",
            "support/" + "a" * 64: b"support\n",
        }
        first = indexer.response_package_digest(files)
        changed = dict(files)
        changed["response-root.sig"] = b"other-signature\n"
        self.assertNotEqual(first, indexer.response_package_digest(changed))
        unsafe = dict(files)
        unsafe["../escape"] = b"bad"
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.response_package_digest(unsafe)
        nonbytes = dict(files)
        nonbytes["response-root.json"] = "root"
        with self.assertRaises(indexer.ResponseIndexError):
            indexer.response_package_digest(nonbytes)

    def make_roots(self, temporary):
        packet_root = Path(temporary) / "packets"
        response_root = Path(temporary) / "responses"
        packet_root.mkdir()
        response_root.mkdir()
        for packet_id in indexer.EXPECTED_PACKET_IDS:
            (packet_root / packet_id).mkdir()
            (response_root / packet_id).mkdir()
        return packet_root, response_root

    def test_fixture_injection_builds_only_exact_root_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            packet_root, response_root = self.make_roots(temporary)
            by_id = {
                record["packet_id"]: self.entry(
                    record["packet_id"], record["unit_count"]
                )
                for record in self.packet_counts
            }
            seen = []

            def verifier(packet_id, packet_directory, response_directory):
                self.assertEqual(packet_directory, packet_root / packet_id)
                self.assertEqual(response_directory, response_root / packet_id)
                seen.append(packet_id)
                return copy.deepcopy(by_id[packet_id])

            built = indexer.build_index(
                self.authority,
                self.campaign,
                response,
                packet_root,
                response_root,
                verifier,
            )
            self.assertEqual(seen, list(indexer.EXPECTED_PACKET_IDS))
            self.assertEqual(built["packet_count"], 219)
            self.assertFalse(built["all_packet_responses_verified"])
            (response_root / "extra").mkdir()
            with self.assertRaises(indexer.ResponseIndexError):
                indexer.collect_verified_packets(
                    response, packet_root, response_root, verifier
                )

    def test_symlink_and_toctou_packet_directory_are_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            packet_root, response_root = self.make_roots(temporary)
            target = Path(temporary) / "target"
            target.mkdir()
            shutil.rmtree(str(response_root / "0001"))
            os.symlink(str(target), str(response_root / "0001"))
            with self.assertRaises(indexer.ResponseIndexError):
                indexer.collect_verified_packets(
                    response,
                    packet_root,
                    response_root,
                    lambda packet_id, packet, response_path: None,
                )
        with tempfile.TemporaryDirectory() as temporary:
            packet_root, response_root = self.make_roots(temporary)
            record = self.packet_counts[0]

            def mutate(packet_id, packet_directory, response_directory):
                if packet_id == "0001":
                    os.rmdir(str(response_directory))
                    os.mkdir(str(response_directory))
                return self.entry(packet_id, record["unit_count"])

            with self.assertRaises(indexer.ResponseIndexError):
                indexer.collect_verified_packets(
                    response, packet_root, response_root, mutate
                )

    def test_malformed_root_repetition_closes_every_descriptor(self):
        if not Path("/proc/self/fd").is_dir():
            self.skipTest("descriptor census unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            malformed = Path(temporary) / "malformed"
            malformed.mkdir()
            (malformed / "0001").mkdir()
            before = len(os.listdir("/proc/self/fd"))
            for _index in range(64):
                with self.assertRaises(indexer.ResponseIndexError):
                    indexer._directory_child_identities(
                        response, malformed, "malformed root"
                    )
            after = len(os.listdir("/proc/self/fd"))
            self.assertEqual(after, before)

    def test_roots_are_absolutized_once_before_chdir_injection(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            packet_root, response_root = self.make_roots(temporary)
            other = base / "other"
            other.mkdir()
            by_id = {
                record["packet_id"]: self.entry(
                    record["packet_id"], record["unit_count"]
                )
                for record in self.packet_counts
            }
            original_cwd = os.getcwd()
            try:
                os.chdir(str(base))
                seen = []

                def verifier(packet_id, packet_directory, response_directory):
                    self.assertTrue(packet_directory.is_absolute())
                    self.assertTrue(response_directory.is_absolute())
                    self.assertEqual(packet_directory, packet_root / packet_id)
                    self.assertEqual(response_directory, response_root / packet_id)
                    seen.append((packet_directory, response_directory))
                    os.chdir(str(other))
                    return by_id[packet_id]

                try:
                    result = indexer.collect_verified_packets(
                        response, Path("packets"), Path("responses"), verifier
                    )
                except indexer.ResponseIndexError as error:
                    self.assertIn("namespace changed", str(error))
                else:
                    self.assertEqual(len(result), 219)
                for packet_directory, response_directory in seen:
                    self.assertTrue(str(packet_directory).startswith(str(packet_root)))
                    self.assertTrue(str(response_directory).startswith(str(response_root)))
            finally:
                os.chdir(original_cwd)

    def test_campaign_package_error_is_wrapped_at_public_boundary(self):
        class FakeCampaign(object):
            class ReviewCampaignError(RuntimeError):
                pass

            @staticmethod
            def verify_package(*_arguments):
                raise FakeCampaign.ReviewCampaignError("fixture campaign rejection")

        class FakeResponse(object):
            class ReviewResponseError(RuntimeError):
                pass

        arguments = (
            FakeResponse,
            {},
            FakeCampaign,
            {},
            {},
            "0001",
            Path("/tmp/packet"),
            Path("/tmp/response"),
        )
        with self.assertRaises(indexer.ResponseIndexError) as caught:
            indexer.verify_packet_snapshot(
                *arguments
            )
        self.assertIn("frozen loaded stack", str(caught.exception))
        with self.assertRaises(indexer.ResponseIndexError) as caught:
            indexer._verify_packet_snapshot_implementation(*arguments)
        self.assertIn("fixture campaign rejection", str(caught.exception))

    def test_fifo_input_is_rejected_without_blocking(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            fifo = Path(temporary) / "index.fifo"
            os.mkfifo(str(fifo), 0o600)
            program = (
                "import importlib.util;"
                "p={0!r};"
                "s=importlib.util.spec_from_file_location('idx',p);"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                "\ntry:m._read_regular({1!r},1024,'fifo')\n"
                "except m.ResponseIndexError:print('REJECTED')\n"
                "else:raise SystemExit('FAIL-OPEN')"
            ).format(
                str(REPO_ROOT / "scripts/rocky_kernel_license_review_response_index.py"),
                str(fifo),
            )
            result = subprocess.run(
                [sys.executable, "-c", program],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b"REJECTED\n")

    def test_new_output_refuses_overwrite_and_is_exact(self):
        built = self.build()
        data = self.serialize(built)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "index.json"
            original = indexer._validate_output_snapshot
            retained_access_modes = []

            def record_access_mode(descriptor, parent_fd, name, expected, mode, label):
                if label == "published index":
                    retained_access_modes.append(
                        fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE
                    )
                return original(descriptor, parent_fd, name, expected, mode, label)

            with mock.patch.object(
                indexer, "_validate_output_snapshot", side_effect=record_access_mode
            ):
                indexer._write_new_file(response, output, data)
            self.assertEqual(output.read_bytes(), data)
            self.assertEqual(retained_access_modes, [os.O_RDONLY, os.O_RDONLY])

    def test_output_fsync_mutation_is_retracted_and_retry_succeeds(self):
        data = self.serialize(self.build())
        evil = b"E" * len(data)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "index.json"
            original_fsync = indexer.os.fsync
            raced = [False]

            def fsync_then_corrupt(descriptor):
                result = original_fsync(descriptor)
                info = os.fstat(descriptor)
                if stat.S_ISREG(info.st_mode) and info.st_size == len(data) and not raced[0]:
                    raced[0] = True
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    os.write(descriptor, evil)
                    os.fchmod(descriptor, 0o777)
                return result

            with mock.patch.object(
                indexer.os, "fsync", side_effect=fsync_then_corrupt
            ):
                with self.assertRaises(indexer.ResponseIndexError):
                    indexer._write_new_file(response, output, data)
            self.assertTrue(raced[0])
            self.assertFalse(output.exists())
            self.assertFalse(any(Path(temporary).glob(".rk001-index-stage-*")))
            indexer._write_new_file(response, output, data)
            self.assertEqual(output.read_bytes(), data)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o444)

    def test_output_post_validation_byte_race_is_retracted(self):
        data = self.serialize(self.build())
        evil = b"X" * len(data)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "index.json"
            original = indexer._validate_output_snapshot
            raced = [False]

            def validate_then_corrupt(descriptor, parent_fd, name, expected, mode, label):
                result = original(descriptor, parent_fd, name, expected, mode, label)
                if label == "published index" and not raced[0]:
                    raced[0] = True
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    os.write(descriptor, evil)
                    os.fsync(descriptor)
                return result

            with mock.patch.object(
                indexer, "_validate_output_snapshot", side_effect=validate_then_corrupt
            ):
                with self.assertRaises(indexer.ResponseIndexError):
                    indexer._write_new_file(response, output, data)
            self.assertTrue(raced[0])
            self.assertFalse(output.exists())

    def test_output_parent_rename_and_external_hardlink_are_retracted(self):
        data = self.serialize(self.build())
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            parent = base / "parent"
            moved = base / "moved"
            parent.mkdir()
            output = parent / "index.json"
            original = indexer._rename_noreplace

            def rename_then_move(parent_fd, old_name, new_name):
                original(parent_fd, old_name, new_name)
                os.rename(str(parent), str(moved))
                parent.mkdir()

            with mock.patch.object(
                indexer, "_rename_noreplace", side_effect=rename_then_move
            ):
                with self.assertRaises(indexer.ResponseIndexError):
                    indexer._write_new_file(response, output, data)
            self.assertFalse(output.exists())
            self.assertFalse((moved / "index.json").exists())
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            output = base / "index.json"
            external = base / "external-hardlink"
            original = indexer._rename_noreplace

            def rename_then_link(parent_fd, old_name, new_name):
                original(parent_fd, old_name, new_name)
                os.link(
                    new_name,
                    str(external),
                    src_dir_fd=parent_fd,
                    follow_symlinks=False,
                )

            with mock.patch.object(
                indexer, "_rename_noreplace", side_effect=rename_then_link
            ):
                with self.assertRaises(indexer.ResponseIndexError):
                    indexer._write_new_file(response, output, data)
            self.assertFalse(output.exists())
            self.assertTrue(external.exists())
            external.unlink()

    def test_output_partial_eio_is_cleaned_and_retry_succeeds(self):
        data = self.serialize(self.build())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "index.json"
            original_write = indexer.os.write
            failed = [False]

            def fail_first_write(descriptor, block):
                if not failed[0]:
                    failed[0] = True
                    raise OSError(errno.EIO, "fixture partial write")
                return original_write(descriptor, block)

            with mock.patch.object(
                indexer.os, "write", side_effect=fail_first_write
            ):
                with self.assertRaises(indexer.ResponseIndexError):
                    indexer._write_new_file(response, output, data)
            self.assertFalse(output.exists())
            self.assertFalse(any(Path(temporary).glob(".rk001-index-stage-*")))
            indexer._write_new_file(response, output, data)
            self.assertEqual(output.read_bytes(), data)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o444)
            with self.assertRaises(indexer.ResponseIndexError):
                indexer._write_new_file(response, output, b"replacement\n")
            self.assertEqual(output.read_bytes(), data)

    def test_output_unsafe_filename_is_rejected_without_a_stage(self):
        data = self.serialize(self.build())
        with tempfile.TemporaryDirectory() as temporary:
            for name in ("nonascii-\N{SNOWMAN}.json", "nul-\x00.json"):
                with self.subTest(name=repr(name)):
                    with self.assertRaises(indexer.ResponseIndexError):
                        indexer._write_new_file(response, Path(temporary) / name, data)
                    self.assertFalse(
                        any(Path(temporary).glob(".rk001-index-stage-*"))
                    )

    def test_index_file_read_and_output_reject_symlink_ancestors(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        built = self.build()
        data = self.serialize(built)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real"
            real.mkdir()
            source = real / "index.json"
            source.write_bytes(data)
            link = root / "linked"
            os.symlink(str(real), str(link))
            with self.assertRaises(indexer.ResponseIndexError):
                indexer._read_regular(link / "index.json", indexer.MAX_INDEX_BYTES, "index")
            with self.assertRaises(indexer.ResponseIndexError):
                indexer._write_new_file(response, link / "new.json", data)


if __name__ == "__main__":
    unittest.main()
