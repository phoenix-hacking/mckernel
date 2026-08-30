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
EXPECTED_REVIEW = {
    "artifact": {
        "digest": "sha256:86de90ac2488599e6576537049e9ae0426ad06b1f6341de7812f3ffd23cf3993",
        "id": 9128694499,
        "name": "rk001-source-evidence-31563766469-1",
        "size": 8425,
    },
    "capture_context": {
        "path": "capture-context.json",
        "runtime": {
            "architecture": "x86_64",
            "os_release": {"id": "rocky", "version_id": "10.2"},
            "packages": [
                "coreutils-single-0:9.5-7.el10.x86_64",
                "git-core-0:2.52.0-1.el10.x86_64",
                "gnupg2-0:2.4.5-4.el10_1.x86_64",
                "gzip-0:1.13-3.el10.x86_64",
                "python3-0:3.12.13-2.el10_2.1.x86_64",
                "rpm-0:4.19.1.1-23.el10.x86_64",
            ],
            "platform": "linux/amd64",
            "tool_versions": {
                "git": "git version 2.52.0",
                "gpg": "gpg (GnuPG) 2.4.5",
                "gpgv": "gpgv (GnuPG) 2.4.5",
                "gzip": "gzip 1.13",
                "python": "Python 3.12.13",
                "rpm": "RPM version 4.19.1.1",
                "rpmkeys": "RPM version 4.19.1.1",
            },
        },
        "sha256": "ae9560a6f6bbd02d58bb973b92ad0b7702d0b3dda3ca034e087c2bb3f84fcb33",
    },
    "files": {
        "acquisition_replay": {
            "path": "host-kernel/rocky/evidence/acquisition-replay.json",
            "sha256": "d37019bfa3c295867c68461c89bd70d9bcc8417e8dfc6ffd23ff46601280e2a0",
        },
        "dist_git_object_replay": {
            "path": "host-kernel/rocky/evidence/dist-git-object-replay.json",
            "sha256": "359ed16070bd3a401fe733a00581499e6784fa2b017c51cbf3da2bbd7fe499de",
        },
        "repository_metadata_signature_replay": {
            "path": "host-kernel/rocky/evidence/repository-metadata-signature-replay.json",
            "sha256": "4573f66b43019a6b45907a611d3c52a3af4ac92cdacd0ff3c1ee8a945b270dc5",
        },
        "srpm_header_signature": {
            "path": "host-kernel/rocky/evidence/srpm-header-signature.json",
            "sha256": "0106cd8d9ae07a9191affa55f35f7d79390e66ca95c1e85034d3434d06a79901",
        },
    },
    "gate_claim": False,
    "review_id": REVIEW_ID,
    "review_status": "accepted_capture_not_gate_complete",
    "schema_version": 1,
    "workflow": {
        "head_sha": "72be3a56a65958482ce14ee98a9a18b0be4ea4c5",
        "job_id": 94011284079,
        "repository": "phoenix-hacking/mckernel",
        "run_attempt": 1,
        "run_id": 31563766469,
    },
}
EXPECTED_BINDING = {
    "checkpoint_id": CHECKPOINT_ID,
    "container": {
        "image": EXPECTED_CONTAINER,
        "manifest_digest": EXPECTED_CONTAINER.rsplit("@", 1)[1],
        "platform": "linux/amd64",
        "tag_index_digest_observed_at_authoring": (
            "sha256:827d37bc128288ccf160ee318bb3cb92d591164cb217e92f8bc61e3982ae1834"
        ),
    },
    "github": {
        "head_sha": "72be3a56a65958482ce14ee98a9a18b0be4ea4c5",
        "repository": "phoenix-hacking/mckernel",
        "run_attempt": 1,
        "run_id": 31563766469,
    },
    "inputs": {
        "capture_script": {
            "path": "scripts/rocky_kernel_source_evidence.py",
            "sha256": "e117a23159e56e9b3ac737fa7ba786609470399e4354bf81195523263af49ecf",
            "size": 46444,
        },
        "patch_series": {
            "path": "host-kernel/rocky/patches/series.json",
            "sha256": "6a1a5e8fb13b6ce6ed35bd8e5487bb67ecf92d2be927799b660f21b5631f68fb",
            "size": 1454,
        },
        "source_lock": {
            "path": "host-kernel/rocky/source-lock.json",
            "sha256": "6b8571b229f31bf68b58749217391d917a2ba2028ac876e8475be1ec5bfef222",
            "size": 9549,
        },
        "source_lock_validator": {
            "path": "scripts/rocky_kernel_source_lock.py",
            "sha256": "d58e32ad59f89cee72e201b4cfa4f7301b07f2d8783a8682aee19743836e948f",
            "size": 38173,
        },
        "workflow": {
            "path": ".github/workflows/rocky-kernel-source-evidence.yml",
            "sha256": "02861a8d11f12af4e618918a73262def0ba1681a7a162c3cc060a3d2298d0308",
            "size": 5017,
        },
    },
    "schema_version": 1,
}
EXPECTED_BLOB_OIDS = {
    ".kernel.checksum": "0e0888676a21bb1176ede56c31a360c9a78ed159",
    ".kernel.metadata": "d0d48a7c40d09d1dd3305a390acf96d0cf22cf51",
    "SOURCES/1000-debrand-some-messages.patch": "df02897136a7a6825d7998c4dba4cc433dbd9740",
    "SOURCES/kernel-x86_64-rhel.config": "b390068c4142a5a26e60c9774410ed976e48f004",
    "SOURCES/linux-kernel-test.patch": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "SOURCES/patch-6.12-redhat.patch": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "SPECS/kernel.spec": "23c0fc8c47dc5db949e6093abe4975a3801c834e",
}
EXPECTED_TAG_ANNOTATION_SHA256 = (
    "2acc40424a1aeaab3de10cd52f89fea8fd16d39cf8894d36d5c1b3305f28be55"
)
EXPECTED_SRPM_OUTPUT_SHA256 = (
    "e018e9a5d7ed5ea1c21f5a76b1646420af0a6e6d6cec3e5adcd90038cc93c8d2"
)


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


def require_exact(actual, expected, label):
    if type(actual) is not type(expected) or actual != expected:
        raise ReviewError("{0} contradicts the reviewed capture".format(label))


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
    require_exact(item, EXPECTED_BINDING, label + ".binding")
    require_exact(
        item["github"],
        {
            "head_sha": review["workflow"]["head_sha"],
            "repository": review["workflow"]["repository"],
            "run_attempt": review["workflow"]["run_attempt"],
            "run_id": review["workflow"]["run_id"],
        },
        label + ".workflow_binding",
    )
    return item


def expected_download(url, digest, size):
    return {
        "content_length": size,
        "final_url": url,
        "http_status": 200,
        "redirect_count": 0,
        "sha256": digest,
        "size": size,
        "url": url,
    }


def verify_acquisition(record, lock):
    source = lock["source_rpm"]
    expected = {
        "artifact": {
            "arch": source["arch"],
            "filename": source["filename"],
            "nevra": source["nevra"],
        },
        "download": expected_download(
            source["url"], source["sha256"], source["size"]
        ),
    }
    require_exact(record["result"], expected, "acquisition result")


def verify_dist_git(record, lock, series):
    dist = lock["dist_git"]
    blobs = []
    for item in list(dist["content"]) + list(series["patches"]):
        path = item["path"]
        if path not in EXPECTED_BLOB_OIDS:
            raise ReviewError("review has no immutable blob OID for {0}".format(path))
        blobs.append(
            {
                "git_blob_oid": EXPECTED_BLOB_OIDS[path],
                "path": path,
                "sha256": item["sha256"],
                "size": item["size"],
            }
        )
    expected = {
        "blobs": blobs,
        "commit": dist["commit"],
        "commit_parent": dist["commit_parent"],
        "http_redirects_allowed": False,
        "repository_url": dist["repository_url"],
        "tag": dist["tag"],
        "tag_annotation_sha256": EXPECTED_TAG_ANNOTATION_SHA256,
        "tag_object": dist["tag_object"],
        "tag_peel": dist["commit"],
    }
    require_exact(record["result"], expected, "dist-git result")


def verify_repository(record, lock):
    snapshot = lock["repository_snapshot"]
    primary = snapshot["primary_metadata"]
    repomd = snapshot["repomd"]
    release_key = snapshot["release_key"]
    signature = repomd["signature"]
    fingerprint = snapshot["release_key"]["fingerprint"]
    expected = {
        "downloads": {
            "primary": expected_download(
                snapshot["base_url"] + primary["href"],
                primary["sha256"],
                primary["size"],
            ),
            "release_key": expected_download(
                release_key["url"], release_key["sha256"], 1688
            ),
            "repomd": expected_download(repomd["url"], repomd["sha256"], 3180),
            "repomd_signature": expected_download(
                signature["url"], signature["sha256"], 833
            ),
        },
        "primary": dict(primary),
        "repomd_signature": {
            "created_unix": signature["created_unix"],
            "hash_algorithm_id": 8,
            "primary_fingerprint": fingerprint,
            "public_key_algorithm_id": 1,
            "release_key_fingerprint": fingerprint,
            "signature_fingerprint": fingerprint,
            "status": "verified",
        },
    }
    require_exact(record["result"], expected, "repository metadata result")


def verify_srpm_signature(record, lock):
    fingerprint = lock["repository_snapshot"]["release_key"]["fingerprint"]
    expected = {
        "hash_algorithm": "SHA256",
        "isolated_rpm_key_record": "gpg-pubkey-6fedfc85-682ae1a9",
        "public_key_algorithm": "RSA",
        "signature_algorithm": "RSA/SHA256",
        "signature_key_identity": "6FEDFC85",
        "signature_key_identity_type": "key-id",
        "signer_fingerprint": fingerprint,
        "status": "verified",
        "verification_output_sha256": EXPECTED_SRPM_OUTPUT_SHA256,
    }
    require_exact(record["result"], expected, "SRPM signature result")


def check(repo, lock_override=None, series_override=None):
    lock, _ = read_json(regular_file(repo, SOURCE_LOCK, "source lock"))
    series, _ = read_json(regular_file(repo, PATCH_SERIES, "patch series"))
    if lock_override is not None:
        lock = lock_override
    if series_override is not None:
        series = series_override
    review, review_payload = read_json(regular_file(repo, REVIEW, "review manifest"))
    if review_payload != (json.dumps(review, indent=2, sort_keys=True) + "\n").encode("utf-8"):
        raise ReviewError("review manifest is not canonical pretty JSON")
    require_exact(review, EXPECTED_REVIEW, "review manifest")

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
