#!/usr/bin/env python3
"""Review committed RK-001 capture records against the locked Rocky identity.

This checkpoint accepts the four source replay/signature evidence classes.  It
does not claim RK-001 credit: the complete path-by-path license inventory is a
separate mandatory input and remains fail-closed in source-lock.json.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import stat
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_LOCK = "host-kernel/rocky/source-lock.json"
PATCH_SERIES = "host-kernel/rocky/patches/series.json"
REVIEW = "host-kernel/rocky/evidence/source-evidence-review.json"
CHECKPOINT_ID = "rk-001-source-evidence-capture-v1"
REVIEW_ID = "rk-001-source-evidence-review-v1"
EXPECTED_CONTAINER = (
    "rockylinux/rockylinux:10.2@sha256:"
    "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
EXPECTED_FILES = {
    "acquisition_replay": "acquisition_replay",
    "dist_git_object_replay": "dist_git_object_replay",
    "repository_metadata_signature_replay": "repository_metadata_signature_replay",
    "srpm_header_signature": "srpm_header_signature",
}


class ReviewError(Exception):
    pass


def object_without_duplicates(pairs):
    value = {}
    for key, child in pairs:
        if key in value:
            raise ReviewError("duplicate JSON key: {0}".format(key))
        value[key] = child
    return value


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def read_json(path):
    try:
        with open(path, "rb") as stream:
            payload = stream.read()
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=object_without_duplicates)
    except (IOError, OSError, UnicodeError, ValueError) as error:
        raise ReviewError("cannot read {0}: {1}".format(path, error))
    if not isinstance(value, dict):
        raise ReviewError("{0} must contain one JSON object".format(path))
    return value, payload


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def require_keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        actual = set(value) if isinstance(value, dict) else set()
        raise ReviewError(
            "{0} keys differ: missing={1}, extra={2}".format(
                label, sorted(set(keys) - actual), sorted(actual - set(keys))
            )
        )
    return value


def regular_file(repo, relative, label):
    if (
        not isinstance(relative, str)
        or not relative
        or relative.startswith("/")
        or "\\" in relative
        or ".." in relative.split("/")
    ):
        raise ReviewError("unsafe {0} path".format(label))
    root = os.path.realpath(repo)
    requested = os.path.join(root, relative)
    resolved = os.path.realpath(requested)
    try:
        info = os.lstat(requested)
    except OSError as error:
        raise ReviewError("missing {0}: {1}".format(label, error))
    if (
        os.path.commonpath([root, resolved]) != root
        or requested != resolved
        or stat.S_ISLNK(info.st_mode)
        or not stat.S_ISREG(info.st_mode)
    ):
        raise ReviewError("{0} must be a regular repository file".format(label))
    return requested


def binding(record, review, label):
    item = require_keys(record["binding"], {
        "checkpoint_id", "container", "github", "inputs", "schema_version"
    }, label + ".binding")
    if item["schema_version"] != 1 or item["checkpoint_id"] != CHECKPOINT_ID:
        raise ReviewError("{0} checkpoint identity differs".format(label))
    container = item["container"]
    if (
        container.get("image") != EXPECTED_CONTAINER
        or container.get("manifest_digest") != EXPECTED_CONTAINER.rsplit("@", 1)[1]
        or container.get("platform") != "linux/amd64"
    ):
        raise ReviewError("{0} container binding differs".format(label))
    github = item["github"]
    workflow = review["workflow"]
    for key in ("head_sha", "repository", "run_attempt", "run_id"):
        if github.get(key) != workflow[key]:
            raise ReviewError("{0} GitHub {1} binding differs".format(label, key))
    return item


def verify_download(actual, expected, label):
    expected_size = expected.get("size")
    captured_size = actual.get("size")
    captured_length = actual.get("content_length")
    if (
        actual.get("url") != expected["url"]
        or actual.get("final_url") != expected["url"]
        or actual.get("sha256") != expected["sha256"]
        or not isinstance(captured_size, int)
        or captured_size < 1
        or captured_length != captured_size
        or (expected_size is not None and captured_size != expected_size)
        or actual.get("http_status") != 200
        or actual.get("redirect_count") != 0
    ):
        raise ReviewError("{0} download identity differs".format(label))


def verify_acquisition(record, lock):
    result = record["result"]
    source = lock["source_rpm"]
    verify_download(result["download"], source, "source RPM")
    artifact = result["artifact"]
    for key in ("filename", "nevra", "arch"):
        if artifact.get(key) != source[key]:
            raise ReviewError("source RPM artifact {0} differs".format(key))


def verify_dist_git(record, lock, series):
    result = record["result"]
    dist = lock["dist_git"]
    for key in ("repository_url", "tag", "tag_object", "commit", "commit_parent"):
        if result.get(key) != dist[key]:
            raise ReviewError("dist-git {0} differs".format(key))
    if result.get("tag_peel") != dist["commit"] or result.get("http_redirects_allowed") is not False:
        raise ReviewError("dist-git tag peel or redirect policy differs")
    expected = {
        item["path"]: (item["sha256"], item["size"])
        for item in dist["content"]
    }
    for item in series["patches"]:
        expected[item["path"]] = (item["sha256"], item["size"])
    actual = {}
    for item in result["blobs"]:
        if item["path"] in actual:
            raise ReviewError("duplicate dist-git blob path")
        actual[item["path"]] = (item["sha256"], item["size"])
        if not isinstance(item.get("git_blob_oid"), str) or len(item["git_blob_oid"]) != 40:
            raise ReviewError("invalid dist-git blob object ID")
    if actual != expected:
        raise ReviewError("dist-git blob set differs from source lock and patch series")


def verify_repository(record, lock):
    result = record["result"]
    snapshot = lock["repository_snapshot"]
    downloads = result["downloads"]
    verify_download(downloads["release_key"], snapshot["release_key"], "release key")
    verify_download(downloads["repomd"], snapshot["repomd"], "repomd")
    verify_download(
        downloads["repomd_signature"], snapshot["repomd"]["signature"], "repomd signature"
    )
    primary_expected = dict(snapshot["primary_metadata"])
    primary_expected["url"] = snapshot["base_url"] + primary_expected["href"]
    verify_download(downloads["primary"], primary_expected, "primary metadata")
    primary = result["primary"]
    for key in ("href", "sha256", "size", "open_sha256", "open_size", "timestamp"):
        if primary.get(key) != snapshot["primary_metadata"][key]:
            raise ReviewError("primary metadata {0} differs".format(key))
    signature = result["repomd_signature"]
    fingerprint = snapshot["release_key"]["fingerprint"]
    if (
        signature.get("status") != "verified"
        or signature.get("release_key_fingerprint") != fingerprint
        or signature.get("signature_fingerprint") != fingerprint
        or signature.get("primary_fingerprint") != fingerprint
        or signature.get("created_unix") != snapshot["repomd"]["signature"]["created_unix"]
    ):
        raise ReviewError("repomd signature proof differs")


def verify_srpm_signature(record, lock):
    result = record["result"]
    fingerprint = lock["repository_snapshot"]["release_key"]["fingerprint"]
    if (
        result.get("status") != "verified"
        or result.get("signer_fingerprint") != fingerprint
        or result.get("signature_algorithm") != "RSA/SHA256"
        or result.get("hash_algorithm") != "SHA256"
        or result.get("public_key_algorithm") != "RSA"
    ):
        raise ReviewError("SRPM signature proof differs")


def check(repo):
    lock, _ = read_json(regular_file(repo, SOURCE_LOCK, "source lock"))
    series, _ = read_json(regular_file(repo, PATCH_SERIES, "patch series"))
    review, review_payload = read_json(regular_file(repo, REVIEW, "review manifest"))
    if review_payload != (json.dumps(review, indent=2, sort_keys=True) + "\n").encode("utf-8"):
        raise ReviewError("review manifest is not canonical pretty JSON")
    require_keys(review, {
        "artifact", "files", "gate_claim", "review_id", "review_status",
        "schema_version", "workflow"
    }, "review manifest")
    if (
        review["schema_version"] != 1
        or review["review_id"] != REVIEW_ID
        or review["review_status"] != "accepted_capture_not_gate_complete"
        or review["gate_claim"] is not False
    ):
        raise ReviewError("review manifest overclaims or has the wrong identity")
    if set(review["files"]) != set(EXPECTED_FILES):
        raise ReviewError("review manifest evidence classes differ")

    records = {}
    for evidence_id, class_name in EXPECTED_FILES.items():
        file_record = require_keys(
            review["files"][evidence_id], {"path", "sha256"},
            "review.files." + evidence_id
        )
        path = regular_file(repo, file_record["path"], evidence_id)
        record, payload = read_json(path)
        if payload != canonical_bytes(record):
            raise ReviewError("{0} is not canonical JSON".format(evidence_id))
        if sha256_bytes(payload) != file_record["sha256"]:
            raise ReviewError("{0} digest differs".format(evidence_id))
        require_keys(record, {"binding", "evidence_class", "result", "schema_version"}, evidence_id)
        if record["schema_version"] != 1 or record["evidence_class"] != class_name:
            raise ReviewError("{0} class identity differs".format(evidence_id))
        binding(record, review, evidence_id)
        records[evidence_id] = record

    verify_acquisition(records["acquisition_replay"], lock)
    verify_dist_git(records["dist_git_object_replay"], lock, series)
    verify_repository(records["repository_metadata_signature_replay"], lock)
    verify_srpm_signature(records["srpm_header_signature"], lock)
    if lock["gate"]["credit_eligible"] is not False or lock["licenses"]["inventory"]["complete"] is not False:
        raise ReviewError("capture review must not silently close RK-001 or its license inventory")
    return review


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not args.check:
        parser.error("--check is required")
    try:
        review = check(os.path.abspath(args.repo))
    except ReviewError as error:
        print("RK-001 source evidence review failed: {0}".format(error), file=sys.stderr)
        return 1
    print(
        "RK-001 source evidence review accepted: run={0} artifact={1}; "
        "gate credit remains false pending license inventory".format(
            review["workflow"]["run_id"], review["artifact"]["id"]
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
