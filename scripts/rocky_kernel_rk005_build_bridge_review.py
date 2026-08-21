#!/usr/bin/env python3
"""Verify the exact ef58 RK-005 policy-to-build configuration bridge.

This is a bounded, non-crediting composition review.  It proves that the
configuration compiled by the exact native-module build is the independently
resolved RK-005 v2 configuration plus one exact, canonical McKernel menu block
that enables the three project modules as modules.  It does not prove durable
retention, an RPM production build, RK-003 closure, RK-005 credit, or tracker
credit.
"""

from __future__ import print_function

import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import struct
import subprocess
import sys
import types
import zipfile
from pathlib import Path, PurePosixPath


class BridgeReviewError(RuntimeError):
    """Raised when the review, repository, or either artifact fails closed."""


REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = Path(
    "host-kernel/rocky/evidence/rk005-config-build-bridge-ef58-v1.json"
)
CONFIG_REVIEW_PATH = Path(
    "host-kernel/rocky/evidence/config-resolution-review-bebf-v2.json"
)
BUILD_REVIEW_PATH = Path(
    "host-kernel/rocky/evidence/rk007-native-build-review-ef58-v2.json"
)
REVIEW_ID = "rk-005-config-build-bridge-ef58860e-v1"
REVIEW_SHA256 = "ffacde556c5cba046eb84aa4257b15e7c50b05ceaee0eef9c5aa565e25842e73"
RUNTIME_HEAD = "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b"
RUNTIME_TREE = "ae853aa5a48ad85698709a50074cd86d91d02761"

CONFIG_ARTIFACT = {
    "expires_at": "2026-09-17T22:23:46Z",
    "id": 9344695830,
    "job_id": 95888740437,
    "name": "rk005-config-resolution-v2-32192198982-1",
    "run_id": 32192198982,
    "sha256": "d1f9f26982ab41dea062f303c3fcdd6d9e9d102e87d5b8a826545941a573c790",
    "size": 1718245,
}
BUILD_ARTIFACT = {
    "expires_at": "2026-09-17T22:54:22Z",
    "id": 9345473288,
    "job_id": 95888740940,
    "name": "native-rust-exact-build-32192199024-1",
    "run_id": 32192199024,
    "sha256": "d0d63f49311f308b6e1f59e505cf0afc9bde95876ad8955b3ca49bd084a1c84e",
    "size": 22510502,
}
POLICY_CONFIG = {
    "path": "capture/resolved-pass-1.config",
    "sha256": "fc8c835cdd67d50bf71353d956b0c9932ea83a2553a79a951e9254cf72505b7a",
    "size": 260311,
}
BUILD_CONFIG = {
    "path": "resolved.config",
    "sha256": "106055ad26cfc19373b1bc52e1dcc24b3eaa7c48125c451be029898b8f696474",
    "size": 260490,
}
INSERTION_OFFSET = 65546
MCKERNEL_BLOCK = (
    b"\n#\n# McKernel native Rust host modules\n#\n"
    b"CONFIG_MCKERNEL_IHK_RUST=m\n"
    b"CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=m\n"
    b"CONFIG_MCKERNEL_MCCTRL_RUST=m\n"
    b"# end of McKernel native Rust host modules\n"
)
MCKERNEL_BLOCK_SHA256 = "9bb59a745ca8c8614aa677d252c57a20664cd021e675900f4f3c6ba124cc2879"
PROJECT_SYMBOLS = {
    "CONFIG_MCKERNEL_IHK_RUST": "m",
    "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST": "m",
    "CONFIG_MCKERNEL_MCCTRL_RUST": "m",
}
PRESERVED_SYMBOLS = {
    "CONFIG_ASM_MODVERSIONS": "n",
    "CONFIG_DEBUG_INFO_BTF": "y",
    "CONFIG_DEBUG_INFO_BTF_MODULES": "y",
    "CONFIG_HAVE_RUST": "y",
    "CONFIG_MODULES": "y",
    "CONFIG_MODULE_SIG": "y",
    "CONFIG_MODULE_SIG_ALL": "y",
    "CONFIG_MODVERSIONS": "n",
    "CONFIG_RUST": "y",
    "CONFIG_RUST_IS_AVAILABLE": "y",
    "CONFIG_WERROR": "y",
}
CLAIMS = {
    "credit_eligible": False,
    "durable_archive": False,
    "gate_claims": {"RK-003": False, "RK-005": False, "RK-007": False},
    "production_rpm_build": False,
    "tracker_credit": False,
}
PREREQUISITES = [
    "Durably archive both exact artifact ZIPs before their GitHub Actions copies expire.",
    "Close RK-003 with a signed immutable RPM snapshot, complete transitive offline replay, and independently reviewed tool probes.",
    "Extend the RK-005 authority with an explicit fail-closed production projection for the exact three staged McKernel module symbols.",
    "Produce and independently review the exact-NVR Rocky RPM kernel and module set; this compiler artifact is not that production package build.",
    "A separate authority and tracker update is required before RK-005 or any tracker credit can become true.",
]

CONFIG_PATHS = (
    "capture/baseline.config",
    "capture/blockers.json",
    "capture/SHA256SUMS",
    "capture/checkpoint.json",
    "capture/commands.json",
    "capture/config-delta.json",
    "capture/control-pass-1.config",
    "capture/control-pass-2.config",
    "capture/dependency-assertions.json",
    "capture/environment.json",
    "capture/fragment.config",
    "capture/resolved-pass-1.config",
    "capture/resolved-pass-2.config",
    "capture.exit-code",
    "capture.log",
    "workflow-state",
)
SHA_LINE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9_.-]*)$")
CONFIG_VALUE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
CONFIG_UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
CONFIG_ASSIGNMENT = re.compile(
    r'^(?:y|m|n|-?[0-9]+|0[xX][0-9A-Fa-f]+|"(?:[^"\\\r\n]|\\.)*")$'
)

ORACLE_BINDINGS = {
    "rocky_kernel_config_review_v2.py": (
        66353,
        "a7bb7f156ac489afbda14a4f58b2ba29792e2bc8d0a5740d60bcd48c9801d83d",
    ),
    "rocky_kernel_rk007_build_review_v2.py": (
        69660,
        "946a0ed26bcd35c9de1f15e6f33fa1f65f63194a9677f26f70575623061c8c12",
    ),
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def exact_keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise BridgeReviewError("{0} keys differ".format(label))
    return value


def require_equal(actual, expected, label):
    if type(actual) is not type(expected) or actual != expected:
        if type(actual) is not type(expected):
            raise BridgeReviewError("{0} type differs".format(label))
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise BridgeReviewError("{0} keys differ".format(label))
        for key in expected:
            require_equal(actual[key], expected[key], label + "." + str(key))
        return
    if isinstance(expected, (list, tuple)):
        if len(actual) != len(expected):
            raise BridgeReviewError("{0} length differs".format(label))
        for index, (left, right) in enumerate(zip(actual, expected)):
            require_equal(left, right, "{0}[{1}]".format(label, index))
        return
    if actual != expected:
        raise BridgeReviewError("{0} differs".format(label))


def canonical_bytes(value):
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    except (TypeError, ValueError) as error:
        raise BridgeReviewError("value is not canonical JSON: {0}".format(error))
    return (text + "\n").encode("ascii")


def read_canonical_json(data, label):
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_no_duplicates)
    except (UnicodeError, ValueError) as error:
        raise BridgeReviewError("{0} is invalid JSON: {1}".format(label, error))
    if data != canonical_bytes(value):
        raise BridgeReviewError("{0} is not canonical JSON".format(label))
    return value


def _no_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate key {0}".format(key))
        value[key] = item
    return value


def load_exact_module(name, file_name):
    path = REPO_ROOT / "scripts" / file_name
    expected_size, expected_sha = ORACLE_BINDINGS[file_name]
    try:
        before = path.lstat()
    except OSError as error:
        raise BridgeReviewError("cannot inspect {0}: {1}".format(file_name, error))
    if not stat.S_ISREG(before.st_mode) or path.resolve() != path.absolute():
        raise BridgeReviewError("oracle path is not a direct regular file")
    data = path.read_bytes()
    after = path.lstat()
    if (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise BridgeReviewError("oracle changed while read")
    require_equal(len(data), expected_size, file_name + " size")
    require_equal(sha256_bytes(data), expected_sha, file_name + " digest")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    specification = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    module.__spec__ = specification
    sys.modules[name] = module
    try:
        exec(compile(data, str(path), "exec", dont_inherit=True), module.__dict__)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


CONFIG_ORACLE = load_exact_module(
    "_mckernel_rk005_bridge_config_review", "rocky_kernel_config_review_v2.py"
)
BUILD_ORACLE = load_exact_module(
    "_mckernel_rk005_bridge_build_review", "rocky_kernel_rk007_build_review_v2.py"
)


def load_review(path):
    path = CONFIG_ORACLE.regular_file(path, "bridge review")
    data = BUILD_ORACLE.v1_review.read_regular_file_once(
        path, "bridge review", expected_mode=0o644
    )
    require_equal(sha256_bytes(data), REVIEW_SHA256, "review digest")
    review = read_canonical_json(data, "bridge review")
    validate_review(review)
    return review


def validate_review(review):
    exact_keys(
        review,
        {
            "claims",
            "remaining_prerequisites",
            "review_id",
            "runtime",
            "schema_version",
            "source_artifacts",
            "verified_facts",
        },
        "review",
    )
    require_equal(review["schema_version"], 1, "schema version")
    require_equal(review["review_id"], REVIEW_ID, "review id")
    require_equal(review["claims"], CLAIMS, "claims")
    require_equal(review["remaining_prerequisites"], PREREQUISITES, "prerequisites")
    require_equal(
        review["runtime"],
        {"head_sha": RUNTIME_HEAD, "tree_sha": RUNTIME_TREE},
        "runtime",
    )
    require_equal(
        review["source_artifacts"],
        {"config_v2": CONFIG_ARTIFACT, "native_build": BUILD_ARTIFACT},
        "source artifacts",
    )
    facts = exact_keys(
        review["verified_facts"],
        {"build_config", "policy_config", "preserved_symbols", "projection"},
        "verified facts",
    )
    require_equal(facts["policy_config"], POLICY_CONFIG, "policy config")
    require_equal(facts["build_config"], BUILD_CONFIG, "build config")
    require_equal(facts["preserved_symbols"], PRESERVED_SYMBOLS, "preserved symbols")
    require_equal(
        facts["projection"],
        {
            "block_sha256": MCKERNEL_BLOCK_SHA256,
            "block_size": len(MCKERNEL_BLOCK),
            "insertion_offset": INSERTION_OFFSET,
            "nonproject_drift_count": 0,
            "project_symbols": PROJECT_SYMBOLS,
            "stripped_bytes_equal_policy": True,
        },
        "projection",
    )
    return review


def run_git(repo, arguments, allow_failure=False):
    environment = dict(os.environ)
    for name in list(environment):
        if name.startswith("GIT_"):
            environment.pop(name, None)
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_GRAFT_FILE"] = os.devnull
    environment["LC_ALL"] = "C"
    completed = subprocess.run(
        ["git", "-C", str(repo)] + list(arguments),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        check=False,
    )
    if completed.returncode and not allow_failure:
        raise BridgeReviewError("git command failed")
    return completed


def validate_repository(repo, review):
    repo = Path(repo).resolve()
    current = run_git(repo, ["rev-parse", "HEAD"]).stdout.decode("ascii").strip()
    require_equal(
        run_git(repo, ["cat-file", "-t", current]).stdout.decode("ascii").strip(),
        "commit",
        "current HEAD type",
    )
    if run_git(repo, ["merge-base", "--is-ancestor", RUNTIME_HEAD, current], True).returncode:
        raise BridgeReviewError("current HEAD is not a runtime descendant")
    require_equal(
        run_git(repo, ["show", "-s", "--format=%T", RUNTIME_HEAD]).stdout.decode("ascii").strip(),
        RUNTIME_TREE,
        "runtime tree",
    )
    inherited_git = dict(
        (name, value) for name, value in os.environ.items() if name.startswith("GIT_")
    )
    inherited_lc_all = os.environ.get("LC_ALL")
    for name in list(os.environ):
        if name.startswith("GIT_"):
            os.environ.pop(name, None)
    os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    os.environ["GIT_NO_REPLACE_OBJECTS"] = "1"
    os.environ["GIT_GRAFT_FILE"] = os.devnull
    os.environ["LC_ALL"] = "C"
    try:
        config_review_path = CONFIG_ORACLE.repository_file(
            repo, CONFIG_REVIEW_PATH.as_posix(), "config authority review"
        )
        config_review = CONFIG_ORACLE.load_review(config_review_path)
        CONFIG_ORACLE.validate_review_object(config_review)
        require_equal(
            CONFIG_ORACLE.validate_repository(repo, config_review),
            current,
            "config authority repository snapshot",
        )
        build_review = BUILD_ORACLE.load_review(repo / BUILD_REVIEW_PATH)
        require_equal(
            BUILD_ORACLE.validate_repository(repo, build_review),
            current,
            "build authority repository snapshot",
        )
    finally:
        for name in list(os.environ):
            if name.startswith("GIT_"):
                os.environ.pop(name, None)
        os.environ.update(inherited_git)
        if inherited_lc_all is None:
            os.environ.pop("LC_ALL", None)
        else:
            os.environ["LC_ALL"] = inherited_lc_all
    require_equal(
        run_git(repo, ["rev-parse", "HEAD"]).stdout.decode("ascii").strip(),
        current,
        "final repository HEAD snapshot",
    )
    validate_review(review)
    return current


def safe_zip_name(name):
    if (
        not isinstance(name, str)
        or not name
        or "\\" in name
        or "\x00" in name
        or "//" in name
        or name.endswith("/")
        or any(part in ("", ".", "..") for part in name.split("/"))
    ):
        raise BridgeReviewError("unsafe ZIP path")
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts:
        raise BridgeReviewError("unsafe ZIP path")
    return name


def read_zip(data, expected_paths, label):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data), "r")
    except (OSError, zipfile.BadZipFile) as error:
        raise BridgeReviewError("{0} is not a ZIP: {1}".format(label, error))
    with archive:
        if archive.comment:
            raise BridgeReviewError(label + " has a ZIP comment")
        infos = archive.infolist()
        names = [safe_zip_name(info.filename) for info in infos]
        if len(names) != len(set(names)):
            raise BridgeReviewError(label + " has duplicate paths")
        require_equal(tuple(names), tuple(expected_paths), label + " path order")
        offsets = [info.header_offset for info in infos]
        if not offsets or offsets[0] != 0 or offsets != sorted(set(offsets)):
            raise BridgeReviewError(label + " local-header offsets are not closed")

        central_offset = archive.start_dir
        central_rows = []
        for info in infos:
            if central_offset + 46 > len(data):
                raise BridgeReviewError(label + " central header is truncated")
            try:
                central = struct.unpack_from("<4s6H3I5H2I", data, central_offset)
            except struct.error as error:
                raise BridgeReviewError(label + " central header is malformed: {0}".format(error))
            (
                signature, made_by, needed, flags, method, dos_time, dos_date,
                crc, compressed_size, file_size, name_length, extra_length,
                comment_length, disk_start, internal_attr, external_attr,
                local_offset,
            ) = central
            name_start = central_offset + 46
            name_end = name_start + name_length
            central_end = name_end + extra_length + comment_length
            try:
                expected_name = info.filename.encode("ascii")
            except UnicodeError as error:
                raise BridgeReviewError(label + " member name is not ASCII: {0}".format(error))
            if (
                signature != b"PK\x01\x02"
                or central_end > len(data)
                or data[name_start:name_end] != expected_name
                or extra_length != 0
                or comment_length != 0
                or flags != info.flag_bits
                or method != info.compress_type
                or crc != info.CRC
                or compressed_size != info.compress_size
                or file_size != info.file_size
                or local_offset != info.header_offset
                or disk_start != 0
                or internal_attr != info.internal_attr
                or external_attr != info.external_attr
            ):
                raise BridgeReviewError(label + " central record differs: " + info.filename)
            central_rows.append(
                {
                    "date": dos_date,
                    "external_attr": external_attr,
                    "made_by": made_by,
                    "needed": needed,
                    "time": dos_time,
                }
            )
            central_offset = central_end

        if central_offset + 22 != len(data):
            raise BridgeReviewError(label + " has a prefix, trailing bytes, or noncanonical EOCD")
        try:
            eocd = struct.unpack_from("<4s4H2IH", data, central_offset)
        except struct.error as error:
            raise BridgeReviewError(label + " EOCD is malformed: {0}".format(error))
        (
            signature, disk_number, central_disk, disk_entries, total_entries,
            central_size, central_directory_offset, comment_length,
        ) = eocd
        if (
            signature != b"PK\x05\x06"
            or disk_number != 0
            or central_disk != 0
            or disk_entries != len(infos)
            or total_entries != len(infos)
            or central_size != central_offset - archive.start_dir
            or central_directory_offset != archive.start_dir
            or comment_length != 0
        ):
            raise BridgeReviewError(label + " EOCD differs from the exact single-disk shape")

        files = {}
        for position, info in enumerate(infos):
            central = central_rows[position]
            expected_attr = (
                0x81A40020
                if info.filename in ("capture.exit-code", "capture.log", "workflow-state")
                else 0x81000020
            )
            expected_mode = (
                stat.S_IFREG | (0o644 if expected_attr == 0x81A40020 else 0o400)
            )
            if (
                info.create_system != 3
                or info.create_version != 45
                or central["made_by"] != 0x032D
                or info.extract_version != 20
                or central["needed"] != 20
                or info.external_attr != expected_attr
                or ((info.external_attr >> 16) & 0o177777) != expected_mode
                or info.internal_attr != 0
                or info.flag_bits != 8
                or info.compress_type != zipfile.ZIP_STORED
                or info.compress_size != info.file_size
                or info.extra
                or info.comment
            ):
                raise BridgeReviewError(label + " member metadata differs: " + info.filename)
            if info.header_offset + 30 > len(data):
                raise BridgeReviewError(label + " local header is truncated")
            try:
                local = struct.unpack_from("<4s5H3I2H", data, info.header_offset)
            except struct.error as error:
                raise BridgeReviewError(label + " local header is malformed: {0}".format(error))
            (
                local_signature, local_version, local_flags, local_method,
                local_time, local_date, local_crc, local_compressed_size,
                local_file_size, local_name_length, local_extra_length,
            ) = local
            name_start = info.header_offset + 30
            name_end = name_start + local_name_length
            extra_end = name_end + local_extra_length
            if (
                local_signature != b"PK\x03\x04"
                or local_version != central["needed"]
                or local_flags != 8
                or local_flags != info.flag_bits
                or local_method != info.compress_type
                or local_time != central["time"]
                or local_date != central["date"]
                or (local_crc, local_compressed_size, local_file_size) != (0, 0, 0)
                or local_extra_length != 0
                or data[name_start:name_end] != info.filename.encode("ascii")
                or extra_end > len(data)
            ):
                raise BridgeReviewError(label + " local record differs: " + info.filename)
            payload_end = extra_end + info.compress_size
            descriptor_end = payload_end + 16
            if descriptor_end > len(data):
                raise BridgeReviewError(label + " data descriptor is truncated")
            descriptor = struct.unpack_from("<4sIII", data, payload_end)
            if descriptor != (b"PK\x07\x08", info.CRC, info.compress_size, info.file_size):
                raise BridgeReviewError(label + " data descriptor differs: " + info.filename)
            expected_next = (
                infos[position + 1].header_offset
                if position + 1 < len(infos)
                else archive.start_dir
            )
            if descriptor_end != expected_next:
                raise BridgeReviewError(label + " local records contain a gap")
            try:
                files[info.filename] = archive.read(info)
            except (OSError, RuntimeError, zipfile.BadZipFile) as error:
                raise BridgeReviewError("cannot read {0}: {1}".format(info.filename, error))
    return files


def parse_sums(data, expected_names):
    try:
        text = data.decode("ascii")
    except UnicodeError as error:
        raise BridgeReviewError("SHA256SUMS is not ASCII: {0}".format(error))
    if not text.endswith("\n"):
        raise BridgeReviewError("SHA256SUMS lacks final newline")
    values = {}
    for line in text.splitlines():
        match = SHA_LINE.fullmatch(line)
        if match is None:
            raise BridgeReviewError("malformed SHA256SUMS row")
        digest, name = match.groups()
        if name in values:
            raise BridgeReviewError("duplicate SHA256SUMS path")
        values[name] = digest
    require_equal(tuple(values), tuple(expected_names), "SHA256SUMS paths")
    return values


def parse_config(data, label):
    try:
        text = data.decode("utf-8")
    except UnicodeError as error:
        raise BridgeReviewError("{0} is not UTF-8: {1}".format(label, error))
    if not text.endswith("\n"):
        raise BridgeReviewError(label + " lacks final newline")
    if any(
        (ord(char) < 0x20 and char != "\n")
        or 0x7F <= ord(char) <= 0x9F
        or char in ("\u2028", "\u2029")
        for char in text
    ):
        raise BridgeReviewError(label + " has a control character")
    values = {}
    for number, line in enumerate(text.splitlines(), 1):
        match = CONFIG_VALUE.fullmatch(line)
        if match is not None:
            symbol, value = match.groups()
            if CONFIG_ASSIGNMENT.fullmatch(value) is None:
                raise BridgeReviewError("malformed config assignment")
        else:
            match = CONFIG_UNSET.fullmatch(line)
            if match is None:
                if line.startswith("# CONFIG"):
                    raise BridgeReviewError("malformed config comment")
                if line == "" or line.startswith("#"):
                    continue
                raise BridgeReviewError("malformed config row {0}".format(number))
            symbol, value = match.group(1), "n"
        if symbol in values:
            raise BridgeReviewError("duplicate config symbol " + symbol)
        values[symbol] = value
    if not values:
        raise BridgeReviewError(label + " has no config symbols")
    return values


def verify_config_artifact_bytes(data, review):
    validate_review(review)
    require_equal(len(data), CONFIG_ARTIFACT["size"], "config artifact size")
    require_equal(sha256_bytes(data), CONFIG_ARTIFACT["sha256"], "config artifact digest")
    files = read_zip(data, CONFIG_PATHS, "config artifact")
    sums_names = (
        "baseline.config",
        "fragment.config",
        "control-pass-1.config",
        "control-pass-2.config",
        "resolved-pass-1.config",
        "resolved-pass-2.config",
        "commands.json",
        "environment.json",
        "config-delta.json",
        "dependency-assertions.json",
        "blockers.json",
        "checkpoint.json",
    )
    sums = parse_sums(files["capture/SHA256SUMS"], sums_names)
    for name, digest in sums.items():
        require_equal(sha256_bytes(files["capture/" + name]), digest, "checksum " + name)
    checkpoint = read_canonical_json(files["capture/checkpoint.json"], "checkpoint")
    exact_keys(
        checkpoint,
        {
            "credit_eligible", "gate_claims", "github", "manifests", "phase",
            "schema_version", "two_independent_resolutions_identical",
        },
        "config checkpoint",
    )
    identity = {
        "head_sha": RUNTIME_HEAD,
        "repository": "phoenix-hacking/mckernel",
        "run_attempt": 1,
        "run_id": CONFIG_ARTIFACT["run_id"],
    }
    require_equal(checkpoint.get("github"), identity, "config checkpoint identity")
    require_equal(checkpoint.get("credit_eligible"), False, "config checkpoint credit")
    require_equal(
        checkpoint.get("gate_claims"),
        CONFIG_ORACLE.EXPECTED_GATE_CLAIMS,
        "config checkpoint gates",
    )
    require_equal(checkpoint.get("phase"), "config-resolution-v2", "config phase")
    require_equal(checkpoint.get("schema_version"), 2, "config checkpoint schema")
    require_equal(checkpoint.get("two_independent_resolutions_identical"), True, "config equivalence")
    manifests = checkpoint.get("manifests")
    if not isinstance(manifests, list) or not manifests:
        raise BridgeReviewError("config checkpoint manifests are missing")
    require_equal(
        tuple(row.get("path") for row in manifests),
        tuple(sums_names[:-1]),
        "config checkpoint manifest paths",
    )
    for index, row in enumerate(manifests):
        exact_keys(row, {"path", "sha256", "size"}, "config checkpoint row")
        if type(row["size"]) is not int or row["size"] < 1:
            raise BridgeReviewError("config checkpoint size is invalid")
        payload = files["capture/" + row["path"]]
        require_equal(row["sha256"], sums[row["path"]], "config checkpoint digest")
        require_equal(len(payload), row["size"], "config checkpoint size")
        require_equal(sha256_bytes(payload), row["sha256"], "config checkpoint payload")
    blockers = read_canonical_json(files["capture/blockers.json"], "config blockers")
    exact_keys(blockers, {"gate_claims", "success_blockers"}, "config blockers")
    require_equal(
        blockers["gate_claims"],
        CONFIG_ORACLE.EXPECTED_GATE_CLAIMS,
        "config blocker gates",
    )
    require_equal(
        blockers["success_blockers"],
        CONFIG_ORACLE.EXPECTED_REMAINING_PREREQUISITES,
        "config success blockers",
    )
    environment = read_canonical_json(files["capture/environment.json"], "environment")
    require_equal(environment.get("github"), identity, "config environment identity")
    require_equal(files["capture.exit-code"], b"0\n", "config exit")
    require_equal(files["workflow-state"], b"bootstrap-complete\n", "config workflow state")
    first = files["capture/resolved-pass-1.config"]
    second = files["capture/resolved-pass-2.config"]
    require_equal(first, second, "resolved pass bytes")
    require_equal(len(first), POLICY_CONFIG["size"], "policy config size")
    require_equal(sha256_bytes(first), POLICY_CONFIG["sha256"], "policy config digest")
    parse_config(first, "policy config")
    return first


def verify_build_artifact_bytes(data, review):
    validate_review(review)
    require_equal(len(data), BUILD_ARTIFACT["size"], "build artifact size")
    require_equal(sha256_bytes(data), BUILD_ARTIFACT["sha256"], "build artifact digest")
    build_review = BUILD_ORACLE.load_review(REPO_ROOT / BUILD_REVIEW_PATH)
    BUILD_ORACLE.verify_artifact_bytes(data, build_review)
    files = BUILD_ORACLE.read_zip_members(data)[0]
    config = files[BUILD_CONFIG["path"]]
    require_equal(len(config), BUILD_CONFIG["size"], "build config size")
    require_equal(sha256_bytes(config), BUILD_CONFIG["sha256"], "build config digest")
    parse_config(config, "build config")
    return config


def verify_projection(policy_config, build_config, review):
    validate_review(review)
    require_equal(len(policy_config), POLICY_CONFIG["size"], "policy config size")
    require_equal(sha256_bytes(policy_config), POLICY_CONFIG["sha256"], "policy config digest")
    require_equal(len(build_config), BUILD_CONFIG["size"], "build config size")
    require_equal(sha256_bytes(build_config), BUILD_CONFIG["sha256"], "build config digest")
    if sha256_bytes(MCKERNEL_BLOCK) != MCKERNEL_BLOCK_SHA256:
        raise BridgeReviewError("embedded projection block changed")
    require_equal(
        build_config,
        policy_config[:INSERTION_OFFSET] + MCKERNEL_BLOCK + policy_config[INSERTION_OFFSET:],
        "exact production projection",
    )
    stripped = build_config[:INSERTION_OFFSET] + build_config[INSERTION_OFFSET + len(MCKERNEL_BLOCK):]
    require_equal(stripped, policy_config, "stripped projection")
    policy_values = parse_config(policy_config, "policy config")
    build_values = parse_config(build_config, "build config")
    changed = {
        symbol: value
        for symbol, value in build_values.items()
        if policy_values.get(symbol, "n") != value
    }
    require_equal(changed, PROJECT_SYMBOLS, "project-only semantic delta")
    for symbol in PROJECT_SYMBOLS:
        if symbol in policy_values:
            raise BridgeReviewError("project symbol already appears in policy config")
    for symbol, expected in PRESERVED_SYMBOLS.items():
        require_equal(policy_values.get(symbol, "n"), expected, "policy " + symbol)
        require_equal(build_values.get(symbol, "n"), expected, "build " + symbol)
    return {
        "build_config_sha256": sha256_bytes(build_config),
        "policy_config_sha256": sha256_bytes(policy_config),
        "project_symbol_count": len(PROJECT_SYMBOLS),
    }


def verify_artifacts(config_path, build_path, review):
    config_path = CONFIG_ORACLE.regular_file(config_path, "config artifact")
    build_path = CONFIG_ORACLE.regular_file(build_path, "build artifact")
    config_data = BUILD_ORACLE.v1_review.read_regular_file_once(
        config_path, "config artifact", expected_mode=0o644
    )
    build_data = BUILD_ORACLE.v1_review.read_regular_file_once(
        build_path, "build artifact", expected_mode=0o644
    )
    policy = verify_config_artifact_bytes(config_data, review)
    built = verify_build_artifact_bytes(build_data, review)
    return verify_projection(policy, built, review)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--review", type=Path, default=REVIEW_PATH)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-config-artifact", type=Path)
    parser.add_argument("--verify-build-artifact", type=Path)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not args.check and args.verify_config_artifact is None and args.verify_build_artifact is None:
        raise SystemExit("at least one verification mode is required")
    if (args.verify_config_artifact is None) != (args.verify_build_artifact is None):
        raise SystemExit("both artifact paths are required together")
    try:
        review_path = args.review if args.review.is_absolute() else args.repo / args.review
        review = load_review(review_path)
        current = validate_repository(args.repo, review)
        if args.verify_config_artifact is not None:
            result = verify_artifacts(
                args.verify_config_artifact,
                args.verify_build_artifact,
                review,
            )
            print(
                "RK-005 config/build bridge VERIFIED: head={0}; policy={1}; build={2}; project_symbols={3}; credit=FORBIDDEN".format(
                    RUNTIME_HEAD,
                    result["policy_config_sha256"],
                    result["build_config_sha256"],
                    result["project_symbol_count"],
                )
            )
        else:
            print(
                "RK-005 config/build bridge review VALID: current_head={0}; credit=FORBIDDEN".format(
                    current
                )
            )
    except (BridgeReviewError, BUILD_ORACLE.BuildReviewV2Error, CONFIG_ORACLE.ConfigReviewV2Error, OSError) as error:
        print("RK-005 config/build bridge review error: {0}".format(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
