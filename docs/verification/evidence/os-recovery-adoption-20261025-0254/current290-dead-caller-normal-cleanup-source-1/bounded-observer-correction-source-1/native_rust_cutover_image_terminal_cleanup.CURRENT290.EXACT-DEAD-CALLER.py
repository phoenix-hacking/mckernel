#!/usr/bin/env python3
"""Fixed-path archival retirement; default is read-only validation.

The persistent mutex is never unlinked. flock releases it on process death.
A torn plan/journal is retained and quarantined, never repaired speculatively.
Execution requires an independently reviewed release and runs under sudo -A.
Historical observations are frozen evidence, never execution authority.
Ownership records exchange with empty directory sentinels and remain archived.
Sentinels keep the active names occupied until durable release authorization;
only rmdir releases them, so a newer regular ownership record is never deleted.

Supported publisher contract: one campaign coordinator, no concurrent project
build/cleanup worker, and ordinary publishers creating regular files with
O_CREAT|O_EXCL. The privileged census checks these prerequisites immediately
before mutations and sentinel release. This is NOT protection against an
arbitrary same-UID adversary swapping directories between the final check and
rmdir. Such directory publishers are excluded by the execution prerequisite.
"""
import argparse
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import signal
import time


FP_AUTHORITY = Path('/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/populated-source-preparation-1/fp_authority.py')
FP_AUTHORITY_SHA = 'e389dde20e339ed50005ba36ebd641a8244d4d30ddefaeabb2a0b798b93c312b'
def fp_contract():
    raw=FP_AUTHORITY.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=FP_AUTHORITY_SHA:
        raise RuntimeError('FP authority source bytes differ')
    import types
    module=types.ModuleType('_exact_fp_authority');module.__file__=str(FP_AUTHORITY)
    exec(compile(raw,str(FP_AUTHORITY),'exec'),module.__dict__)
    return module

REPO = Path('/home/holden/mckernel')
PUBLISHED_SCRIPT = 'docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-dead-caller-normal-cleanup-source-1/bounded-observer-correction-source-1/native_rust_cutover_image_terminal_cleanup.CURRENT290.EXACT-DEAD-CALLER.py'
PUBLISHED_TESTS = 'scripts/tests/test_native_rust_cutover_image_terminal_cleanup.py'
SELFTEST = REPO / PUBLISHED_TESTS
NAMESPACE = Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/actual-current290-default-image-attempt-4')
NAMESPACE_ANCESTRY = [{'device': 66306, 'gid': 0, 'inode': 2, 'mode': 16877, 'path': '/', 'uid': 0}, {'device': 66306, 'gid': 0, 'inode': 45481985, 'mode': 16877, 'path': '/home', 'uid': 0}, {'device': 66306, 'gid': 1000, 'inode': 45481986, 'mode': 16877, 'path': '/home/holden', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 47459795, 'mode': 16893, 'path': '/home/holden/mckernel', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 47460229, 'mode': 16893, 'path': '/home/holden/mckernel/docs', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 47468442, 'mode': 16877, 'path': '/home/holden/mckernel/docs/verification', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 47468450, 'mode': 16877, 'path': '/home/holden/mckernel/docs/verification/evidence', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 56123581, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 56123582, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 56123583, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59542426, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59542783, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59544015, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59544136, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59652809, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59653427, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59653445, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59653515, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59653779, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59654533, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59654969, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59655048, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59655120, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59655144, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1', 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59655232, 'mode': 16832, 'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1', 'uid': 1000}, {'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/actual-current290-default-image-attempt-4', 'device': 66306, 'inode': 59655333, 'mode': 16832, 'uid': 1000, 'gid': 1000}]
NAMESPACE_BINDING = {'device': 66306, 'inode': 59655333, 'mode': 16832, 'uid': 1000, 'gid': 1000}
ROOT = Path('/home/holden/mckernel-work/scratch')
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
DEVICE = None  # A future, independently reviewed release binds the live device.
UID = GID = 1000
PREFIX = 'm14-current290-owner213-rolejoin-pathfix-retirement-20261026-1'
CANDIDATE = None  # Derived only from the exact consumed image request at release validation.
ATTEMPT = NAMESPACE / "common-exclusion.json"
SHARED = ROOT / 'mckernel-heavy-operation.lock'
REQUEST = Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/image-request.CURRENT290.ATTEMPT4.READONLY-SEED.NAMESPACE-ABSENT.NOT-GRANTED.json')
LEASE = NAMESPACE / "lease.json"
OUTPUT = NAMESPACE / "owner-work"
EVIDENCE = NAMESPACE / "owner-evidence"
MUTEX = ROOT / (PREFIX + '.mutex')
PLAN = ROOT / (PREFIX + '.plan.json')
JOURNAL = ROOT / (PREFIX + '.journal.jsonl')
CAPTURE = ROOT / (PREFIX + '.docker-logs.capture')
QUARANTINE = ROOT / (PREFIX + '.quarantine.json')
ARCHIVE_NAMES = (PREFIX + '.attempt.archive', PREFIX + '.shared.archive')
ROOT_LOCK = Path('/run/lock/mckernel-development.lock')
BASELINE_SOURCE_SHA = '6606af40114eb5b6019438c4127948081d80bbe65144d841e906a7cba84aabed'
NATIVE_BASELINE_SOURCE_SHA = '8449b4b87b2286d4dc3d08e0c5921d2d79e44f17920d0aaee3eae646993fc995'
KNOWN_TARGET = None  # Actual identity comes only from the released normal caller PROCESS/JOIN/receipt.
REQUEST_SHA = '31a38f75dea33c1b280270ce9d3e8ce25fd6ae354c0bf4808a7ada5def3ca435'
IMAGE_CANDIDATE = 'eb3ce544eb1f479a56933a5c7fa8300ab6dfe533'
ROOT_TERMINAL = None  # Exact future nonce-bound guard-result.json proof.
CONTAINER = CONTAINER_NAME = OWNER_NONCE = OWNER_PID = OWNER_START = None
EXPECTED_EXIT = None
# Retain the root guard and all eight historical Docker clients as census roots.
WAITER_PIDS = ()  # Future exact guard command ledger supplies every current client PID.
BOOT_ID = None
RECORDS = {}
DIRS = {}
PROTECTED = []
TERMINAL = EVIDENCE / 'owner-receipt.json'
TERMINAL_SHA = TERMINAL_INODE = TERMINAL_SIZE = None
LIMIT = 1 << 20
# Preserve the reviewed authority1 actual-size caps and complete inventory bounds.
PROTECTED_LIMIT = 128 << 20
DOCUMENT_LIMIT = 256 << 20
INVENTORY_LIMIT = 400000
RELEASE = None
ROOT_LOCK_BINDING = None
EXPECTED_CONTAINER = None

CURRENT230_SOURCE_ROOT = Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1/materialized-source')
CURRENT230_OWNER_ARGV = ['/usr/bin/taskset', '-c', '7', '/usr/bin/prlimit', '--fsize=33554432', '--as=2147483648:2147483648', '--core=0:0', '--', '/home/holden/anaconda3/bin/python3', '-I', '-B', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/owner-namespace-constant-reconciliation-source-1/native_rust_exact_mckernel_image_container_owner.CURRENT290.NAMESPACE4-COMMON-BOUND.py', '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/image-request.CURRENT290.ATTEMPT4.READONLY-SEED.NAMESPACE-ABSENT.NOT-GRANTED.json']
CURRENT230_CALLER_CAPTURE = Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/actual-entry-1')
CURRENT230_TYPED_PROTOCOL = {'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/current290_cleanup_typed_protocol.ATTEMPT4.READONLY-SEED.py', 'sha256': '164d89899d28d4e9faf8d435ee49af74920a3d7c08ac1731cb985bc645967971', 'bytes': 19804}
INHERITED_ROOT_LOCK = None
OWNERSHIP_CASE = None
PUBLISHER_CONTRACT = {
    'schema': 'fp-save-image.publisher-contract.v1',
    'coordination': 'sole-campaign-coordinator-no-concurrent-build-or-cleanup',
    'publishers': 'project-owned-regular-file-O_CREAT|O_EXCL-only',
    'census': 'root-full-process-and-container-before-transaction-and-every-rmdir',
    'excluded': 'arbitrary-same-UID-directory-substitution-after-final-check',
}
DEFERRED_SIGNALS = {signal.SIGHUP, signal.SIGINT, signal.SIGTERM, signal.SIGQUIT}

class SameOFDRefusal(ValueError):
    pass

def same_ofd_need(value, message):
    if not value:
        raise SameOFDRefusal(message)

def same_ofd_read(path, maximum=1048576):
    with open(path, 'rb') as stream:
        raw = stream.read(maximum + 1)
    same_ofd_need(len(raw) <= maximum, 'same-ofd-read-bound:' + str(path))
    return raw

def same_ofd_metadata(meta):
    return dict(device=meta.st_dev, inode=meta.st_ino, uid=meta.st_uid,
                gid=meta.st_gid, mode=stat.S_IMODE(meta.st_mode), nlink=meta.st_nlink)

def same_ofd_process(pid):
    same_ofd_need(type(pid) is int and pid > 0, 'same-ofd-holder-pid')
    raw = same_ofd_read('/proc/' + str(pid) + '/stat', 65536)
    left, separator, right = raw.rpartition(b') ')
    fields = right.split()
    same_ofd_need(separator and left.startswith(str(pid).encode() + b' (') and
                  len(fields) >= 50 and fields[0] not in (b'Z', b'X', b'x') and
                  fields[19].isdigit(), 'same-ofd-holder-stat')
    status = same_ofd_read('/proc/' + str(pid) + '/status', 65536).decode('ascii')
    uids = [line.split()[1:] for line in status.splitlines() if line.startswith('Uid:')]
    gids = [line.split()[1:] for line in status.splitlines() if line.startswith('Gid:')]
    same_ofd_need(len(uids) == len(gids) == 1 and len(uids[0]) == len(gids[0]) == 4,
                  'same-ofd-holder-credentials')
    return dict(pid=pid, starttime=fields[19].decode(),
                uids=[int(value) for value in uids[0]], gids=[int(value) for value in gids[0]])

def same_ofd_fd_locks(pid, fd):
    same_ofd_need(type(fd) is int and fd >= 0, 'same-ofd-descriptor-number')
    text = same_ofd_read('/proc/' + str(pid) + '/fdinfo/' + str(fd), 65536).decode('ascii')
    return [line.split()[2:] for line in text.splitlines() if line.startswith('lock:')]

def validate_held_same_ofd(fd, holder, expected_path, expected_identity, caller_source):
    """Read-only proof of the particular locked description, not merely the inode."""
    same_ofd_need(type(holder) is dict and type(caller_source) is dict, 'same-ofd-binding-shape')
    same_ofd_need(holder.get('path') == str(expected_path) and holder.get('identity') == expected_identity,
                  'same-ofd-fixed-path-identity')
    same_ofd_need(holder.get('transport') == 'STDIN_FD0_SUDO_A' and holder.get('transported_fd') == 0 and
                  type(holder.get('fd')) is int and holder['fd'] == holder.get('original_holder_fd'),
                  'same-ofd-stdin-transport')
    same_ofd_need(type(holder.get('owner_relationship')) is str and holder['owner_relationship'] and
                  type(holder.get('acquired_at_epoch')) in (int, float) and holder['acquired_at_epoch'] > 0,
                  'same-ofd-holder-contract')
    pid = holder.get('pid')
    before_process = same_ofd_process(pid)
    same_ofd_need(str(holder.get('starttime')) == before_process['starttime'] and
                  before_process['uids'] == [1000] * 4 and before_process['gids'] == [1000] * 4,
                  'same-ofd-exact-holder-birth-credentials')
    same_ofd_need(same_ofd_read('/proc/sys/kernel/random/boot_id', 128).decode().strip() == holder.get('boot_id'),
                  'same-ofd-holder-boot')
    command = same_ofd_read('/proc/' + str(pid) + '/cmdline', 65536)
    same_ofd_need(command.endswith(b'\0') and caller_source.get('path') in
                  [word.decode('utf-8', 'strict') for word in command[:-1].split(b'\0')],
                  'same-ofd-exact-caller-source-argv')
    source = same_ofd_read(caller_source['path'], 4194304)
    same_ofd_need(len(source) == caller_source.get('bytes') and
                  hashlib.sha256(source).hexdigest() == caller_source.get('sha256'), 'same-ofd-caller-source-bytes')
    before = os.fstat(fd)
    named = os.stat(expected_path, follow_symlinks=False)
    same_ofd_need(stat.S_ISREG(before.st_mode) and stat.S_ISREG(named.st_mode) and before.st_size == named.st_size == 0 and
                  same_ofd_metadata(before) == same_ofd_metadata(named) == expected_identity,
                  'same-ofd-held-fd-and-name')
    same_ofd_need(fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY,
                  'same-ofd-readonly-description')
    key = '{:02x}:{:02x}:{}'.format(os.major(before.st_dev), os.minor(before.st_dev), before.st_ino)
    expected_lock = ['FLOCK', 'ADVISORY', 'WRITE', str(pid), key, '0', 'EOF']
    # fdinfo reports locks owned by this open description. An independently opened
    # descriptor has no such row even when it names the same locked inode.
    same_ofd_need(same_ofd_fd_locks(os.getpid(), fd) == [expected_lock] and
                  same_ofd_fd_locks(pid, holder['original_holder_fd']) == [expected_lock],
                  'same-ofd-description-lock-binding')
    locks = [line.split()[1:] for line in same_ofd_read('/proc/locks').decode('ascii').splitlines()
             if key in line.split()]
    same_ofd_need(locks == [expected_lock], 'same-ofd-exclusive-global-lock-owner')
    after = os.fstat(fd)
    named_after = os.stat(expected_path, follow_symlinks=False)
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    same_ofd_need(all(getattr(before, field) == getattr(after, field) == getattr(named_after, field)
                      for field in fields) and same_ofd_process(pid) == before_process,
                  'same-ofd-holder-or-path-raced')
    return True

def duplicate_held_same_ofd(fd, holder, expected_path, expected_identity, caller_source):
    validate_held_same_ofd(fd, holder, expected_path, expected_identity, caller_source)
    duplicate = os.dup(fd)
    try:
        validate_held_same_ofd(duplicate, holder, expected_path, expected_identity, caller_source)
        same_ofd_need(not os.get_inheritable(duplicate), 'same-ofd-private-duplicate-cloexec')
        return duplicate
    except BaseException:
        os.close(duplicate)
        raise

def current230_contract():
    import types
    ref = CURRENT230_TYPED_PROTOCOL
    raw = read_bounded(Path(ref['path']))
    if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
        raise Refusal('current230-typed-protocol-source-binding')
    module = types.ModuleType('_exact_current230_typed_protocol')
    module.__file__ = ref['path']
    exec(compile(raw, ref['path'], 'exec'), module.__dict__)
    return module


# Separate recovery mode; original same-OFD transport remains the default.
DEAD_CALLER_MODE = 'EXACT_DEAD_CALLER_NEW_OFD'
DEAD_CALLER_BINDING = None
DEAD_CALLER_FROZEN = json.loads('{"boot_id": "7bfc5687-6c04-4d15-84eb-b92ab9a55dcb", "caller_pgid": "UNKNOWN_NOT_RECONSTRUCTED", "caller_pid": 1043200, "caller_starttime": "80013658", "group_ids": [1043203, 1043212, 1043234, 1043716], "operation_argv_paths": ["/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/actual-current290-default-image-attempt-4", "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/run_frozen_current290_image_entry.ATTEMPT4.READONLY-SEED.py", "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/image-request.CURRENT290.ATTEMPT4.READONLY-SEED.NAMESPACE-ABSENT.NOT-GRANTED.json", "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/owner-namespace-constant-reconciliation-source-1/native_rust_exact_mckernel_image_container_owner.CURRENT290.NAMESPACE4-COMMON-BOUND.py"], "owner_pid": 1043716, "owner_starttime": "80020161", "recorded_children": [{"expected_returncode": 0, "name": "five", "pgid": 1043203, "pid": 1043203, "starttime": "80013809"}, {"expected_returncode": 0, "name": "prepare", "pgid": 1043212, "pid": 1043212, "starttime": "80013842"}, {"expected_returncode": 0, "name": "finish", "pgid": 1043234, "pid": 1043234, "starttime": "80013975"}, {"expected_returncode": 1, "name": "owner", "pgid": 1043716, "pid": 1043716, "starttime": "80020161"}], "references": {"ACTUAL-OWNER-ENTRY.json": {"bytes": 4432, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/actual-entry-1/ACTUAL-OWNER-ENTRY.json", "sha256": "0d2f48f62a8907f3636525e64a290033afe5f0c547bf0a6f6ce424fc5dc9c471"}, "ROOT-NORMAL-CLEANUP-COMPLETION-READY.json": {"bytes": 9134, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/actual-entry-1/ROOT-NORMAL-CLEANUP-COMPLETION-READY.json", "sha256": "f95323788f1315d1f8aab364754f7dc8d032c71987144fc1f99acf104f382c41"}, "caller_source": {"bytes": 35403, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/run_frozen_current290_image_entry.ATTEMPT4.READONLY-SEED.py", "sha256": "13af5011ffc4ccaa7510b0e720ba1b79ab34c444a7a3aa32f14a503a39a4d3b4"}, "finish.JOIN.json": {"bytes": 7368, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/actual-entry-1/finish.JOIN.json", "sha256": "4675a29987720762c67616b04a5a4ec3f0a0748ad1dcb5f5671aa9b3c4b2db0d"}, "finish.PROCESS.json": {"bytes": 2547, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/actual-entry-1/finish.PROCESS.json", "sha256": "14f4f3ffc89f62d443e63762da463af916175461606fea3f2ce980d4ed1417a6"}, "five.JOIN.json": {"bytes": 6209, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/actual-entry-1/five.JOIN.json", "sha256": "06ec2db4173a1fb2b2b7a1e16dfe43aaefb5c0bc6295f4410345bdf5a94caca8"}, "five.PROCESS.json": {"bytes": 1394, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/actual-entry-1/five.PROCESS.json", "sha256": "fb5a1f688ba7761f98525e3e05cd63b43de4d01a86b82e674f3730a80f7df013"}, "owner.JOIN.json": {"bytes": 7033, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/actual-entry-1/owner.JOIN.json", "sha256": "93c18cb9a5029ceb1da2277e83f446e0ccfc29c4098b5bfb1c6a5f3b5a7576b7"}, "owner.PROCESS.json": {"bytes": 2221, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/actual-entry-1/owner.PROCESS.json", "sha256": "026837b4eb908457dcf5bf3a186eb569c8a91fe1d1dee840d052c847b75b9103"}, "owner_receipt": {"bytes": 37704, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/actual-current290-default-image-attempt-4/owner-evidence/owner-receipt.json", "sha256": "af5934cce5e375f4d3c49f3aca01b66f20361f0b78857a0cfe06d781ddfd9389"}, "prepare.JOIN.json": {"bytes": 7536, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/actual-entry-1/prepare.JOIN.json", "sha256": "0d490016d26b68986211ca18d84e2f7d25840614bd6e5196ed6a4ee7e9632c67"}, "prepare.PROCESS.json": {"bytes": 2710, "path": "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/actual-entry-1/prepare.PROCESS.json", "sha256": "597a5443d8540f9cf5e1927e2d2e5b8ff399e483e2b525eb946316e0426b072a"}}, "schema": "mckernel.current290.cleanup.exact-dead-caller-new-ofd.v1"}')
DEAD_CALLER_OBSERVATIONS = []
DEAD_CALLER_CAPTURE_BYTES = 0

def validate_dead_caller_binding(value):
    if value.get('cleanup_mode') != DEAD_CALLER_MODE or value.get('inherited_root_lock') is not None:
        raise Refusal('dead-caller-mode-cannot-inherit-or-waive-lock')
    binding = value.get('dead_caller_new_ofd')
    if binding != DEAD_CALLER_FROZEN:
        raise Refusal('dead-caller-exact-frozen-binding-required')
    for ref in binding['references'].values():
        raw = read_bounded(Path(ref['path']))
        if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
            raise Refusal('dead-caller-original-evidence-changed:' + ref['path'])
    for child in binding['recorded_children']:
        process = parse(read_bounded(Path(binding['references'][child['name']+'.PROCESS.json']['path'])))
        joined = parse(read_bounded(Path(binding['references'][child['name']+'.JOIN.json']['path'])))
        if (process['pid'] != joined['pid'] or process['pid'] != child['pid'] or
                process['starttime'] != joined['starttime'] or process['starttime'] != child['starttime'] or
                process['pgid'] != child['pgid'] or child['pgid'] != child['pid'] or
                joined['returncode'] != child['expected_returncode'] or
                any(joined[k] is not True for k in ('direct_child_joined','group_absent','closed_streams')) or
                joined['error'] is not None or joined['retirement_error'] is not None):
            raise Refusal('dead-caller-recorded-child-positive-join-binding')
    # configure() separately retains the full normal typed join/readiness/source
    # validation. This check does not replace or waive any original predicate.
    entry = parse(read_bounded(Path(binding['references']['ACTUAL-OWNER-ENTRY.json']['path'])))
    if (entry['caller_pid'] != binding['caller_pid'] or
            entry['caller_starttime'] != binding['caller_starttime'] or
            entry['holder']['boot_id'] != binding['boot_id'] or
            entry['holder']['identity'] != dict(device=27, inode=4, uid=0, gid=0, mode=0o644, nlink=1)):
        raise Refusal('dead-caller-original-birth-and-mutex-binding')
    return binding

def validate_dead_caller_snapshots(snapshots, binding, boot_id):
    if boot_id != binding['boot_id'] or len(snapshots) != 2:
        raise Refusal('dead-caller-boot-or-snapshot-count')
    if not isinstance(binding.get('group_ids'), list) or not binding['group_ids'] or any(type(x) is not int or x <= 0 for x in binding['group_ids']):
        raise Refusal('dead-caller-original-group-proof-required')
    combined = {}
    groups = set(binding['group_ids'])
    roots = {binding['caller_pid'], binding['owner_pid'], *WAITER_PIDS,
             *(row['pid'] for row in binding['recorded_children'])}
    for rows in snapshots:
        seen = set()
        for row in rows:
            if (not isinstance(row, list) or len(row) != 4 or
                    any(type(x) is not int or x < 0 for x in (row[0],row[1],row[3])) or
                    row[0] <= 0 or row[0] in seen or not isinstance(row[2], str) or not row[2].isdigit()):
                raise Refusal('dead-caller-process-row')
            seen.add(row[0])
            combined.setdefault(row[0], set()).add(row[1])
            if row[3] in groups:
                raise Refusal('dead-caller-or-owner-group-present')
        if 1 not in seen:
            raise Refusal('dead-caller-incomplete-snapshot')
    related = set(roots)
    while True:
        expanded = related | {pid for pid, parents in combined.items() if parents & related}
        if expanded == related:
            break
        related = expanded
    # Any PID presence, including a reused birth or zombie, is refused.
    if related & set(combined):
        raise Refusal('dead-caller-owner-waiter-or-descendant-present')
    return True

def validate_dead_operation_argv(pid, argv, binding, observer_pid):
    if pid == observer_pid:
        return
    for word in argv:
        if any(word == path or word.startswith(path + '/') for path in binding['operation_argv_paths']):
            raise Refusal('dead-caller-unknown-operation-process-present')

def record_dead_caller_observation(raw_snapshots, boot_id, error=None):
    """Retain first full pair and failures; every later complete pair has hashes.

    Every recheck still reads and validates complete EOF bytes. Compact evidence
    prevents ordinary repeated transaction checks exhausting the capture budget.
    """
    observation = dict(boot_id=boot_id, observed_epoch=time.time(), observer_pid=os.getpid(),
                       sequence=len(DEAD_CALLER_OBSERVATIONS), status='REFUSED' if error else 'PASS_FULL_EOF_RECHECK',
                       snapshots=[dict(process_count=len(rows), sha256=digest(canonical(rows)), bytes=len(canonical(rows)))
                                  for rows in raw_snapshots])
    if not DEAD_CALLER_OBSERVATIONS or error:
        observation['raw_full_eof_snapshots'] = raw_snapshots
    if error:
        observation['error'] = error
    global DEAD_CALLER_CAPTURE_BYTES
    encoded = canonical(observation)
    if DEAD_CALLER_CAPTURE_BYTES + len(encoded) > 16 << 20:
        raise Refusal('dead-caller-capture-total-bound')
    DEAD_CALLER_CAPTURE_BYTES += len(encoded)
    DEAD_CALLER_OBSERVATIONS.append(observation)

def dead_caller_absent():
    if DEAD_CALLER_BINDING is None:
        return
    if os.getuid() != 0 or os.geteuid() != 0:
        raise Refusal('dead-caller-root-observation-required')
    boot_path = Path('/proc/sys/kernel/random/boot_id')
    before = boot_path.read_text().strip()
    snapshots = []
    raw_snapshots = []
    try:
        for _ in range(2):
            rows = []
            raw_rows = []
            raw_snapshots.append(raw_rows)
            entries = list(Path('/proc').iterdir())
            if len(entries) > 4096:
                raise Refusal('dead-caller-process-count')
            for path in entries:
                if not path.name.isdigit():
                    continue
                raw = same_ofd_read(str(path / 'stat'), 65536)
                left, separator, right = raw.rpartition(b') ')
                fields = right.split()
                if not separator or not left.startswith(path.name.encode() + b' (') or len(fields) < 50:
                    raise Refusal('dead-caller-process-stat')
                row = [int(path.name), int(fields[1]), fields[19].decode('ascii'), int(fields[2])]
                check_raw = same_ofd_read(str(path / 'stat'), 65536)
                check = check_raw.rpartition(b') ')[2].split()
                if len(check) < 50 or (check[1], check[2], check[19]) != (fields[1], fields[2], fields[19]):
                    raise Refusal('dead-caller-process-raced')
                command = same_ofd_read(str(path / 'cmdline'), 65536)
                if command and not command.endswith(b'\0'):
                    raise Refusal('dead-caller-cmdline-not-full-eof')
                argv = [word.decode('utf-8', 'strict') for word in command[:-1].split(b'\0')] if command else []
                if not argv and fields[0] not in (b'Z', b'X', b'x') and not (int(fields[6]) & 0x200000):
                    raise Refusal('dead-caller-live-command-unknown')
                executable = os.readlink(path / 'exe') if argv else ''
                raw_rows.append(dict(pid=row[0], stat_hex=raw.hex(), stat_after_hex=check_raw.hex(), cmdline_hex=command.hex(), executable=executable))
                validate_dead_operation_argv(row[0], argv, DEAD_CALLER_BINDING, os.getpid())
                rows.append(row)
            snapshots.append(rows)
        if boot_path.read_text().strip() != before:
            raise Refusal('dead-caller-boot-raced')
        validate_dead_caller_snapshots(snapshots, DEAD_CALLER_BINDING, before)
    except Exception as error:
        record_dead_caller_observation(raw_snapshots, before, type(error).__name__ + ':' + str(error))
        raise
    record_dead_caller_observation(raw_snapshots, before)

def inherited_root_binding(value):
    binding = value.get('inherited_root_lock')
    if (not isinstance(binding, dict) or set(binding) != {'schema', 'holder', 'caller_source'} or
            binding['schema'] != 'mckernel.current230.image-cleanup.inherited-root-lock.v1'):
        raise Refusal('current230-inherited-root-lock-binding-required')
    holder = binding['holder']
    expected_caller = current230_contract().contract()['static']['caller']
    if binding['caller_source'] != expected_caller:
        raise Refusal('current230-exact-frozen-caller-source-required')
    expected = dict(device=27, inode=4, uid=0, gid=0, mode=0o644, nlink=1)
    if holder.get('path') != str(ROOT_LOCK) or holder.get('identity') != expected:
        raise Refusal('current230-exact-permanent-root-lock')
    validate_held_same_ofd(0, holder, ROOT_LOCK, expected, binding['caller_source'])
    entry = parse(read_bounded(CURRENT230_CALLER_CAPTURE / 'ACTUAL-OWNER-ENTRY.json'))
    if entry['holder'] != holder or entry['caller_pid'] != holder['pid'] or entry['caller_starttime'] != holder['starttime']:
        raise Refusal('current230-normal-caller-held-lock-binding')
    return binding


def duplicate_inherited_root_lock():
    if os.getuid() != 0 or os.geteuid() != 0 or INHERITED_ROOT_LOCK is None:
        raise Refusal('current230-authenticated-root-stdin-required')
    return duplicate_held_same_ofd(0, INHERITED_ROOT_LOCK['holder'], ROOT_LOCK,
        dict(device=27, inode=4, uid=0, gid=0, mode=0o644, nlink=1), INHERITED_ROOT_LOCK['caller_source'])


def validate_transaction_inherited_lock(fd):
    if INHERITED_ROOT_LOCK is None:
        raise Refusal('current230-inherited-root-lock-lost')
    return validate_held_same_ofd(fd, INHERITED_ROOT_LOCK['holder'], ROOT_LOCK,
        dict(device=27, inode=4, uid=0, gid=0, mode=0o644, nlink=1), INHERITED_ROOT_LOCK['caller_source'])

def owned_record_paths():
    if OWNERSHIP_CASE in (None, 'FAIL_COMMON_AND_SHARED'):
        return (ATTEMPT, SHARED)
    if OWNERSHIP_CASE == 'PASS_COMMON_ONLY_SHARED_ABSENT':
        return (ATTEMPT,)
    raise Refusal('unsupported-current230-ownership-case')


def ownership_case_binding(receipt, obs, records):
    if not isinstance(records, list):
        raise Refusal('current230-retained-record-list')
    if receipt.get('status') == 'PASS':
        expected = 'PASS_COMMON_ONLY_SHARED_ABSENT'
        if (obs.get('ownership_case') != expected or obs.get('shared_record_already_absent') is not True or
                len(records) != 1 or {row.get('path') for row in records} != {str(ATTEMPT)} or
                os.path.lexists(SHARED)):
            raise Refusal('current230-positive-common-only-shared-absence')
        return expected
    if receipt.get('status') == 'FAIL':
        expected = 'FAIL_COMMON_AND_SHARED'
        if (obs.get('ownership_case') != expected or obs.get('shared_record_already_absent') is not False or
                len(records) != 2 or {row.get('path') for row in records} != {str(ATTEMPT), str(SHARED)}):
            raise Refusal('current230-failed-common-and-shared')
        return expected
    raise Refusal('current230-positive-normal-owner-status-required')


def require_unowned_shared_absent():
    if OWNERSHIP_CASE == 'PASS_COMMON_ONLY_SHARED_ABSENT':
        if os.path.lexists(SHARED) or os.path.lexists(ROOT / ARCHIVE_NAMES[1]):
            raise Refusal('current230-unowned-shared-or-unused-archive-reappeared')

def namespace_ancestry():
    rows = []
    for path in reversed((NAMESPACE, *NAMESPACE.parents)):
        meta = path.lstat()
        if not stat.S_ISDIR(meta.st_mode):
            raise Refusal('namespace-ancestor-not-directory')
        rows.append(dict(path=str(path), device=meta.st_dev, inode=meta.st_ino,
                         mode=meta.st_mode, uid=meta.st_uid, gid=meta.st_gid))
    return rows


def metadata_identity(path):
    """Cheap complete output/evidence census; never follow a build symlink."""
    meta = path.lstat()
    if not (stat.S_ISREG(meta.st_mode) or stat.S_ISDIR(meta.st_mode) or stat.S_ISLNK(meta.st_mode)):
        raise Refusal('protected-inventory-type:' + str(path))
    row = {'path': str(path), 'device': meta.st_dev, 'inode': meta.st_ino,
           'mode': meta.st_mode, 'uid': meta.st_uid, 'gid': meta.st_gid,
           'size': meta.st_size, 'nlink': meta.st_nlink,
           'mtime_ns': meta.st_mtime_ns, 'ctime_ns': meta.st_ctime_ns}
    if stat.S_ISLNK(meta.st_mode):
        row['target'] = os.readlink(path)
    return row

def metadata_inventory(root):
    paths = []
    for path in root.rglob('*'):
        if len(paths) + 1 >= INVENTORY_LIMIT:
            raise Refusal('protected-inventory-bound')
        paths.append(path)
    return [metadata_identity(root)] + [metadata_identity(path) for path in sorted(paths)]

def protected_files():
    require_unowned_shared_absent()
    """Preserve complete metadata census and only selected published byte joins."""
    if RELEASE is None:
        raise Refusal('release-not-configured')
    if os.path.lexists(LEASE):
        raise Refusal('request-lease-reappeared')
    for root in (OUTPUT, EVIDENCE):
        wanted = RELEASE['observation']['inventories'][str(root)]
        if metadata_inventory(root) != wanted:
            raise Refusal('protected-inventory-drift:' + str(root))
    if observe_identity(CANDIDATE) != RELEASE['observation']['candidate_root']:
        raise Refusal('candidate-root-drift')
    backup = RELEASE['observation']['backup_root']
    if observe_identity(Path(backup['path'])) != backup:
        raise Refusal('backup-root-drift')
    for row in PROTECTED:
        if observe_identity(Path(row['path'])) != row:
            raise Refusal('selected-artifact-or-receipt-drift:' + row['path'])

def capture_logs(present, execute=False, transaction=None):
    expected = read_bounded(EVIDENCE / 'attempt/container.log', maximum=PROTECTED_LIMIT)
    if os.path.lexists(CAPTURE):
        read_at_path(CAPTURE, expected)
        return
    if not present:
        raise Refusal('docker-log-capture-missing')
    raw = run_privileged_large(['/usr/bin/docker', '--host=unix:///var/run/docker.sock',
                                'logs', '--', CONTAINER])
    if raw != expected:
        raise Refusal('docker-log-mismatch')
    if execute:
        fd, _ = directory(ROOT)
        try:
            create_at(fd, CAPTURE.name, raw,
                      on_created=(lambda: setattr(transaction, 'mutation_started', True))
                      if transaction is not None else None)
        finally:
            os.close(fd)

def validate_container_profile(item):
    # Bind every recorded config/host-profile field, the command and exact mounts.
    for key in ('Id', 'Name', 'Image', 'Path', 'Args', 'Config', 'HostConfig', 'State',
                'Created', 'RestartCount', 'AppArmorProfile', 'Platform'):
        if canonical(item.get(key)) != canonical(EXPECTED_CONTAINER.get(key)):
            raise Refusal('container-profile-binding:' + key)
    if canonical(sorted(item.get('Mounts', []), key=lambda m: m['Destination'])) != canonical(sorted(
            EXPECTED_CONTAINER['Mounts'], key=lambda m: m['Destination'])):
        raise Refusal('container-mounts-binding')

class Refusal(ValueError):
    pass

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def parse(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise Refusal('duplicate-json-key')
            out[key] = value
        return out
    try:
        return json.loads(raw, object_pairs_hook=pairs)
    except (ValueError, UnicodeError) as exc:
        raise Refusal('invalid-json') from exc

def identity(meta):
    return (meta.st_dev, meta.st_ino)

def read_bounded(path, maximum=DOCUMENT_LIMIT):
    fd, _ = directory(path.parent)
    opened = None
    try:
        opened = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        before = os.fstat(opened)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise Refusal('bounded-file-shape:' + str(path))
        chunks = []
        remaining = before.st_size + 1
        while remaining:
            raw = os.read(opened, min(remaining, 1 << 20))
            if not raw:
                break
            chunks.append(raw)
            remaining -= len(raw)
        raw = b''.join(chunks)
        after = os.fstat(opened)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_nlink', 'st_uid',
                  'st_gid', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(before, k) != getattr(after, k) for k in fields) or
                len(raw) != before.st_size or identity(before) != identity(
                    os.stat(path.name, dir_fd=fd, follow_symlinks=False))):
            raise Refusal('bounded-file-raced:' + str(path))
        return raw
    finally:
        if opened is not None:
            os.close(opened)
        os.close(fd)

def observe_identity(path):
    parent, _ = directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        meta = os.fstat(fd)
        if not (stat.S_ISREG(meta.st_mode) or stat.S_ISDIR(meta.st_mode)):
            raise Refusal('identity-type:' + str(path))
        row = {'path': str(path), 'device': meta.st_dev, 'inode': meta.st_ino,
               'mode': oct(stat.S_IMODE(meta.st_mode)), 'uid': meta.st_uid,
               'gid': meta.st_gid, 'size': meta.st_size, 'nlink': meta.st_nlink}
        if stat.S_ISREG(meta.st_mode):
            if meta.st_size > PROTECTED_LIMIT:
                raise Refusal('protected-file-size-bound:' + str(path))
            hashed = hashlib.sha256()
            remaining = meta.st_size + 1
            observed = 0
            while remaining:
                raw = os.read(fd, min(remaining, 1 << 20))
                if not raw:
                    break
                observed += len(raw)
                remaining -= len(raw)
                hashed.update(raw)
            if observed != meta.st_size:
                raise Refusal('protected-file-size-raced:' + str(path))
            row['sha256'] = hashed.hexdigest()
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_nlink', 'st_uid',
                  'st_gid', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(meta, key) != getattr(after, key) for key in fields) or
                identity(after) != identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False))):
            raise Refusal('identity-raced')
        return row
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)

def read_at_path(path, expected):
    row = observe_identity(path)
    if (row['device'] != DEVICE or row['mode'] != '0o600' or row['uid'] != UID or
            row['gid'] != GID or row['nlink'] != 1 or row['size'] != len(expected) or
            row.get('sha256') != digest(expected)):
        raise Refusal('retained-capture-bytes')

def create_at(parent, name, data, on_created=None):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=parent)
    try:
        if on_created is not None:
            on_created()
        os.fchown(fd, UID, GID)
        write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.fsync(parent)

def validate_mount():
    raw = subprocess.check_output(['/usr/bin/findmnt', '-J', '-T', str(ROOT), '-o',
                                   'TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'], timeout=10)
    mounts = parse(raw)['filesystems']
    if len(mounts) != 1 or mounts[0] != RELEASE['observation']['mount']:
        raise Refusal('mount-drift')
    root = observe_identity(ROOT)
    expected = RELEASE['observation']['root']
    for key in ('path', 'device', 'inode', 'mode', 'uid', 'gid'):
        if root[key] != expected[key]:
            raise Refusal('root-identity-drift')

def validate_attempt_binding(target, request_identity):
    if (request_identity.get('path') != str(REQUEST) or request_identity.get('sha256') != REQUEST_SHA or
            not re.fullmatch('mckernel-image-[0-9a-f]{32}', str(target.get('container_name', ''))) or
            not re.fullmatch('[0-9a-f]{32}', str(target.get('owner_nonce', '')))):
        raise Refusal('exact-current230-request-and-target-shape')
    process = parse(read_bounded(CURRENT230_CALLER_CAPTURE / 'owner.PROCESS.json'))
    joined = parse(read_bounded(CURRENT230_CALLER_CAPTURE / 'owner.JOIN.json'))
    entry = parse(read_bounded(CURRENT230_CALLER_CAPTURE / 'ACTUAL-OWNER-ENTRY.json'))
    if (process['pid'] != target['owner_pid'] or process['starttime'] != target['owner_starttime'] or
            joined['pid'] != target['owner_pid'] or joined['starttime'] != target['owner_starttime'] or
            process['argv'] != joined['argv'] or joined['argv'] != entry['owner_argv'] or
            entry['owner_argv'] != CURRENT230_OWNER_ARGV or process['parent_pid'] != entry['caller_pid'] or
            not all(joined[k] is True for k in ('direct_child_joined', 'group_absent', 'closed_streams')) or
            joined['error'] is not None or joined['retirement_error'] is not None):
        raise Refusal('exact-current230-normal-owner-entry-and-join')

def image_request_binding(request):
    fixed = {'work_root': OUTPUT, 'owner_evidence_root': EVIDENCE,
             'output_root': OUTPUT / 'output', 'evidence_root': OUTPUT / 'evidence',
             'attempt_root': EVIDENCE / 'attempt', 'lease_path': LEASE,
             'common_exclusion_path': ATTEMPT}
    if (request.get('schema') != 'mckernel.native-exact-mckernel-image-container-request.v1' or
            request.get('candidate_sha') != IMAGE_CANDIDATE or
            any(request.get(key) != str(path) for key, path in fixed.items())):
        raise Refusal('image-request-namespace')
    for key in ('source_root', 'backup_root'):
        path = Path(request[key])
        if path != (CURRENT230_SOURCE_ROOT if key == 'source_root' else ROOT / 'mckernel-exact-candidate-scratch-22-authority3-metadata-backup') or '..' in path.parts or path in (OUTPUT, EVIDENCE):
            raise Refusal('image-input-root-binding')
    return Path(request['source_root'])

def image_record_binding(path, row, owner, request, target, boot):
    common = path == ATTEMPT
    expected = {'schema': 'mckernel.native-exact-operational-exclusion.v1' if common else
                'mckernel.heavy-operation.v1', 'pid': target['owner_pid'],
                'starttime': target['owner_starttime'], 'boot_id': boot,
                'request_sha256': digest(json.dumps(request, sort_keys=True).encode()) if common else
                digest(canonical(request)), 'dev' if common else 'device': row['device'],
                'inode': row['inode']}
    if not common:
        expected['kind'] = 'image'
    if path not in owned_record_paths() or canonical(owner) != canonical(expected):
        raise Refusal('image-exclusion-owner-binding')

def image_layout(request):
    command = ['/driver.py', '--source-root', '/src', '--candidate-sha', request['candidate_sha'],
               '--ihk-sha', request['ihk_sha'], '--manifest', '/inputs.json',
               '--toolchain', '/toolchain.json', '--output', '/work/output',
               '--evidence', '/work/evidence', '--jobs', str(request['jobs']),
               '--timeout', str(request['timeout'])]
    mounts = [('/src', request['source_root'], 'bind', False),
              ('/inputs.json', request['source_manifest'], 'bind', False),
              ('/toolchain.json', request['toolchain_manifest'], 'bind', False),
              ('/driver.py', request['driver_path'], 'bind', False),
              ('/native_rust_exact_build_offline.py', request['provenance_path'], 'bind', False),
              ('/work', str(OUTPUT), 'bind', True)]
    if request.get('gitlink_manifest') is not None:
        mounts += [('/libdwarf-inputs.json', request['gitlink_manifest'], 'bind', False),
                   ('/src/executer/user/lib/libdwarf/libdwarf', request['gitlink_root'], 'bind', False)]
        command += ['--gitlink-manifest', '/libdwarf-inputs.json']
    roots = request['toolchain_roots']
    if (not isinstance(roots, list) or len(roots) != 2 or
            {row['container_path'] for row in roots} != {'/out', '/nightly'}):
        raise Refusal('image-v2-toolchain-mounts')
    mounts += [(row['container_path'], row['host_path'], 'bind', False) for row in roots]
    command += ['--readonly-reuse-inputs','/reuse-inputs.json']
    mounts += current230_contract().readonly_mode().seed_mounts(request)
    return command, sorted(mounts)

def image_owner_receipt_binding(receipt, item, receipt_sha):
    """Positive owner evidence alone never authorizes cleanup."""
    import importlib.util
    path = REPO / 'scripts/native_exact_scratch22_authority1_quarantine_recovery.py'
    spec = importlib.util.spec_from_file_location('image_receipt_mount_core', path)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    if (receipt.get('schema') != 'mckernel.native-exact-mckernel-image-container-receipt.v1' or
            receipt.get('status') not in ('PASS', 'FAIL') or receipt.get('retired') is not True or
            receipt.get('terminal_container_retained') is not True or
            receipt.get('cleanup_separately_required') is not True or
            receipt.get('client_retirement_unproven', False) or
            receipt.get('candidate_sha') != IMAGE_CANDIDATE):
        raise Refusal('image-positive-owner-retirement')
    try:
        if core.inspect_comparison(receipt.get('terminal_container_info')) != core.inspect_comparison(item):
            raise Refusal('image-positive-owner-terminal-inspect')
    except core.Refusal as exc:
        raise Refusal('image-positive-owner-terminal-inspect') from exc


def image_receipt_binding(receipt, guard, target, item, receipt_sha):
    image_owner_receipt_binding(receipt, item, receipt_sha)
    if (canonical(receipt.get('exit_code')) != canonical(target['exit_code']) or
            (receipt.get('status') == 'PASS' and target['exit_code'] != 0) or
            any(receipt.get(key) != target[key] for key in ('container_id', 'container_name', 'owner_nonce')) or
            canonical(guard) != canonical({'owner_status': receipt['status'], 'owner_receipt_sha256': receipt_sha,
                      'container_id': target['container_id'], 'retired': True,
                      'retained_for_separate_cleanup': True, 'interrupted_signal': None})):
        raise Refusal('image-positive-owner-and-guard-retirement')


def recovery_proof_binding(binding, obs):
    import importlib.util
    path = REPO / 'scripts/native_exact_scratch22_image_retirement_reconcile.py'
    spec = importlib.util.spec_from_file_location('cleanup_image_reconciliation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.validate_proof(binding, obs)
    except module.Refusal as exc:
        raise Refusal('image-reconciliation-proof: ' + str(exc)) from exc

def typed_source_binding(request, obs, selected_map):
    return current230_contract().typed_source_binding(request, obs, selected_map)


def configure(value, execute=False, dead_caller=False):
    """Future release only. No runtime identity is inherited from scratch21."""
    global RELEASE, DEVICE, BOOT_ID, ROOT_LOCK_BINDING, EXPECTED_CONTAINER, EXPECTED_EXIT
    global CONTAINER, CONTAINER_NAME, OWNER_NONCE, OWNER_PID, OWNER_START
    global RECORDS, PROTECTED, DIRS, TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE
    global CANDIDATE, ROOT_TERMINAL, WAITER_PIDS, INHERITED_ROOT_LOCK, OWNERSHIP_CASE
    global DEAD_CALLER_BINDING
    DEAD_CALLER_BINDING = None
    RELEASE = None
    INHERITED_ROOT_LOCK = None
    OWNERSHIP_CASE = None
    if (not isinstance(value, dict) or value.get('schema') != 'fp-save-image.cleanup-release.v1' or
            value.get('status') != 'PASS_EXECUTION_RELEASE' or
            value.get('baseline_source_sha256') != BASELINE_SOURCE_SHA or
            value.get('script_sha256') != digest(read_bounded(Path(__file__).resolve())) or
            value.get('tests_sha256') != digest(read_bounded(
                SELFTEST)) or
            value.get('publisher_contract') != PUBLISHER_CONTRACT):
        raise Refusal('cleanup-not-released')
    for key in ('source_review', 'execution_review'):
        review = value.get(key) or {}
        if (review.get('status') != 'PASS' or not review.get('reviewer') or
                review.get('reviewer') == value.get('author') or not review.get('evidence_sha256')):
            raise Refusal('independent-review-required:' + key)
    if (not value.get('author') or value.get('fetched_source_verified') is not True or
            not value.get('git_commit') or not value.get('git_tree')):
        raise Refusal('source-git-binding-required')
    commit, tree = value['git_commit'], value['git_tree']
    if any(not isinstance(item, str) or len(item) != 40 or
           any(char not in '0123456789abcdef' for char in item) for item in (commit, tree)):
        raise Refusal('source-git-shape')
    if subprocess.check_output(['/usr/bin/git', '-C', str(REPO), 'rev-parse', commit + '^{tree}'],
                               timeout=10).decode().strip() != tree:
        raise Refusal('source-git-tree-binding')
    for relative, expected in ((PUBLISHED_SCRIPT, value['script_sha256']),
                               (PUBLISHED_TESTS, value['tests_sha256'])):
        if digest(subprocess.check_output(['/usr/bin/git', '-C', str(REPO), 'show', commit + ':' + relative],
                                           timeout=10)) != expected:
            raise Refusal('source-git-blob-binding')
    obs = value.get('observation') or {}
    required = {'mount', 'root', 'boot_id', 'root_lock', 'request', 'target', 'container_inspect',
                'retained_exclusions', 'request_lease_absent', 'inventories', 'candidate_root',
                'candidate_commit', 'candidate_tree', 'selected_files', 'backup_root', 'namespace_binding', 'namespace_ancestry', 'client_ledger', 'ownership_case', 'shared_record_already_absent'}
    proof_keys = set(obs) & {'normal_owner_join'}
    if len(proof_keys) != 1:
        raise Refusal('exactly-one-positive-retirement-proof-required')
    proof_key = next(iter(proof_keys))
    required.add(proof_key)
    if set(obs) != required or obs.get('request_lease_absent') is not True:
        raise Refusal('future-runtime-observation-required')
    mount = obs['mount']
    if (mount.get('target') != str(ROOT) or mount.get('uuid') != UUID or
            mount.get('fstype') != 'ext4' or obs['boot_id'] != '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb' or
            not {'rw', 'nodev', 'nosuid'} <= set(mount.get('options', '').split(','))):
        raise Refusal('fresh-mount-binding')
    device = obs['root'].get('device')
    if type(device) is not int or device <= 0 or obs['root'].get('path') != str(ROOT):
        raise Refusal('fresh-root-binding')
    if obs['namespace_binding'] != NAMESPACE_BINDING or obs['namespace_ancestry'] != NAMESPACE_ANCESTRY or namespace_ancestry() != NAMESPACE_ANCESTRY:
        raise Refusal('exact-namespace-binding')
    client_rows = obs['client_ledger']
    if not isinstance(client_rows, list) or not client_rows or any(set(r) != {'pid', 'status_path', 'status_sha256'} or type(r['pid']) is not int or r['pid'] <= 0 for r in client_rows):
        raise Refusal('positive-client-ledger-required')
    guard_capture = EVIDENCE / 'attempt'
    if {r['status_path'] for r in client_rows} != {str(p) for p in guard_capture.glob('command-*/status.json')} or any(Path(r['status_path']).parent.parent != guard_capture for r in client_rows):
        raise Refusal('complete-current-guard-client-ledger-required')
    for row in client_rows:
        status = parse(read_bounded(Path(row['status_path'])))
        if digest(read_bounded(Path(row['status_path']))) != row['status_sha256'] or status.get('pid') != row['pid'] or status.get('state') != 'exited' or type(status.get('exit_code')) is not int or status['exit_code'] < 0 or status.get('client_retirement_unproven'):
            raise Refusal('positive-client-status-required')
    WAITER_PIDS = tuple(r['pid'] for r in client_rows)
    if len(set(WAITER_PIDS)) != len(WAITER_PIDS):
        raise Refusal('duplicate-client-pid')
    target, item = obs['target'], obs['container_inspect']
    keys = {'container_id', 'container_name', 'owner_nonce', 'image_id', 'owner_pid', 'owner_starttime', 'exit_code'}
    if (set(target) != keys or type(target['owner_pid']) is not int or target['owner_pid'] <= 0 or
            not isinstance(target['owner_starttime'], str) or not target['owner_starttime'].isdigit() or
            type(target['exit_code']) is not int or not 0 <= target['exit_code'] <= 255 or
            not isinstance(target['container_id'], str) or len(target['container_id']) != 64 or
            any(char not in '0123456789abcdef' for char in target['container_id']) or
            not target['container_name'] or not target['owner_nonce']):
        raise Refusal('future-owner-binding')
    validate_attempt_binding(target, obs['request'])
    state = item.get('State', {})
    wanted_state = {'Status': 'exited', 'Running': False, 'Paused': False, 'Restarting': False,
                    'OOMKilled': False, 'Dead': False, 'Pid': 0, 'ExitCode': target['exit_code'], 'Error': ''}
    if (any(canonical(state.get(key)) != canonical(wanted) for key, wanted in wanted_state.items()) or
            item.get('Id') != target['container_id'] or item.get('Name') != '/' + target['container_name'] or
            item.get('Image') != target['image_id'] or
            item.get('Config', {}).get('Labels', {}).get('mckernel.owner') != target['owner_nonce']):
        raise Refusal('exact-terminal-container-binding')
    lock = obs['root_lock']
    if (lock.get('path') != str(ROOT_LOCK) or lock.get('uid') != 0 or lock.get('gid') != 0 or
            lock.get('mode') != '0o644' or lock.get('nlink') != 1 or lock.get('size') != 0 or
            lock.get('sha256') != digest(b'') or type(lock.get('device')) is not int or
            type(lock.get('inode')) is not int or (lock['device'], lock['inode']) != (27, 4)):
        raise Refusal('fresh-root-lock-binding')
    if observe_identity(REQUEST) != obs['request']:
        raise Refusal('exact-request-binding')
    request = parse(read_bounded(REQUEST))
    CANDIDATE = image_request_binding(request)
    if request.get('candidate_sha') != obs['candidate_commit'] or request.get('image_id') != target['image_id']:
        raise Refusal('request-candidate-image-binding')
    config, host = item.get('Config', {}), item.get('HostConfig', {})
    profile = {'CpusetCpus': '2-5', 'NanoCpus': 4000000000, 'Memory': 12884901888,
               'MemorySwap': 12884901888, 'PidsLimit': 512, 'NetworkMode': 'none',
               'IpcMode': 'private', 'ReadonlyRootfs': True, 'Privileged': False,
               'CapDrop': ['ALL'], 'Init': True, 'SecurityOpt': ['no-new-privileges'],
               'Tmpfs': {'/tmp': 'rw,nodev,nosuid,size=256m'},
               'RestartPolicy': {'MaximumRetryCount': 0, 'Name': 'no'}, 'AutoRemove': False}
    expected_args, expected_mounts = image_layout(request)
    if (any(canonical(host.get(key)) != canonical(wanted) for key, wanted in profile.items()) or
            config.get('User') != '1000:1000' or config.get('Entrypoint') != ['/usr/bin/python3'] or
            config.get('Cmd') != expected_args or item.get('Args') != expected_args or
            item.get('Path') != '/usr/bin/python3' or config.get('Image') != target['image_id']):
        raise Refusal('reviewed-container-profile')
    if sorted((m.get('Destination'), m.get('Source'), m.get('Type'), m.get('RW'))
              for m in item.get('Mounts', []) if m.get('Type') == 'bind') != expected_mounts:
        raise Refusal('exact-image-mounts')
    extra_mounts = [m for m in item.get('Mounts', []) if m.get('Type') != 'bind']
    if extra_mounts and (len(extra_mounts) != 1 or extra_mounts[0].get('Type') != 'tmpfs' or
                         extra_mounts[0].get('Destination') != '/tmp' or extra_mounts[0].get('RW') is not True):
        raise Refusal('unexpected-image-mount')
    records = obs['retained_exclusions']
    OWNERSHIP_CASE = ownership_case_binding(parse(read_bounded(TERMINAL)), obs, records)
    for row in records:
        if (row.get('device') != (NAMESPACE_BINDING['device'] if Path(row['path']) == ATTEMPT else device) or row.get('uid') != UID or row.get('gid') != GID or
                row.get('mode') != '0o600' or row.get('nlink') != 1 or
                type(row.get('inode')) is not int or row['inode'] <= 0 or
                observe_identity(Path(row['path'])) != row):
            raise Refusal('future-exclusion-binding')
        owner = parse(read_bounded(Path(row['path'])))
        image_record_binding(Path(row['path']), row, owner, request, target, obs['boot_id'])
    selected = obs['selected_files']
    selected_map = {r['path']: r for r in selected}
    if len(selected_map) != len(selected):
        raise Refusal('duplicate-selected-file')
    ROOT_TERMINAL = Path(obs[proof_key]['path'])
    if ROOT_TERMINAL != CURRENT230_CALLER_CAPTURE / 'owner.JOIN.json':
        raise Refusal('current230-normal-owner-join-proof-path')
    joins = {'driver_path': 'driver_sha256', 'provenance_path': 'provenance_sha256',
             'host_owner_path': 'host_owner_sha256', 'source_manifest': 'source_manifest_sha256',
             'toolchain_manifest': 'toolchain_manifest_sha256'}
    if request.get('gitlink_manifest') is not None:
        joins['gitlink_manifest'] = 'gitlink_manifest_sha256'
    needed = {str(REQUEST), str(TERMINAL), str(ROOT_TERMINAL), str(EVIDENCE / 'attempt/container.log'),
              str(OUTPUT / 'evidence/receipt.json')}
    if target['exit_code'] == 0:
        needed.update(str(OUTPUT / relative) for relative in
                      ('output/build/kernel/mckernel.img', 'evidence/artifacts/mckernel.img'))
    needed.update(request[key] for key in joins)
    needed.update(current230_contract().required_runtime_references(request, parse(read_bounded(TERMINAL))))
    needed.update(row['status_path'] for row in client_rows)
    needed.update(str(CURRENT230_CALLER_CAPTURE / name) for name in ('owner.PROCESS.json', 'ACTUAL-OWNER-ENTRY.json',
        'ROOT-NORMAL-CLEANUP-COMPLETION-READY.json', 'owner.stdout', 'owner.stderr'))
    for ref in current230_contract().required_static_references():
        needed.add(ref['path'])
        selected_ref = selected_map.get(ref['path'], {})
        if selected_ref.get('sha256') != ref['sha256'] or selected_ref.get('size') != ref['bytes']:
            raise Refusal('current230-required-static-source-binding:' + ref['path'])
    if not needed <= set(selected_map):
        raise Refusal('complete-receipt-and-source-joins-required')
    for key, hash_key in joins.items():
        if selected_map[request[key]].get('sha256') != request[hash_key]:
            raise Refusal('request-source-hash-binding')
    if selected_map[str(ROOT_TERMINAL)] != obs[proof_key]:
        raise Refusal('exact-image-guard-proof-binding')
    image_owner_receipt_binding(parse(read_bounded(TERMINAL)), item, selected_map[str(TERMINAL)]['sha256'])
    current230_contract().normal_owner_join_binding(parse(read_bounded(TERMINAL)), parse(read_bounded(ROOT_TERMINAL)),
        target, item, selected_map[str(TERMINAL)]['sha256'], request, obs, selected_map)
    if target['exit_code'] == 0 and not any(r.get('sha256') and
                                            str(r['path']).startswith(str(OUTPUT) + '/')
                                            for r in selected):
        raise Refusal('successful-output-artifact-required')
    if set(obs['inventories']) != {str(OUTPUT), str(EVIDENCE)}:
        raise Refusal('complete-inventories-required')
    if obs['candidate_root'].get('path') != str(CANDIDATE):
        raise Refusal('candidate-root-required')
    for key, row in (('source_identity', obs['candidate_root']), ('backup_identity', obs['backup_root'])):
        expected = request[key]
        if any(canonical(expected.get(k)) != canonical(v) for k, v in {
                'path': row['path'], 'dev': row['device'], 'inode': row['inode'],
                'uid': row['uid'], 'gid': row['gid'], 'mode': int(row['mode'], 8),
                'file_type': stat.S_IFDIR}.items()):
            raise Refusal('image-source-or-backup-identity')
    if obs['backup_root']['path'] != request['backup_root']:
        raise Refusal('image-backup-path')
    typed_source_binding(request, obs, selected_map)
    for path in (OUTPUT, EVIDENCE):
        if obs['inventories'][str(path)][0]['path'] != str(path):
            raise Refusal('inventory-root-binding')
    if value.get('transaction_paths') != transaction_paths():
        raise Refusal('transaction-path-binding')
    if dead_caller:
        DEAD_CALLER_BINDING = validate_dead_caller_binding(value)
        inheritance = None
    else:
        if value.get('cleanup_mode') is not None or value.get('dead_caller_new_ofd') is not None:
            raise Refusal('dead-caller-explicit-mode-required')
        inheritance = inherited_root_binding(value)
    RELEASE, DEVICE, BOOT_ID = value, device, obs['boot_id']
    INHERITED_ROOT_LOCK = inheritance
    ROOT_LOCK_BINDING, EXPECTED_CONTAINER, EXPECTED_EXIT = lock, item, target['exit_code']
    CONTAINER, CONTAINER_NAME, OWNER_NONCE = target['container_id'], target['container_name'], target['owner_nonce']
    OWNER_PID, OWNER_START = target['owner_pid'], target['owner_starttime']
    RECORDS = {Path(r['path']): (r['sha256'], r['inode'], r['size']) for r in records}
    PROTECTED = selected
    terminal = selected_map[str(TERMINAL)]
    TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE = terminal['sha256'], terminal['inode'], terminal['size']
    DIRS = {path: (obs['inventories'][str(path)][0]['device'],
                   obs['inventories'][str(path)][0]['inode'],
                   obs['inventories'][str(path)][0]['nlink']) for path in (OUTPUT, EVIDENCE)}
    validate_mount()
    protected_files()

def path_device(path):
    # Only the two frozen parents are supported. Never infer authority from a
    # newly opened object's device or widen this to an arbitrary caller path.
    if path in (ATTEMPT, OUTPUT, EVIDENCE, TERMINAL) or path in archive_paths()[:1]:
        return NAMESPACE_BINDING['device']
    if path in (SHARED, MUTEX, PLAN, JOURNAL, CAPTURE, QUARANTINE) or path in archive_paths()[1:]:
        return DEVICE
    raise Refusal('unmapped-fixed-device')

def archive_paths():
    # renameat2 exchange requires both names on the same filesystem. Each
    # ownership record retains its archive beside its exact original parent.
    return tuple(path.parent / name for path, name in zip(owned_record_paths(), ARCHIVE_NAMES))

def transaction_paths():
    return [str(path) for path in (MUTEX, PLAN, JOURNAL, CAPTURE, QUARANTINE)] + [
        str(path) for path in archive_paths()]

def prepare_release(observation, git_commit, git_tree):
    """Bind only a supplied future runtime observation; always emit an unreleased draft."""
    return {'schema': 'fp-save-image.cleanup-release.v1', 'status': 'NOT_RELEASED',
            'author': '/root/debugreg_pair_terminal_prepare_1920', 'script_sha256': digest(read_bounded(Path(__file__).resolve())),
            'tests_sha256': digest(read_bounded(SELFTEST)),
            'baseline_source_sha256': BASELINE_SOURCE_SHA, 'git_commit': git_commit, 'git_tree': git_tree,
            'fetched_source_verified': False, 'source_review': None, 'execution_review': None,
            'inherited_root_lock': None,
            'publisher_contract': PUBLISHER_CONTRACT, 'observation': observation,
            'transaction_paths': ([str(path) for path in (MUTEX, PLAN, JOURNAL, CAPTURE, QUARANTINE)] +
                [str(ATTEMPT.parent / ARCHIVE_NAMES[0])]) if observation.get('ownership_case') == 'PASS_COMMON_ONLY_SHARED_ABSENT' else transaction_paths()}

def quarantine_wait():
    """Nonreturning hold. Signal deferral starts before transaction acquisition."""
    while True:
        try:
            time.sleep(60)
        except BaseException:
            # Diagnostics, handlers and interrupted waits cannot surrender ownership.
            # SIGKILL is intentionally outside this contract; sentinels survive it.
            pass

def terminal_result(status, plan):
    return {'schema': 'fp-save-image.cleanup-result.v1', 'status': status, 'terminal': True,
            'container_absent': True, 'container_id': CONTAINER, 'filesystem_uuid': UUID,
            'boot_id': BOOT_ID, 'release_sha256': digest(canonical(RELEASE)),
            'plan_sha256': digest(canonical(plan)),
            'plan': observe_identity(PLAN), 'journal': observe_identity(JOURNAL),
            'capture': observe_identity(CAPTURE),
            'archives': [observe_identity(path) for path in archive_paths()],
            'publisher_contract': PUBLISHER_CONTRACT}

def directory(path):
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('noncanonical-directory')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    chain = [identity(os.fstat(fd))]
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
            chain.append(identity(os.fstat(fd)))
        return fd, chain
    except BaseException:
        os.close(fd)
        raise

def exists(fd, name):
    try:
        os.stat(name, dir_fd=fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False

def read_at(fd, name, binding=None, *, expected_device=None):
    expected_device = DEVICE if expected_device is None else expected_device
    if type(expected_device) is not int or expected_device <= 0:
        raise Refusal('unbound-file-device')
    opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        before = os.fstat(opened)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
            before.st_dev != expected_device or before.st_size > LIMIT or
            stat.S_IMODE(before.st_mode) != 0o600 or
            (before.st_uid, before.st_gid) != (UID, GID)):
            raise Refusal('file-shape:' + name)
        data = bytearray()
        while len(data) <= before.st_size:
            chunk = os.read(opened, min(65536, before.st_size + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(opened)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(before, k) != getattr(after, k) for k in fields) or
            len(data) != before.st_size or
            identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != identity(before)):
            raise Refusal('file-raced:' + name)
        if binding is not None and (digest(data), before.st_ino, before.st_size) != binding:
            raise Refusal('file-binding:' + name)
        return bytes(data), before
    finally:
        os.close(opened)

def write_all(fd, data):
    while data:
        count = os.write(fd, data)
        if count <= 0:
            raise Refusal('write-no-progress')
        data = data[count:]

def rename_exchange(fd, source, destination, destination_fd=None):
    destination_fd = fd if destination_fd is None else destination_fd
    """Atomically leave a directory sentinel at the active ownership name."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None:
        raise Refusal('renameat2-unavailable')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(fd, os.fsencode(source), destination_fd, os.fsencode(destination), 2):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))

# Executed only by root's absolute Python, isolated from caller modules/env.
# Every listed stat must read/parse; disappearing processes cause a retryable
# refusal. Two full snapshots and unchanged boot identity authenticate scope.
PROC_CODE = r'''
import json,os,sys
caller=[int(sys.argv[2]),sys.argv[3]]
caller_parent=int(open('/proc/'+str(caller[0])+'/stat','rb').read().rpartition(b') ')[2].split()[1])
heavy={'qemu-system-x86_64','qemu-system-aarch64','qemu-kvm','mcexec','firecracker',
       'rustc','cargo','make','ninja','buildah','gcc','g++','cc','clang','clang++'}
def publisher(exe,argv):
    name=os.path.basename(exe[:-10] if exe.endswith(' (deleted)') else exe)
    if name in heavy or name.startswith('qemu-system-'): return True
    if name in ('docker','podman') and any(a in ('build','run','start') for a in argv[1:]): return True
    for arg in argv:
        base=os.path.basename(arg)
        if (base.startswith(('native_rust_exact_','native-exact-','native_exact_')) and
            base.endswith(('.py','.sh')) and any(term in base for term in ('build','cleanup','recovery','prepare'))): return True
    return False
def snapshot():
    rows=[]; publishers=[]; found=False
    entries=os.listdir('/proc')
    if len(entries)>4096: raise ValueError('process-count')
    for name in entries:
        if not name.isdigit(): continue
        pid=int(name)
        with open('/proc/'+name+'/stat','rb') as f: raw=f.read(65537)
        if len(raw)>65536: raise ValueError('stat-size')
        left,sep,right=raw.rpartition(b') ')
        if not sep or not left.startswith(str(pid).encode()+b' ('): raise ValueError('stat-prefix')
        fields=right.split()
        if len(fields)<50 or fields[0] not in (b'R',b'S',b'D',b'Z',b'T',b't',b'X',b'x',b'K',b'W',b'P',b'I'): raise ValueError('stat-fields')
        for field in fields[1:]:
            digits=field[1:] if field.startswith(b'-') else field
            if not digits or any(c<48 or c>57 for c in digits): raise ValueError('stat-number')
        ppid=int(fields[1]); start=int(fields[19])
        if ppid<0 or start<0: raise ValueError('stat-number')
        with open('/proc/'+name+'/cmdline','rb') as f: command=f.read(65537)
        if len(command)>65536 or (command and not command.endswith(b'\0')): raise ValueError('cmdline-size-or-termination')
        argv=[a.decode('utf-8','strict') for a in command[:-1].split(b'\0')] if command else []
        if len(argv)>256 or any(len(a)>16384 for a in argv): raise ValueError('cmdline-arguments')
        if not argv and fields[0] not in (b'Z',b'X',b'x') and not (int(fields[6]) & 0x200000): raise ValueError('live-cmdline-empty')
        exe=os.readlink('/proc/'+name+'/exe') if argv else ''
        with open('/proc/'+name+'/stat','rb') as f: again=f.read(65537)
        check=again.rpartition(b') ')[2].split()
        if len(check)<50 or check[19]!=fields[19]: raise ValueError('process-raced')
        if pid==caller[0]:
            if str(start)!=caller[1]: raise ValueError('caller-raced')
            found=True
        elif argv and not (pid==caller_parent and os.path.basename(exe)=='sudo') and publisher(exe,argv): publishers.append([pid,str(start),exe])
        rows.append([pid,ppid,str(start)])
    if not found: raise ValueError('caller-missing')
    return sorted(rows),publishers
if os.geteuid()!=0: raise ValueError('not-root')
with open('/proc/sys/kernel/random/boot_id') as f: boot=f.read().strip()
first,pubs1=snapshot(); second,pubs2=snapshot()
with open('/proc/sys/kernel/random/boot_id') as f: after=f.read().strip()
if boot!=after: raise ValueError('boot-raced')
print(json.dumps({'schema':'fp-save-image.proc.v1','uid':os.geteuid(),'boot_id':boot,
                  'challenge':sys.argv[1],'caller':caller,'publishers':pubs1+pubs2,'snapshots':[first,second]}))
'''

def run_privileged(args):
    return root_command(args, LIMIT)

def run_privileged_large(args):
    return root_command(args, PROTECTED_LIMIT)

def root_command(args, limit):
    if os.geteuid() != 0:
        raise Refusal('root-execution-required-use-sudo-A')
    result = subprocess.run(args, env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'},
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=30, check=False)
    if result.returncode or result.stderr or len(result.stdout) > limit:
        raise Refusal('root-command-failed:' + args[0])
    return result.stdout

def validate_process_report(report, challenge, caller):
    if (not isinstance(report, dict) or set(report) != {'schema','uid','boot_id','challenge','caller','publishers','snapshots'} or
        report['schema'] != 'fp-save-image.proc.v1' or type(report['uid']) is not int or report['uid'] != 0 or
        report['boot_id'] != BOOT_ID or report['challenge'] != challenge or report['caller'] != caller or
        not isinstance(report['snapshots'], list) or len(report['snapshots']) != 2):
        raise Refusal('process-report-binding')
    if report['publishers'] != []:
        raise Refusal('concurrent-build-or-cleanup-publisher')
    combined = {}
    for snapshot in report['snapshots']:
        if not isinstance(snapshot, list) or not snapshot:
            raise Refusal('process-snapshot-shape')
        seen = set()
        for row in snapshot:
            if (not isinstance(row, list) or len(row) != 3 or type(row[0]) is not int or row[0] <= 0 or
                type(row[1]) is not int or row[1] < 0 or not isinstance(row[2], str) or
                not row[2].isdigit() or row[0] in seen):
                raise Refusal('process-row-shape')
            seen.add(row[0])
            if row[0] == caller[0] and row[2] != caller[1]:
                raise Refusal('process-caller-binding')
            combined.setdefault(row[0], set()).add(row[1])
        if 1 not in seen or caller[0] not in seen:
            raise Refusal('process-snapshot-incomplete')
    related = {OWNER_PID, *WAITER_PIDS}
    while True:
        expanded = related | {pid for pid, parents in combined.items() if parents & related}
        if expanded == related:
            break
        related = expanded
    if related & set(combined):
        # PID reuse is also refused, including a changed owner starttime.
        raise Refusal('owner-waiter-or-descendant-present')

def process_absent():
    challenge = os.urandom(24).hex()
    raw_stat = Path('/proc/self/stat').read_bytes()
    caller = [os.getpid(), raw_stat.rpartition(b') ')[2].split()[19].decode('ascii')]
    raw = run_privileged(['/usr/bin/python3', '-I', '-B', '-c', PROC_CODE, challenge, str(caller[0]), caller[1]])
    validate_process_report(parse(raw), challenge, caller)

def docker(args):
    return run_privileged(['/usr/bin/docker', '--host=unix:///var/run/docker.sock', *args])

def census():
    dead_caller_absent()
    process_absent()
    raw = docker(['ps', '-a', '--no-trunc', '--format', '{{json .}}'])
    candidates = []
    seen = set()
    for line in raw.splitlines():
        item = parse(line)
        if (not isinstance(item, dict) or not isinstance(item.get('ID'), str) or len(item['ID']) != 64 or
            any(c not in '0123456789abcdef' for c in item['ID']) or
            not isinstance(item.get('Names'), str) or not isinstance(item.get('Labels'), str) or
            item.get('State') not in ('created','restarting','running','removing','paused','exited','dead') or item['ID'] in seen):
            raise Refusal('container-inventory-shape')
        if item['State'] in ('running','restarting','paused','removing'):
            raise Refusal('concurrent-active-container')
        seen.add(item['ID'])
        labels = item['Labels'].split(',')
        if item['ID'] == CONTAINER or item['Names'] == CONTAINER_NAME or 'mckernel.owner='+OWNER_NONCE in labels:
            candidates.append(item)
    if not candidates:
        return False
    if len(candidates) != 1 or candidates[0]['ID'] != CONTAINER or candidates[0]['Names'] != CONTAINER_NAME:
        raise Refusal('container-inventory-binding')
    data = parse(docker(['inspect', '--type', 'container', CONTAINER]))
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise Refusal('container-inspect-shape')
    item = data[0]
    state = item.get('State')
    config = item.get('Config')
    if (not isinstance(state, dict) or not isinstance(config, dict) or
        item.get('Id') != CONTAINER or item.get('Name') != '/' + CONTAINER_NAME or
        not isinstance(config.get('Labels'), dict) or config['Labels'].get('mckernel.owner') != OWNER_NONCE or
        state.get('Status') != 'exited' or type(state.get('ExitCode')) is not int or state['ExitCode'] != EXPECTED_EXIT or
        state.get('Running') is not False or state.get('Pid') != 0):
        raise Refusal('container-retirement-binding')
    validate_container_profile(item)
    return True

class Transaction:
    def __init__(self):
        self.fd = self.mfd = self.rfd = self.nfd = None
        self.mutation_started = False
        self.root_locked = False
        self.root_lock_inherited = False
        if RELEASE is None:
            raise Refusal('release-not-configured')
        if INHERITED_ROOT_LOCK is None:
            if DEAD_CALLER_BINDING is not None:
                dead_caller_absent()
            self.rfd = os.open(ROOT_LOCK, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        else:
            self.rfd = duplicate_inherited_root_lock()
            self.root_lock_inherited = True
        try:
            if observe_identity(ROOT_LOCK) != ROOT_LOCK_BINDING:
                raise Refusal('root-lock-binding')
            if self.root_lock_inherited:
                validate_transaction_inherited_lock(self.rfd)
            else:
                fcntl.flock(self.rfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                if DEAD_CALLER_BINDING is not None:
                    dead_caller_absent()
            self.root_locked = True
            if identity(os.fstat(self.rfd)) != (ROOT_LOCK_BINDING['device'], ROOT_LOCK_BINDING['inode']):
                raise Refusal('root-lock-replaced')
            self.fd, self.chain = directory(ROOT)
            self.nfd, self.namespace_chain = directory(NAMESPACE)
            self.pinned()
        except BaseException:
            self.close()
            raise
        if os.fstat(self.fd).st_dev != DEVICE:
            self.close()
            raise Refusal('scratch-device')
        for path in (ATTEMPT, SHARED, MUTEX, PLAN, JOURNAL, CAPTURE, OUTPUT, EVIDENCE):
            wanted_parent = NAMESPACE if path in (ATTEMPT, OUTPUT, EVIDENCE) else ROOT
            if path.parent != wanted_parent:
                self.close()
                raise Refusal('fixed-path-parent')

    def parent_fd(self, path):
        if path in (ATTEMPT, OUTPUT, EVIDENCE) and path.parent == NAMESPACE:
            return self.nfd
        if path in (SHARED, MUTEX, PLAN, JOURNAL, CAPTURE, QUARANTINE) and path.parent == ROOT:
            return self.fd
        raise Refusal('unmapped-fixed-path')

    def close(self):
        for name in ('mfd', 'nfd', 'fd', 'rfd'):
            fd = getattr(self, name, None)
            if fd is not None:
                os.close(fd)
                setattr(self, name, None)
        self.root_locked = False

    def pinned(self):
        dead_caller_absent()
        require_unowned_shared_absent()
        if self.root_lock_inherited:
            validate_transaction_inherited_lock(self.rfd)
        validate_mount()
        if (observe_identity(ROOT_LOCK) != ROOT_LOCK_BINDING or
                identity(os.fstat(self.rfd)) != (ROOT_LOCK_BINDING['device'], ROOT_LOCK_BINDING['inode'])):
            raise Refusal('root-lock-replaced')
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != BOOT_ID:
            raise Refusal('boot-drift')
        fd, chain = directory(ROOT)
        os.close(fd)
        if chain != self.chain:
            raise Refusal('ancestor-replaced')
        nfd, nchain = directory(NAMESPACE)
        try:
            meta = os.fstat(nfd)
            actual = dict(device=meta.st_dev, inode=meta.st_ino, mode=meta.st_mode, uid=meta.st_uid, gid=meta.st_gid)
            if (actual != NAMESPACE_BINDING or namespace_ancestry() != NAMESPACE_ANCESTRY or nchain != self.namespace_chain or
                    identity(os.fstat(self.nfd)) != identity(meta) or meta.st_dev != NAMESPACE_BINDING['device']):
                raise Refusal('namespace-parent-replaced')
        finally:
            os.close(nfd)
        if self.mfd is not None and identity(os.stat(MUTEX.name, dir_fd=self.fd, follow_symlinks=False)) != identity(os.fstat(self.mfd)):
            raise Refusal('mutex-replaced')

    def preserved(self):
        self.pinned()
        for path, (device, inode, nlink) in DIRS.items():
            fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.parent_fd(path))
            try:
                meta = os.fstat(fd)
                if (identity(meta) != (path_device(path), inode) or device != path_device(path) or meta.st_nlink != nlink or
                    stat.S_IMODE(meta.st_mode) != 0o700 or (meta.st_uid, meta.st_gid) != (UID, GID)):
                    raise Refusal('preserved-directory-binding')
                if path == EVIDENCE:
                    read_at(fd, TERMINAL.name, (TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE), expected_device=path_device(TERMINAL))
                if identity(os.stat(path.name, dir_fd=self.parent_fd(path), follow_symlinks=False)) != identity(meta):
                    raise Refusal('preserved-directory-raced')
            finally:
                os.close(fd)

    def lock(self, execute):
        self.pinned()
        if not exists(self.fd, MUTEX.name):
            if not execute:
                return
            try:
                self.mfd = os.open(MUTEX.name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
                self.mutation_started = True
                os.fchown(self.mfd, UID, GID)
            except FileExistsError:
                pass
        if self.mfd is None:
            self.mfd = os.open(MUTEX.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        meta = os.fstat(self.mfd)
        if (not stat.S_ISREG(meta.st_mode) or identity(meta)[0] != DEVICE or meta.st_size != 0 or
            meta.st_nlink != 1 or stat.S_IMODE(meta.st_mode) != 0o600 or (meta.st_uid, meta.st_gid) != (UID, GID)):
            raise Refusal('mutex-binding')
        try:
            fcntl.flock(self.mfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refusal('cleanup-busy') from exc
        self.pinned()
        if execute:
            os.fsync(self.mfd)
            os.fsync(self.fd)

    def expected_plan(self, sentinels):
        return {'schema': 'fp-save-image.terminal-cleanup.v1', 'root': str(ROOT),
                'release_sha256': digest(canonical(RELEASE)),
                'filesystem_uuid': UUID, 'root_lock': ROOT_LOCK_BINDING,
                'ancestry': [list(x) for x in self.chain], 'device': DEVICE,
                'mutex': list(identity(os.fstat(self.mfd))) if self.mfd is not None else None,
                'journal_identity': list(identity(os.stat(JOURNAL.name, dir_fd=self.fd, follow_symlinks=False)))
                    if exists(self.fd, JOURNAL.name) else None,
                'owner': [BOOT_ID, OWNER_PID, OWNER_START], 'waiters': list(WAITER_PIDS),
                'container': [CONTAINER, CONTAINER_NAME, OWNER_NONCE],
                'namespace': {'path': str(NAMESPACE), 'binding': NAMESPACE_BINDING, 'ancestry': NAMESPACE_ANCESTRY, 'chain': [list(x) for x in self.namespace_chain]},
                'records': [[str(p), str(p.parent), archive, *RECORDS[p]]
                            for p, archive in zip(owned_record_paths(), ARCHIVE_NAMES)],
                'sentinels': sentinels,
                'publisher_contract': PUBLISHER_CONTRACT,
                'directories': [[p.name, *DIRS[p]] for p in (OUTPUT, EVIDENCE)],
                'terminal': [TERMINAL.name, TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE]}

    def pristine(self):
        self.preserved()
        if exists(self.fd, JOURNAL.name):
            raise Refusal('journal-without-plan')
        for path, archive in zip(owned_record_paths(), ARCHIVE_NAMES):
            read_at(self.parent_fd(path), path.name, RECORDS[path], expected_device=path_device(path))
            if exists(self.parent_fd(path), archive):
                # A crash during preparation has not touched any active record.
                # Retain unbound preparation, rather than adopt a foreign dir.
                raise Refusal('unbound-sentinel-preparation')

    def sentinel(self, name, expected, parent_fd=None):
        parent_fd = self.fd if parent_fd is None else parent_fd
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            meta = os.fstat(fd)
            if (meta.st_dev != expected[0] or os.fstat(parent_fd).st_dev != expected[0] or list(identity(meta)) != expected or meta.st_nlink != 2 or
                stat.S_IMODE(meta.st_mode) != 0o700 or (meta.st_uid, meta.st_gid) != (UID, GID) or
                os.listdir(fd)):
                raise Refusal('sentinel-binding')
            if identity(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)) != identity(meta):
                raise Refusal('sentinel-raced')
        finally:
            os.close(fd)

    def load_plan(self):
        raw, _ = read_at(self.fd, PLAN.name)
        value = parse(raw)
        sentinels = value.get('sentinels') if isinstance(value, dict) else None
        if (not isinstance(sentinels, list) or len(sentinels) != len(owned_record_paths()) or
            any(not isinstance(row, list) or len(row) != 2 or
                type(row[0]) is not int or row[0] != path_device(path) or
                type(row[1]) is not int or row[1] <= 0 for row, path in zip(sentinels, owned_record_paths())) or
            len({tuple(row) for row in sentinels}) != len(owned_record_paths())):
            raise Refusal('plan-sentinel-binding')
        plan = self.expected_plan(sentinels)
        if raw != canonical(plan) + b'\n':
            raise Refusal('plan-binding')
        return plan

    def prepare(self):
        self.pristine()
        sentinels = []
        for path, archive in zip(owned_record_paths(), ARCHIVE_NAMES):
            self.pinned()
            parent = self.parent_fd(path)
            os.mkdir(archive, 0o700, dir_fd=parent)
            self.mutation_started = True
            fd = os.open(archive, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            try:
                os.fchown(fd, UID, GID)
                expected = list(identity(os.fstat(fd)))
                self.sentinel(archive, expected, parent)
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(parent)
            sentinels.append(expected)
        self.create(JOURNAL.name, b'')
        plan = self.expected_plan(sentinels)
        self.create(PLAN.name, canonical(plan) + b'\n')
        return plan

    def create(self, name, data):
        self.pinned()
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        self.mutation_started = True
        try:
            os.fchown(fd, UID, GID)
            write_all(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.fd)

    def state(self, plan):
        self.preserved()
        if exists(self.fd, PLAN.name):
            raw, _ = read_at(self.fd, PLAN.name)
            if raw != canonical(plan) + b'\n':
                raise Refusal('plan-binding')
        else:
            raise Refusal('missing-plan')
        rows = []
        if exists(self.fd, JOURNAL.name):
            raw, _ = read_at(self.fd, JOURNAL.name)
            if raw and not raw.endswith(b'\n'):
                raise Refusal('torn-journal')
            rows = [parse(line) for line in raw.splitlines()]
        legal = [(event, index) for index in range(len(owned_record_paths()))
                 for event in ('before_exchange', 'after_exchange', 'release', 'after_release')] + [('complete', len(owned_record_paths()))]
        if len(rows) > len(legal):
            raise Refusal('journal-after-complete')
        previous = digest(canonical(plan))
        for seq, row in enumerate(rows):
            event, index = legal[seq]
            body = {'event': event, 'index': index, 'sequence': seq,
                    'plan_sha256': digest(canonical(plan)), 'previous': previous,
                    'plan_identity': list(identity(os.stat(PLAN.name, dir_fd=self.fd, follow_symlinks=False)))}
            wanted = dict(body, hash=digest(canonical(body)))
            if canonical(row) != canonical(wanted) or canonical(row) + b'\n' != raw.splitlines(keepends=True)[seq]:
                raise Refusal('journal-prefix-binding')
            previous = wanted['hash']
        paths = owned_record_paths()
        actual = []
        for index, path in enumerate(paths):
            phase = min(max(len(rows) - 4 * index, 0), 4)
            archive = ARCHIVE_NAMES[index]
            sentinel = plan['sentinels'][index]
            archived_meta = os.stat(archive, dir_fd=self.parent_fd(path), follow_symlinks=False)
            if stat.S_ISDIR(archived_meta.st_mode):
                if phase not in (0, 1):
                    raise Refusal('exchange-state-regression')
                self.sentinel(archive, sentinel, self.parent_fd(path))
                read_at(self.parent_fd(path), path.name, RECORDS[path], expected_device=path_device(path))
                actual.append('before_exchange')
                continue
            read_at(self.parent_fd(path), archive, RECORDS[path], expected_device=path_device(path))
            if phase == 0:
                raise Refusal('unplanned-exchange')
            if exists(self.parent_fd(path), path.name):
                active_meta = os.stat(path.name, dir_fd=self.parent_fd(path), follow_symlinks=False)
                if stat.S_ISDIR(active_meta.st_mode):
                    if phase == 4:
                        raise Refusal('sentinel-reappeared-after-release')
                    self.sentinel(path.name, sentinel, self.parent_fd(path))
                    actual.append('after_exchange')
                    continue
                # A fresh ordinary owner may acquire the name after release.
                # Validate its shape only; never remove or claim its ownership.
                read_at(self.parent_fd(path), path.name, expected_device=path_device(path))
            if phase < 3:
                raise Refusal('unauthorized-sentinel-release')
            actual.append('after_release')
        return rows, actual

    def append(self, plan, rows, event, index):
        self.pinned()
        raw, before = read_at(self.fd, JOURNAL.name)
        if raw != b''.join(canonical(row) + b'\n' for row in rows):
            raise Refusal('journal-raced')
        body = {'event': event, 'index': index, 'sequence': len(rows),
                'plan_sha256': digest(canonical(plan)),
                'plan_identity': list(identity(os.stat(PLAN.name, dir_fd=self.fd, follow_symlinks=False))),
                'previous': rows[-1]['hash'] if rows else digest(canonical(plan))}
        row = dict(body, hash=digest(canonical(body)))
        fd = os.open(JOURNAL.name, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=self.fd)
        try:
            if identity(os.fstat(fd)) != identity(before):
                raise Refusal('journal-replaced')
            write_all(fd, canonical(row) + b'\n')
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.fd)
        rows.append(row)

    def run(self, execute):
        if os.path.lexists(QUARANTINE):
            raise Refusal('quarantined-independent-reconciliation-required')
        self.lock(execute)
        protected_files()
        if execute and exists(self.fd, PLAN.name):
            self.mutation_started = True  # Reconciliation owns a prior transaction.
        plan = self.load_plan() if exists(self.fd, PLAN.name) else None
        if plan is None:
            if execute and (exists(self.fd, JOURNAL.name) or any(
                    exists(self.parent_fd(path), name) for path, name in zip(owned_record_paths(), ARCHIVE_NAMES))):
                self.mutation_started = True  # Prior unbound mutation is uncertain.
            self.pristine()
            rows, actual = [], []
        else:
            rows, actual = self.state(plan)
        present = census()
        if not present and plan is None:
            raise Refusal('container-absent-before-plan')
        capture_logs(present, execute, transaction=self)
        self.pinned()
        if len(rows) == 4 * len(owned_record_paths()) + 1:
            if present:
                raise Refusal('terminal-container-reappeared')
            return terminal_result('PASS_TERMINAL_REPLAY', plan)
        if not execute:
            return {'status': 'PASS_VALIDATE_ONLY', 'terminal': False, 'events': len(rows),
                    'container_present': present, 'publisher_contract': PUBLISHER_CONTRACT}
        if plan is None:
            plan = self.prepare()
        if not exists(self.fd, JOURNAL.name):
            self.create(JOURNAL.name, b'')
        if present:
            # Require the same exited identity immediately before removal.
            protected_files()
            capture_logs(True, execute=True, transaction=self)
            if not census():
                raise Refusal('container-disappeared-before-rm')
            self.pinned()
            self.mutation_started = True
            removed = docker(['rm', '--', CONTAINER]).strip()
            if removed not in (CONTAINER.encode(), CONTAINER_NAME.encode()):
                raise Refusal('container-remove-response')
        if census():
            raise Refusal('container-still-present')
        self.pinned()
        for index, path in enumerate(owned_record_paths()):
            protected_files()
            rows, actual = self.state(plan)
            if len(rows) >= 4 * index + 4:
                continue
            if census():
                raise Refusal('container-reappeared')
            self.preserved()
            if len(rows) == 4 * index:
                self.append(plan, rows, 'before_exchange', index)
            rows, actual = self.state(plan)
            if actual[index] == 'before_exchange':
                read_at(self.parent_fd(path), path.name, RECORDS[path], expected_device=path_device(path))
                self.sentinel(ARCHIVE_NAMES[index], plan['sentinels'][index], self.parent_fd(path))
                self.pinned()
                # Atomic exchange never vacates the active ownership pathname.
                # A foreign capture fails validation while its sentinel stays
                # active; neither object is deleted or speculatively rolled back.
                rename_exchange(self.parent_fd(path), path.name, ARCHIVE_NAMES[index])
                os.fsync(self.parent_fd(path))
                os.fsync(self.fd)
            os.fsync(self.fd)
            rows, actual = self.state(plan)
            if len(rows) == 4 * index + 1:
                self.append(plan, rows, 'after_exchange', index)
            if len(rows) == 4 * index + 2:
                self.append(plan, rows, 'release', index)
            rows, actual = self.state(plan)
            if actual[index] == 'after_exchange':
                if census():
                    raise Refusal('container-reappeared-before-release')
                protected_files()
                self.sentinel(path.name, plan['sentinels'][index], self.parent_fd(path))
                self.pinned()
                # This is the intended release point. A raced-in regular file
                # causes ENOTDIR and remains intact; replay preserves that owner.
                os.rmdir(path.name, dir_fd=self.parent_fd(path))
                os.fsync(self.parent_fd(path))
            os.fsync(self.fd)
            rows, actual = self.state(plan)
            self.append(plan, rows, 'after_release', index)
        rows, actual = self.state(plan)
        protected_files()
        if census():
            raise Refusal('container-reappeared')
        self.preserved()
        self.append(plan, rows, 'complete', len(owned_record_paths()))
        self.state(plan)
        return terminal_result('PASS_EXECUTED', plan)

def recover(execute=False):
    # Defer ordinary termination before acquiring any cleanup lock or mutating.
    # Successful/preflight paths restore delivery only after all held locks close.
    # Uncertain mutation never reaches restoration: quarantine holds indefinitely.
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, DEFERRED_SIGNALS) if execute else None
    tx = None
    try:
        tx = Transaction()
        return tx.run(execute)
    except BaseException as error:
        # The preserved root lock remains held while durable quarantine is written.
        # No ownership name is ever unlinked or restored speculatively.
        if execute and tx is not None and tx.fd is not None and tx.root_locked and tx.mutation_started:
            try:
                tx.create(QUARANTINE.name, canonical({
                    'schema': 'fp-save-image.cleanup-quarantine.v1',
                    'release_sha256': digest(canonical(RELEASE)),
                    'error_type': type(error).__name__,
                    'requires': 'independent-exact-state-reconciliation'}) + b'\n')
            except BaseException:
                pass
            try:
                print(json.dumps({'status': 'QUARANTINED_ROOT_LOCK_HELD',
                                  'error_type': type(error).__name__,
                                  'requires': 'independent-exact-state-reconciliation',
                                  'dead_caller_observations': DEAD_CALLER_OBSERVATIONS}), flush=True)
            except BaseException:
                pass
            quarantine_wait()
        raise
    finally:
        if tx is not None:
            tx.close()
        if previous_mask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)

def main(argv=None):
    # configure() requires exact independent source/execution releases before effects.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path)
    parser.add_argument('--release-sha256')
    parser.add_argument('--prepare-observation', type=Path)
    parser.add_argument('--observation-sha256')
    parser.add_argument('--git-commit')
    parser.add_argument('--git-tree')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--inherited-root-lock-stdin', action='store_true')
    parser.add_argument('--exact-dead-caller-new-ofd', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.prepare_observation:
            if args.execute or args.release or not args.git_commit or not args.git_tree:
                raise Refusal('prepare-arguments')
            raw = read_bounded(args.prepare_observation)
            if digest(raw) != args.observation_sha256:
                raise Refusal('observation-file-digest')
            if args.exact_dead_caller_new_ofd and args.inherited_root_lock_stdin:
                raise Refusal('dead-caller-and-same-ofd-mutually-exclusive')
            draft = prepare_release(parse(raw), args.git_commit, args.git_tree)
            if args.exact_dead_caller_new_ofd:
                draft.update(cleanup_mode=DEAD_CALLER_MODE, dead_caller_new_ofd=DEAD_CALLER_FROZEN)
            print(json.dumps(draft, sort_keys=True))
            return 0
        if not args.release or not args.release_sha256:
            raise Refusal('exact-release-required')
        raw = read_bounded(args.release)
        if digest(raw) != args.release_sha256:
            raise Refusal('release-file-digest')
        if args.exact_dead_caller_new_ofd and args.inherited_root_lock_stdin:
            raise Refusal('dead-caller-and-same-ofd-mutually-exclusive')
        if not args.exact_dead_caller_new_ofd and not args.inherited_root_lock_stdin:
            raise Refusal('current230-requires-same-ofd-stdin-transport')
        configure(parse(raw), execute=args.execute, dead_caller=args.exact_dead_caller_new_ofd)
        if os.geteuid() != 0:
            raise Refusal('root-execution-required-use-sudo-A')
        result = recover(args.execute)
    except (Refusal, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc),
                          'dead_caller_observations': DEAD_CALLER_OBSERVATIONS}, sort_keys=True))
        return 1
    if DEAD_CALLER_BINDING is not None:
        result['dead_caller_observations'] = DEAD_CALLER_OBSERVATIONS
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())





