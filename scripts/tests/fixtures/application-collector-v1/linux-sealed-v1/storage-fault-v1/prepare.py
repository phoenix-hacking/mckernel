#!/usr/bin/env python3
"""Prepare storage-fault-v2 source. This module never builds or executes it."""
import argparse
import difflib
import hashlib
import json
import os
import stat
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "collector.c"
SOURCE_SHA = "09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f"
SOURCE_PROGRAMS = {"supervisor": HERE / "supervise.py",
                   "owner": HERE / "witness_owner.py",
                   "oracle": HERE / "oracle.py"}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def attach_secondary(primary, secondary):
    values = list(getattr(primary, "_prepare_secondary_exceptions", []))
    values.append(secondary)
    primary._prepare_secondary_exceptions = values

def close_fds(fds, primary=None):
    """Close each acquired descriptor, retaining the first failure."""
    for fd in fds:
        if fd < 0:
            continue
        try:
            os.close(fd)
        except Exception as error:
            if primary is None:
                primary = error
            else:
                attach_secondary(primary, error)
    return primary

def read(path, limit=1 << 20):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("canonical absolute input required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    primary = None
    result = None
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("bounded regular input required")
        chunks, remaining = [], before.st_size
        while remaining:
            chunk = os.read(fd, min(remaining, 65536))
            if not chunk:
                raise OSError("short input read")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != \
           (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise OSError("input changed during read")
        result = b"".join(chunks)
    except Exception as error:
        primary = error
    primary = close_fds((fd,), primary)
    if primary is not None:
        raise primary
    return result

def packet(path):
    record = json.loads(read(path))
    if set(record) != {"schema_version", "kind", "status", "backend_enabled",
                       "application_acceptance", "collector", "retained_input",
                       "witness", "supervisor", "cases"}:
        raise ValueError("packet fields")
    if record["schema_version"] != 2 or record["kind"] != "linux-sealed-collector-storage-fault-v2":
        raise ValueError("packet identity")
    if record["status"] != "SOURCE_PACKET_ONLY" or record["backend_enabled"] is not False or \
       record["application_acceptance"] is not False:
        raise ValueError("packet scope")
    if record["supervisor"] != {"path": "supervise.py",
            "owner_path": "witness_owner.py", "oracle_path": "oracle.py",
            "schema_version": 1, "preflight_seconds": 5,
            "owner_wait_seconds": 220, "cleanup_seconds": 22,
            "publication_seconds": 6, "total_seconds": 248,
            "preflight_total_seconds": 33, "stream_limit_bytes": 1048576}:
        raise ValueError("supervisor packet")
    collector = record["collector"]
    if collector != {"path": "../collector.c", "sha256": SOURCE_SHA,
                      "guard": "M02_STORAGE_FAULT_TEST_ONLY", "guard_value": 1,
                      "selector_macro": "M02_STORAGE_FAULT_CASE"}:
        raise ValueError("collector binding")
    selectors = [case["selector"] for case in record["cases"]]
    if selectors != list(range(7)) or [case["witness_packets"] for case in record["cases"]] != \
       [22, 10, 17, 22, 17, 22, 17]:
        raise ValueError("selector schedule")
    if any(case["witness_packets"] >= record["witness"]["packet_count_max"]
           for case in record["cases"]):
        raise ValueError("witness bound")
    source = read(SOURCE)
    if sha(source) != SOURCE_SHA:
        raise ValueError("collector hash")
    return record

def replace_once(text, old, new, label):
    if text.count(old) != 1:
        raise ValueError("anchor " + label)
    return text.replace(old, new, 1)

def generate(raw):
    if sha(raw) != SOURCE_SHA:
        raise ValueError("collector hash")
    text = raw.decode("utf-8")
    if "M02_STORAGE_FAULT_TEST_ONLY" in text or '#include "storage-fault-v1/inject.h"' in text:
        raise ValueError("already instrumented")
    text = replace_once(
        text, "static volatile sig_atomic_t interrupted;\n",
        "static volatile sig_atomic_t interrupted;\n#include \"storage-fault-v1/inject.h\"\n",
        "include")
    text = replace_once(
        text,
        "    int opened = openat(attempt_fd, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);\n",
        "    int opened = !strcmp(name, \"events.jsonl\") ? sf_open(SF_EVENTS_CREATE, SF_EVENTS, attempt_fd, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600) : openat(attempt_fd, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);\n"
        "    if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n",
        "events create")
    text = replace_once(
        text,
        "    s->fd = high_fd(opened);\n",
        "    s->fd = high_fd(opened);\n"
        "    if (!strcmp(name, \"events.jsonl\") && s->fd >= 0) sf_bind(SF_EVENTS_CREATE, SF_EVENTS, opened, s->fd);\n"
        "    if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n",
        "events bind")
    text = replace_once(
        text,
        "        ssize_t n = write(s->fd, bytes + done, keep - done);\n",
        "        ssize_t n = s == &request_artifact ? sf_write(SF_REQUEST, s->fd, bytes + done, keep - done) : write(s->fd, bytes + done, keep - done);\n"
        "        if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n",
        "request write")
    text = replace_once(
        text,
        "            if (!n) { s->eof = true; close(s->fd); s->fd = -1; break; }\n",
        "            if (!n) { int closed_fd = s->fd; s->eof = true; close(s->fd); s->fd = -1; sf_observe_eof(i, closed_fd); if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO); break; }\n",
        "eof observation")
    text = replace_once(
        text,
        "    p->raw_wait = raw; p->reaped = true;\n",
        "    p->raw_wait = raw; p->reaped = true; sf_observe_reap(p->pid, p->ticks, raw);\n"
        "    if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n",
        "reap observation")
    text = replace_once(
        text,
        "        if (no_children && leader.reaped && streams[0].eof && streams[1].eof && streams[2].eof) {\n            cleanup_complete = true; break;\n        }\n",
        "        if (no_children && leader.reaped && streams[0].eof && streams[1].eof && streams[2].eof) {\n"
        "            sf_observe_cleanup_ready(leader.pid, leader.ticks, leader.raw_wait);\n"
        "            if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n"
        "            cleanup_complete = true; break;\n        }\n",
        "cleanup ready")
    text = replace_once(
        text,
        "    if (!cleanup_complete || cleanup_finished >= cleanup_deadline) {\n        cleanup_complete = false; fail(\"CLEANUP_ERROR\", \"owned-cleanup-deadline-or-pipe-holder\", ETIMEDOUT);\n    }\n",
        "    if (!cleanup_complete || cleanup_finished >= cleanup_deadline) {\n"
        "        cleanup_complete = false; fail(\"CLEANUP_ERROR\", \"owned-cleanup-deadline-or-pipe-holder\", ETIMEDOUT);\n"
        "    }\n"
        "    sf_observe_cleanup_final(cleanup_start, cleanup_deadline, cleanup_finished, cleanup_complete, owned_count, owned_omitted, failure);\n"
        "    if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n",
        "cleanup final")
    text = replace_once(
        text,
        "        if (all[i]->fd >= 0 && fsync(all[i]->fd) != 0) fail(\"COLLECTOR_ERROR\", \"artifact-fsync\", errno);\n",
        "        if (all[i]->fd >= 0) {\n"
        "            int sync_result = all[i] == &request_artifact ? sf_sync(SF_REQUEST_SYNC, SF_REQUEST, all[i]->fd) : fsync(all[i]->fd);\n"
        "            if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n"
        "            if (sync_result != 0) fail(\"COLLECTOR_ERROR\", \"artifact-fsync\", errno);\n"
        "        }\n",
        "request sync")
    text = replace_once(
        text,
        "    int fd = high_fd(openat(attempt_fd, \"report.json\", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));\n",
        "    int report_opened = sf_open(SF_REPORT_CREATE, SF_REPORT, attempt_fd, \"report.json\", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);\n"
        "    if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n"
        "    int fd = high_fd(report_opened);\n"
        "    if (fd >= 0) sf_bind(SF_REPORT_CREATE, SF_REPORT, report_opened, fd);\n"
        "    if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n",
        "report create")
    text = replace_once(
        text,
        "    bool ok = fflush(f) == 0 && !ferror(f) && fsync(fd) == 0;\n",
        "    int flush_result = sf_flush(fd, f);\n"
        "    if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n"
        "    bool ok = flush_result == 0 && !ferror(f);\n"
        "    if (ok) {\n"
        "        int report_sync_result = sf_sync(SF_REPORT_SYNC, SF_REPORT, fd);\n"
        "        if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n"
        "        ok = report_sync_result == 0;\n"
        "    }\n",
        "report flush sync")
    text = replace_once(
        text,
        "    if (argc != 5) { fputs(\"usage: linux-collector --linux-sealed-infrastructure-v1 REQUEST INPUT_MANIFEST ATTEMPT\\n\", stderr); return 2; }\n",
        "    if (argc != 5) { fputs(\"usage: linux-collector --linux-sealed-infrastructure-v1 REQUEST INPUT_MANIFEST ATTEMPT\\n\", stderr); return 2; }\n"
        "    if (!sf_startup()) return 125;\n",
        "startup")
    text = replace_once(
        text,
        "    if (pid == 0) child_run(input.fd, pipes[0][1], pipes[1][1], pipes[2][1]);\n",
        "    if (pid == 0) { sf_child_close(); child_run(input.fd, pipes[0][1], pipes[1][1], pipes[2][1]); }\n",
        "child close")
    text = replace_once(
        text,
        "    cleanup(); validate_setup();\n",
        "    cleanup(); validate_setup();\n"
        "    if (child_created) {\n"
        "        sf_observe_setup(setup_words, &cwd_identity, &devnull_identity, &pipe_identity[0], &pipe_identity[1], &executable.backing, executable.seals, leader.pid, leader.ticks);\n"
        "        if (sf_transport_failed()) fail(\"COLLECTOR_ERROR\", \"test-witness\", EIO);\n"
        "    }\n",
        "setup observation")
    return text.encode("utf-8")

def diff(raw, generated):
    return "".join(difflib.unified_diff(
        raw.decode().splitlines(True), generated.decode().splitlines(True),
        fromfile="collector.c", tofile="storage-fault-v2-collector.c")).encode()

def write_complete(path, raw, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, mode)
    primary = None
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("short output write")
            view = view[count:]
        os.fsync(fd)
    except Exception as error:
        primary = error
    primary = close_fds((fd,), primary)
    if primary is not None:
        raise primary

def source_bindings():
    records = {}
    for name, path in SOURCE_PROGRAMS.items():
        canonical = path.resolve()
        raw = read(canonical)
        records[name] = {"path": str(canonical), "size": len(raw),
                         "sha256": sha(raw)}
    return records

def prepare(packet_path, attempt_root):
    record = packet(packet_path)
    attempt_root = Path(attempt_root)
    if attempt_root.exists():
        raise FileExistsError("attempt root exists")
    parent = attempt_root.parent.resolve()
    if not parent.is_dir() or attempt_root.parent != parent:
        raise ValueError("canonical attempt parent required")
    raw = read(SOURCE)
    generated = generate(raw)
    patch = diff(raw, generated)
    expected_patch = read(HERE / "collector.patch")
    if patch != expected_patch:
        raise ValueError("collector patch binding")
    attempt_root.mkdir(mode=0o700)
    write_complete(attempt_root / "source.collector.c", raw, 0o600)
    write_complete(attempt_root / "storage-fault-v2-collector.c", generated, 0o600)
    write_complete(attempt_root / "inject.h", read(HERE / "inject.h"), 0o600)
    write_complete(attempt_root / "generated.diff", patch, 0o600)
    result = {
        "schema_version": 2, "status": "PREPARED_NOT_BUILT",
        "source_sha256": sha(raw), "generated_sha256": sha(generated),
        "header_sha256": sha(read(HERE / "inject.h")),
        "diff_sha256": sha(patch),
        "source_bindings": source_bindings(),
        "selectors": [case["selector"] for case in record["cases"]],
        "backend_enabled": False, "application_acceptance": False,
    }
    write_complete(attempt_root / "prepare.json",
                   (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode(),
                   0o600)
    directory = parent_fd = -1
    primary = None
    try:
        directory = os.open(attempt_root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        os.fsync(directory)
        os.fsync(parent_fd)
    except Exception as error:
        primary = error
    primary = close_fds((directory, parent_fd), primary)
    if primary is not None:
        raise primary
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--attempt-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.packet.resolve(), args.attempt_root), sort_keys=True))

if __name__ == "__main__":
    main()
