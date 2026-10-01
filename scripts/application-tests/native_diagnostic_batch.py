#!/usr/bin/env python3
"""Sequential runner for already-released native diagnostic cases.

This is orchestration only: it does not grant execution authority, validate a
guest, or create a release.  Each case must carry the exact, independently
published release and manifest identities.  Cases are run once, in order, and
the first non-zero or uncertain result terminates the batch.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

SHA = __import__("re").compile(r"[0-9a-f]{64}\Z")


class BatchError(ValueError):
    pass


def _fail(ok, msg):
    if not ok:
        raise BatchError(msg)


def _hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _file_ref(obj, label):
    _fail(isinstance(obj, dict) and set(obj) == {"path", "sha256"}, label + " shape")
    path = obj["path"]
    _fail(isinstance(path, str) and os.path.isabs(path) and "\0" not in path,
          label + " path")
    path = str(Path(path).resolve(strict=True))
    _fail(path == obj["path"] and Path(path).is_file() and not Path(path).is_symlink(),
          label + " must be regular")
    _fail(isinstance(obj["sha256"], str) and SHA.fullmatch(obj["sha256"]), label + " hash")
    _fail(_hash(path) == obj["sha256"], label + " hash drift")
    return path


def _load(path):
    raw = Path(path).read_bytes()
    _fail(len(raw) <= 4 * 1024 * 1024, "batch spec too large")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BatchError("malformed batch spec") from exc


def validate_spec(spec):
    _fail(isinstance(spec, dict) and set(spec) == {"schema_version", "kind", "cases"},
          "batch keys")
    _fail(spec["schema_version"] == 1 and spec["kind"] == "native-diagnostic-batch",
          "batch identity")
    cases = spec["cases"]
    _fail(isinstance(cases, list) and 1 <= len(cases) <= 32, "case count")
    ids, commands, seen_outputs = set(), set(), set()
    checked = []
    for i, case in enumerate(cases):
        _fail(isinstance(case, dict) and set(case) == {"case_id", "command", "timeout_seconds",
                                                       "manifest", "release", "output_name"},
              f"case {i} keys")
        cid = case["case_id"]
        _fail(isinstance(cid, str) and cid and "\0" not in cid and cid not in ids, f"case {i} id")
        ids.add(cid)
        command = case["command"]
        _fail(isinstance(command, list) and command and len(command) <= 64 and
              all(isinstance(x, str) and x and "\0" not in x for x in command),
              f"case {cid} command")
        command_key = json.dumps(command, ensure_ascii=False, separators=(",", ":"))
        _fail(command_key not in commands, f"case {cid} command reused")
        commands.add(command_key)
        timeout = case["timeout_seconds"]
        _fail(type(timeout) in (int, float) and 0 < timeout <= 900, f"case {cid} timeout")
        manifest = _file_ref(case["manifest"], f"case {cid} manifest")
        release = _file_ref(case["release"], f"case {cid} release")
        try:
            release_obj = _load(release)
        except BatchError:
            raise
        _fail(isinstance(release_obj, dict) and release_obj.get("status") == "PASS_EXECUTION",
              f"case {cid} release status")
        _fail(release_obj.get("case_id") == cid and release_obj.get("manifest_sha256") == case["manifest"]["sha256"] and
              release_obj.get("command") == command, f"case {cid} release identity")
        output = case["output_name"]
        _fail(isinstance(output, str) and output and "/" not in output and "\0" not in output and
              output not in seen_outputs, f"case {cid} output name")
        seen_outputs.add(output)
        checked.append((cid, command, float(timeout), manifest, release, output))
    return checked


def _publish(path, obj):
    fd, temp = tempfile.mkstemp(prefix=".batch.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, sort_keys=True, separators=(",", ":")); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.link(temp, path, follow_symlinks=False)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def run_batch(spec_path, output_dir, runner=subprocess.run, now=time.monotonic):
    """Run a validated batch. ``runner`` is injectable for source-only tests."""
    spec = _load(str(Path(spec_path).resolve(strict=True)))
    cases = validate_spec(spec)
    out = Path(output_dir).resolve()
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    results = []
    for cid, command, timeout, manifest, release, output_name in cases:
        started = now()
        record = {"case_id": cid, "manifest": manifest, "release": release,
                  "command": command, "started_monotonic": started}
        try:
            completed = runner(command, shell=False, capture_output=True, timeout=timeout,
                               check=False)
            record.update({"returncode": completed.returncode,
                           "stdout_hex": completed.stdout.hex(), "stderr_hex": completed.stderr.hex(),
                           "uncertain": False})
            stop = completed.returncode != 0
        except subprocess.TimeoutExpired as exc:
            record.update({"returncode": None, "stdout_hex": (exc.stdout or b"").hex(),
                           "stderr_hex": (exc.stderr or b"").hex(), "uncertain": True,
                           "error": "timeout"})
            stop = True
        except (OSError, subprocess.SubprocessError) as exc:
            record.update({"returncode": None, "stdout_hex": "", "stderr_hex": "",
                           "uncertain": True, "error": type(exc).__name__})
            stop = True
        record["elapsed_seconds"] = max(0.0, now() - started)
        _publish(out / output_name, record)
        results.append(record)
        if stop:
            break
    summary = {"schema_version": 1, "kind": "native-diagnostic-batch-result",
               "stopped_on_failure": len(results) < len(cases) or results[-1].get("uncertain") or results[-1].get("returncode") != 0,
               "results": [r["case_id"] for r in results]}
    _publish(out / "batch-result.json", summary)
    return summary


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("spec"); p.add_argument("output_dir")
    args = p.parse_args()
    print(json.dumps(run_batch(args.spec, args.output_dir), sort_keys=True))
