#!/usr/bin/env python3
"""One separately released external-module build; no guest or Linux build.

Reuse the accepted Docker client rundown and root quarantine mechanisms.
Uncertain ownership never releases the development flock or exclusion records.
Stopped containers are retained unless this new operation's exact execution
release expressly authorizes owned terminal removal.
"""
import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

import native_rust_exact_mckernel_image_container_owner as image
import native_rust_exact_build_image_rebind_probe as guard

host = image._HOST_OWNER
shared = image._SHARED_HEAVY_ENTRY_CONTRACT
REPO = Path(__file__).resolve().parents[1]
ROOT = Path('/home/holden/mckernel-work/scratch')
BASIS = ROOT / 'mckernel-exact-candidate-scratch-22-authority3-output'
PREPARATION = REPO / 'docs/verification/evidence/held-host-control-fullmodule-sdk-20261019-1.json'
PREPARATION_SHA = '61525aca567a920e6ed05e7f5fb60d66876d056d6d7d5053646d522bc582631b'
DRIVER = REPO / 'scripts/native_running_external_modules_offline.py'
HISTORICAL_OBSERVER = REPO / 'scripts/native_exact_historical_lease_observer.py'
HISTORICAL_OBSERVER_SHA = '463ae558e141c2a6fe5a016fb19baddb26ed883c3bf6d39c114b27711ee78a51'
HISTORICAL_PREFIX = ('/usr/bin/sudo', '-A', '/home/holden/anaconda3/bin/python3', '-I', '-B')
IMAGE = 'sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d'
CANDIDATE = '942c927b1ec93cc31284ff498455909d9bb2d0fc'
SOURCE_CANDIDATE = '03f9c016c259eb3ce10bb5ad61905ffe20409466df68f114211b329a5cc55de6'
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
LEASE = ROOT / 'native-held-host-control-fullmodule-external-modules.lease.json'
COMMON = ROOT / 'native-held-host-control-fullmodule-external-modules-operational-exclusion.json'
COMMAND = ['/driver.py', '--execute']
MODULES = ('ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko')
SOURCES = ('scripts/native_running_external_modules_owner.py',
           'scripts/tests/test_native_running_external_modules_owner.py',
           'scripts/native_running_external_modules_offline.py',
           'scripts/native_rust_exact_mckernel_image_container_owner.py',
           'scripts/native_rust_exact_build_container_owner.py',
           'scripts/native_rust_exact_build_offline.py',
           'scripts/native_rust_exact_disk_build_wrapper.py',
           'scripts/native_rust_exact_build_image_rebind_probe.py',
           'scripts/native_rust_exact_build_image_prepare.py',
           'scripts/native_rust_exact_build_image_rebind.py',
           'scripts/native_exact_historical_lease_observer.py')


class Refusal(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise Refusal(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bound(ref):
    need(set(ref) == {'path', 'sha256'}, 'exact file reference required')
    return guard._read_json_snapshot(ref['path'], 'external-module bound JSON', ref['sha256'])[0]


def safe_path(value, directory=True):
    path = Path(value)
    need(path.is_absolute() and str(path) == value and '..' not in path.parts,
         'canonical absolute path required')
    need(all(not p.is_symlink() for p in (path, *path.parents)), 'symlink path refused')
    if directory:
        need(path.is_dir(), 'existing directory required')
    else:
        need(path.is_file() and stat.S_ISREG(path.stat().st_mode), 'regular file required')
    return path


def node(path):
    meta = path.stat()
    return dict(path=str(path), device=meta.st_dev, inode=meta.st_ino,
                mode=stat.S_IMODE(meta.st_mode), uid=meta.st_uid, gid=meta.st_gid)


def mounts(request):
    return [(str(BASIS), '/out', True), (request['candidate_root'], '/candidate', False),
            (request['input_root'], '/inputs', True), (str(DRIVER), '/driver.py', True),
            (request['request_path'], '/request.json', True)]


def mount_rows(rows):
    need(isinstance(rows, list) and all(isinstance(r, dict) for r in rows), 'mount shape')
    targets = [r.get('Destination') for r in rows]
    need(all(isinstance(t, str) and t.startswith('/') for t in targets) and
         len(set(targets)) == len(targets), 'duplicate/nonabsolute mount target')
    return sorted(canonical(row) for row in rows)


def profile(info, request, name, nonce, cid=None):
    need(info.get('Name') == '/' + name and re.fullmatch('[0-9a-f]{64}', str(info.get('Id', ''))),
         'exact container name/ID required')
    if cid is not None:
        need(info['Id'] == cid, 'foreign container ID')
    host.check_profile(info, IMAGE, nonce)
    config, control = info['Config'], info['HostConfig']
    need(config.get('User') == '1000:1000' and config.get('Entrypoint') == ['/usr/bin/python3'] and
         config.get('Cmd') == COMMAND and info.get('Path') == '/usr/bin/python3' and
         info.get('Args') == COMMAND, 'exact external driver command/user')
    need(control.get('Tmpfs') == {'/tmp': 'rw,nodev,nosuid,size=256m'} and
         control.get('AutoRemove') is False and control.get('RestartPolicy') == {'Name': 'no', 'MaximumRetryCount': 0},
         'tmpfs/retention/restart profile')
    mount_rows(info.get('Mounts'))
    actual = [(r.get('Source'), r.get('Destination'), r.get('RW'))
              for r in info['Mounts'] if r.get('Type') == 'bind']
    need(sorted(actual) == sorted((s, t, not ro) for s, t, ro in mounts(request)), 'exact five bind mounts')
    extras = [r for r in info['Mounts'] if r.get('Type') != 'bind']
    need(not extras or (len(extras) == 1 and extras[0].get('Type') == 'tmpfs' and
         extras[0].get('Destination') == '/tmp' and extras[0].get('RW') is True), 'extra mount refused')


def live_admission(request):
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT == request['boot_id'], 'boot changed')
    raw = subprocess.check_output(['/usr/bin/findmnt', '-J', '-T', str(ROOT), '-o',
                                   'TARGET,UUID,FSTYPE,OPTIONS,MAJ:MIN'], timeout=15)
    rows = json.loads(raw)['filesystems']
    need(len(rows) == 1 and rows[0].get('target') == str(ROOT) and rows[0].get('uuid') == UUID and
         rows[0].get('fstype') == 'ext4' and rows[0].get('maj:min') == '7:36' and
         {'rw', 'nodev', 'nosuid'} <= set(rows[0].get('options', '').split(',')) and
         ROOT.stat().st_dev == 1828, 'scratch UUID/device/mount differs')
    for path, identity in ((BASIS, request['basis_identity']),
                           (Path(request['candidate_root']), request['candidate_identity']),
                           (Path(request['input_root']), request['input_identity'])):
        actual = node(safe_path(str(path)))
        need(actual == identity and actual['device'] == 1828 and actual['uid'] == actual['gid'] == 1000,
             'input directory identity/device/owner differs')
        if path != BASIS:
            need(actual['mode'] == 0o700, 'private input/candidate directory required')
    return json.loads(raw)


def measure(request):
    # Reserve both candidate and captures above the continuing host/scratch floors.
    reserve = request['disk_budget_bytes'] + request['capture_budget_bytes']
    observed = host.measure('/', str(ROOT), 16 * 2**30 + reserve, 12 * 2**30 + reserve)
    for key, maximum in (('candidate_root', request['disk_budget_bytes']),
                         ('owner_evidence_root', request['capture_budget_bytes'])):
        root = Path(request[key]); total = count = 0
        if not root.exists():
            continue
        for path in root.rglob('*'):
            count += 1
            need(count <= 4096 and not path.is_symlink(), 'bounded output inventory/type')
            if path.is_file():
                total += path.stat().st_size
                need(total <= maximum, key + ' byte budget exceeded')
    return observed


def historical_source():
    raw = shared._stable_file_bytes(HISTORICAL_OBSERVER.parent, HISTORICAL_OBSERVER,
                                    HISTORICAL_OBSERVER_SHA, 'fixed historical lease observer')
    namespace = {'__name__': '_external_owner_historical_constants', '__file__': str(HISTORICAL_OBSERVER)}
    # Import the authenticated constant contract only. observe() executes solely
    # in the separately released, captured/reaped fixed privileged client below.
    exec(compile(raw, str(HISTORICAL_OBSERVER), 'exec'), namespace)
    need(namespace['ROOT'] == ROOT and namespace['CURRENT_BOOT'] == BOOT and
         namespace['CURRENT_DEVICE'] == 1828 and namespace['FILESYSTEM_UUID'] == UUID and
         str(namespace['BLOCK_DEVICE']) == '/dev/loop36', 'historical observer generation differs')
    return namespace, raw


def historical_paths():
    return sorted(ROOT.glob('native-exact-build-lease-*.json'))


def historical_metadata(path):
    meta = path.lstat()
    return dict(device=meta.st_dev, inode=meta.st_ino, size=meta.st_size,
                mode=meta.st_mode, uid=meta.st_uid, gid=meta.st_gid, nlink=meta.st_nlink,
                mtime_ns=meta.st_mtime_ns, ctime_ns=meta.st_ctime_ns)


def validate_historical_report(report):
    contract, _ = historical_source()
    expected = []
    for suffix, inode, size, digest, pid, start, evidence in contract['LEASES']:
        expected.append(dict(path=str(ROOT / ('native-exact-build-lease-' + suffix + '.json')),
                             sha256=digest, device=1828, inode=inode, size=size, pid=pid, starttime=start,
                             evidence_sha256=contract['EVIDENCE_BINDINGS'][evidence][1]))
    authority = dict(historical_boot_id=contract['HISTORICAL_BOOT'], historical_device=contract['HISTORICAL_DEVICE'],
                     current_device=1828, filesystem_uuid=UUID, block_device='/dev/loop36',
                     uuid_proof='ext4-primary-superblock-pread-1024-at-1024')
    wanted = dict(schema='mckernel.historical-lease-observation.v1', boot_id=BOOT,
                  status='PASS_READ_ONLY', leases=expected, authority=authority)
    need(canonical(report) == canonical(wanted), 'exact seven historical lease report differs')
    paths = {row['path'] for row in expected}
    need({str(path) for path in historical_paths()} == paths, 'unknown/missing historical lease')
    joined = []
    for row in expected:
        path = Path(row['path']);before = historical_metadata(path)
        need(all(before[key] == row[key] for key in ('device', 'inode', 'size')) and
             before['mode'] == stat.S_IFREG | 0o600 and before['uid'] == before['gid'] == 0 and
             before['nlink'] == 1, 'historical lease replaced after observation')
        try:
            current = image._proc_starttime(row['pid'])
        except FileNotFoundError:
            current = None
        need(current != row['starttime'], 'historical owner is live')
        need(historical_metadata(path) == before, 'historical lease metadata raced')
        joined.append(dict(observation=row, metadata=before))
    need({str(path) for path in historical_paths()} == paths, 'historical lease census changed')
    return dict(observer_sha256=HISTORICAL_OBSERVER_SHA, boot_id=BOOT, authority=authority, leases=joined)


def validate_request(request, request_path, historical_observe=None):
    required = {'schema', 'candidate_sha', 'image_id', 'nonce', 'request_path', 'preparation', 'driver',
                'input_root', 'candidate_root', 'owner_evidence_root', 'lease_path', 'common_exclusion_path',
                'basis_identity', 'candidate_identity', 'input_identity', 'boot_id', 'timeout',
                'disk_budget_bytes', 'capture_budget_bytes', 'terminal_policy'}
    need(set(request) == required and request['schema'] == 'mckernel.native-running-external-modules-request.v1',
         'exact external-module request schema')
    nonce = request['nonce']
    need(re.fullmatch('[0-9a-f]{32}', str(nonce)) and request['candidate_sha'] == CANDIDATE and
         request['image_id'] == IMAGE and request['request_path'] == str(request_path), 'request pins/nonce/path')
    need(request['preparation'] == {'path': str(PREPARATION), 'sha256': PREPARATION_SHA} and
         request['driver']['path'] == str(DRIVER) and host.digest(safe_path(str(DRIVER), False)) == request['driver']['sha256'],
         'preparation/driver pins')
    need(request['lease_path'] == str(LEASE) and request['common_exclusion_path'] == str(COMMON), 'exact lease paths')
    need(type(request['timeout']) is int and request['timeout'] == 1800 and
         type(request['disk_budget_bytes']) is int and request['disk_budget_bytes'] == 512 * 2**20 and
         type(request['capture_budget_bytes']) is int and request['capture_budget_bytes'] == 64 * 2**20 and
         request['terminal_policy'] == 'remove-owned-terminal', 'fixed budget/terminal policy')
    for key, prefix in (('candidate_root', 'nsd-c-'),
                        ('input_root', 'nsd-i-'),
                        ('owner_evidence_root', 'nsd-o-')):
        path = Path(request[key])
        need(path.parent == ROOT and path.name == prefix + nonce, 'fresh nonce-bound namespace')
        if key == 'owner_evidence_root':
            need(not os.path.lexists(path), 'owner evidence already exists')
        else:
            safe_path(str(path))
    safe_path(str(request_path), False)
    prep = bound(request['preparation'])
    need(prep['baseline_candidate'] == CANDIDATE and prep['tool_image'] == IMAGE and len(prep['closure']) == 62,
         'frozen preparation closure')
    inputs = Path(request['input_root'])
    selected = {'preparation.json': (PREPARATION_SHA, PREPARATION.stat().st_size)}
    for ref in prep['references'].values():
        name = Path(ref['retained_copy']).name
        need(name not in selected, 'duplicate prepared input basename')
        selected[name] = (ref['sha256'], ref['bytes'])
    need({p.name for p in inputs.iterdir()} == set(selected), 'complete exact RO input directory')
    for name, (digest, size) in selected.items():
        path = safe_path(str(inputs / name), False)
        need(path.stat().st_size == size and host.digest(path) == digest, 'prepared input bytes differ')
    candidate = Path(request['candidate_root'])
    need({p.name for p in candidate.iterdir()} == {'modules', 'home', 'tmp'}, 'fresh candidate layout')
    for name in ('home', 'tmp'):
        need(not list(safe_path(str(candidate / name)).iterdir()), 'fresh home/tmp required')
    expected = {row['path']: row for row in prep['closure']}
    actual = {str(p.relative_to(candidate / 'modules')): p for p in (candidate / 'modules').rglob('*') if p.is_file()}
    need(set(actual) == set(expected), 'exact 60-file closure required')
    for name, path in actual.items():
        safe_path(str(path), False)
        need(path.stat().st_size == expected[name]['bytes'] and host.digest(path) == expected[name]['sha256'], 'closure bytes differ')
    conflicts = {LEASE, COMMON, Path(shared.SHARED_HEAVY_LOCK_PATH), Path(image.COMMON_EXCLUSION),
                 Path(host.OPERATIONAL_EXCLUSION_PATH)}
    conflicts.update(ROOT.glob('native-exact-mckernel-image-lease-*.json'))
    need(not any(os.path.lexists(path) for path in conflicts), 'conflicting native/image/shared ownership')
    mount = live_admission(request)
    resources = measure(request)
    need(historical_observe is not None, 'fresh authenticated historical lease observation required')
    historical = validate_historical_report(historical_observe())
    return dict(resources=resources, mount=mount, historical_leases=historical)


class PollSignals:
    def __init__(self, signals, request):
        self.signals, self.request = signals, request
        self.cleaning = False
        self.last = 0

    def check(self):
        if self.signals and not self.cleaning:
            self.signals.check()
        if not self.cleaning and time.monotonic() - self.last >= 1:
            measure(self.request)
            self.last = time.monotonic()


class ExternalDocker(host.Docker):
    """Add normal-client group closure without changing the frozen transport.

    The inherited failure path already attempts client rundown. A normal sudo
    wrapper exit additionally needs an empty group census. Unreadable/raced
    observations latch uncertainty; stop/kill/inspect remain available for
    bounded retirement, while create/start/rm and ownership release are barred.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_checks = []

    def check_client_groups(self, paths, stage):
        for path in paths:
            check = dict(status_path=str(path), stage=stage, empty=False)
            try:
                row = guard._read_json_snapshot(path, 'normal Docker client status')[0]
                need(row.get('state') == 'exited' and type(row.get('pid')) is int and row['pid'] > 0 and
                     type(row.get('exit_code')) is int and row['exit_code'] >= 0,
                     'normal client exit not proven')
                check['pid'] = row['pid']
                survivors = self._surviving_group_members(row['pid'])
                check['surviving_members'] = survivors
                if survivors:
                    self.client_retirement_unproven = True
                # The accepted census also latches unreadable/raced proc rows
                # internally, even when it cannot return a surviving PID.
                check['empty'] = not survivors and not self.client_retirement_unproven
            except BaseException as exc:
                self.client_retirement_unproven = True
                check['error'] = str(exc)
            self.group_checks.append(check)

    def check_all_client_groups(self):
        self.check_client_groups(sorted(self.log.parent.glob('command-*/status.json')), 'final-all-clients')

    def call(self, args, **kwargs):
        if args and args[0] in ('create', 'start', 'rm'):
            need(not self.client_retirement_unproven, 'normal client group retirement unproven; mutation blocked')
        before = set(self.log.parent.glob('command-*/status.json'))
        try:
            return super().call(args, **kwargs)
        finally:
            after = set(self.log.parent.glob('command-*/status.json'))
            self.check_client_groups(sorted(after - before), 'normal-command-completion')


class HistoricalObserverClient(ExternalDocker):
    """One fixed existing read-only observer; not an arbitrary command runner."""
    def __init__(self, log, signals):
        super().__init__(log, signals, sudo=False)
        self.command_prefix = HISTORICAL_PREFIX

    def _record_client_exit(self, code, status):
        super()._record_client_exit(code, status)
        if code is not None and code < 0:
            self.client_retirement_unproven = True
            status['client_retirement_unproven'] = True

    def call(self, *args, **kwargs):
        raise Refusal('historical client accepts only the fixed observe operation')

    def observe(self):
        _, raw = historical_source()
        result = super().call(['-c', raw.decode('utf-8')], timeout=30)
        need(result.returncode == 0 and result.stderr == '' and len(result.stdout.encode()) <= 1 << 20,
             'historical observer report unavailable or unbounded')
        report = json.loads(result.stdout, object_pairs_hook=guard._duplicates)
        positive_clients(self, self.log.parent)
        return report


class BoundDocker:
    """Bind every inspect and retirement mutation to the one admitted ID."""
    def __init__(self, docker, name, nonce):
        self.docker, self.name, self.nonce, self.cid = docker, name, nonce, None

    def call(self, args, **kwargs):
        command = list(args)
        if command[0] in ('stop', 'kill', 'wait', 'logs', 'rm'):
            need(self.cid is not None and command[-1] in (self.name, self.cid), 'unbound lifecycle target')
            command[-1] = self.cid
        result = self.docker.call(command, **kwargs)
        if command[0] == 'inspect':
            rows = json.loads(result.stdout)
            need(len(rows) == 1 and rows[0].get('Name') == '/' + self.name and
                 rows[0].get('Config', {}).get('Labels', {}).get('mckernel.owner') == self.nonce and
                 re.fullmatch('[0-9a-f]{64}', str(rows[0].get('Id', ''))), 'foreign retirement identity')
            if self.cid is not None:
                need(rows[0]['Id'] == self.cid, 'foreign container ID')
            self.cid = rows[0]['Id']
        return result


def positive_clients(docker, evidence):
    check_groups = getattr(docker, 'check_all_client_groups', None)
    if check_groups is not None:
        check_groups()
    need(not docker.client_retirement_unproven, 'Docker client retirement unproven')
    statuses = sorted(evidence.glob('command-*/status.json'))
    need(bool(statuses), 'positive command ledger absent')
    pids = set()
    for path in statuses:
        row = guard._read_json_snapshot(path, 'Docker client status')[0]
        need(row.get('state') == 'exited' and type(row.get('exit_code')) is int and
             row['exit_code'] >= 0 and type(row.get('pid')) is int and row['pid'] > 0 and
             row['pid'] not in pids and not row.get('client_retirement_unproven'), 'client exit ledger unproven')
        pids.add(row['pid'])
    return len(statuses)


def create_args(request, name, nonce):
    args = ['create', '--name', name, '--label', 'mckernel.owner=' + nonce,
            '--init', '--network=none', '--ipc=private', *host.RESOURCE_ARGS,
            '--user', '1000:1000', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--read-only', '--restart=no', '--tmpfs', '/tmp:rw,nodev,nosuid,size=256m']
    for source, target, readonly in mounts(request):
        args += ['--mount', 'type=bind,src=' + source + ',dst=' + target + (',readonly' if readonly else '')]
    return args + ['--entrypoint', '/usr/bin/python3', IMAGE, *COMMAND]


def record_snapshot(path, expected):
    safe_path(str(path), False)
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(before.st_nlink == 1 and stat.S_IMODE(before.st_mode) == 0o600 and
             before.st_uid == before.st_gid == 1000 and before.st_size <= 1 << 20,
             'owned record shape differs')
        raw = b''
        while len(raw) <= before.st_size:
            block = os.read(fd, min(65536, before.st_size + 1 - len(raw)))
            if not block:
                break
            raw += block
        after = os.fstat(fd)
        linked = path.lstat()
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        need(all(getattr(before, k) == getattr(after, k) == getattr(linked, k) for k in fields) and
             len(raw) == before.st_size and json.loads(raw, object_pairs_hook=guard._duplicates) == expected,
             'owned record bytes/identity raced')
        need(expected.get('pid') == os.getpid() and
             expected.get('starttime') == image._proc_starttime(os.getpid()), 'foreign record owner')
        if 'inode' in expected:
            need(expected['inode'] == before.st_ino and expected.get('device', expected.get('dev')) == before.st_dev,
                 'owned exclusion inode differs')
        identity = dict(path=str(path), device=before.st_dev, inode=before.st_ino,
                        size=before.st_size, sha256=sha(raw), record=expected)
        return identity, raw
    finally:
        os.close(fd)


def absence(docker, name, nonce, cid):
    queries = [('name', 'name=^/' + name + '$'), ('label', 'label=mckernel.owner=' + nonce)]
    if cid is not None:
        queries.append(('id', 'id=' + cid))
    for key, query in queries:
        result = docker.call(['ps', '--all', '--quiet', '--no-trunc', '--filter', query], timeout=30)
        need(result.stdout.strip() == '', 'owned container absence unproven: ' + key)
    return dict(container_id=cid, name=name, nonce=nonce, queries=[key for key, _ in queries],
                absent=True)


def release_owned_records(request, records, evidence, proof, authority):
    """New-profile-only postflight: archive all three before any release.

    This is deliberately separate from the old shared _release_exclusion API.
    It requires actual owned-container absence and all cleanup-client exits,
    independently of compiler success. Partial archival failure releases nothing.
    Cooperative publishers use O_EXCL and the preserved development flock;
    arbitrary same-UID record substitution is outside this execution contract.
    """
    need(proof.get('container_absent') is True and proof.get('all_clients_reaped') is True,
         'exact postflight absence/client proof required')
    need(set(records) == {LEASE, COMMON, Path(shared.SHARED_HEAVY_LOCK_PATH)}, 'only this operation records')
    snapshots = {}
    for path, expected in records.items():
        identity, raw = record_snapshot(path, expected)
        filename = ('lease' if path == LEASE else 'common' if path == COMMON else 'shared') + '.record.raw'
        guard._write_new(evidence / filename, raw)
        need((evidence / filename).read_bytes() == raw, 'ownership archive bytes differ')
        snapshots[path] = identity
    archive = dict(schema='mckernel.native-running-external-modules-ownership-archive.v1',
                   request=authority['request'], source_sha256=authority['source_sha256'],
                   nonce=request['nonce'], records=list(snapshots.values()), postflight=proof)
    guard._write_json(evidence / 'ownership-archive.json', archive)
    for path, expected in records.items():
        need(record_snapshot(path, expected)[0] == snapshots[path], 'record changed after archival')
    guard._write_json(evidence / 'record-release-authorized.json',
                      dict(schema='mckernel.native-running-external-modules-record-release.v1',
                           status='POSTFLIGHT_RELEASE_AUTHORIZED', archive_sha256=host.digest(evidence / 'ownership-archive.json'),
                           nonce=request['nonce'], records=list(snapshots.values())))
    parent = os.open(str(ROOT), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for path in (LEASE, COMMON, Path(shared.SHARED_HEAVY_LOCK_PATH)):
            need(record_snapshot(path, records[path])[0] == snapshots[path], 'record changed before exact release')
            os.unlink(path.name, dir_fd=parent)
            os.fsync(parent)
    finally:
        os.close(parent)
    guard._write_json(evidence / 'record-release-complete.json',
                      dict(status='OWNED_RECORDS_RELEASED', nonce=request['nonce'],
                           archive_sha256=host.digest(evidence / 'ownership-archive.json')))
    return archive


def run_owner(request, docker, signals, measurement, authority, admission_client=None):
    """Caller must hold authenticated root flock; all exclusions remain on failure."""
    evidence = Path(request['owner_evidence_root'])
    shared_path, shared_record = shared.acquire_heavy_operation(request, 'build')
    common = image.CommonExclusion(str(COMMON), request); common.acquire()
    name = 'mckernel-external-' + request['nonce']
    lease = host.Lease(LEASE, name); lease.acquire()
    evidence.mkdir(mode=0o700)
    transport = BoundDocker(docker, name, request['nonce'])
    receipt = dict(schema='mckernel.native-running-external-modules-owner-receipt.v1', status='FAIL',
                   request=request, measurement=measurement, container_name=name, owner_nonce=request['nonce'],
                   build_status='FAIL', cleanup_status='NOT_PROVEN', authority=authority,
                   retired=False, cleanup_separately_required=True, terminal_container_retained=None,
                   shared_record=shared_record, common_record=common.record, operation_lease=lease.record)
    attempted = False
    first = None
    try:
        absence(docker, name, request['nonce'], None)
        image_info = json.loads(docker.call(['image', 'inspect', IMAGE]).stdout)
        need(len(image_info) == 1 and image_info[0].get('Id') == IMAGE and
             image_info[0].get('Architecture') == 'amd64', 'immutable tool image differs')
        attempted = True
        created = docker.call(create_args(request, name, request['nonce']))
        cid = created.stdout.strip()
        need(re.fullmatch('[0-9a-f]{64}', cid), 'create returned malformed ID')
        transport.cid = cid
        first = host.inspect(transport, name)
        host.atomic(evidence / 'inspect-before-start.json', first)
        profile(first, request, name, request['nonce'], cid)
        transport.call(['start', name])
        waited = transport.call(['wait', name], timeout=request['timeout'] + 60)
        raw_exit = waited.stdout.strip()
        need(re.fullmatch('[0-9]+', raw_exit) and 0 <= int(raw_exit) <= 255, 'bounded container exit code required')
        receipt['wait_exit_code'] = int(raw_exit)
        need(receipt['wait_exit_code'] == 0, 'offline external-module driver failed')
        driver_receipt = guard._read_json_snapshot(Path(request['candidate_root']) / 'evidence/receipt.json', 'external driver receipt')[0]
        prep = bound(request['preparation'])
        need(driver_receipt.get('status') == 'BUILD_ARTIFACT_CHECKS_PASS' and
             type(driver_receipt.get('make_returncode')) is int and driver_receipt['make_returncode'] == 0 and
             driver_receipt.get('preparation_sha256') == PREPARATION_SHA and
             driver_receipt.get('source_sha256') == {r['path']: r['sha256'] for r in prep['closure']} and
             driver_receipt.get('application_acceptance') is False and driver_receipt.get('production_acceptance') is False,
             'external driver artifact receipt failed')
        provenance = driver_receipt.get('source_provenance', {})
        sources = {r['path']: r['sha256'] for r in prep['closure']}
        need(driver_receipt.get('baseline_source_sha') == CANDIDATE and
             driver_receipt.get('source_candidate_sha') == SOURCE_CANDIDATE and
             provenance.get('baseline_source_sha') == CANDIDATE and
             provenance.get('source_candidate_sha') == SOURCE_CANDIDATE and
             provenance.get('closure_sha256') == sha(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()),
             'baseline/source candidate provenance differs')
        receipt['source_provenance'] = provenance
        need(set(driver_receipt.get('artifacts', {})) == {'ihk', 'ihk-smp-x86_64', 'mcctrl'}, 'complete matched module set required')
        for name_ko in MODULES:
            artifact = safe_path(str(Path(request['candidate_root']) / 'modules' / name_ko), False)
            recorded = driver_receipt['artifacts'][name_ko[:-3]]
            need(artifact.stat().st_size > 0 and artifact.stat().st_size == recorded['bytes'] and
                 host.digest(artifact) == recorded['sha256'] and recorded['compiler_binding'].get('sources'),
                 'matched module identity/compiler binding missing')
        receipt['driver_receipt'] = driver_receipt
        receipt['status'] = receipt['build_status'] = 'PASS'
    except BaseException as exc:
        receipt['error'] = str(exc)
    finally:
        if signals:
            signals.cleaning = True
        try:
            if attempted:
                terminal = host.retire(transport, name, request['nonce'])
                receipt['container_id'] = transport.cid
                host.atomic(evidence / 'inspect-terminal.json', terminal)
                need(terminal['State'].get('Status') in ('exited', 'created') and
                     terminal['State'].get('Pid') == 0 and terminal['State'].get('Running') is False and
                     terminal['State'].get('OOMKilled') is False and
                     type(terminal['State'].get('ExitCode')) is int and
                     ('wait_exit_code' not in receipt or terminal['State']['ExitCode'] == receipt['wait_exit_code']),
                     'owned stopped container/exit code unproven')
                if first is not None:
                    need(terminal['Config'] == first['Config'] and terminal['HostConfig'] == first['HostConfig'] and
                         mount_rows(terminal['Mounts']) == mount_rows(first['Mounts']), 'terminal profile drift')
                else:
                    # A create error may still have produced this exact owned,
                    # never-started container; validate its full created profile.
                    profile(terminal, request, name, request['nonce'], transport.cid)
                logs = transport.call(['logs', name], timeout=30)
                (evidence / 'container.log').write_text(logs.stdout + logs.stderr)
                fresh = host.inspect(transport, name)
                need({k: v for k, v in fresh.items() if k != 'Mounts'} ==
                     {k: v for k, v in terminal.items() if k != 'Mounts'} and
                     mount_rows(fresh.get('Mounts')) == mount_rows(terminal.get('Mounts')),
                     'fresh terminal inspection differs')
                host.atomic(evidence / 'inspect-terminal-fresh.json', fresh)
                receipt.update(terminal_container_info=fresh, terminal_container_retained=True,
                               terminal_container_info_current=True)
            receipt['client_count_before_cleanup'] = positive_clients(docker, evidence)
            if admission_client is not None:
                receipt['admission_client_count'] = positive_clients(admission_client, admission_client.log.parent)
            receipt['retired'] = True
            if attempted:
                removed = transport.call(['rm', name], timeout=30)
                need(removed.stdout.strip() == transport.cid, 'owned terminal removal result differs')
            empty = absence(docker, name, request['nonce'], transport.cid)
            receipt['client_count'] = positive_clients(docker, evidence)
            if admission_client is not None:
                receipt['admission_client_count'] = positive_clients(admission_client, admission_client.log.parent)
            postflight = dict(schema='mckernel.native-running-external-modules-postflight.v1',
                             container_absent=True, all_clients_reaped=True, absence=empty,
                             compiler_status=receipt['build_status'],
                             client_group_checks=list(getattr(docker, 'group_checks', [])),
                             admission_client_group_checks=list(getattr(admission_client, 'group_checks', [])))
            guard._write_json(evidence / 'postflight-proof.json', postflight)
            release_owned_records(request, {LEASE: lease.record, COMMON: common.record, shared_path: shared_record},
                                  evidence, postflight, authority)
            receipt.update(cleanup_status='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE', cleanup_separately_required=False,
                           terminal_container_info=None, terminal_container_retained=False,
                           terminal_container_info_current=True, postflight=postflight)
        except BaseException as exc:
            receipt.update(status='FAIL', retired=False, cleanup_status='UNCERTAIN_RECORDS_RETAINED', retirement_error=str(exc))
        receipt['client_group_checks'] = list(getattr(docker, 'group_checks', []))
        receipt['admission_client_group_checks'] = list(getattr(admission_client, 'group_checks', []))
        requested = getattr(getattr(signals, 'signals', None), 'requested', None)
        if requested is not None:
            receipt.update(status='FAIL', interrupted_signal=requested)
        host.atomic(evidence / 'owner-receipt.json', receipt)
    return receipt


def authenticate(request_path, request_sha, release_path, release_sha):
    request = bound(dict(path=str(request_path), sha256=request_sha))
    release = bound(dict(path=str(release_path), sha256=release_sha))
    need(release.get('schema') == 'mckernel.native-running-external-modules-release.v1' and
         release.get('status') == 'PASS_EXECUTION_RELEASE' and release.get('execution_count') == 1 and
         type(release['execution_count']) is int and release.get('request') == {'path': str(request_path), 'sha256': request_sha} and
         release.get('nonce') == request.get('nonce') and release.get('boot_id') == BOOT and
         release.get('fetched_source_verified') is True and release.get('terminal_policy') == request.get('terminal_policy') and
         release.get('historical_observer') == dict(path=str(HISTORICAL_OBSERVER), sha256=HISTORICAL_OBSERVER_SHA,
              prefix=list(HISTORICAL_PREFIX), timeout_seconds=30),
         'independent one-shot external-module execution release required')
    need(set(release.get('source_sha256', {})) == set(SOURCES), 'complete runtime source closure required')
    for name in SOURCES:
        need(host.digest(safe_path(str(REPO / name), False)) == release['source_sha256'][name], 'reviewed source drift')
    need(request['driver']['sha256'] == release['source_sha256']['scripts/native_running_external_modules_offline.py'], 'driver source release differs')
    for key, decision in (('source_review', 'PASS_SOURCE'), ('execution_review', 'PASS_EXECUTION')):
        review = bound(release[key])
        need(review.get('decision') == decision and review.get('implementation_ownership') is False and
             review.get('reviewer') and review['reviewer'] != release.get('author') and release.get('author'),
             'independent review required')
        if key == 'source_review':
            need(review.get('source_sha256') == release['source_sha256'], 'exact independent source review required')
        else:
            payload = {k: v for k, v in release.items() if k != 'execution_review'}
            need(review.get('reviewed_release_payload_sha256') == sha(canonical(payload)), 'exact independent execution payload required')
    return request, release


class DeferredSignals(host.CliSignals):
    """Use the existing latch for all four root-guard termination signals."""
    def __enter__(self):
        self.previous = {number: signal.getsignal(number) for number in guard.DEFERRED_SIGNALS}
        for number in self.previous:
            signal.signal(number, self.receive)
        return self


def guarded_execute(request_path, request_sha, release_path, release_sha):
    need(os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000, 'ordinary holden owner required')
    with DeferredSignals() as latch:
        fd = guard._development_lock(guard.DEVELOPMENT_LOCK, (27, 4), (0, 0))
        entered = safe = False
        admission_client = None
        try:
            request, release = authenticate(request_path, request_sha, release_path, release_sha)
            admission = ROOT / ('nsd-a-' + request['nonce'])
            need(not os.path.lexists(admission), 'fresh nonce-bound admission evidence required')
            def observe_historical():
                nonlocal admission_client
                admission.mkdir(mode=0o700)
                admission_client = HistoricalObserverClient(admission / 'observer.log', latch)
                report = admission_client.observe()
                guard._write_json(admission / 'historical-lease-observation.json', report)
                return report
            measurement = validate_request(request, request_path, historical_observe=observe_historical)
            guard._write_json(admission / 'historical-lease-disposition.json', measurement['historical_leases'])
            latch.check()
            poll = PollSignals(latch, request)
            docker = ExternalDocker(Path(request['owner_evidence_root']) / 'docker.log', poll, sudo=True)
            entered = True
            result = run_owner(request, docker, poll, measurement,
                               dict(request={'path': str(request_path), 'sha256': request_sha},
                                    source_sha256=release['source_sha256']), admission_client=admission_client)
            need(result.get('retired') is True and not docker.client_retirement_unproven and
                 (admission_client is None or not admission_client.client_retirement_unproven),
                 'terminal/client retirement unproven')
            guard._development_lock(guard.DEVELOPMENT_LOCK, (27, 4), (0, 0), held_fd=fd)
            need(result.get('cleanup_status') == 'PASS_OWNED_REMOVAL_AND_RECORD_RELEASE' and
                 result.get('cleanup_separately_required') is False, 'new-profile postflight archival release unproven')
            safe = True
            return result
        finally:
            if (entered and not safe) or (admission_client is not None and admission_client.client_retirement_unproven):
                guard.quarantine_root_lock(fd, release_path)
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request', 'request-sha256', 'release', 'release-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    result = guarded_execute(Path(args.request), args.request_sha256, Path(args.release), args.release_sha256)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
