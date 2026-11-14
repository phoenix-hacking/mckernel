#!/usr/bin/python3
"""Finite separately released ROOT-GIT-METADATA-ONLY child; no observer/effect mode."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
import types

BASE = Path('/home/holden/mckernel-work/host-preparation/evening-git-metadata-diagnostic-20261019-1')
P = Path('/home/holden/mckernel-work/host-preparation/duplicate-archive-cleanup-execution-preparation-20261018-1')
SOURCE = P / 'exact120.py'
SOURCE_SHA256 = '0c134ee778b273610ead1ecc507caa038642459c0a065c956b4431c35c755917'


def load_contract():
    # No __main__ execution, import cache writes, or cleanup entrypoint call.
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise RuntimeError('exact source pin')
    contract = types.ModuleType('git_only_exact_contract')
    contract.__file__ = str(SOURCE)
    exec(compile(raw, str(SOURCE), 'exec'), contract.__dict__)
    # Re-read via production nofollow/identity-bounded reader before any effect.
    if contract.digest(contract.raw_small(SOURCE)) != SOURCE_SHA256:
        raise RuntimeError('exact source identity pin')
    return contract


def main():
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument('--release', required=True)
    p.add_argument('--release-sha256', required=True)
    a = p.parse_args()
    c = load_contract()
    c.require(os.getuid() == 0 and os.geteuid() == 0, 'root diagnostic required')
    raw = c.raw_small(Path(a.release))
    c.require(c.digest(raw) == a.release_sha256, 'release digest')
    r = json.loads(raw)
    own_sha = c.digest(c.raw_small(Path(__file__).resolve()))
    c.require(r['status'] == 'ROOT_GIT_METADATA_ONLY_RELEASE' and r['source_sha256'] == SOURCE_SHA256 and
              r['diagnostic_sha256'] == own_sha and r['manifest_sha256'] == c.PIN, 'diagnostic release pins')
    c.require(r['independent_review']['status'] == 'PASS' and len(r['independent_review']['sha256']) == 64,
              'independent diagnostic review')
    c.require(r['boot_id'] == c.BOOT == Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'boot identity')
    c.require(time.time() <= r['expires_unix'] <= time.time() + 600, 'release freshness')
    c.require(c.proc_identity(r['coordinator_identity'][0])[0] == r['coordinator_identity'][1], 'coordinator identity')
    rows = c.pinned()['rows']
    # All frozen restoration headers, once; never candidate/archive bodies.
    selected = rows
    expected_count = len({oid for row in rows for oid in
                          (row['restoration']['git_blob'], row['restoration']['git_commit'])})
    c.require(r['selected_rows'] == 120 and r['selected_objects'] == expected_count, 'selected metadata closure')
    fd = os.open(c.LOCK, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        c.require((os.fstat(fd).st_dev, os.fstat(fd).st_ino) == c.LOCK_ID, 'mutex fd identity')
        c.require((os.lstat(c.LOCK).st_dev, os.lstat(c.LOCK).st_ino) == c.LOCK_ID, 'mutex name identity')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = c.git_available(selected)
        c.require(result['objects'] == expected_count, 'selected metadata object count')
        print(json.dumps({'status': 'ROOT_GIT_METADATA_ONLY_PASS', 'source_sha256': SOURCE_SHA256,
                          'diagnostic_sha256': own_sha, 'manifest_sha256': c.PIN,
                          'selected_rows': len(selected), 'git': result,
                          'blob_bodies_read': False, 'cleanup_observation': False, 'deletion': False}, sort_keys=True))
    finally:
        os.close(fd)


if __name__ == '__main__':
    main()
