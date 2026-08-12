#!/usr/bin/env python3
"""Fail-closed tests for the RK-001 Rocky kernel source lock."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import rocky_kernel_source_lock as source_lock  # noqa: E402


def identity_leaves(value: object, path: tuple[object, ...] = ()):
    """Yield every scalar identity so additions automatically need mutation tests."""

    if isinstance(value, dict):
        for key, child in value.items():
            yield from identity_leaves(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from identity_leaves(child, (*path, index))
    else:
        yield path, value


def replace_at_path(value: object, path: tuple[object, ...], replacement: object) -> None:
    target = value
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = replacement  # type: ignore[index]


def changed_scalar(value: object) -> object:
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        if source_lock.HEX_SHA256.fullmatch(value):
            return ("0" if value[0] != "0" else "1") + value[1:]
        if source_lock.HEX_SHA1.fullmatch(value):
            return ("0" if value[0] != "0" else "1") + value[1:]
        return value + "-mutated"
    raise TypeError(f"unsupported identity scalar {value!r}")


class SourceLockFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lock, cls.lock_bytes = source_lock.read_json(
            REPO_ROOT / source_lock.SOURCE_LOCK_PATH
        )
        cls.series, cls.series_bytes = source_lock.read_json(
            REPO_ROOT / source_lock.PATCH_SERIES_PATH
        )

    def validate(
        self, lock: dict | None = None, series: dict | None = None
    ) -> list[str]:
        actual_lock = copy.deepcopy(self.lock if lock is None else lock)
        actual_series = copy.deepcopy(self.series if series is None else series)
        series_bytes = (
            self.series_bytes
            if actual_series == self.series
            else (json.dumps(actual_series, indent=2, sort_keys=True) + "\n").encode()
        )
        if actual_series != self.series:
            actual_lock["patch_series"]["sha256"] = hashlib.sha256(
                series_bytes
            ).hexdigest()
        return source_lock.validate_loaded_manifests(
            actual_lock, actual_series, series_bytes, REPO_ROOT
        )


class LockedIdentityTests(SourceLockFixture):
    def test_duplicate_json_keys_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"gate":{},"gate":{}}\n', encoding="utf-8")
            with self.assertRaisesRegex(source_lock.SourceLockError, "duplicate"):
                source_lock.read_json(path)

    def test_committed_lock_is_valid_but_not_gate_ready(self) -> None:
        blockers = self.validate()
        self.assertEqual(len(blockers), 1)
        self.assertEqual(
            {blocker.split(":", 1)[0] for blocker in blockers},
            {"license_inventory"},
        )
        self.assertFalse(self.lock["gate"]["credit_eligible"])

    def test_every_reviewed_evidence_row_leaf_is_authoritative(self) -> None:
        tested = 0
        for evidence_id, expected in source_lock.EXPECTED_REVIEWED_EVIDENCE.items():
            self.assertEqual(self.lock["evidence"][evidence_id], expected)
            for path, original in identity_leaves(expected):
                with self.subTest(evidence=evidence_id, path=path):
                    broken = copy.deepcopy(self.lock)
                    replacement = "not-null" if original is None else changed_scalar(original)
                    replace_at_path(broken["evidence"][evidence_id], path, replacement)
                    with self.assertRaises(source_lock.SourceLockError):
                        self.validate(broken)
                    tested += 1
        self.assertGreater(tested, 20)

    def test_review_manifest_digest_is_an_authoritative_cross_lock(self) -> None:
        original = source_lock.SOURCE_EVIDENCE_REVIEW_SHA256
        source_lock.SOURCE_EVIDENCE_REVIEW_SHA256 = "0" * 64
        try:
            with self.assertRaisesRegex(source_lock.SourceLockError, "review manifest"):
                self.validate()
        finally:
            source_lock.SOURCE_EVIDENCE_REVIEW_SHA256 = original

    def test_every_license_capture_authority_leaf_is_immutable(self) -> None:
        self.assertEqual(
            source_lock.EXPECTED_LICENSE_CAPTURE_AUTHORITY,
            self.lock["licenses"]["capture_authority"],
        )
        tested = 0
        for path, original in identity_leaves(
            source_lock.EXPECTED_LICENSE_CAPTURE_AUTHORITY
        ):
            with self.subTest(path=path):
                broken = copy.deepcopy(self.lock)
                replace_at_path(
                    broken["licenses"]["capture_authority"],
                    path,
                    changed_scalar(original),
                )
                with self.assertRaises(source_lock.SourceLockError):
                    self.validate(broken)
                tested += 1
        self.assertGreater(tested, 15)

    def test_srpm_identity_mutations_fail_closed(self) -> None:
        cases = {
            "nevra": "kernel-0:6.12.0-211.46.1.el10_2.src",
            "url": "https://example.invalid/kernel.src.rpm",
            "repository_location": "Packages/k/other.src.rpm",
            "size": self.lock["source_rpm"]["size"] + 1,
            "sha256": "0" * 64,
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                broken = copy.deepcopy(self.lock)
                broken["source_rpm"][field] = value
                with self.assertRaises(source_lock.SourceLockError):
                    self.validate(broken)

    def test_every_authoritative_source_identity_leaf_has_a_mutation_test(self) -> None:
        tested = 0
        for path, original in identity_leaves(source_lock.EXPECTED_SOURCE_IDENTITIES):
            with self.subTest(path=".".join(map(str, path))):
                broken = copy.deepcopy(self.lock)
                replace_at_path(broken, path, changed_scalar(original))
                with self.assertRaises(source_lock.SourceLockError):
                    self.validate(broken)
                tested += 1
        self.assertGreater(tested, 50)

    def test_every_authoritative_patch_series_leaf_has_a_mutation_test(self) -> None:
        tested = 0
        for path, original in identity_leaves(source_lock.EXPECTED_SERIES):
            with self.subTest(path=".".join(map(str, path))):
                broken = copy.deepcopy(self.series)
                replace_at_path(broken, path, changed_scalar(original))
                with self.assertRaises(source_lock.SourceLockError):
                    self.validate(series=broken)
                tested += 1
        self.assertGreater(tested, 30)

    def test_repository_metadata_signature_and_key_mutations_fail_closed(self) -> None:
        mutations = (
            ("primary_metadata", "sha256", "0" * 64),
            ("primary_metadata", "timestamp", 0),
            ("repomd", "sha256", "0" * 64),
            ("release_key", "fingerprint", "0" * 40),
            ("release_key", "sha256", "0" * 64),
        )
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                broken = copy.deepcopy(self.lock)
                broken["repository_snapshot"][section][field] = value
                with self.assertRaises(source_lock.SourceLockError):
                    self.validate(broken)

        for field, value in (
            ("sha256", "0" * 64),
            ("validsig_fingerprint", "0" * 40),
            ("status", "assumed"),
            ("url", "http://download.rockylinux.org/repomd.xml.asc"),
        ):
            with self.subTest(signature_field=field):
                broken = copy.deepcopy(self.lock)
                broken["repository_snapshot"]["repomd"]["signature"][field] = value
                with self.assertRaises(source_lock.SourceLockError):
                    self.validate(broken)

    def test_dist_git_identity_and_every_locked_blob_mutation_fail_closed(self) -> None:
        for field, value in (
            ("commit", "0" * 40),
            ("commit_parent", "0" * 40),
            ("tag", "patched/r10/kernel-wrong"),
            ("tag_object", "0" * 40),
            ("tag_annotation_original_hash", "0" * 64),
            ("repository_url", "https://example.invalid/kernel.git"),
            ("branch_is_immutable_identity", True),
        ):
            with self.subTest(field=field):
                broken = copy.deepcopy(self.lock)
                broken["dist_git"][field] = value
                with self.assertRaises(source_lock.SourceLockError):
                    self.validate(broken)

        for index, entry in enumerate(self.lock["dist_git"]["content"]):
            with self.subTest(blob=entry["path"]):
                broken = copy.deepcopy(self.lock)
                broken["dist_git"]["content"][index]["sha256"] = "0" * 64
                with self.assertRaises(source_lock.SourceLockError):
                    self.validate(broken)

    def test_every_embedded_object_identity_mutation_fails_closed(self) -> None:
        for index, entry in enumerate(self.lock["embedded_objects"]):
            for field, value in (
                ("path", f"SOURCES/wrong-{index}"),
                ("size", entry["size"] + 1),
                ("sha256", "0" * 64),
            ):
                with self.subTest(object=entry["path"], field=field):
                    broken = copy.deepcopy(self.lock)
                    broken["embedded_objects"][index][field] = value
                    with self.assertRaises(source_lock.SourceLockError):
                        self.validate(broken)

    def test_every_patch_identity_and_order_mutation_fails_closed(self) -> None:
        for index, entry in enumerate(self.series["patches"]):
            for field, value in (
                ("path", f"SOURCES/wrong-{index}.patch"),
                ("sha256", "0" * 64),
                ("size", entry["size"] + 1),
                ("line_count", entry["line_count"] + 1),
                ("applied", not entry["applied"]),
                ("empty", not entry["empty"]),
                ("spec_reference", "Patch0"),
            ):
                with self.subTest(patch=entry["path"], field=field):
                    broken = copy.deepcopy(self.series)
                    broken["patches"][index][field] = value
                    with self.assertRaises(source_lock.SourceLockError):
                        self.validate(series=broken)

        reordered = copy.deepcopy(self.series)
        reordered["patches"][0], reordered["patches"][1] = (
            reordered["patches"][1],
            reordered["patches"][0],
        )
        with self.assertRaises(source_lock.SourceLockError):
            self.validate(series=reordered)

    def test_patch_series_file_hash_is_a_cross_manifest_lock(self) -> None:
        broken_bytes = self.series_bytes + b"\n"
        with self.assertRaisesRegex(source_lock.SourceLockError, "patch-series"):
            source_lock.validate_loaded_manifests(
                copy.deepcopy(self.lock),
                copy.deepcopy(self.series),
                broken_bytes,
                REPO_ROOT,
            )

    def test_cache_identity_and_path_escape_mutations_fail_closed(self) -> None:
        for field, value in (
            ("cache_relative_path", "../outside/kernel.src.rpm"),
            ("allowed_redirect_hosts", ["example.invalid"]),
            ("hash_algorithm", "sha1"),
        ):
            with self.subTest(field=field):
                broken = copy.deepcopy(self.lock)
                broken["acquisition"][field] = value
                with self.assertRaises(source_lock.SourceLockError):
                    self.validate(broken)

    def test_license_expression_scope_and_completeness_mutations_fail_closed(self) -> None:
        broken = copy.deepcopy(self.lock)
        broken["licenses"]["declared_spdx_expression"] += " AND MIT"
        with self.assertRaises(source_lock.SourceLockError):
            self.validate(broken)

        broken = copy.deepcopy(self.lock)
        broken["licenses"]["policy"]["scope"].pop()
        with self.assertRaises(source_lock.SourceLockError):
            self.validate(broken)

        broken = copy.deepcopy(self.lock)
        broken["licenses"]["inventory"]["complete"] = True
        with self.assertRaises(source_lock.SourceLockError):
            self.validate(broken)

        broken = copy.deepcopy(self.lock)
        broken["licenses"]["inventory"]["required"] = False
        with self.assertRaises(source_lock.SourceLockError):
            self.validate(broken)

    def test_missing_signature_cannot_be_claimed_verified_without_evidence(self) -> None:
        broken = copy.deepcopy(self.lock)
        signature = broken["evidence"]["srpm_header_signature"]
        signature.update(
            {
                "evidence_path": "host-kernel/rocky/evidence/not-present.json",
                "evidence_sha256": "0" * 64,
                "signature_algorithm": "RSA/SHA256",
                "signer_fingerprint": self.lock["repository_snapshot"][
                    "release_key"
                ]["fingerprint"],
                "status": "verified",
            }
        )
        with self.assertRaises(source_lock.SourceLockError):
            self.validate(broken)

    def test_every_required_evidence_class_cannot_be_weakened_or_faked(self) -> None:
        for evidence_id in self.lock["evidence"]:
            with self.subTest(evidence=evidence_id, mutation="optional"):
                broken = copy.deepcopy(self.lock)
                broken["evidence"][evidence_id]["required"] = False
                with self.assertRaises(source_lock.SourceLockError):
                    self.validate(broken)

            with self.subTest(evidence=evidence_id, mutation="fake-verified"):
                broken = copy.deepcopy(self.lock)
                item = broken["evidence"][evidence_id]
                item["evidence_path"] = "host-kernel/rocky/evidence/not-present.json"
                item["evidence_sha256"] = "0" * 64
                item["status"] = "verified"
                if evidence_id == "srpm_header_signature":
                    item["signature_algorithm"] = "RSA/SHA256"
                    item["signer_fingerprint"] = self.lock["repository_snapshot"][
                        "release_key"
                    ]["fingerprint"]
                with self.assertRaises(source_lock.SourceLockError):
                    self.validate(broken)

    def test_captured_but_unverified_evidence_always_remains_a_blocker(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_path = Path(temporary) / "capture.json"
            evidence_path.write_text('{"unverified":true}\n', encoding="utf-8")
            relative = evidence_path.relative_to(REPO_ROOT).as_posix()
            digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
            broken = copy.deepcopy(self.lock)
            item = broken["evidence"]["acquisition_replay"]
            item.update(
                {
                    "blocker": "captured record still needs review",
                    "evidence_path": relative,
                    "evidence_sha256": digest,
                    "status": "captured-unverified",
                }
            )
            blockers = self.validate(broken)
            self.assertTrue(
                any(blocker.startswith("acquisition_replay:") for blocker in blockers)
            )

            item["blocker"] = ""
            with self.assertRaises(source_lock.SourceLockError):
                self.validate(broken)

    def test_evidence_symlinks_are_rejected_even_when_bytes_match(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            directory = Path(temporary)
            real_path = directory / "real.json"
            link_path = directory / "link.json"
            real_path.write_text('{"captured":true}\n', encoding="utf-8")
            link_path.symlink_to(real_path)
            broken = copy.deepcopy(self.lock)
            item = broken["evidence"]["acquisition_replay"]
            item.update(
                {
                    "blocker": None,
                    "evidence_path": link_path.relative_to(REPO_ROOT).as_posix(),
                    "evidence_sha256": hashlib.sha256(real_path.read_bytes()).hexdigest(),
                    "status": "verified",
                }
            )
            with self.assertRaises(source_lock.SourceLockError):
                self.validate(broken)

    def test_gate_credit_claim_fails_while_license_inventory_is_missing(self) -> None:
        broken = copy.deepcopy(self.lock)
        broken["gate"]["credit_eligible"] = True
        with self.assertRaisesRegex(
            source_lock.SourceLockError, "credit_eligible|silently close"
        ):
            self.validate(broken)

    def test_rehashed_one_line_inventory_cannot_close_rk001(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            path = Path(temporary) / "forged-license-inventory.jsonl"
            path.write_text('{"review_status":"verified"}\n', encoding="utf-8")
            broken = copy.deepcopy(self.lock)
            broken["licenses"]["inventory"].update(
                {
                    "blocker": None,
                    "complete": True,
                    "inventory_path": path.relative_to(REPO_ROOT).as_posix(),
                    "inventory_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "item_count": 1,
                    "status": "verified",
                }
            )
            broken["gate"]["credit_eligible"] = True
            with self.assertRaisesRegex(
                source_lock.SourceLockError, "item_count|credit_eligible"
            ):
                self.validate(broken)

    def test_self_authored_license_decision_cannot_close_rk001(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            path = Path(temporary) / "forged-license-inventory.jsonl"
            path.write_text('{"review_status":"verified"}\n', encoding="utf-8")
            broken = copy.deepcopy(self.lock)
            broken["licenses"]["inventory"].update(
                {
                    "blocker": None,
                    "complete": True,
                    "inventory_path": path.relative_to(REPO_ROOT).as_posix(),
                    "inventory_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "item_count": source_lock.EXPECTED_LICENSE_INVENTORY_ITEM_COUNT,
                    "status": "verified",
                }
            )
            broken["licenses"]["decision"].update(
                {
                    "blocker": None,
                    "decision_path": source_lock.LICENSE_DECISION_PATH,
                    "decision_sha256": "0" * 64,
                    "status": "verified",
                }
            )
            broken["gate"]["credit_eligible"] = True
            with self.assertRaisesRegex(
                source_lock.SourceLockError, "independently reviewed"
            ):
                self.validate(broken)

    def test_unknown_fields_are_rejected(self) -> None:
        broken = copy.deepcopy(self.lock)
        broken["unreviewed_escape_hatch"] = True
        with self.assertRaises(source_lock.SourceLockError):
            self.validate(broken)


class ArtifactTests(SourceLockFixture):
    def test_verify_artifact_checks_size_hash_and_regular_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "artifact.rpm"
            payload = b"locked artifact\n"
            artifact.write_bytes(payload)
            source_lock.verify_artifact(
                artifact, len(payload), hashlib.sha256(payload).hexdigest()
            )
            with self.assertRaises(source_lock.SourceLockError):
                source_lock.verify_artifact(
                    artifact, len(payload) + 1, hashlib.sha256(payload).hexdigest()
                )
            with self.assertRaises(source_lock.SourceLockError):
                source_lock.verify_artifact(artifact, len(payload), "0" * 64)
            link = root / "link.rpm"
            link.symlink_to(artifact)
            with self.assertRaises(source_lock.SourceLockError):
                source_lock.verify_artifact(
                    link, len(payload), hashlib.sha256(payload).hexdigest()
                )

    def test_stream_download_is_atomic_and_rejects_truncation_or_wrong_hash(self) -> None:
        payload = b"source rpm bytes"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "cache" / "source.rpm"
            source_lock.stream_verified_download(
                io.BytesIO(payload), target, len(payload), digest
            )
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(target.stat().st_mode & 0o777, 0o444)

            truncated = root / "truncated.rpm"
            with self.assertRaises(source_lock.SourceLockError):
                source_lock.stream_verified_download(
                    io.BytesIO(payload[:-1]), truncated, len(payload), digest
                )
            self.assertFalse(truncated.exists())

            wrong_hash = root / "wrong-hash.rpm"
            with self.assertRaises(source_lock.SourceLockError):
                source_lock.stream_verified_download(
                    io.BytesIO(payload), wrong_hash, len(payload), "0" * 64
                )
            self.assertFalse(wrong_hash.exists())
            self.assertFalse(
                list(root.glob(".wrong-hash.rpm.*")),
                "failed download left a temporary artifact",
            )

    def test_deterministic_cache_path_stays_within_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = source_lock.artifact_cache_path(root, self.lock)
            self.assertTrue(target.is_relative_to(root.resolve()))
            self.assertEqual(target.name, self.lock["source_rpm"]["filename"])
            self.assertIn(self.lock["source_rpm"]["sha256"], target.parts)

    def test_redirect_handler_rejects_http_and_unlisted_hosts(self) -> None:
        handler = source_lock.PinnedRedirectHandler(["download.rockylinux.org"])
        request = source_lock.urllib.request.Request(
            self.lock["source_rpm"]["url"]
        )
        for redirect in (
            "http://download.rockylinux.org/kernel.rpm",
            "https://evil.invalid/kernel.rpm",
            "https://download.rockylinux.org@evil.invalid/kernel.rpm",
        ):
            with self.subTest(redirect=redirect):
                with self.assertRaises(source_lock.SourceLockError):
                    handler.redirect_request(
                        request, io.BytesIO(), 302, "Found", {}, redirect
                    )


class CommandLineTests(SourceLockFixture):
    def test_check_succeeds_but_gate_ready_returns_one(self) -> None:
        self.assertEqual(source_lock.main(["--repo", str(REPO_ROOT), "--check"]), 0)
        self.assertEqual(
            source_lock.main(["--repo", str(REPO_ROOT), "--gate-ready"]), 1
        )


if __name__ == "__main__":
    unittest.main()
