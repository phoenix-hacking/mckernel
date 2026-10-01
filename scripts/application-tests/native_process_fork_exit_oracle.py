"""Fail-closed oracle for the reviewed process.fork-exit diagnostic."""
import hashlib
import json
from pathlib import Path

CASE_ID = "process.fork-exit"
SOURCE_SHA256 = "860b0b61c901958070d844894da7250118a4dc1508d785615d824876f5ea42c3"
ORACLE_SHA256 = "fd756e4767cf26dfa6eb6ee9b78188a3d1ebd3d0dc902c433a86aeff68fb4122"
EXPECTED_STDOUT = b"child_pid_positive=1 reaped_match=1 exited=1 code=23\n"


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(result, *, payload_sha256, source_sha256=SOURCE_SHA256,
             oracle_sha256=ORACLE_SHA256, case_id=CASE_ID):
    """Validate one collector result and its immutable case identity."""
    if not isinstance(result, dict) or result.get("case_id") != case_id:
        raise ValueError("case identity mismatch")
    if result.get("status") not in ("PROTOCOL_PASS", "DIAGNOSTIC_PASS"):
        raise ValueError("diagnostic result is not a pass")
    if result.get("application_acceptance") is not False:
        raise ValueError("diagnostic result must not claim acceptance")
    if result.get("exit_code") != 0 or result.get("stderr", b"") not in (b"", ""):
        raise ValueError("exit or stderr mismatch")
    stdout = result.get("stdout")
    if isinstance(stdout, str):
        stdout = stdout.encode()
    if stdout != EXPECTED_STDOUT:
        raise ValueError("fork/wait stdout relation mismatch")
    if result.get("source_sha256") != source_sha256:
        raise ValueError("source hash mismatch")
    if result.get("oracle_sha256") != oracle_sha256:
        raise ValueError("oracle hash mismatch")
    if result.get("payload_sha256") != payload_sha256:
        raise ValueError("payload hash mismatch")
    return {"case_id": case_id, "status": "DIAGNOSTIC_PASS",
            "application_acceptance": False, "source_sha256": source_sha256,
            "oracle_sha256": oracle_sha256, "payload_sha256": payload_sha256}


def canonical_oracle_sha256(path):
    """Bind the on-disk canonical oracle before a result is admitted."""
    digest = _sha(path)
    if digest != ORACLE_SHA256:
        raise ValueError("canonical oracle changed")
    return digest
