#!/usr/bin/env python3
"""Capture a bounded, signed Rocky repository-metadata snapshot.

This is a capture and drift-diagnostics checkpoint, not an acceptance gate.
The versioned contract hard-codes every credit and gate claim to ``false``.
The captured tar contains the exact release key, repomd.xml, detached
signature, and every metadata object referenced by each verified repomd.xml.
"""

import argparse
import bz2
import gzip
import hashlib
import json
import lzma
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


CONTRACT_PATH = Path(
    "host-kernel/rocky/evidence/repository-snapshot-capture-contract-v2.json"
)
CHECKER_PATH = Path("scripts/rocky_repository_snapshot_capture.py")
TEST_PATH = Path("scripts/tests/test_rocky_repository_snapshot_capture.py")
WORKFLOW_PATH = Path(".github/workflows/rocky-repository-snapshot-capture-v2.yml")
CAPTURE_ID = "rocky-10.2-x86_64-repository-metadata-capture-v2"
RELEASE_FINGERPRINT = "FC226859C0860BF0DDB95B085B106C736FEDFC85"
RELEASE_KEY_SHA256 = (
    "be8c4f070b696e64d8ce40e59a95a57e8b5c776f0015c2fd64e14b896622bdb4"
)
RELEASE_KEY_SIZE = 1688
RELEASE_KEY_URL = "https://download.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-10"
REPOSITORIES = [
    (
        "source-baseos",
        "source",
        "https://download.rockylinux.org/pub/rocky/10.2/BaseOS/source/tree/",
    ),
    (
        "baseos",
        "binary",
        "https://download.rockylinux.org/pub/rocky/10.2/BaseOS/x86_64/os/",
    ),
    (
        "appstream",
        "binary",
        "https://download.rockylinux.org/pub/rocky/10.2/AppStream/x86_64/os/",
    ),
    (
        "crb",
        "binary",
        "https://download.rockylinux.org/pub/rocky/10.2/CRB/x86_64/os/",
    ),
]
REQUIRED_INPUTS = {
    "checker": CHECKER_PATH.as_posix(),
    "contract": CONTRACT_PATH.as_posix(),
    "tests": TEST_PATH.as_posix(),
    "workflow": WORKFLOW_PATH.as_posix(),
}
FALSE_CLAIMS = {
    "accepted_checkpoint": False,
    "credit_eligible": False,
    "durable_archive": False,
    "gate_rk_001": False,
    "gate_rk_003": False,
    "gate_rk_005": False,
    "old_checkpoint_replaced": False,
    "repository_metadata_closure_accepted": False,
    "routine_ci_replay_ready": False,
    "rpm_closure_complete": False,
    "tracker_credit": False,
}
TARGET = {
    "architecture": "x86_64",
    "distribution": "Rocky Linux",
    "release": "10.2",
}

MAX_JSON_BYTES = 2 * 1024 * 1024
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REPO_ID = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
REPOMD_NS = "http://linux.duke.edu/metadata/repo"


class SnapshotError(RuntimeError):
    """A fail-closed snapshot capture or verification error."""


def canonical_json_bytes(value):
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise SnapshotError("value is not canonical-JSON serializable: {}".format(exc))
    return (text + "\n").encode("ascii")


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotError("duplicate JSON key: {!r}".format(key))
        result[key] = value
    return result


def strict_json_bytes(data, label):
    if len(data) > MAX_JSON_BYTES:
        raise SnapshotError("{} exceeds the JSON size limit".format(label))
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs
        )
    except (UnicodeDecodeError, json.JSONDecodeError, SnapshotError) as exc:
        raise SnapshotError("cannot parse {}: {}".format(label, exc))
    if not isinstance(value, dict):
        raise SnapshotError("{} must contain one JSON object".format(label))
    return value


def exact_keys(value, expected, label):
    if not isinstance(value, dict):
        raise SnapshotError("{} must be an object".format(label))
    actual = set(value)
    wanted = set(expected)
    if actual != wanted:
        raise SnapshotError(
            "{} fields changed: actual={}, expected={}".format(
                label, sorted(actual), sorted(wanted)
            )
        )
    return value


def require_exact(actual, expected, label):
    if actual != expected or type(actual) is not type(expected):
        raise SnapshotError(
            "{} changed: actual={!r}, expected={!r}".format(label, actual, expected)
        )


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise SnapshotError("cannot hash {}: {}".format(path, exc))
    return size, digest.hexdigest()


def normalized_relative_path(value, label):
    if not isinstance(value, str) or not value or "\\" in value or "%" in value:
        raise SnapshotError("{} must be a plain normalized relative path".format(label))
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise SnapshotError("{} is not a normalized relative path".format(label))
    if path.as_posix() != value:
        raise SnapshotError("{} is not canonically spelled".format(label))
    return path


def within(root, candidate):
    try:
        return Path(os.path.commonpath((str(root), str(candidate)))) == root
    except ValueError:
        return False


def lexical_absolute_path(path, label):
    try:
        result = Path(os.path.abspath(str(path)))
    except (OSError, TypeError, ValueError) as exc:
        raise SnapshotError("{} is not a usable path: {}".format(label, exc))
    if not result.is_absolute():
        raise SnapshotError("{} did not normalize to an absolute path".format(label))
    return result


def require_real_directory_path(path, label):
    """Require an existing directory path with no symlink component."""
    current = Path(path.parts[0])
    for part in path.parts[1:]:
        current = current / part
        try:
            metadata = os.lstat(str(current))
        except OSError as exc:
            raise SnapshotError(
                "{} contains a missing or unreadable directory {}: {}".format(
                    label, current, exc
                )
            )
        if stat.S_ISLNK(metadata.st_mode):
            raise SnapshotError("{} contains a symlink component: {}".format(label, current))
        if not stat.S_ISDIR(metadata.st_mode):
            raise SnapshotError(
                "{} contains a non-directory component: {}".format(label, current)
            )


def lstat_optional(path, label):
    try:
        return os.lstat(str(path))
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SnapshotError("cannot inspect {} {}: {}".format(label, path, exc))


def path_contains(parent, child):
    try:
        return Path(os.path.commonpath((str(parent), str(child)))) == parent
    except ValueError:
        return False


def validate_capture_destinations(output_dir, diagnostics_dir):
    output_dir = lexical_absolute_path(output_dir, "capture output directory")
    diagnostics_dir = (
        lexical_absolute_path(diagnostics_dir, "capture diagnostics directory")
        if diagnostics_dir is not None
        else None
    )
    if diagnostics_dir is not None and (
        path_contains(output_dir, diagnostics_dir)
        or path_contains(diagnostics_dir, output_dir)
    ):
        raise SnapshotError(
            "capture output and diagnostics directories must not overlap"
        )

    require_real_directory_path(
        output_dir.parent, "capture output directory parent path"
    )
    output_metadata = lstat_optional(output_dir, "capture output directory")
    if output_metadata is not None:
        if stat.S_ISLNK(output_metadata.st_mode):
            raise SnapshotError("capture output directory must not be a symlink")
        raise SnapshotError("capture output directory must not already exist")

    if diagnostics_dir is not None:
        require_real_directory_path(
            diagnostics_dir.parent, "capture diagnostics directory parent path"
        )
        diagnostics_metadata = lstat_optional(
            diagnostics_dir, "capture diagnostics directory"
        )
        if diagnostics_metadata is not None:
            if stat.S_ISLNK(diagnostics_metadata.st_mode):
                raise SnapshotError("capture diagnostics directory must not be a symlink")
            if not stat.S_ISDIR(diagnostics_metadata.st_mode):
                raise SnapshotError(
                    "capture diagnostics destination must be a directory"
                )
    return output_dir, diagnostics_dir


def validate_artifact_path(artifact):
    artifact = lexical_absolute_path(artifact, "snapshot artifact")
    require_real_directory_path(artifact.parent, "snapshot artifact parent path")
    metadata = lstat_optional(artifact, "snapshot artifact")
    if metadata is None:
        raise SnapshotError("snapshot artifact does not exist")
    if stat.S_ISLNK(metadata.st_mode):
        raise SnapshotError("snapshot artifact must not be a symlink")
    if not stat.S_ISREG(metadata.st_mode):
        raise SnapshotError("snapshot artifact must be a regular file")
    return artifact


def regular_repository_file(repo, relative):
    relative = normalized_relative_path(relative.as_posix(), "repository path")
    root = repo.resolve()
    requested = root.joinpath(*relative.parts)
    resolved = requested.resolve()
    if not within(root, resolved):
        raise SnapshotError("repository path escapes checkout: {}".format(relative))
    if requested != resolved or requested.is_symlink() or not requested.is_file():
        raise SnapshotError(
            "repository input must be a regular file without symlink traversal: {}".format(
                relative
            )
        )
    return requested


def load_contract(repo):
    path = regular_repository_file(repo, CONTRACT_PATH)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SnapshotError("cannot read capture contract: {}".format(exc))
    contract = strict_json_bytes(data, CONTRACT_PATH.as_posix())
    validate_contract(contract)
    return contract, data


def validate_contract(contract):
    exact_keys(
        contract,
        {
            "artifact",
            "capture_id",
            "claims",
            "diagnostic_baselines",
            "limits",
            "network",
            "release_key",
            "repositories",
            "required_repository_inputs",
            "schema_version",
            "target",
        },
        "capture contract",
    )
    require_exact(contract["schema_version"], 2, "contract schema_version")
    require_exact(contract["capture_id"], CAPTURE_ID, "contract capture_id")
    require_exact(contract["claims"], FALSE_CLAIMS, "contract claims")
    require_exact(contract["target"], TARGET, "contract target")
    require_exact(
        contract["required_repository_inputs"],
        REQUIRED_INPUTS,
        "contract repository inputs",
    )
    release_key = exact_keys(
        contract["release_key"],
        {"fingerprint", "sha256", "size", "url"},
        "release_key",
    )
    require_exact(release_key["fingerprint"], RELEASE_FINGERPRINT, "key fingerprint")
    require_exact(release_key["sha256"], RELEASE_KEY_SHA256, "key sha256")
    require_exact(release_key["size"], RELEASE_KEY_SIZE, "key size")
    require_exact(release_key["url"], RELEASE_KEY_URL, "key URL")

    actual_repositories = []
    if not isinstance(contract["repositories"], list):
        raise SnapshotError("contract repositories must be an array")
    for index, row in enumerate(contract["repositories"]):
        row = exact_keys(row, {"base_url", "id", "kind"}, "repository row")
        if not isinstance(row["id"], str) or not REPO_ID.fullmatch(row["id"]):
            raise SnapshotError("repository id is invalid at index {}".format(index))
        actual_repositories.append((row["id"], row["kind"], row["base_url"]))
    require_exact(actual_repositories, REPOSITORIES, "repository set and order")

    claims = contract["claims"]
    if any(value is not False for value in claims.values()):
        raise SnapshotError("every capture claim must remain false")

    network = exact_keys(
        contract["network"], {"allowed_hosts", "policy"}, "network policy"
    )
    require_exact(network["allowed_hosts"], ["download.rockylinux.org"], "allowed hosts")
    if not isinstance(network["policy"], str) or "HTTPS only" not in network["policy"]:
        raise SnapshotError("network policy must explicitly require HTTPS")

    limits = exact_keys(
        contract["limits"],
        {
            "download_timeout_seconds",
            "max_key_bytes",
            "max_metadata_object_bytes",
            "max_metadata_open_bytes",
            "max_open_bytes_total",
            "max_repository_objects",
            "max_repomd_bytes",
            "max_signature_bytes",
            "max_total_download_bytes",
            "redirect_limit",
        },
        "limits",
    )
    for name, value in limits.items():
        if type(value) is not int or value <= 0:
            raise SnapshotError("limit {} must be a positive integer".format(name))
    if limits["redirect_limit"] > 10 or limits["max_repository_objects"] > 256:
        raise SnapshotError("capture redirect/object limits are not bounded tightly enough")
    if limits["max_metadata_object_bytes"] > limits["max_total_download_bytes"]:
        raise SnapshotError("per-object byte limit exceeds the total download limit")
    if limits["max_metadata_open_bytes"] > limits["max_open_bytes_total"]:
        raise SnapshotError("per-object open-byte limit exceeds the total open-byte limit")

    artifact = exact_keys(
        contract["artifact"],
        {
            "deterministic_payload",
            "deterministic_payload_digest",
            "format",
            "retention_days",
        },
        "artifact policy",
    )
    require_exact(artifact["deterministic_payload"], "snapshot.tar", "payload name")
    require_exact(
        artifact["deterministic_payload_digest"],
        "snapshot.tar.sha256",
        "payload digest name",
    )
    require_exact(artifact["retention_days"], 30, "artifact retention")

    baselines = contract["diagnostic_baselines"]
    if not isinstance(baselines, list) or len(baselines) != len(REPOSITORIES):
        raise SnapshotError("diagnostic baselines must cover every repository exactly once")
    ids = []
    for row in baselines:
        row = exact_keys(
            row,
            {
                "id",
                "primary_sha256",
                "primary_size",
                "repomd_sha256",
                "signature_sha256",
            },
            "diagnostic baseline",
        )
        ids.append(row["id"])
        for field in ("primary_sha256", "repomd_sha256", "signature_sha256"):
            if not isinstance(row[field], str) or not SHA256.fullmatch(row[field]):
                raise SnapshotError("baseline {} must be a SHA-256".format(field))
        if type(row["primary_size"]) is not int or row["primary_size"] <= 0:
            raise SnapshotError("baseline primary_size must be positive")
    require_exact(ids, [row[0] for row in REPOSITORIES], "baseline repository order")


def check_repository_inputs(repo):
    contract, data = load_contract(repo)
    records = []
    for role in sorted(REQUIRED_INPUTS):
        relative = Path(REQUIRED_INPUTS[role])
        path = regular_repository_file(repo, relative)
        size, digest = sha256_file(path)
        records.append(
            {
                "path": relative.as_posix(),
                "role": role,
                "sha256": digest,
                "size": size,
            }
        )
    if sha256_bytes(data) != records[1]["sha256"]:
        raise SnapshotError("internal contract input digest mismatch")
    return contract, records


def validate_https_url(url, allowed_hosts, label, required_prefix=None):
    if not isinstance(url, str) or not url:
        raise SnapshotError("{} must be a non-empty HTTPS URL".format(label))
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or not parsed.path.startswith("/")
        or "%" in parsed.path
        or "\\" in parsed.path
        or any(part in (".", "..") for part in parsed.path.split("/"))
        or parsed.query
        or parsed.fragment
        or urllib.parse.urlunsplit(parsed) != url
    ):
        raise SnapshotError("{} is outside the locked HTTPS policy".format(label))
    if required_prefix is not None and not url.startswith(required_prefix):
        raise SnapshotError("{} escaped its repository base URL".format(label))
    return url


class BoundedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts, redirect_limit, required_prefix=None):
        urllib.request.HTTPRedirectHandler.__init__(self)
        self.allowed_hosts = allowed_hosts
        self.redirect_limit = redirect_limit
        self.required_prefix = required_prefix
        self.redirect_count = 0

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > self.redirect_limit:
            raise SnapshotError("download exceeded the redirect limit")
        validate_https_url(
            newurl,
            self.allowed_hosts,
            "redirect URL",
            required_prefix=self.required_prefix,
        )
        return urllib.request.HTTPRedirectHandler.redirect_request(
            self, request, fp, code, msg, headers, newurl
        )


def download_to_path(url, destination, maximum, contract, required_prefix=None):
    allowed_hosts = contract["network"]["allowed_hosts"]
    validate_https_url(url, allowed_hosts, "download URL", required_prefix)
    handler = BoundedRedirectHandler(
        allowed_hosts,
        contract["limits"]["redirect_limit"],
        required_prefix=required_prefix,
    )
    opener = urllib.request.build_opener(handler)
    request = urllib.request.Request(
        url,
        headers={
            "Accept-Encoding": "identity",
            "User-Agent": "mckernel-rocky-snapshot-capture-v2",
        },
    )
    try:
        response = opener.open(
            request, timeout=contract["limits"]["download_timeout_seconds"]
        )
    except (OSError, urllib.error.URLError, SnapshotError) as exc:
        raise SnapshotError("download failed for {}: {}".format(url, exc))
    try:
        status = response.getcode()
        if status != 200:
            raise SnapshotError("download returned HTTP {} for {}".format(status, url))
        final_url = response.geturl()
        validate_https_url(
            final_url, allowed_hosts, "final download URL", required_prefix
        )
        encoding = response.headers.get("Content-Encoding")
        if encoding not in (None, "", "identity"):
            raise SnapshotError("download used a forbidden content encoding")
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                announced = int(content_length)
            except ValueError:
                raise SnapshotError("download Content-Length is not an integer")
            if announced < 0 or announced > maximum:
                raise SnapshotError("download Content-Length exceeds its byte limit")
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        try:
            with destination.open("xb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > maximum:
                        raise SnapshotError("download exceeded its byte limit")
                    digest.update(chunk)
                    output.write(chunk)
        except OSError as exc:
            raise SnapshotError("cannot write download {}: {}".format(destination, exc))
        if content_length is not None and size != announced:
            raise SnapshotError("download length differs from Content-Length")
        return {
            "final_url": final_url,
            "redirect_count": handler.redirect_count,
            "sha256": digest.hexdigest(),
            "size": size,
            "url": url,
        }
    finally:
        response.close()


def run_checked(command, label, environment=None):
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=environment,
        )
    except OSError as exc:
        raise SnapshotError("cannot run {}: {}".format(label, exc))
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", "replace").strip()
        raise SnapshotError(
            "{} failed with status {}: {}".format(
                label, completed.returncode, stderr[-800:]
            )
        )
    return completed.stdout, completed.stderr


def verify_key_fingerprint(key_path, expected_fingerprint):
    with tempfile.TemporaryDirectory(prefix="mck-rocky-snapshot-key.") as home_text:
        home = Path(home_text)
        os.chmod(str(home), 0o700)
        environment = os.environ.copy()
        environment.update({"GNUPGHOME": str(home), "LC_ALL": "C"})
        stdout, _ = run_checked(
            [
                "gpg",
                "--batch",
                "--no-options",
                "--homedir",
                str(home),
                "--with-colons",
                "--show-keys",
                str(key_path),
            ],
            "release-key fingerprint inspection",
            environment,
        )
    primary_fingerprints = []
    waiting_for_primary = False
    for raw_line in stdout.decode("utf-8", "replace").splitlines():
        fields = raw_line.split(":")
        if fields[0] == "pub":
            waiting_for_primary = True
        elif fields[0] == "fpr" and waiting_for_primary:
            primary_fingerprints.append(fields[9].upper())
            waiting_for_primary = False
    if primary_fingerprints != [expected_fingerprint]:
        raise SnapshotError(
            "release key primary fingerprints changed: {}".format(primary_fingerprints)
        )
    return expected_fingerprint


def verify_detached_signature(key_path, signature_path, signed_path, fingerprint):
    with tempfile.TemporaryDirectory(prefix="mck-rocky-snapshot-gpg.") as home_text:
        home = Path(home_text)
        os.chmod(str(home), 0o700)
        environment = os.environ.copy()
        environment.update({"GNUPGHOME": str(home), "LC_ALL": "C"})
        keyring = home / "release-key.gpg"
        run_checked(
            [
                "gpg",
                "--batch",
                "--no-options",
                "--no-autostart",
                "--homedir",
                str(home),
                "--dearmor",
                "--output",
                str(keyring),
                str(key_path),
            ],
            "release-key dearmor",
            environment,
        )
        stdout, _ = run_checked(
            [
                "gpgv",
                "--status-fd",
                "1",
                "--keyring",
                str(keyring),
                str(signature_path),
                str(signed_path),
            ],
            "repomd detached-signature verification",
            environment,
        )
    valid = []
    for line in stdout.decode("utf-8", "replace").splitlines():
        if line.startswith("[GNUPG:] VALIDSIG "):
            fields = line.split()
            if len(fields) != 12 or fields[0:2] != ["[GNUPG:]", "VALIDSIG"]:
                raise SnapshotError("gpgv emitted a malformed VALIDSIG status")
            valid.append(
                {
                    "hash_algorithm_id": int(fields[9]),
                    "primary_fingerprint": fields[-1].upper(),
                    "public_key_algorithm_id": int(fields[8]),
                    "signature_fingerprint": fields[2].upper(),
                    "signature_timestamp": int(fields[4]),
                    "status": "verified",
                }
            )
    if len(valid) != 1 or valid[0]["primary_fingerprint"] != fingerprint:
        raise SnapshotError("repomd signature is not bound to the pinned primary key")
    if (
        valid[0]["public_key_algorithm_id"] != 1
        or valid[0]["hash_algorithm_id"] != 8
    ):
        raise SnapshotError("repomd signature must use RSA with SHA-256")
    return valid[0]


def integer_text(element, label, required=True):
    if element is None:
        if required:
            raise SnapshotError("repomd entry is missing {}".format(label))
        return None
    text = element.text
    if (
        element.attrib
        or len(element)
        or not isinstance(text, str)
        or not re.fullmatch(r"[0-9]+", text)
    ):
        raise SnapshotError("repomd {} is not a nonnegative integer".format(label))
    return int(text)


def checksum_element(element, label, required=True):
    if element is None:
        if required:
            raise SnapshotError("repomd entry is missing {}".format(label))
        return None
    if element.attrib != {"type": "sha256"} or len(element):
        raise SnapshotError("repomd {} must use SHA-256 only".format(label))
    value = element.text
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise SnapshotError("repomd {} is not a lowercase SHA-256".format(label))
    return value


def parse_repomd(data, maximum_objects):
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise SnapshotError("cannot parse repomd.xml: {}".format(exc))
    if root.tag != "{{{}}}repomd".format(REPOMD_NS):
        raise SnapshotError("repomd.xml has an unexpected root element")
    namespace = {"repo": REPOMD_NS}
    allowed_root_children = {"revision", "tags", "data"}
    root_child_counts = {}
    for child in root:
        prefix = "{{{}}}".format(REPOMD_NS)
        if not child.tag.startswith(prefix):
            raise SnapshotError("repomd.xml contains a foreign-namespace child")
        name = child.tag[len(prefix) :]
        if name not in allowed_root_children:
            raise SnapshotError("repomd.xml contains an unexpected child")
        root_child_counts[name] = root_child_counts.get(name, 0) + 1
    if root_child_counts.get("revision") != 1 or root_child_counts.get("tags", 0) > 1:
        raise SnapshotError("repomd.xml revision/tags multiplicity changed")
    revision = root.find("repo:revision", namespace)
    if revision is None or revision.text != "10.2" or revision.attrib:
        raise SnapshotError("repomd revision must be exactly 10.2")
    elements = root.findall("repo:data", namespace)
    if not elements or len(elements) > maximum_objects:
        raise SnapshotError("repomd metadata-object count is outside the contract")
    rows = []
    seen_types = set()
    seen_hrefs = set()
    for element in elements:
        if set(element.attrib) != {"type"}:
            raise SnapshotError("repomd data entry attributes changed")
        data_type = element.attrib["type"]
        if not re.fullmatch(r"[a-z0-9_+-]+", data_type) or data_type in seen_types:
            raise SnapshotError("repomd data type is invalid or duplicated")
        seen_types.add(data_type)
        allowed_children = {
            "checksum",
            "database_version",
            "location",
            "open-checksum",
            "open-size",
            "size",
            "timestamp",
        }
        child_counts = {}
        prefix = "{{{}}}".format(REPOMD_NS)
        for child in element:
            if not child.tag.startswith(prefix):
                raise SnapshotError("repomd data contains a foreign-namespace child")
            child_name = child.tag[len(prefix) :]
            if child_name not in allowed_children:
                raise SnapshotError("repomd data contains an unexpected child")
            child_counts[child_name] = child_counts.get(child_name, 0) + 1
        for child_name in ("checksum", "location", "size", "timestamp"):
            if child_counts.get(child_name) != 1:
                raise SnapshotError(
                    "repomd data {} multiplicity changed".format(child_name)
                )
        for child_name in ("database_version", "open-checksum", "open-size"):
            if child_counts.get(child_name, 0) > 1:
                raise SnapshotError(
                    "repomd data {} multiplicity changed".format(child_name)
                )
        location = element.find("repo:location", namespace)
        if (
            location is None
            or set(location.attrib) != {"href"}
            or len(location)
            or (location.text is not None and location.text.strip())
        ):
            raise SnapshotError("repomd location must contain only href")
        href = normalized_relative_path(location.attrib["href"], "repomd href").as_posix()
        if not href.startswith("repodata/") or href in seen_hrefs:
            raise SnapshotError("repomd href is outside repodata or duplicated")
        seen_hrefs.add(href)
        compressed_sha256 = checksum_element(
            element.find("repo:checksum", namespace), "checksum"
        )
        compressed_size = integer_text(element.find("repo:size", namespace), "size")
        integer_text(element.find("repo:timestamp", namespace), "timestamp")
        integer_text(
            element.find("repo:database_version", namespace),
            "database_version",
            required=False,
        )
        open_checksum_element = element.find("repo:open-checksum", namespace)
        open_size_element = element.find("repo:open-size", namespace)
        if (open_checksum_element is None) != (open_size_element is None):
            raise SnapshotError("repomd open checksum and size must appear together")
        open_sha256 = checksum_element(
            open_checksum_element, "open-checksum", required=False
        )
        open_size = integer_text(open_size_element, "open-size", required=False)
        compression = compression_for_href(href)
        if compression != "none" and (open_sha256 is None or open_size is None):
            raise SnapshotError("compressed repomd objects require open hash and size")
        rows.append(
            {
                "compressed_sha256": compressed_sha256,
                "compressed_size": compressed_size,
                "compression": compression,
                "href": href,
                "open_sha256": open_sha256,
                "open_size": open_size,
                "type": data_type,
            }
        )
    if "primary" not in seen_types:
        raise SnapshotError("repomd does not name primary metadata")
    return {"objects": rows, "revision": "10.2"}


def compression_for_href(href):
    if href.endswith(".gz"):
        return "gzip"
    if href.endswith(".bz2"):
        return "bzip2"
    if href.endswith(".xz"):
        return "xz"
    if href.endswith((".xml", ".sqlite")):
        return "none"
    raise SnapshotError("unsupported or ambiguous metadata compression: {}".format(href))


def open_metadata_stream(path, compression):
    if compression == "gzip":
        return gzip.open(str(path), "rb")
    if compression == "bzip2":
        return bz2.open(str(path), "rb")
    if compression == "xz":
        return lzma.open(str(path), "rb")
    if compression == "none":
        return path.open("rb")
    raise SnapshotError("unknown metadata compression: {}".format(compression))


def verify_metadata_object(path, row, per_open_limit, total_open_counter):
    size, digest = sha256_file(path)
    if size != row["compressed_size"] or digest != row["compressed_sha256"]:
        raise SnapshotError("metadata object compressed bytes differ from repomd.xml")
    open_digest = hashlib.sha256()
    open_size = 0
    try:
        with open_metadata_stream(path, row["compression"]) as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                open_size += len(chunk)
                total_open_counter[0] += len(chunk)
                if open_size > per_open_limit:
                    raise SnapshotError("opened metadata object exceeds its byte limit")
                if total_open_counter[0] > total_open_counter[1]:
                    raise SnapshotError("opened metadata exceeds the total byte limit")
                open_digest.update(chunk)
    except SnapshotError:
        raise
    except (OSError, EOFError, lzma.LZMAError) as exc:
        raise SnapshotError("cannot decompress metadata object: {}".format(exc))
    opened_sha256 = open_digest.hexdigest()
    if row["open_size"] is not None:
        if open_size != row["open_size"] or opened_sha256 != row["open_sha256"]:
            raise SnapshotError("metadata object open bytes differ from repomd.xml")
        declared = True
    else:
        if row["compression"] != "none":
            raise SnapshotError("compressed metadata lacks an open-byte binding")
        declared = False
    result = dict(row)
    result.update(
        {
            "open_checksum_declared": declared,
            "verified_open_sha256": opened_sha256,
            "verified_open_size": open_size,
        }
    )
    return result


def safe_write_json(path, value):
    data = canonical_json_bytes(value)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        path.write_bytes(data)
        os.chmod(str(path), 0o600)
    except OSError as exc:
        raise SnapshotError("cannot write {}: {}".format(path, exc))


def diagnostics_claims():
    return {
        "accepted_checkpoint": False,
        "credit_eligible": False,
        "durable_archive": False,
        "tracker_credit": False,
    }


def write_capture_diagnostics(diagnostics_dir, state, error=None):
    if diagnostics_dir is None:
        return
    diagnostics_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    value = {
        "capture_id": CAPTURE_ID,
        "claims": diagnostics_claims(),
        "error": error,
        "observations": state,
        "schema_version": 1,
        "status": "failed" if error is not None else "bounded-capture-complete",
    }
    safe_write_json(diagnostics_dir / "drift-report.json", value)


def repository_archive_path(repository_id, href):
    href_path = normalized_relative_path(href, "repository object href")
    return Path("repositories") / repository_id / Path(*href_path.parts)


def build_repository_record(tree, repository, contract, total_open_counter):
    repository_id = repository["id"]
    root = tree / "repositories" / repository_id
    repomd_path = root / "repodata" / "repomd.xml"
    signature_path = root / "repodata" / "repomd.xml.asc"
    key_path = tree / "release-key" / "RPM-GPG-KEY-Rocky-10"
    repomd_size, repomd_sha256 = sha256_file(repomd_path)
    signature_size, signature_sha256 = sha256_file(signature_path)
    if repomd_size > contract["limits"]["max_repomd_bytes"]:
        raise SnapshotError("captured repomd.xml exceeds its byte limit")
    if signature_size > contract["limits"]["max_signature_bytes"]:
        raise SnapshotError("captured repomd signature exceeds its byte limit")
    try:
        repomd_data = repomd_path.read_bytes()
    except OSError as exc:
        raise SnapshotError("cannot read captured repomd.xml: {}".format(exc))
    parsed = parse_repomd(repomd_data, contract["limits"]["max_repository_objects"])
    signature = verify_detached_signature(
        key_path, signature_path, repomd_path, RELEASE_FINGERPRINT
    )
    objects = []
    for row in parsed["objects"]:
        path = tree / repository_archive_path(repository_id, row["href"])
        objects.append(
            verify_metadata_object(
                path,
                row,
                contract["limits"]["max_metadata_open_bytes"],
                total_open_counter,
            )
        )
    signature_record_path = root / "repodata" / "signature.json"
    try:
        signature_record = strict_json_bytes(
            signature_record_path.read_bytes(), signature_record_path.as_posix()
        )
    except OSError as exc:
        raise SnapshotError("cannot read signature record: {}".format(exc))
    require_exact(signature_record, signature, "captured signature record")
    primary = [row for row in objects if row["type"] == "primary"][0]
    return {
        "base_url": repository["base_url"],
        "id": repository_id,
        "kind": repository["kind"],
        "metadata_object_count": len(objects),
        "objects": objects,
        "primary": {
            "href": primary["href"],
            "sha256": primary["compressed_sha256"],
            "size": primary["compressed_size"],
        },
        "repomd": {
            "revision": parsed["revision"],
            "sha256": repomd_sha256,
            "size": repomd_size,
        },
        "signature": dict(
            signature,
            sha256=signature_sha256,
            size=signature_size,
        ),
    }


def payload_file_records(tree):
    records = []
    for path in sorted(tree.rglob("*")):
        if path.is_dir():
            continue
        if path.is_symlink() or not path.is_file():
            raise SnapshotError("snapshot tree contains a non-regular payload entry")
        relative = path.relative_to(tree).as_posix()
        if relative == "capture-manifest.json":
            continue
        normalized_relative_path(relative, "payload path")
        size, digest = sha256_file(path)
        records.append({"path": relative, "sha256": digest, "size": size})
    return records


def build_capture_manifest(tree, repo, contract, input_records):
    contract_copy = tree / "inputs" / CONTRACT_PATH
    try:
        copied_contract = contract_copy.read_bytes()
    except OSError as exc:
        raise SnapshotError("cannot read archived contract input: {}".format(exc))
    _, repository_contract_data = load_contract(repo)
    if copied_contract != repository_contract_data:
        raise SnapshotError("archived contract differs from the repository input")
    for record in input_records:
        archived = tree / "inputs" / Path(record["path"])
        size, digest = sha256_file(archived)
        if size != record["size"] or digest != record["sha256"]:
            raise SnapshotError("archived repository input differs: {}".format(record["path"]))

    key_path = tree / "release-key" / "RPM-GPG-KEY-Rocky-10"
    key_size, key_sha256 = sha256_file(key_path)
    require_exact(key_size, contract["release_key"]["size"], "release key size")
    require_exact(key_sha256, contract["release_key"]["sha256"], "release key SHA-256")
    fingerprint = verify_key_fingerprint(key_path, contract["release_key"]["fingerprint"])

    total_open_counter = [0, contract["limits"]["max_open_bytes_total"]]
    repositories = []
    for repository in contract["repositories"]:
        repositories.append(
            build_repository_record(tree, repository, contract, total_open_counter)
        )
    identity_rows = []
    for row in repositories:
        identity_rows.append(
            {
                "id": row["id"],
                "object_bindings": [
                    {
                        "href": item["href"],
                        "sha256": item["compressed_sha256"],
                        "size": item["compressed_size"],
                    }
                    for item in row["objects"]
                ],
                "repomd_sha256": row["repomd"]["sha256"],
                "signature_sha256": row["signature"]["sha256"],
            }
        )
    snapshot_identity = sha256_bytes(canonical_json_bytes(identity_rows))
    return {
        "capture_id": CAPTURE_ID,
        "capture_results": {
            "all_declared_open_checksums_verified": True,
            "all_repomd_objects_archived": True,
            "all_repomd_signatures_verified": True,
            "release_key_verified": True,
        },
        "claims": FALSE_CLAIMS,
        "payload_files": payload_file_records(tree),
        "release_key": {
            "fingerprint": fingerprint,
            "path": "release-key/RPM-GPG-KEY-Rocky-10",
            "sha256": key_sha256,
            "size": key_size,
        },
        "repositories": repositories,
        "repository_inputs": input_records,
        "schema_version": 2,
        "snapshot_identity": snapshot_identity,
        "target": TARGET,
    }


def drift_rows(contract, repository_records):
    baselines = {row["id"]: row for row in contract["diagnostic_baselines"]}
    result = []
    for current in repository_records:
        baseline = baselines[current["id"]]
        current_values = {
            "primary_sha256": current["primary"]["sha256"],
            "primary_size": current["primary"]["size"],
            "repomd_sha256": current["repomd"]["sha256"],
            "signature_sha256": current["signature"]["sha256"],
        }
        expected_values = {key: baseline[key] for key in sorted(current_values)}
        changed_fields = [
            key for key in sorted(current_values) if current_values[key] != expected_values[key]
        ]
        result.append(
            {
                "baseline": expected_values,
                "changed_fields": changed_fields,
                "current": current_values,
                "drift_observed": bool(changed_fields),
                "id": current["id"],
            }
        )
    return result


def copy_repository_inputs(repo, tree, input_records):
    for record in input_records:
        source = regular_repository_file(repo, Path(record["path"]))
        destination = tree / "inputs" / Path(record["path"])
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copyfile(str(source), str(destination))
        os.chmod(str(destination), 0o600)


def create_deterministic_tar(tree, destination):
    names = sorted(
        path.relative_to(tree).as_posix()
        for path in tree.rglob("*")
        if path.is_file()
    )
    with tarfile.open(str(destination), "w", format=tarfile.USTAR_FORMAT) as archive:
        for name in names:
            path = tree / Path(name)
            size, _ = sha256_file(path)
            info = tarfile.TarInfo(name=name)
            info.size = size
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.mtime = 0
            info.uname = ""
            info.gname = ""
            with path.open("rb") as source:
                archive.addfile(info, source)


def capture_snapshot(repo, output_dir, diagnostics_dir, contract, input_records):
    output_dir, diagnostics_dir = validate_capture_destinations(
        output_dir, diagnostics_dir
    )
    state = []
    total_downloaded = 0
    try:
        with tempfile.TemporaryDirectory(
            prefix="mck-rocky-snapshot-stage.", dir=str(output_dir.parent)
        ) as stage_text:
            stage = Path(stage_text)
            tree = stage / "tree"
            tree.mkdir(mode=0o700)
            copy_repository_inputs(repo, tree, input_records)

            key_path = tree / "release-key" / "RPM-GPG-KEY-Rocky-10"
            key_download = download_to_path(
                contract["release_key"]["url"],
                key_path,
                contract["limits"]["max_key_bytes"],
                contract,
            )
            total_downloaded += key_download["size"]
            require_exact(
                key_download["size"],
                contract["release_key"]["size"],
                "downloaded key size",
            )
            require_exact(
                key_download["sha256"],
                contract["release_key"]["sha256"],
                "downloaded key digest",
            )
            verify_key_fingerprint(
                key_path, contract["release_key"]["fingerprint"]
            )

            total_open_counter = [0, contract["limits"]["max_open_bytes_total"]]
            for repository in contract["repositories"]:
                repository_id = repository["id"]
                base_url = repository["base_url"]
                root = tree / "repositories" / repository_id / "repodata"
                repomd_path = root / "repomd.xml"
                signature_path = root / "repomd.xml.asc"
                repomd_download = download_to_path(
                    base_url + "repodata/repomd.xml",
                    repomd_path,
                    contract["limits"]["max_repomd_bytes"],
                    contract,
                    required_prefix=base_url,
                )
                signature_download = download_to_path(
                    base_url + "repodata/repomd.xml.asc",
                    signature_path,
                    contract["limits"]["max_signature_bytes"],
                    contract,
                    required_prefix=base_url,
                )
                total_downloaded += repomd_download["size"] + signature_download["size"]
                if total_downloaded > contract["limits"]["max_total_download_bytes"]:
                    raise SnapshotError("capture exceeded its total download byte limit")
                signature = verify_detached_signature(
                    key_path,
                    signature_path,
                    repomd_path,
                    RELEASE_FINGERPRINT,
                )
                safe_write_json(root / "signature.json", signature)
                try:
                    repomd_data = repomd_path.read_bytes()
                except OSError as exc:
                    raise SnapshotError("cannot read downloaded repomd.xml: {}".format(exc))
                parsed = parse_repomd(
                    repomd_data, contract["limits"]["max_repository_objects"]
                )
                objects = []
                for row in parsed["objects"]:
                    object_path = tree / repository_archive_path(repository_id, row["href"])
                    download = download_to_path(
                        urllib.parse.urljoin(base_url, row["href"]),
                        object_path,
                        contract["limits"]["max_metadata_object_bytes"],
                        contract,
                        required_prefix=base_url,
                    )
                    total_downloaded += download["size"]
                    if total_downloaded > contract["limits"]["max_total_download_bytes"]:
                        raise SnapshotError("capture exceeded its total download byte limit")
                    verified = verify_metadata_object(
                        object_path,
                        row,
                        contract["limits"]["max_metadata_open_bytes"],
                        total_open_counter,
                    )
                    objects.append(verified)
                primary = [row for row in objects if row["type"] == "primary"][0]
                state.append(
                    {
                        "id": repository_id,
                        "metadata_object_count": len(objects),
                        "primary_sha256": primary["compressed_sha256"],
                        "primary_size": primary["compressed_size"],
                        "repomd_sha256": repomd_download["sha256"],
                        "signature_sha256": signature_download["sha256"],
                        "status": "verified",
                    }
                )
                write_capture_diagnostics(diagnostics_dir, state)

            manifest = build_capture_manifest(tree, repo, contract, input_records)
            safe_write_json(tree / "capture-manifest.json", manifest)
            rebuilt = build_capture_manifest(tree, repo, contract, input_records)
            require_exact(rebuilt, manifest, "self-verified capture manifest")

            payload = stage / "payload"
            payload.mkdir(mode=0o700)
            tar_path = payload / "snapshot.tar"
            create_deterministic_tar(tree, tar_path)
            tar_size, tar_digest = sha256_file(tar_path)
            (payload / "snapshot.tar.sha256").write_text(
                "{}  snapshot.tar\n".format(tar_digest), encoding="ascii"
            )
            os.chmod(str(payload / "snapshot.tar.sha256"), 0o600)
            os.replace(str(payload), str(output_dir))
            write_capture_diagnostics(
                diagnostics_dir,
                {
                    "drift": drift_rows(contract, manifest["repositories"]),
                    "snapshot_identity": manifest["snapshot_identity"],
                    "snapshot_tar_sha256": tar_digest,
                    "snapshot_tar_size": tar_size,
                },
            )
            return manifest
    except Exception as exc:
        error = str(exc) if isinstance(exc, SnapshotError) else "unexpected capture failure"
        try:
            write_capture_diagnostics(diagnostics_dir, state, error=error)
        except Exception:
            pass
        if isinstance(exc, SnapshotError):
            raise
        raise


def extract_canonical_tar(artifact, destination):
    try:
        archive = tarfile.open(str(artifact), "r:")
    except (OSError, tarfile.TarError) as exc:
        raise SnapshotError("cannot open snapshot tar: {}".format(exc))
    with archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if not names or names != sorted(names) or len(names) != len(set(names)):
            raise SnapshotError("snapshot tar paths are empty, unsorted, or duplicated")
        for member in members:
            path = normalized_relative_path(member.name, "snapshot tar path")
            if not member.isfile():
                raise SnapshotError("snapshot tar may contain regular files only")
            if (
                member.mode != 0o644
                or member.uid != 0
                or member.gid != 0
                or member.mtime != 0
                or member.uname != ""
                or member.gname != ""
            ):
                raise SnapshotError("snapshot tar metadata is not canonical")
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise SnapshotError("cannot read snapshot tar member")
            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            os.chmod(str(target), 0o600)


def verify_artifact(repo, artifact, contract, input_records):
    artifact = validate_artifact_path(artifact)
    with tempfile.TemporaryDirectory(prefix="mck-rocky-snapshot-verify.") as temp_text:
        tree = Path(temp_text) / "tree"
        tree.mkdir(mode=0o700)
        extract_canonical_tar(artifact, tree)
        manifest_path = tree / "capture-manifest.json"
        try:
            manifest_data = manifest_path.read_bytes()
        except OSError as exc:
            raise SnapshotError("snapshot manifest is missing: {}".format(exc))
        manifest = strict_json_bytes(manifest_data, "capture-manifest.json")
        expected = build_capture_manifest(tree, repo, contract, input_records)
        require_exact(manifest, expected, "snapshot capture manifest")
        rebuilt_tar = Path(temp_text) / "rebuilt.tar"
        create_deterministic_tar(tree, rebuilt_tar)
        original_size, original_digest = sha256_file(artifact)
        rebuilt_size, rebuilt_digest = sha256_file(rebuilt_tar)
        if original_size != rebuilt_size or original_digest != rebuilt_digest:
            raise SnapshotError("snapshot tar byte stream is not deterministic/canonical")
        return manifest


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--verify-artifact", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--diagnostics-dir", type=Path)
    args = parser.parse_args(argv)
    if args.capture and args.output_dir is None:
        parser.error("--capture requires --output-dir")
    if not args.capture and (args.output_dir is not None or args.diagnostics_dir is not None):
        parser.error("output/diagnostics directories are valid only with --capture")
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        repo = args.repo.resolve()
        contract, input_records = check_repository_inputs(repo)
        if args.check:
            print(
                json.dumps(
                    {
                        "capture_id": CAPTURE_ID,
                        "claims": FALSE_CLAIMS,
                        "repository_count": len(REPOSITORIES),
                        "status": "contract-valid-no-credit",
                    },
                    sort_keys=True,
                )
            )
        elif args.capture:
            manifest = capture_snapshot(
                repo,
                args.output_dir,
                args.diagnostics_dir,
                contract,
                input_records,
            )
            print(
                json.dumps(
                    {
                        "claims": FALSE_CLAIMS,
                        "snapshot_identity": manifest["snapshot_identity"],
                        "status": "bounded-capture-complete",
                    },
                    sort_keys=True,
                )
            )
        else:
            manifest = verify_artifact(
                repo, args.verify_artifact, contract, input_records
            )
            print(
                json.dumps(
                    {
                        "claims": FALSE_CLAIMS,
                        "snapshot_identity": manifest["snapshot_identity"],
                        "status": "artifact-verified-no-credit",
                    },
                    sort_keys=True,
                )
            )
    except SnapshotError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
