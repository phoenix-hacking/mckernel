#!/usr/bin/env python3
"""Copy the two frozen, qualified executables into a fresh private prefix."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output-1"
INPUT_SHA = "6c8f90d461ad0096f3330dfbdded16b16aab4ff81c959170e2c70066e9b5d9af"


def read_regular(path, expected):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("not a regular file: " + str(path))
        if before.st_size != expected["bytes"]:
            raise ValueError("wrong size: " + str(path))
        if stat.S_IMODE(before.st_mode) != 0o755:
            raise ValueError("wrong executable mode: " + str(path))
        chunks = []
        remaining = expected["bytes"] + 1
        while remaining:
            data = os.read(fd, min(1048576, remaining))
            if not data:
                break
            chunks.append(data)
            remaining -= len(data)
        data = b"".join(chunks)
        after = os.fstat(fd)
        fields = ("st_dev", "st_ino", "st_size", "st_mode", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, k) != getattr(after, k) for k in fields):
            raise ValueError("file changed while reading: " + str(path))
        if len(data) != expected["bytes"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError("wrong bytes: " + str(path))
        return data
    finally:
        os.close(fd)


def main():
    raw = (ROOT / "INPUTS.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != INPUT_SHA:
        raise ValueError("frozen INPUTS.json changed")
    inputs = json.loads(raw)
    programs = inputs["programs"]
    if [p["name"] for p in programs] != ["mcps", "mcinspect"]:
        raise ValueError("wrong two-program contract")
    # Check both complete source files before creating any stage output.
    data = [read_regular(p["source"]["path"], p["source"]) for p in programs]
    OUT.mkdir(mode=0o755)  # Existing or partial output is preserved and refused.
    for relative in ("stage", "stage/usr", "stage/usr/local", "stage/usr/local/bin"):
        directory = OUT / relative
        directory.mkdir(mode=0o755)
        directory.chmod(0o755)
    rows = []
    for p, contents in zip(programs, data):
        if p["relative_destination"] != "stage/usr/local/bin/" + p["name"]:
            raise ValueError("wrong private destination")
        target = OUT / p["relative_destination"]
        fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fchmod(stream.fileno(), 0o755)
            os.fsync(stream.fileno())
        if read_regular(target, p["source"]) != contents:
            raise ValueError("copy differs: " + str(target))
        rows.append(dict(p, private_installed={
            "path": str(target), "bytes": len(contents),
            "sha256": hashlib.sha256(contents).hexdigest(), "mode": "0755",
            "byte_equal": True, "executed": False}))
    if sorted(p.name for p in (OUT / "stage/usr/local/bin").iterdir()) != ["mcinspect", "mcps"]:
        raise ValueError("unexpected private-bin entry")
    manifest = {
        "schema": "mckernel.mcps.corrected-provider.private-pair.result.v1",
        "status": "PASS_EXACT_SAVED_ARTIFACT_PRIVATE_PAIR_ONLY",
        "inputs_sha256": INPUT_SHA, "programs": rows,
        "configured_process_contract": inputs["configured_process_contract"],
        "corrected_provider_provenance": inputs["corrected_provider_provenance"],
        "receipts": inputs["receipts"],
        "remaining_conditions": inputs["remaining_conditions"],
        "new_build_test_ELF_or_program_execution": False,
        "old_private_pair_modified": False,
        "old_UNKNOWN_released": False,
        "original_acceptance": False,
        "Root_positive_direct_and_whole_family_wait_and_stream_receipt_required": True,
    }
    with (OUT / "MANIFEST.json").open("x") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": manifest["status"], "manifest": str(OUT / "MANIFEST.json"),
                      "sha256": hashlib.sha256((OUT / "MANIFEST.json").read_bytes()).hexdigest()}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Root's existing capture retains this diagnostic and all partial output.
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__,
                          "error": str(error), "output": str(OUT)}), file=sys.stderr)
        raise
