#!/usr/bin/env python3
"""Read-only scratch21 cleanup review inputs. No removal/release code exists here.

--live additionally uses sudo for Docker inspect/logs and the process/lock census.
JSON output is a fresh observation, never an execution release or cleanup receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('/home/holden/mckernel-work/scratch')
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
CHECKPOINT = REPO / 'docs/verification/evidence/native-exact-scratch21-build-failure-checkpoint-20261001.json'
EVIDENCE = ROOT / 'mckernel-exact-candidate-scratch-21-evidence'
PROC_CODE = r'''
import json,os
heavy={'qemu-system-x86_64','qemu-system-aarch64','qemu-kvm','mcexec',
       'rustc','cargo','make','ninja','buildah','gcc','g++','cc','clang','clang++'}
rows=[]
for name in os.listdir('/proc'):
    if not name.isdigit(): continue
    try:
        raw=open('/proc/'+name+'/stat','rb').read()
        fields=raw.rpartition(b') ')[2].split()
        argv=open('/proc/'+name+'/cmdline','rb').read().split(b'\0')
        base=os.path.basename(argv[0].decode(errors='strict')) if argv[0] else ''
        is_heavy=base in heavy or base.startswith('qemu-system-')
        is_owner=any(os.path.basename(a.decode(errors='strict')).startswith(
            ('native_rust_exact_','native-exact-','native_diagnostic_')) for a in argv if a)
        if is_heavy or is_owner: rows.append({'pid':int(name),'starttime':fields[19].decode(),'program':base})
    except FileNotFoundError: raise RuntimeError('process census raced; refresh before release')
print(json.dumps({'uid':os.geteuid(),'publishers':rows,
 'locks':open('/proc/locks').read(),'boot_id':open('/proc/sys/kernel/random/boot_id').read().strip()}))
'''


def identity(path, content=True):
    if path.resolve() != path:
        raise ValueError('Symlink/alias in retained path: ' + str(path))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not (stat.S_ISREG(before.st_mode) or stat.S_ISDIR(before.st_mode)):
            raise ValueError('Unexpected retained file type: ' + str(path))
        row = {'path': str(path), 'device': before.st_dev, 'inode': before.st_ino,
               'mode': oct(stat.S_IMODE(before.st_mode)), 'uid': before.st_uid,
               'gid': before.st_gid, 'size': before.st_size, 'nlink': before.st_nlink}
        if content and stat.S_ISREG(before.st_mode):
            if before.st_size > 32 * 1024 * 1024:
                raise ValueError('Observation file exceeds bound: ' + str(path))
            digest = hashlib.sha256()
            while True:
                raw = os.read(fd, 1024 * 1024)
                if not raw:
                    break
                digest.update(raw)
            row['sha256'] = digest.hexdigest()
        after = os.fstat(fd)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_nlink')
        if any(getattr(before, k) != getattr(after, k) for k in keys):
            raise ValueError('Retained identity changed during read: ' + str(path))
        return row
    finally:
        os.close(fd)


def privileged(argv):
    env = dict(os.environ,
               SUDO_ASKPASS=str(REPO / 'scripts/os_goal_sudo_askpass.py'),
               MCKERNEL_OS_SUDO_CREDENTIAL=str(Path.home() / '.local/state/mckernel-os-goal/sudo-password'))
    result = subprocess.run(['/usr/bin/sudo', '-A', '--', *argv], env=env,
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=30, check=True)
    if len(result.stdout) > 4 * 1024 * 1024:
        raise ValueError('Privileged observation exceeds output bound')
    return result.stdout


def validate_container(item, target):
    state = item['State']
    expected = {'Status': 'exited', 'Running': False, 'Paused': False,
                'Restarting': False, 'OOMKilled': False, 'Dead': False, 'Pid': 0, 'ExitCode': 1}
    if (item['Id'] != target['container_id'] or item['Name'] != '/' + target['container_name'] or
            item['Image'] != target['image_id'] or
            item['Config']['Labels'].get('mckernel.owner') != target['owner_nonce'] or
            any(type(state.get(k)) != type(v) or state.get(k) != v for k, v in expected.items())):
        raise ValueError('Exact terminal container identity/state changed')


def inspect(live=False):
    checkpoint = json.loads(CHECKPOINT.read_text())
    target = checkpoint['terminal_owner']
    mount = json.loads(subprocess.check_output(
        ['findmnt', '-J', '-T', str(ROOT), '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],
        timeout=10))['filesystems']
    if (len(mount) != 1 or mount[0]['target'] != str(ROOT) or mount[0]['uuid'] != UUID or
            mount[0]['fstype'] != 'ext4' or
            not {'rw', 'nodev', 'nosuid'} <= set(mount[0]['options'].split(','))):
        raise ValueError('Scratch mount identity changed')
    root = identity(ROOT, False)
    records = []
    for old in checkpoint['retained_exclusions']:
        row = identity(Path(old['path']))
        for key in ('inode', 'uid', 'gid', 'size', 'sha256'):
            if row[key] != old[key]:
                raise ValueError('Retained exclusion changed: ' + key)
        if row['device'] != root['device'] or row['mode'] != '0o600' or row['nlink'] != 1:
            raise ValueError('Retained exclusion metadata changed')
        row['historical_device'] = old['device']
        records.append(row)
    lease = ROOT / 'native-exact-build-lease-scratch-21.json'
    if os.path.lexists(lease):
        raise ValueError('Scratch21 request lease unexpectedly exists')
    files = [ROOT / 'native-exact-build-request-scratch-21.execution.json',
             ROOT / 'native-exact-scratch21-heavy-build-v2.terminal.json',
             EVIDENCE / 'receipt.json', EVIDENCE / 'build/receipt.json', EVIDENCE / 'build/driver.log']
    keys = ('request_sha256', 'release_terminal_sha256', 'owner_receipt_sha256',
            'driver_receipt_sha256', 'driver_log_sha256')
    protected = []
    for path, key in zip(files, keys):
        row = identity(path)
        if row['sha256'] != checkpoint['execution'][key]:
            raise ValueError('Failure evidence digest changed: ' + str(path))
        protected.append(row)
    # Bind the complete small owner-evidence tree; no candidate/build mutation.
    evidence_inventory = [identity(p) for p in sorted(EVIDENCE.rglob('*'))]
    result = {'schema': 'mckernel.scratch21-cleanup-preparation.v1',
              'status': 'READ_ONLY_REVIEW_INPUT', 'execution_released': False,
              'mount': mount[0], 'root': root,
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'retained_exclusions': records, 'protected_failure_files': protected,
              'owner_evidence_inventory': evidence_inventory,
              'request_lease_absent': True, 'container': target,
              'root_lock': identity(Path('/run/lock/mckernel-development.lock')),
              'output_entries': sorted(p.name for p in (ROOT / 'mckernel-exact-candidate-scratch-21-output').iterdir()),
              'cleanup_execution': 'NOT_IMPLEMENTED_OR_RELEASED; use the reviewed scratch21-specific transaction only.',
              'future_transaction': [
                  'Pin UUID plus fresh live st_dev/inodes, current boot and all process/container/evidence identities.',
                  'Acquire preserved root development lock; hold through every mutation and terminal reconciliation.',
                  'Use fresh scratch21 plan/journal/mutex/archive names; retain all original ownership bytes.',
                  'Authenticate complete terminal profile/mounts and capture exact Docker logs before non-force removal.',
                  'Prove exact container absence, atomically exchange exclusions with sentinels, durably archive originals.',
                  'Recheck publisher census and identities before sentinel release; quarantine uncertain retirement.',
                  'Independently review actual cleanup evidence and immutable terminal replay before another workload.'
              ]}
    if live:
        argv = ['/usr/bin/docker', '--host=unix:///var/run/docker.sock']
        items = json.loads(privileged(argv + ['inspect', '--type', 'container', target['container_id']]))
        if len(items) != 1:
            raise ValueError('Ambiguous terminal container')
        validate_container(items[0], target)
        log = privileged(argv + ['logs', '--', target['container_id']])
        if log != (EVIDENCE / 'container.log').read_bytes():
            raise ValueError('Docker log differs from retained evidence')
        census = json.loads(privileged(['/usr/bin/python3', '-I', '-B', '-c', PROC_CODE]))
        if census['uid'] != 0 or census['boot_id'] != result['boot_id']:
            raise ValueError('Privileged census identity changed')
        result['live'] = {'container': items[0], 'docker_log_sha256': hashlib.sha256(log).hexdigest(),
                          'process_and_lock_census': census}
    if identity(ROOT, False) != root or [identity(Path(r['path'])) for r in records] != [
            {k: v for k, v in r.items() if k != 'historical_device'} for r in records]:
        raise ValueError('Scratch/exclusion identity changed during observations')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Read-only privileged Docker/process observations')
    args = parser.parse_args(argv)
    print(json.dumps(inspect(args.live), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('scratch21 preparation refused: ' + str(error), file=sys.stderr)
        sys.exit(1)
