#!/usr/bin/env python3
"""Bounded, candidate-bound tool-image execution packet.

Validation is deliberately side-effect free.  Execution is gated by an
independent release record and then delegates exactly once to the reviewed
source-free producer.  This packet itself never invokes Docker during
``--validate-only`` and does not mount or copy source files.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

CANDIDATE = '50b084322610a9326b1b7b528edd4cd73b635632'
ROOT = Path('/home/holden/mckernel')
PRODUCER = ROOT / 'scripts/native_rust_exact_build_image_prepare.py'
OWNER = ROOT / 'scripts/native_rust_exact_build_container_owner.py'
LOCK = ROOT / 'host-kernel/rocky/toolchain-lock.json'
PRODUCER_SHA256 = '7ffa3a75a4d45f350803282eeeabce2d608377a4ccd4536bab2c4080412118ad'
OWNER_SHA256 = 'a8c4c9fc61fab312e3a6e48e93b417453ec12e6543d6adbb7038933f92e79155'
LOCK_SHA256 = 'fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802'
OUTPUT = Path('/home/holden/mckernel-exact-image-50b08432-scratch17-toolimage-1')
EVIDENCE = Path('/home/holden/mckernel-exact-image-evidence-50b08432-scratch17-toolimage-1')
LEASE = Path('/home/holden/mckernel-work/scratch/native-exact-image-preparation-lease-50b08432-scratch17-toolimage-1.json')
RELEASE_STATUS = 'PASS_EXECUTION_SCRATCH17_TOOLIMAGE_1'

COMMAND = (
    '/usr/bin/python3', '-B', str(PRODUCER), '--candidate-sha', CANDIDATE,
    '--output-root', str(OUTPUT), '--evidence-root', str(EVIDENCE),
    '--lease-path', str(LEASE), '--toolchain-lock', str(LOCK),
)


class PacketError(RuntimeError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _fresh(path):
    if not path.is_absolute() or '..' in path.parts:
        raise PacketError('non-canonical packet path: ' + str(path))
    if path.exists() or path.is_symlink():
        raise PacketError('target is not fresh: ' + str(path))


def validate():
    if len(CANDIDATE) != 40 or any(c not in '0123456789abcdef' for c in CANDIDATE):
        raise PacketError('candidate identity is not a lowercase git SHA')
    for path, expected, label in ((PRODUCER, PRODUCER_SHA256, 'producer'),
                                  (OWNER, OWNER_SHA256, 'owner'),
                                  (LOCK, LOCK_SHA256, 'toolchain lock')):
        if not path.is_file() or path.is_symlink():
            raise PacketError(label + ' is absent or symlinked')
        if sha256(path) != expected:
            raise PacketError(label + ' hash differs from reviewed bytes')
    for path in (OUTPUT, EVIDENCE, LEASE):
        _fresh(path)
    if OUTPUT == EVIDENCE or OUTPUT in EVIDENCE.parents or EVIDENCE in OUTPUT.parents:
        raise PacketError('output/evidence roots overlap')
    if not Path('/home/holden').is_dir() or not Path('/home/holden/mckernel-work/scratch').is_dir():
        raise PacketError('reviewed host/scratch roots are absent')
    return {
        'status': 'PASS_VALIDATE_ONLY',
        'candidate_sha': CANDIDATE,
        'producer_sha256': PRODUCER_SHA256,
        'owner_sha256': OWNER_SHA256,
        'toolchain_lock_sha256': LOCK_SHA256,
        'command': list(COMMAND),
        'fresh_paths': {'output': str(OUTPUT), 'evidence': str(EVIDENCE), 'lease': str(LEASE)},
        'limits': {
            'cpus': '2-5', 'cpu_count': 4, 'memory_bytes': 12 * 2**30,
            'swap_expansion': False, 'pids': 512,
            'preparation_network': 'bridge', 'offline_network': 'none',
            'offline_read_only': True, 'offline_user': 'caller uid/gid',
            'offline_capabilities': 'drop ALL', 'source_mounts': False,
        },
        'execution_requires': RELEASE_STATUS,
    }


def _release(path):
    try:
        release = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise PacketError('cannot read independent release record: ' + str(exc))
    if (release.get('status') != RELEASE_STATUS or
            release.get('candidate_sha') != CANDIDATE or
            release.get('packet_sha256') != sha256(Path(__file__))):
        raise PacketError('independent release does not bind this packet/candidate')


def main(argv=None):
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--validate-only', action='store_true')
    mode.add_argument('--execute', action='store_true')
    parser.add_argument('--release', type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate()
        if args.validate_only:
            if args.release is not None:
                raise PacketError('--release is only valid with --execute')
            print(json.dumps(report, sort_keys=True))
            return 0
        if args.release is None:
            raise PacketError('--execute requires an independent release record')
        _release(args.release)
        # The reviewed producer owns Docker, the lease, both profiles, and all
        # cleanup.  This call is intentionally unreachable without release.
        return subprocess.call(list(COMMAND))
    except PacketError as exc:
        print('FAIL_CLOSED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
