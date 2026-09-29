#!/usr/bin/env python3
"""DRAFT-only continuation for the consumed 704f6654 retirement attempt.

This is deliberately not an execution release.  ``draft_guard`` is the first
operation in ``main`` and rejects every unresolved sentinel before it can open
an output, inspect a process, start Docker, or touch a protected root.  The
future reviewed release must retain the descriptor-based checks below; it may
not rename a quarantine back into an original name or remove the immutable
shared tombstone.

The root-0700 quarantine is an operational exclusion from new ordinary opens.
Privileged/adversarial mutation, reference acquisition, and reference transfer
remain independently excluded during both observation and deletion; this is
not an atomic global /proc proof.
"""
from __future__ import print_function
import argparse
import ctypes
import select
import threading
import types
import fcntl
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tarfile
import time
from pathlib import Path

REPO = Path('/home/holden/mckernel')
SCRATCH = Path('/home/holden/mckernel-work/scratch')
PACKET = REPO / 'docs/verification/evidence/native-exact-candidate-quarantine-recover-704f6654-1.py'
BASIS = REPO / 'docs/verification/evidence/native-exact-candidate-quarantine-recovery-release-basis-704f6654-1.json'
WRAPPER = REPO / 'docs/verification/evidence/native-exact-candidate-quarantine-recovery-execution-704f6654-1.sh'
TEST = REPO / 'scripts/tests/test_native_exact_candidate_quarantine_recovery_704f6654.py'
EXECUTION_RELEASE = REPO / 'docs/verification/stability-native-exact-candidate-quarantine-recovery-execution-release-704f6654-1.json'
V2_PACKET = REPO / 'docs/verification/evidence/native-exact-candidate-retirement-704f6654-2.py'
V2_RELEASE = REPO / 'docs/verification/evidence/stability-native-exact-candidate-retirement-704f6654-2.release.json'
INVENTORY = REPO / 'docs/verification/evidence/stability-native-exact-candidate-retention-704f6654-20260929-1.inventory.json'
CAPSULE = REPO / 'docs/verification/evidence/stability-native-exact-candidate-retention-704f6654-20260929-1.tar'
SUCCESS = REPO / 'docs/verification/evidence/stability-native-exact-retention-preparation-success-704f6654-20260929-1.json'
HELPER = REPO / 'scripts/native_exact_candidate_retire_704f.py'
OBSERVER = REPO / 'docs/verification/evidence/native-exact-candidate-live-reference-observer-704f6654-2.py'
RAW = REPO / 'docs/verification/evidence/stability-native-exact-retirement-704f6654-failure-20260929-1.tar.gz'
TOMBSTONE = SCRATCH / 'native-exact-build-lease-704f6654-1.json'
EVIDENCE = Path('/dev/shm/.mckernel-retirement-evidence-704f6654-2')
ORIGINALS = (Path('/dev/shm/mckernel-exact-candidate-704f6654-1'),
             Path('/dev/shm/mckernel-exact-metadata-backup-704f6654-1'))
QUARANTINES = (Path('/dev/shm/.mckernel-retirement-candidate-704f6654-2'),
               Path('/dev/shm/.mckernel-retirement-metadata-backup-704f6654-2'))
ROOTS = ((ORIGINALS[0], QUARANTINES[0], 26, 36767),
         (ORIGINALS[1], QUARANTINES[1], 26, 47413))

V2_COMMIT = 'cd4d7e63f0c736f2135834a4372a05fa1c3b29c4'
V2_PACKET_SHA = '27753f96ddc358218cad6a8ade00680894b378190f7ddb981df5b945bfc7c582'
V2_RELEASE_SHA = '19093ec1c3db71f16d5fd93264f474a200c823161b6da522400bbd4b238cc281'
INVENTORY_SHA = '4067c653e4767e63d99f8cc396587e1121dba601ea4f51f1020168cd4c61b8e1'
CAPSULE_SHA = 'b6c85e40cbe7782fa3f1652d43d314091bb25fbf3777312c7d455390d42ecec1'
SUCCESS_SHA = 'be700dd5335fdde0d33c0096a865cf6326cb9c72a99a983ec3764f99e7eeed4d'
HELPER_SHA = '4631190894a214821f02142670a2ce6f77058dc7fae986c0f6295214c705c517'
RAW_SHA = 'ba74523dc6917e113134bb8978b64c76a1332efbf096fa85c5400ce38af78806'
SOURCE_TEMPLATE_ONLY = True
OBSERVER_SHA = '6feda9c9cb08b98e7e9763fba92ff79d3f07e9e2ee78c4d94edd4926afa10a42'
MAX_FILE = 64 << 20
MAX_CALLBACK = 8 << 20
TERM_TIMEOUT = 5
KILL_TIMEOUT = 5
H64 = re.compile(r'^[0-9a-f]{64}$')
FS_IOC_GETFLAGS = 0x80086601
FS_IMMUTABLE_FL = 0x00000010
FLOORS = {'MemAvailable': 4 << 30, 'host_free': 16 << 30, 'scratch_free': 12 << 30, 'tmpfs_free': 4 << 30}
CLAIM = SCRATCH / 'native-exact-candidate-quarantine-recovery-704f6654-1.claim.json'
JOURNAL = SCRATCH / 'native-exact-candidate-quarantine-recovery-704f6654-1.journal.jsonl'
OUTPUT = SCRATCH / 'native-exact-candidate-quarantine-recovery-704f6654-1.evidence'
THREAT = ('Root-owned 0700 quarantines and explicit privileged/adversarial mutation, reference acquisition, '
          'and reference-transfer exclusion are operational controls during observation AND deletion, not an '
          'atomic global proof.')


class Error(RuntimeError): pass
class Interrupted(Error): _retirement_interrupted=True
class CompositeError(Error):
 """Serializable failure tree; cleanup never overwrites the causal failure."""
 _retirement_composite=True
 def __init__(self,primary,cleanup):
  self.primary=primary;self.cleanup=cleanup
  super().__init__('primary failure: '+str(primary)+'; cleanup failure: '+str(cleanup))
class CompositeInterrupted(CompositeError,Interrupted):pass
def failure_contains(root,target):
 """Bounded identity-only search of an explicit failure tree."""
 if root is target:return True
 pending=[root];seen=set();budget=128
 while pending and budget:
  value=pending.pop();budget-=1
  if id(value) in seen:continue
  seen.add(id(value))
  if value is target:return True
  if getattr(value,'_retirement_composite',False) is True:
   pending.extend((getattr(value,'primary',None),getattr(value,'cleanup',None)))
 return False
def error_record(error):
 active=set();budget=[128]
 def visit(value,depth):
  if id(value) in active:return {'type':'FailureTreeCycle','message':'explicit failure tree cycle','interrupted':False}
  if depth>=32 or budget[0]<=0:return {'type':'FailureTreeLimit','message':'explicit failure tree limit','interrupted':False}
  budget[0]-=1
  interrupted=isinstance(value,KeyboardInterrupt) or getattr(value,'_retirement_interrupted',False) is True
  if getattr(value,'_retirement_composite',False) is True:
   active.add(id(value))
   try:primary=visit(value.primary,depth+1);cleanup=visit(value.cleanup,depth+1)
   finally:active.remove(id(value))
   return {'type':type(value).__name__,'interrupted':interrupted or primary['interrupted'] or cleanup['interrupted'],'primary':primary,'cleanup':cleanup}
  message=str(value)
  return {'type':type(value).__name__,'message':message[:4096],'message_truncated':len(message)>4096,'interrupted':interrupted}
 return visit(error,0)
def combined(primary,cleanup):
 if primary is None:return cleanup
 if cleanup is None:return primary
 cls=CompositeInterrupted if error_record(primary)['interrupted'] or error_record(cleanup)['interrupted'] else CompositeError
 return cls(primary,cleanup)
def bad(s): raise Error(s)


def fail(message):
    raise Error(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pairs(rows):
    value = {}
    for key, item in rows:
        if key in value:
            fail('duplicate JSON key: ' + key)
        value[key] = item
    return value


def exact_json(data):
    try:
        return json.loads(data.decode('utf-8') if isinstance(data, bytes) else data, object_pairs_hook=pairs)
    except (TypeError, UnicodeError, ValueError) as exc:
        fail('invalid JSON: ' + str(exc))


def read_regular(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    failure = None
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink < 1:
            fail('not regular: ' + str(path))
        data = b''.join(iter(lambda: os.read(fd, 1 << 20), b''))
        after = os.fstat(fd)
        named = os.stat(str(path), follow_symlinks=False)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mode) != (after.st_dev, after.st_ino, after.st_size, after.st_mode) or (after.st_dev, after.st_ino, after.st_size, after.st_mode) != (named.st_dev, named.st_ino, named.st_size, named.st_mode):
            fail('changed while read: ' + str(path))
    except BaseException as exc:
        failure = exc
    try:
        os.close(fd)
    except BaseException as exc:
        failure = combined(failure, exc)
    if failure is not None:
        raise failure
    return data


def checked(path, wanted):
    value = read_regular(path)
    if digest(value) != wanted:
        fail('hash mismatch: ' + str(path))
    return value


def git_bytes(*args):
    return subprocess.check_output(['/usr/bin/git', '--git-dir=' + str(REPO / '.git'), '--work-tree=' + str(REPO), *args], timeout=30)


def draft_guard():
    if SOURCE_TEMPLATE_ONLY:
        fail('DRAFT_NOT_RELEASED')


def source_paths():
    return {'packet': PACKET, 'wrapper': WRAPPER, 'basis': BASIS, 'observer': OBSERVER, 'test': TEST}


def literal_once(template, before, after):
    if template.count(before) != 1:
        fail('template literal must occur exactly once')
    return template.replace(before, after, 1)


def final_packet_bytes(template):
    return literal_once(template, b'\nSOURCE_TEMPLATE_ONLY = True\n',
                        b'\nSOURCE_TEMPLATE_ONLY = False\n')


def final_wrapper_bytes(template):
    return literal_once(template, b'\nSOURCE_TEMPLATE_ONLY=true\n',
                        b'\nSOURCE_TEMPLATE_ONLY=false\n')


def validate_draft_basis(value):
    if value.get('status') != 'DRAFT_NOT_RELEASED' or value.get('execution_authorized') is not False:
        fail('draft basis semantics')
    if 'release_sha256' in value or 'basis_sha256' in value:
        fail('cyclic basis')
    for name in ('packet', 'wrapper', 'observer', 'test'):
        if value.get(name + '_sha256') != name.upper() + '_SHA_REQUIRED':
            fail('draft basis hash placeholder')
    if value.get('operational_threat_assumption') != THREAT:
        fail('basis threat assumption')


def final_basis_bytes(template, hashes):
    # Exact replacements include the JSON key and quoted value: no substring
    # replacement in code, prose, or unrelated JSON positions is permitted.
    validate_draft_basis(exact_json(template))
    result = literal_once(template, b'"status": "DRAFT_NOT_RELEASED"',
                          b'"status": "PASS_SOURCE_BASIS"')
    for name in ('packet', 'wrapper', 'observer', 'test'):
        value = hashes[name]
        if not isinstance(value, str) or H64.fullmatch(value) is None:
            fail('final source hash')
        before = ('"' + name + '_sha256": "' + name.upper() + '_SHA_REQUIRED"').encode('ascii')
        after = ('"' + name + '_sha256": "' + value + '"').encode('ascii')
        result = literal_once(result, before, after)
    return result


def validate_finalized_sources(release, head, git, read):
    paths = source_paths()
    bindings = release['authenticated_sources']
    finalization = release['finalization']
    if not isinstance(bindings, dict) or set(bindings) != set(paths):
        fail('source binding schema')
    if not isinstance(finalization, dict) or set(finalization) != {'template_commit', 'template_hashes', 'allowed_changed_paths'}:
        fail('finalization schema')
    commit = finalization['template_commit']
    if not isinstance(commit, str) or re.fullmatch('[0-9a-f]{40}', commit) is None or commit == head:
        fail('template commit identity')
    # merge-base's exit status is authoritative; an exception rejects admission.
    git('merge-base', '--is-ancestor', commit, head)
    allowed = [str(path.relative_to(REPO)) for path in (PACKET, WRAPPER, BASIS, EXECUTION_RELEASE)]
    if finalization['allowed_changed_paths'] != allowed:
        fail('allowed changed paths')
    changed = git('diff', '--name-only', '-z', commit, head).decode('utf-8', 'strict').split('\0')
    if changed[-1:] != [''] or len(changed[:-1]) != 4 or set(changed[:-1]) != set(allowed):
        fail('actual changed paths')
    pins = finalization['template_hashes']
    if not isinstance(pins, dict) or set(pins) != set(paths):
        fail('template hash schema')
    templates, finals = {}, {}
    for name, path in paths.items():
        rel = str(path.relative_to(REPO))
        templates[name] = git('show', commit + ':' + rel)
        finals[name] = git('show', head + ':' + rel)
        if any(not isinstance(v, str) or H64.fullmatch(v) is None for v in (pins[name], bindings[name])):
            fail('source hash syntax')
        if digest(templates[name]) != pins[name]:
            fail('template substitution: ' + name)
        if digest(finals[name]) != bindings[name] or read(path) != finals[name]:
            fail('final/local source substitution: ' + name)
    expected = {'packet': final_packet_bytes(templates['packet']),
                'wrapper': final_wrapper_bytes(templates['wrapper']),
                'observer': templates['observer'], 'test': templates['test']}
    expected['basis'] = final_basis_bytes(templates['basis'], bindings)
    if finals != expected:
        fail('literal-only mechanical finalization mismatch')
    if bindings['observer'] != OBSERVER_SHA:
        fail('accepted observer substituted')
    basis = exact_json(finals['basis'])
    if basis['execution_authorized'] is not False or basis['status'] != 'PASS_SOURCE_BASIS':
        fail('source basis semantics')
    return bindings


def admit_execution_release(path, git=None, read=None):
    git = git or git_bytes
    read = read or read_regular
    if str(path) != str(EXECUTION_RELEASE):
        fail('release path is not canonical')
    head, upstream, fetched = (git('rev-parse', item).decode('ascii', 'strict').strip()
                               for item in ('HEAD', '@{upstream}', 'FETCH_HEAD'))
    if re.fullmatch('[0-9a-f]{40}', head) is None or head != upstream or head != fetched:
        fail('HEAD/upstream/FETCH_HEAD mismatch')
    raw = git('show', head + ':' + str(EXECUTION_RELEASE.relative_to(REPO)))
    if read(EXECUTION_RELEASE) != raw:
        fail('canonical fetched release bytes mismatch')
    release = exact_json(raw)
    keys = {'schema', 'status', 'execution_authorized', 'one_shot', 'retry', 'rollback',
            'authenticated_sources', 'finalization', 'runtime', 'docker'}
    if not isinstance(release, dict) or set(release) != keys or release['schema'] != 'mckernel.quarantine-continuation-execution-release.v2':
        fail('execution release schema')
    if (release['status'] != 'PASS' or release['execution_authorized'] is not True or
            release['one_shot'] is not True or release['retry'] is not False or release['rollback'] is not False):
        fail('execution release semantics')
    validate_finalized_sources(release, head, git, read)
    return release


def validate_authorities():
    """Bind the consumed attempt to fetched bytes, never to current identities."""
    for path, wanted in ((V2_PACKET, V2_PACKET_SHA), (V2_RELEASE, V2_RELEASE_SHA),
                         (INVENTORY, INVENTORY_SHA), (CAPSULE, CAPSULE_SHA),
                         (SUCCESS, SUCCESS_SHA), (HELPER, HELPER_SHA)):
        checked(path, wanted)
    packet = git_bytes('show', V2_COMMIT + ':' + str(V2_PACKET.relative_to(REPO)))
    release = git_bytes('show', V2_COMMIT + ':' + str(V2_RELEASE.relative_to(REPO)))
    if digest(packet) != V2_PACKET_SHA or digest(release) != V2_RELEASE_SHA:
        fail('fetched v2 authority mismatch')
    current = exact_json(read_regular(V2_RELEASE))
    if current.get('status') != 'PASS_ONE_SHOT_RETIRE' or current.get('template', {}).get('commit') != 'ef7b8ef8afa4ac458368f2d4ba26817846fbf8ee':
        fail('v2 release semantics')
    return current


def archive_members(archive):
    with tarfile.open(str(archive), 'r:gz') as stream:
        result = {}
        for member in stream.getmembers():
            if member.name in result:
                fail('duplicate archive member')
            result[member.name] = member
        return result


def archive_bytes(archive, name):
    with tarfile.open(str(archive), 'r:gz') as stream:
        member = next((item for item in stream.getmembers() if item.name == name and item.isfile()), None)
        if member is None:
            fail('archive member absent: ' + name)
        return stream.extractfile(member).read()


def validate_raw_history(archive=RAW, evidence=EVIDENCE, tombstone=TOMBSTONE):
    if digest(read_regular(archive)) != RAW_SHA:
        fail('raw archive hash')
    members = archive_members(archive)
    directory = '.mckernel-retirement-evidence-704f6654-2'
    prefix = directory + '/'
    expected = {directory, 'native-exact-build-lease-704f6654-1.json'}
    expected.update(prefix + name for name in ('archive.sealed.py', 'claim-704f6654-2.json', 'helper.sealed.py', 'journal-704f6654-2.jsonl', 'observer.sealed.py', 'observer.status', 'observer.stderr', 'observer.stdout', 'packet.failure'))
    if set(members) != expected or not members[directory].isdir():
        fail('raw archive membership')
    live = os.lstat(str(evidence))
    if not stat.S_ISDIR(live.st_mode) or (live.st_uid, live.st_gid, stat.S_IMODE(live.st_mode)) != (0, 0, 0o700):
        fail('historical evidence identity')
    names = set(os.listdir(str(evidence)))
    archived_names = {name[len(prefix):] for name in expected if name.startswith(prefix)}
    if names != archived_names:
        fail('historical evidence membership')
    for name in sorted(archived_names):
        got = read_regular(evidence / name)
        wanted = archive_bytes(archive, prefix + name)
        if got != wanted:
            fail('historical evidence changed: ' + name)
    if read_regular(tombstone) != archive_bytes(archive, 'native-exact-build-lease-704f6654-1.json'):
        fail('tombstone bytes differ from raw archive')


def tombstone_fd(path=TOMBSTONE):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode), info.st_nlink) != (0, 0, 0o600, 1):
            fail('tombstone identity')
        flags = fcntl.ioctl(fd, FS_IOC_GETFLAGS, b'\0\0\0\0')
        flags = int.from_bytes(flags[:4], byteorder=sys.byteorder)
        if not flags & FS_IMMUTABLE_FL:
            fail('tombstone not immutable')
        identity = (info.st_dev, info.st_ino, info.st_size, info.st_uid, info.st_gid,
                    stat.S_IMODE(info.st_mode), info.st_nlink,
                    digest(b''.join(iter(lambda: os.read(fd, 1 << 20), b''))))
    except BaseException as exc:
        failure = exc
        try:
            os.close(fd)
        except BaseException as cleanup:
            failure = combined(failure, cleanup)
        raise failure
    return fd, identity


def revalidate_tombstone(fd, wanted):
    now = os.fstat(fd)
    if (now.st_dev, now.st_ino, now.st_size, now.st_uid, now.st_gid, stat.S_IMODE(now.st_mode), now.st_nlink) != wanted[:7]:
        fail('tombstone descriptor changed')
    named = os.stat(str(TOMBSTONE), follow_symlinks=False)
    if (named.st_dev, named.st_ino, named.st_size, named.st_uid, named.st_gid, stat.S_IMODE(named.st_mode), named.st_nlink) != wanted[:7]:
        fail('tombstone name changed')
    flags = int.from_bytes(fcntl.ioctl(fd, FS_IOC_GETFLAGS, b'\0\0\0\0')[:4], byteorder=sys.byteorder)
    if not flags & FS_IMMUTABLE_FL:
        fail('tombstone immutable flag cleared')
    os.lseek(fd, 0, os.SEEK_SET)
    if digest(b''.join(iter(lambda: os.read(fd, 1 << 20), b''))) != wanted[7]:
        fail('tombstone bytes changed')


def reopen_tombstone(wanted):
    """The retained descriptor is checked again through a fresh nofollow open."""
    fd, got = tombstone_fd()
    failure = None
    try:
        if got != wanted:
            fail('tombstone reopened identity/hash changed')
        revalidate_tombstone(fd, wanted)
    except BaseException as exc:
        failure = exc
    try:
        os.close(fd)
    except BaseException as exc:
        failure = combined(failure, exc)
    if failure is not None:
        raise failure


def member_identity(info):
    kind = 'directory' if stat.S_ISDIR(info.st_mode) else 'file' if stat.S_ISREG(info.st_mode) else 'symlink' if stat.S_ISLNK(info.st_mode) else 'unsupported'
    return {'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid, 'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode), 'kind': kind, 'size': info.st_size}


def validate_quarantines(release):
    if any(os.path.lexists(str(path)) for path in ORIGINALS):
        fail('original path unexpectedly present')
    rows = release.get('roots')
    if not isinstance(rows, list) or len(rows) != 2:
        fail('released root map')
    result = []
    for (original, quarantine, device, inode), row in zip(ROOTS, rows):
        if row.get('path') != str(original) or row.get('quarantine_name') != quarantine.name:
            fail('released quarantine name')
        info = os.lstat(str(quarantine))
        actual = member_identity(info)
        if actual != {'device': device, 'inode': inode, 'uid': 0, 'gid': 0, 'mode': 0o700, 'kind': 'directory', 'size': info.st_size}:
            fail('quarantine root identity')
        expected = {entry['path']: entry for entry in row.get('members', []) if isinstance(entry, dict)}
        if len(expected) != len(row.get('members', [])):
            fail('released member duplicate')
        found = {}
        for base, dirs, files in os.walk(str(quarantine), topdown=True, followlinks=False):
            names = dirs + files
            for name in names:
                path = Path(base) / name
                rel = str(path.relative_to(quarantine))
                item = os.lstat(str(path)); got = member_identity(item)
                wanted = expected.get(rel)
                if wanted is None or any(got[key] != wanted.get(key) for key in got):
                    fail('released member identity: ' + rel)
                if got['device'] != device:
                    fail('cross-device member: ' + rel)
                if got['kind'] == 'file' and digest(read_regular(path)) != wanted.get('sha256'):
                    fail('released file hash: ' + rel)
                if got['kind'] == 'symlink' and (os.readlink(str(path)) != wanted.get('target') or digest(os.fsencode(os.readlink(str(path)))) != wanted.get('sha256')):
                    fail('released symlink: ' + rel)
                found[rel] = dict(wanted, **got)
        if set(found) != set(expected):
            fail('released member map incomplete')
        # Device/inode multiplicity is the released hardlink map.  A copied
        # file with matching bytes but a different inode cannot be adopted.
        released_links, actual_links = {}, {}
        for item in expected.values():
            released_links[(item['device'], item['inode'])] = released_links.get((item['device'], item['inode']), 0) + 1
        for item in found.values():
            actual_links[(item['device'], item['inode'])] = actual_links.get((item['device'], item['inode']), 0) + 1
        if actual_links != released_links:
            fail('released hardlink map')
        result.append(expected)
    return result


def _observer_identity(device, inode, uid, gid, kind, mode):
    kinds = {'directory': stat.S_IFDIR, 'file': stat.S_IFREG, 'symlink': stat.S_IFLNK}
    if kind not in kinds:
        fail('observer unsupported member kind')
    return (device, inode, uid, gid, kinds[kind], mode)


def _observer_membership_digest(identities):
    return digest((''.join(':'.join(str(value) for value in row) + '\n' for row in sorted(identities))).encode('ascii'))


def validate_observer(value, expected, admitted_boot=None, launched=None):
    if (not isinstance(value, dict) or value.get('schema') != 'mckernel.read-only-live-reference-snapshot.v7' or
            value.get('status') != 'PASS' or value.get('observer_sha256') != OBSERVER_SHA or
            value.get('scan_complete') is not True or value.get('failure') is not None):
        fail('observer v7')
    for key in ('boot_id', 'started_at_utc', 'ended_at_utc'):
        if not isinstance(value.get(key), str) or not value[key]:
            fail('observer scalar: ' + key)
    if (type(value.get('observer_pid')) is not int or value['observer_pid'] <= 0 or
            not isinstance(value.get('observer_starttime'), str) or
            re.fullmatch('[0-9]+', value['observer_starttime']) is None):
        fail('observer process identity')
    if admitted_boot is not None and value['boot_id'] != admitted_boot:
        fail('observer boot mismatch')
    if launched is not None and (value['observer_pid'], int(value['observer_starttime'])) != tuple(launched):
        fail('observer launched identity mismatch')
    if not isinstance(value.get('tasks_scanned'), int) or value['tasks_scanned'] < 0 or type(value.get('allowed_self_scan_fds')) is not list:
        fail('observer coverage fields')
    roots = value.get('roots')
    if not isinstance(roots, list) or len(roots) != 2:
        fail('observer roots')
    for root, (_original, quarantine, device, inode), members in zip(roots, ROOTS, expected):
        identities = set(_observer_identity(item['device'], item['inode'], item['uid'], item['gid'], item['kind'], item['mode']) for item in members.values())
        identities.add(_observer_identity(device, inode, 0, 0, 'directory', 0o700))
        identities = sorted(identities)
        identities = [list(item) for item in identities]
        if (root.get('path'), root.get('device_number'), root.get('inode'), root.get('mode'), root.get('tree_member_identities')) != (str(quarantine), device, inode, '0700', identities):
            fail('observer exact member identities')
        if (root.get('device') != '%d:%d' % (os.major(device), os.minor(device)) or root.get('uid') != 0 or
                root.get('gid') != 0 or root.get('tree_root_identity') != list(_observer_identity(device, inode, 0, 0, 'directory', 0o700)) or
                root.get('tree_inode_count') != len(identities) or root.get('tree_membership_sha256') != _observer_membership_digest(identities) or
                not isinstance(root.get('filesystem_root'), str) or not isinstance(root.get('observer_mount'), dict)):
            fail('observer root schema')
    rounds = value.get('rounds')
    if not isinstance(rounds, list) or len(rounds) < 2:
        fail('observer rounds')
    sticky = ('target_references', 'permission_denials', 'tree_revalidation_failures', 'persistent_tree_revalidation_failures', 'unscanned_final_identities')
    if any(value.get(key, []) != [] for key in sticky):
        fail('observer sticky finding')
    for number, row in enumerate(rounds, 1):
        if (row.get('round') != number or
                any(row.get(key, []) != [] for key in ('target_references', 'permission_denials', 'tree_revalidation_failures')) or row.get('complete_mount_proofs') is not True or
                type(row.get('closure_passes')) is not int or type(row.get('task_identities')) is not int or
                type(row.get('rescanned_identities')) is not int or type(row.get('identities')) is not list or
                type(row.get('field_counts')) is not dict or type(row.get('mount_proofs')) is not list or
                type(row.get('unresolved_churn')) is not list or type(row.get('unscanned_final_identities')) is not list or
                type(row.get('closure_nonconvergent')) is not bool or type(row.get('clean')) is not bool):
            fail('observer round finding')
    for row in rounds[-2:]:
        if row.get('clean') is not True or row.get('unresolved_churn') != [] or row.get('closure_nonconvergent') is not False or row.get('unscanned_final_identities') != []:
            fail('observer final clean rounds')


def _canon_mounts(row):
    if not isinstance(row, dict) or not isinstance(row.get('Mounts'), list):
        fail('Docker record/mount schema')
    copy = dict(row)
    mounts = copy['Mounts']
    if not all(isinstance(item, dict) for item in mounts):
        fail('Docker mount schema')
    copy['Mounts'] = sorted(mounts, key=lambda item: json.dumps(item, sort_keys=True, separators=(',', ':')))
    return copy


def _mount_intersects(source, target):
    if not isinstance(source, str) or not source.startswith('/') or '\0' in source:
        fail('Docker mount source')
    source, target = os.path.normpath(source), os.path.normpath(target)
    return os.path.commonpath((source, target)) in (source, target)


def docker_record_sha256(row):
    """Hash the complete inspect object in memory; never persist its bytes."""
    return digest(json.dumps(_canon_mounts(row), sort_keys=True, separators=(',', ':'),
                             ensure_ascii=True, allow_nan=False).encode('utf-8'))


def protected_docker_mounts(row):
    protected = [str(path) for path in ORIGINALS + QUARANTINES]
    return [mount for mount in _canon_mounts(row)['Mounts']
            if any(_mount_intersects(mount.get('Source'), path) for path in protected)]


def docker_safe_summary(records):
    """Only explicit non-secret audit fields cross the persistence boundary."""
    result = []
    state_types = {'Status': str, 'Running': bool, 'Paused': bool, 'Restarting': bool,
                   'OOMKilled': bool, 'Dead': bool, 'Pid': int, 'ExitCode': int}
    mount_types = {'Type': str, 'Name': str, 'Source': str, 'Destination': str,
                   'Driver': str, 'Mode': str, 'RW': bool, 'Propagation': str}
    for row in records:
        ident = row.get('Id')
        if not isinstance(ident, str) or H64.fullmatch(ident) is None:
            fail('Docker safe-summary identifier')
        state = row.get('State')
        policy = row.get('HostConfig', {}).get('RestartPolicy')
        if not isinstance(state, dict) or not isinstance(policy, dict):
            fail('Docker safe-summary state/policy schema')
        safe_state = {}
        for key, kind in state_types.items():
            if type(state.get(key)) is not kind:
                fail('Docker safe-summary state field: ' + key)
            safe_state[key] = state[key]
        if safe_state['Status'] not in ('created', 'restarting', 'running', 'removing', 'paused', 'exited', 'dead'):
            fail('Docker safe-summary status')
        if type(row.get('RestartCount')) is not int or row['RestartCount'] < 0:
            fail('Docker safe-summary restart count')
        if policy.get('Name') not in ('', 'no', 'always', 'unless-stopped', 'on-failure') or type(policy.get('MaximumRetryCount')) is not int:
            fail('Docker safe-summary restart policy')
        mounts = []
        for mount in protected_docker_mounts(row):
            safe_mount = {}
            for key, kind in mount_types.items():
                if key in mount:
                    if type(mount[key]) is not kind:
                        fail('Docker safe-summary mount field: ' + key)
                    safe_mount[key] = mount[key]
            mounts.append(safe_mount)
        result.append({'id': ident, 'record_sha256': docker_record_sha256(row),
                       'protected_mounts': mounts, 'terminal_state': safe_state,
                       'restart_count': row['RestartCount'],
                       'restart_policy': {'Name': policy['Name'],
                                          'MaximumRetryCount': policy['MaximumRetryCount']}})
    return {'schema': 'mckernel.docker-census-safe-summary.v1',
            'records': sorted(result, key=lambda row: row['id'])}


def validate_docker(records, release):
    """Authenticate every current container; ordering of independent mounts is harmless."""
    docker = release.get('docker', {})
    if not isinstance(docker, dict) or set(docker) != {'authenticated_current_record_sha256', 'terminal_candidate_mount_exceptions'}:
        fail('Docker release schema')
    want = docker.get('authenticated_current_record_sha256')
    exceptions = docker.get('terminal_candidate_mount_exceptions', {})
    if not isinstance(want, dict) or len(want) != 17 or not isinstance(exceptions, dict) or len(exceptions) != 4:
        fail('Docker full census/released exception set')
    if set(exceptions) - set(want):
        fail('Docker exception not in authenticated IDs')
    if any(not isinstance(ident, str) or H64.fullmatch(ident) is None or
           not isinstance(pin, str) or H64.fullmatch(pin) is None for ident, pin in want.items()):
        fail('Docker authenticated hash syntax')
    if not isinstance(records, list) or len(records) != 17:
        fail('Docker full census count')
    got = {row.get('Id'): _canon_mounts(row) for row in records if isinstance(row, dict)}
    if len(got) != 17 or set(got) != set(want):
        fail('Docker census omission/churn')
    for ident, row in got.items():
        if docker_record_sha256(row) != want[ident]:
            fail('Docker authenticated record')
        observed = protected_docker_mounts(row)
        allowed = exceptions.get(ident, [])
        if ident in exceptions:
            state = row.get('State')
            if (not isinstance(state, dict) or state.get('Status') != 'exited' or
                    any(state.get(key) is not False for key in ('Running', 'Paused', 'Restarting', 'OOMKilled', 'Dead')) or
                    type(state.get('Pid')) is not int or state['Pid'] != 0 or
                    type(state.get('ExitCode')) is not int or type(row.get('RestartCount')) is not int or row['RestartCount'] != 0 or
                    row.get('HostConfig', {}).get('RestartPolicy') != {'Name': 'no', 'MaximumRetryCount': 0}):
                fail('Docker terminal exception state')
            if _canon_mounts({'Mounts': observed})['Mounts'] != _canon_mounts({'Mounts': allowed})['Mounts']:
                fail('Docker terminal mount exception mismatch')
        elif observed:
            fail('unknown protected Docker mount')


def docker_census():
    """A full ``ps --all``/inspect snapshot; unknown IDs fail closed."""
    ids = subprocess.check_output(['/usr/bin/docker', 'ps', '--all', '--quiet', '--no-trunc'], timeout=60).decode('ascii', 'strict').splitlines()
    if len(ids) != 17 or len(ids) != len(set(ids)) or any(H64.fullmatch(item) is None for item in ids):
        fail('Docker census identifiers')
    data = subprocess.check_output(['/usr/bin/docker', 'inspect', *ids], timeout=60)
    rows = exact_json(data)
    if not isinstance(rows, list) or {row.get('Id') for row in rows if isinstance(row, dict)} != set(ids):
        fail('Docker census inspect omission')
    after = subprocess.check_output(['/usr/bin/docker', 'ps', '--all', '--quiet', '--no-trunc'], timeout=60).decode('ascii', 'strict').splitlines()
    if after != ids:
        fail('Docker census churn')
    return rows


def full_write(fd, data, write=os.write):
    offset = 0
    while offset < len(data):
        count = write(fd, data[offset:])
        if not isinstance(count, int) or count <= 0 or count > len(data) - offset:
            fail('short or invalid write')
        offset += count


def fsync_dir(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    failure = None
    try:
        os.fsync(fd)
    except BaseException as exc:
        failure = exc
    try:
        os.close(fd)
    except BaseException as exc:
        failure = combined(failure, exc)
    if failure is not None:
        raise failure


def exclusive_fd(path):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        fsync_dir(Path(path).parent)
    except BaseException as exc:
        failure = exc
        try:
            os.close(fd)
        except BaseException as cleanup:
            failure = combined(failure, cleanup)
        raise failure
    return fd


def _proc_identity_pid(pid, proc=Path('/proc')):
    row = proc / str(pid) / 'stat'
    try:
        fields = row.read_text().rsplit(')', 1)[1].split()
        return {'pid': pid, 'starttime': int(fields[19]), 'session': int(fields[3])}
    except (OSError, IndexError, ValueError) as exc:
        fail('owned process identity unavailable: ' + str(exc))


# Process ownership primitives copied from the accepted 704f retirement packet.
SYS_pidfd_open=434;SYS_pidfd_send_signal=424
def proc_row(pid):
 try:fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:raise
 except (OSError,IndexError,ValueError) as e:bad('process census unreadable: '+str(e))
 try:return {'pid':int(pid),'pgrp':int(fields[2]),'session':int(fields[3]),'starttime':int(fields[19])}
 except (IndexError,ValueError):bad('process census malformed')
def session_members(session):
 """Census the original session; each returned PID gets a pidfd before signal."""
 answer=[]
 try:names=os.listdir('/proc')
 except OSError as e:bad('process-group census unavailable: '+str(e))
 for name in names:
  if not name.isdigit():continue
  try:row=proc_row(int(name))
  except FileNotFoundError:continue
  if row['session']==session:answer.append(row)
 return answer
def group_members(pgid):return [x['pid'] for x in session_members(pgid)] # retained pure-test compatibility
def _syscall(number,*args):
 try:result=ctypes.CDLL(None,use_errno=True).syscall(number,*args)
 except AttributeError:bad('pidfd syscall unavailable')
 if result<0:
  e=ctypes.get_errno()
  if e==3:raise FileNotFoundError(e,os.strerror(e))
  bad('pidfd syscall failed: '+os.strerror(e))
 return result
def pidfd_open(pid):return _syscall(SYS_pidfd_open,pid,0)
def pidfd_send(fd,sig):_syscall(SYS_pidfd_send_signal,fd,sig,0,0)
def pidfd_identity(fd):
 try:
  rows=(Path('/proc/self/fdinfo')/str(fd)).read_text().splitlines()
  values=[int(row.split(':',1)[1]) for row in rows if row.startswith('Pid:')]
 except FileNotFoundError:raise
 except (OSError,ValueError) as e:bad('leader pidfd identity unavailable: '+str(e))
 if len(values)!=1:bad('leader pidfd identity missing')
 return values[0]
def pidfd_token(fd):
 value=os.fstat(fd);return (value.st_dev,value.st_ino)
def prove_anchor(p):
 """A pidfd alone does not reserve a reaped PID. Keep the child unreaped."""
 fd=getattr(p,'_mckernel_leader_fd',None);start=getattr(p,'_mckernel_leader_starttime',None)
 if not isinstance(fd,int) or not isinstance(start,int):bad('session incarnation anchor unavailable')
 if pidfd_identity(fd)!=p._mckernel_session:bad('session incarnation anchor lost')
 row=proc_row(p._mckernel_session)
 if row!={'pid':p._mckernel_session,'pgrp':p._mckernel_session,'session':p._mckernel_session,'starttime':start}:bad('session incarnation changed')
 if pidfd_identity(fd)!=p._mckernel_session:bad('session incarnation anchor lost')
 return row
def close_anchor(p):
 fd=getattr(p,'_mckernel_leader_fd',None)
 if not isinstance(fd,int):return
 p._mckernel_close_attempted=False
 failure=None
 try:expected=pidfd_identity(fd)
 except FileNotFoundError:p._mckernel_leader_fd=None;return
 for unused in range(3):
  try:p._mckernel_close_attempted=True;os.close(fd);p._mckernel_leader_fd=None;break
  except BaseException as e:
   failure=combined(failure,e)
   try:current=pidfd_identity(fd)
   except FileNotFoundError:p._mckernel_leader_fd=None;break
   except BaseException as proof_error:failure=combined(failure,proof_error);break
   if current!=expected:
    # Relinquish the numeric slot: it is no longer our descriptor to close.
    p._mckernel_leader_fd=None
    failure=combined(failure,Error('uncertain pidfd close: descriptor identity changed'));break
   try:
    token=getattr(p,'_mckernel_leader_token',None)
    if token is None or pidfd_token(fd)!=token:bad('uncertain pidfd close: descriptor object changed')
    # On older anonymous-inode pidfds, all dead handles can share an inode
    # and Pid=-1. Never retry that ambiguous case merely by numeric fd.
    if expected<=0:bad('uncertain pidfd close: reaped identity cannot authorize retry')
    if proc_row(expected)['starttime']!=p._mckernel_leader_starttime:bad('uncertain pidfd close: process incarnation changed')
   except BaseException as proof_error:failure=combined(failure,proof_error);break
 else:failure=combined(failure,Error('uncertain pidfd close: bounded retry exhausted'))
 if failure is not None:raise failure
def recover_anchor(p):
 """Complete a partial bind only through its still-retained born pidfd."""
 fd=getattr(p,'_mckernel_leader_fd',None);session=p._mckernel_session
 if not isinstance(fd,int):bad('session incarnation anchor unavailable')
 if pidfd_identity(fd)!=session:bad('session incarnation anchor lost')
 if getattr(p,'_mckernel_leader_token',None) is None:p._mckernel_leader_token=pidfd_token(fd)
 first=proc_row(session);again=proc_row(session)
 if first!=again or first['pid']!=session or first['pgrp']!=session or first['session']!=session:bad('new session identity unavailable')
 if pidfd_identity(fd)!=session:bad('session incarnation anchor lost')
 previous=getattr(p,'_mckernel_leader_starttime',None)
 if previous is not None and previous!=first['starttime']:bad('session incarnation changed')
 p._mckernel_leader_starttime=first['starttime'];return prove_anchor(p)
def unreaped_child(p):
 """WNOWAIT proves this numeric PID is still our reserved direct child."""
 if getattr(p,'returncode',None) is not None:bad('unreaped direct-child identity unavailable: Popen already reaped')
 try:return os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
 except (ChildProcessError,ProcessLookupError) as error:bad('unreaped direct-child identity unavailable: '+str(error))
def direct_child_row(p):
 unreaped_child(p);first=proc_row(p.pid);again=proc_row(p.pid);unreaped_child(p)
 if first!=again or first['pid']!=p.pid or first['pgrp']!=p.pid or first['session']!=p.pid:bad('unreaped direct-child session changed')
 previous=getattr(p,'_mckernel_leader_starttime',None)
 if previous is not None and previous!=first['starttime']:bad('unreaped direct-child incarnation changed')
 p._mckernel_leader_starttime=first['starttime'];return first
def reacquire_anchor(p):
 """No PID can be adopted unless it remains an unreaped direct child."""
 failure=None
 for unused in range(3):
  try:
   first=direct_child_row(p)
   if not isinstance(getattr(p,'_mckernel_leader_fd',None),int):p._mckernel_leader_fd=pidfd_open(p.pid)
   p._mckernel_leader_token=pidfd_token(p._mckernel_leader_fd)
   if pidfd_identity(p._mckernel_leader_fd)!=p.pid or proc_row(p.pid)!=first:bad('reacquired pidfd incarnation changed')
   unreaped_child(p);return recover_anchor(p)
  except BaseException as error:failure=combined(failure,error)
 raise failure
def pidfd_preflight():
 pid=os.getpid();probe=types.SimpleNamespace(pid=pid,_mckernel_session=pid,_mckernel_leader_fd=None,_mckernel_leader_token=None,_mckernel_leader_starttime=None);failure=None
 try:
  probe._mckernel_leader_fd=pidfd_open(pid);probe._mckernel_leader_token=pidfd_token(probe._mckernel_leader_fd);probe._mckernel_leader_starttime=proc_row(pid)['starttime']
  if pidfd_identity(probe._mckernel_leader_fd)!=pid:bad('pidfd self identity preflight failed')
 except BaseException as error:failure=error
 finally:
  try:close_anchor(probe)
  except BaseException as cleanup:
   failure=combined(failure,cleanup)
   # This fresh self-probe has never been handed to another owner. If fdinfo
   # failed before any close syscall, one close of that retained descriptor
   # is safe; never repeat a close whose outcome is already ambiguous.
   if isinstance(probe._mckernel_leader_fd,int) and getattr(probe,'_mckernel_close_attempted',False) is False:
    try:os.close(probe._mckernel_leader_fd);probe._mckernel_leader_fd=None
    except BaseException as last:failure=combined(failure,last)
 if failure is not None:raise failure
def spawn_preflight(check_pidfd=False):
 if not callable(getattr(signal,'pthread_sigmask',None)) or threading.current_thread() is not threading.main_thread() or threading.active_count()!=1:bad('owned spawn requires single main thread and pthread_sigmask')
 if signal.getsignal(signal.SIGCHLD)!=signal.SIG_DFL:bad('unreaped leader requires default SIGCHLD')
 if not all(hasattr(os,name) for name in ('waitid','WNOWAIT','WEXITED','WNOHANG')):bad('unreaped leader observation unavailable')
 if check_pidfd:pidfd_preflight()
def spawn_owner():return {'p':None,'pid':None,'session':None,'streams':{},'mask':None,'mask_pending':False}
def recover_born_owner(owner):
 """Consume the raw owner independently of any failed decoration helper."""
 p=owner['p'];pid=owner['pid']
 if p is None or not isinstance(pid,int):return p
 if p.pid!=pid or owner['session']!=pid:bad('raw born owner identity changed')
 fields={'_mckernel_session':pid,'_mckernel_leader_starttime':None,'_mckernel_leader_fd':None,'_mckernel_leader_token':None}
 for key,value in fields.items():
  if key not in p.__dict__:object.__setattr__(p,key,value)
 if p._mckernel_session!=pid:bad('decorated born owner identity changed')
 return p
def restore_spawn_mask(owner):
 """Keep restoration errors even when pending signals interrupt the return."""
 if not owner['mask_pending']:return None
 failure=None
 for unused in range(3):
  try:signal.pthread_sigmask(signal.SIG_SETMASK,owner['mask'])
  except BaseException as error:failure=combined(failure,error)
  try:
   if signal.pthread_sigmask(signal.SIG_BLOCK,[])==owner['mask']:
    owner['mask_pending']=False;break
  except BaseException as error:failure=combined(failure,error)
 else:failure=combined(failure,Error('spawn signal mask restoration uncertain'))
 return failure
def owned_spawn(owner,argv,**kwargs):
 """Publish ownership while TERM/INT are blocked, including the Popen return.

 The mutable owner exists before spawning, so callers can retire the child
 even when stream capture, binding or mask restoration raises. The child
 restores the original mask before exec; it must remain TERM-retirable.
 """
 spawn_preflight();failure=None
 owner['mask']=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT});owner['mask_pending']=True
 child_setup=kwargs.pop('preexec_fn',None)
 def before_exec():
  signal.pthread_sigmask(signal.SIG_SETMASK,owner['mask'])
  if child_setup is not None:child_setup()
 try:
  pidfd_preflight()
  owner['p']=subprocess.Popen(argv,preexec_fn=before_exec,**kwargs)
  p=owner['p'];owner['pid']=p.pid;owner['session']=p.pid
  # Only plain record/attribute operations occur between Popen and this raw
  # ownership record; no decoration or adapter may precede it.
  owner['streams']={'stdin':getattr(p,'stdin',None),'stdout':getattr(p,'stdout',None),'stderr':getattr(p,'stderr',None),'stdout_data':bytearray(),'stderr_data':bytearray()}
  born_process(p)
  bind_process(p);owner['streams']=process_streams(p)
 except BaseException as error:failure=error
 finally:failure=combined(failure,restore_spawn_mask(owner))
 if failure is not None:raise failure
 return owner['p'],owner['streams']
def observe_exit(p):
 """Observe exit without freeing the leader PID/session incarnation anchor."""
 if not isinstance(getattr(p,'pid',None),int):return p.poll() # pure test double
 prove_anchor(p)
 result=os.waitid(os.P_PID,p.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
 if result is None:return None
 return result.si_status if result.si_code==os.CLD_EXITED else -result.si_status
def bind_process(p):
 """Pin an unreaped born leader; no poll/wait may run before retirement."""
 if not isinstance(getattr(p,'pid',None),int):return p # in-memory pure test double
 born_process(p)
 spawn_preflight()
 p._mckernel_leader_fd=pidfd_open(p.pid)
 p._mckernel_leader_token=pidfd_token(p._mckernel_leader_fd)
 recover_anchor(p);return p
def born_process(p):
 """Keep a just-created session leader reachable even if binding fails."""
 if not isinstance(getattr(p,'pid',None),int):return p
 p._mckernel_session=p.pid;p._mckernel_leader_starttime=None;p._mckernel_leader_fd=None;p._mckernel_leader_token=None
 return p
def process_streams(p):
 return {'stdin':getattr(p,'stdin',None),'stdout':getattr(p,'stdout',None),'stderr':getattr(p,'stderr',None),'stdout_data':bytearray(),'stderr_data':bytearray()}
def close_streams(streams):
 failure=None
 for stream in (streams.get('stdin'),streams.get('stdout'),streams.get('stderr')):
  if stream is not None:
   for unused in range(8):
    try:stream.close();break
    except (KeyboardInterrupt,Interrupted) as e:failure=combined(failure,e)
    except BaseException as e:failure=combined(failure,e);break
   else:failure=combined(failure,Error('pipe close repeatedly interrupted'))
 return failure
def close_stdin(streams):
 stream=streams.get('stdin')
 if stream is None:return None
 failure=None
 for unused in range(8):
  try:stream.close();return failure
  except (KeyboardInterrupt,Interrupted) as e:failure=combined(failure,e)
  except BaseException as e:return combined(failure,e)
 return combined(failure,Error('stdin close repeatedly interrupted'))
def close_outputs(streams):
 return close_streams({'stdout':streams.get('stdout'),'stderr':streams.get('stderr')})
def cleanup_process(p,streams):
 """One post-spawn retirement path; callers retain both failure families."""
 if p is None:return (bytes(streams.get('stdout_data',b'')),bytes(streams.get('stderr_data',b''))),None
 try:return retire_process(p,streams),None
 except BaseException as e:return (bytes(streams.get('stdout_data',b'')),bytes(streams.get('stderr_data',b''))),e
def cleanup_owned(owner):
 streams=owner['streams']
 try:p=recover_born_owner(owner)
 except BaseException as error:return (bytes(streams.get('stdout_data',b'')),bytes(streams.get('stderr_data',b''))),error
 return cleanup_process(p,streams)
def raise_primary(primary,cleanup):
 raise combined(primary,cleanup)
def _drain(p,streams,limit,deadline):
 """Drain both callback pipes without an unbounded communicate buffer."""
 fds={}
 for k in ('stdout','stderr'):
  s=streams.get(k)
  if s is None:continue
  try:fd=s.fileno()
  except ValueError:continue # a caller may already have closed this pipe
  except (AttributeError,OSError):bad('callback pipe has no descriptor')
  if not isinstance(fd,int) or fd<0:bad('callback pipe has no descriptor')
  fds[fd]=k
 while fds:
  left=deadline-time.monotonic()
  if left<=0:break
  try:ready=select.select(list(fds),[],[],min(left,.25))[0]
  except (OSError,ValueError) as e:bad('callback pipe select: '+str(e))
  if not ready:continue
  for fd in ready:
   try:block=os.read(fd,1<<16)
   except BlockingIOError:continue
   except OSError as e:bad('callback pipe read: '+str(e))
   if not block:del fds[fd];continue
   bucket=streams[fds[fd]+'_data']
   if len(bucket)+len(block)>limit:bad('callback output cap exceeded')
   bucket.extend(block)
 return bytes(streams['stdout_data']),bytes(streams['stderr_data'])
def retire_process(p,streams=None):
 """Bounded TERM/KILL/empty proof with an unreaped session-leader anchor.

 Census and signal failures are accumulated, never exits from escalation.
 A retry may reopen the same unreaped leader; it cannot adopt a new SID.
 """
 streams=streams or {};streams.setdefault('stdout_data',bytearray());streams.setdefault('stderr_data',bytearray())
 if getattr(p,'_mckernel_retired',False) is True:return bytes(streams.get('stdout_data',b'')),bytes(streams.get('stderr_data',b''))
 if getattr(p,'_mckernel_retiring',False) is True:bad('concurrent process retirement')
 p._mckernel_retiring=True
 deferred=[];errors=[];old={};counts={'interrupts':0,'omitted_errors':0}
 def record_interrupt(error):
  counts['interrupts']+=1
  if not deferred:deferred.append(error)
 def record_error(error):
  if len(errors)<32:errors.append(error)
  else:counts['omitted_errors']+=1
 def remember(signum,frame):record_interrupt(Interrupted('signal '+str(signum)))
 def shield(fn):
  # Actual packet signals are latched by remember; this finite retry also
  # covers injected Interrupted/KeyboardInterrupt and interrupted syscalls.
  for unused in range(8):
   try:return fn()
   except (KeyboardInterrupt,Interrupted) as e:
    record_interrupt(e)
  bad('retirement operation repeatedly interrupted')
 def attempt(fn):
  try:return True,shield(fn)
  except BaseException as e:record_error(e);return False,None
 try:
  for sig in (signal.SIGINT,signal.SIGTERM):
   old[sig]=signal.getsignal(sig);attempt(lambda sig=sig:signal.signal(sig,remember))
  session=getattr(p,'_mckernel_session',None)
  if not isinstance(session,int) or session<=0:bad('process session was not recorded')
  def anchor():
   if not isinstance(getattr(p,'_mckernel_leader_fd',None),int):
    return reacquire_anchor(p)
   if getattr(p,'_mckernel_leader_starttime',None) is None:return recover_anchor(p)
   return prove_anchor(p)
  def census():
   anchor();rows=session_members(session);anchor()
   for row in rows:
    if row['pid']==session and row['starttime']!=p._mckernel_leader_starttime:bad('session incarnation changed')
   return rows
  def signal_session(sig):
   rows=shield(census)
   for row in rows:
    fd=None
    try:
     try:fd=shield(lambda:pidfd_open(row['pid']))
     except FileNotFoundError:continue # ESRCH: this specific member exited
     try:again=shield(lambda:proc_row(row['pid']))
     except FileNotFoundError:continue
     if again!=row or again['session']!=session:bad('process identity changed during pidfd admission')
     shield(anchor) # never signal a new session with the same numeric SID
     try:shield(lambda:pidfd_send(fd,sig))
     except FileNotFoundError:continue
    except BaseException as e:record_error(e)
    finally:
     if fd is not None:attempt(lambda:os.close(fd))
  def finish_if_empty():
   rows=census()
   if any(row['pid']!=session for row in rows) or observe_exit(p) is None:return False
   # The direct child is the last session member. Only now may wait reap it.
   p.wait(timeout=.1)
   if session_members(session):bad('session nonempty after leader reap')
   p._mckernel_retired=True;return True
  def direct_signal(sig):
   # A failed pidfd path never authorizes numeric group signalling. This
   # single reserved direct child is the only possible numeric fallback.
   direct_child_row(p);unreaped_child(p);os.kill(p.pid,sig)
  def finish_direct_if_empty():
   direct_child_row(p);rows=session_members(session)
   if any(row['pid']!=session for row in rows) or unreaped_child(p) is None:return False
   direct_child_row(p);p.wait(timeout=.1)
   if session_members(session):bad('uncertain fallback session survivors')
   p._mckernel_retired=True;return True
  fallback_used=False
  for sig,seconds in ((signal.SIGTERM,TERM_TIMEOUT),(signal.SIGKILL,KILL_TIMEOUT)):
   deadline=time.monotonic()+seconds
   signalled,unused=attempt(lambda:signal_session(sig))
   fallback=not signalled and not isinstance(getattr(p,'_mckernel_leader_fd',None),int)
   if fallback:
    fallback_used=True
    record_error(Error('uncertain pidfd cleanup: bounded acquisition exhausted; direct-child fallback only'))
    attempt(lambda:direct_signal(sig))
   attempt(lambda:_drain(p,streams,MAX_CALLBACK,deadline))
   ok,finished=attempt(finish_direct_if_empty if fallback else finish_if_empty)
   if ok and finished:break
   if sig==signal.SIGKILL:
    while ok and time.monotonic()<deadline:
     attempt(lambda:time.sleep(.01))
     attempt(lambda:direct_signal(signal.SIGKILL) if fallback else signal_session(signal.SIGKILL))
     ok,finished=attempt(finish_direct_if_empty if fallback else finish_if_empty)
     if ok and finished:break
  if fallback_used:
   observed,rows=attempt(lambda:session_members(session))
   record_error(Error('pidfd fallback outcome: '+json.dumps({'leader_pid':p.pid,'session':session,'retired':getattr(p,'_mckernel_retired',False) is True,'census_available':observed,'observed_numeric_session_members':rows[:32] if observed else None,'members_truncated':observed and len(rows)>32},sort_keys=True,separators=(',',':'))))
  if getattr(p,'_mckernel_retired',False) is not True:record_error(Error('uncertain child retirement'))
 except BaseException as e:record_error(e)
 finally:
  # close_anchor owns its identity-checked retry. The generic interrupt
  # shield must not retry an ambiguous close after it has refused a retry.
  try:close_anchor(p)
  except BaseException as e:record_error(e)
  p._mckernel_retiring=False
  for sig,handler in old.items():attempt(lambda sig=sig,handler=handler:signal.signal(sig,handler))
 failure=None
 if counts['omitted_errors']:errors.append(Error('additional retirement failures: '+str(counts['omitted_errors'])))
 if counts['interrupts']>1:errors.append(Error('additional retirement interruptions: '+str(counts['interrupts']-1)))
 for error in errors:failure=combined(failure,error)
 for error in reversed(deferred):failure=combined(error,failure)
 if failure is not None:raise failure
 return bytes(streams['stdout_data']),bytes(streams['stderr_data'])
def complete_process(p):
 """Accept natural completion only after anchored census and final empty proof."""
 if not isinstance(getattr(p,'pid',None),int):return p.wait() # pure test double
 rc=observe_exit(p)
 if rc is None:return None
 prove_anchor(p)
 if any(row['pid']!=p.pid for row in session_members(p._mckernel_session)):bad('process descendants survived')
 prove_anchor(p);p.wait(timeout=.1)
 if session_members(p._mckernel_session):bad('session nonempty after leader reap')
 p._mckernel_retired=True;close_anchor(p);return rc

def run_sealed_observer(fd, targets, timeout=180):
    owner = spawn_owner()
    failure = None
    status = None
    launched = None
    out = err = b''
    try:
        argv = ['/usr/bin/python3', '-E', '-s', '-B', '/proc/self/fd/' + str(fd)]
        for target in targets:
            argv.extend(('--target', str(target)))
        process, streams = owned_spawn(owner, argv, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       pass_fds=(fd,), close_fds=True, start_new_session=True)
        launched = (process.pid, process._mckernel_leader_starttime)
        out, err = _drain(process, streams, MAX_CALLBACK, time.monotonic() + timeout)
        status = complete_process(process)
        if status is None:
            fail('observer timed out')
        if status != 0:
            fail('observer returned failure')
    except BaseException as exc:
        failure = exc
    finally:
        (out, err), cleanup = cleanup_owned(owner)
        failure = combined(failure, cleanup)
        failure = combined(failure, close_streams(owner['streams']))
        failure = combined(failure, restore_spawn_mask(owner))
        process = owner['p']
        # Retirement retains the anchored leader until every session member
        # (including descendants in distinct process groups) has disappeared.
        retired = process is not None and getattr(process, '_mckernel_retired', False) is True
        survivors = None
        if process is not None:
            try:
                survivors = session_members(owner['session'])
            except BaseException as exc:
                failure = combined(failure, exc)
            status = process.returncode
        for name, data in (('observer.stdout', out), ('observer.stderr', err)):
            try:
                exclusive_bytes(OUTPUT / name, data)
            except BaseException as exc:
                failure = combined(failure, exc)
        try:
            exclusive_json(OUTPUT / 'observer.status.json',
                           {'returncode': status, 'launched': launched, 'retired': retired,
                            'no_survivors': retired and survivors == [], 'survivors': survivors,
                            'failure': None if failure is None else error_record(failure)})
        except BaseException as exc:
            failure = combined(failure, exc)
        try:
            fsync_dir(OUTPUT)
        except BaseException as exc:
            failure = combined(failure, exc)
        if failure is not None:
            try:
                exclusive_json(OUTPUT / 'observer.failure.json',
                               {'failure': error_record(failure), 'survivors': survivors})
            except BaseException as exc:
                failure = combined(failure, exc)
    if failure is not None:
        raise failure
    return exact_json(out), launched


def seal_and_run_observer(expected, admitted_boot):
    """Finalized-only descriptor seal; observer is never reopened by pathname."""
    source = checked(OBSERVER, OBSERVER_SHA)
    sealed = OUTPUT / 'observer.sealed.py'
    exclusive_bytes(sealed, source)
    read_fd = os.open(str(sealed), os.O_RDONLY | os.O_NOFOLLOW)
    failure = None
    try:
        before = os.fstat(read_fd)
        if not stat.S_ISREG(before.st_mode) or digest(b''.join(iter(lambda: os.read(read_fd, 1 << 20), b''))) != OBSERVER_SHA:
            fail('sealed observer changed')
        value, launched = run_sealed_observer(read_fd, QUARANTINES)
        if os.fstat(read_fd).st_ino != before.st_ino:
            fail('sealed observer descriptor changed')
    except BaseException as exc:
        failure = exc
    try:
        os.close(read_fd)
    except BaseException as exc:
        failure = combined(failure, exc)
    if failure is not None:
        raise failure
    validate_observer(value, expected, admitted_boot=admitted_boot, launched=launched)
    return value


def validate_capacity(statvfs=os.statvfs, meminfo='/proc/meminfo'):
    text = Path(meminfo).read_text()
    match = re.search(r'^MemAvailable:\s+(\d+)\s+kB$', text, re.M)
    if match is None or int(match.group(1)) * 1024 < FLOORS['MemAvailable']:
        fail('MemAvailable floor')
    for path, key in ((REPO, 'host_free'), (SCRATCH, 'scratch_free'), (Path('/dev/shm'), 'tmpfs_free')):
        row = statvfs(str(path))
        if row.f_bavail * row.f_frsize < FLOORS[key]:
            fail('capacity floor: ' + key)


def _proc_starttime(row):
    try:
        return int((row / 'stat').read_text().rsplit(')', 1)[1].split()[19])
    except (OSError, IndexError, ValueError) as exc:
        fail('process identity unreadable: ' + str(exc))


def _proc_cmdline_stable(row):
    try:
        before = _proc_starttime(row)
    except Error:
        if not row.exists():
            return None
        raise
    try:
        data = (row / 'cmdline').read_bytes()
    except FileNotFoundError:
        if not row.exists():
            return None
        fail('process disappearance uncertain')
    except PermissionError as exc:
        fail('process permission denied: ' + str(exc))
    except OSError as exc:
        fail('process cmdline unreadable: ' + str(exc))
    try:
        after = _proc_starttime(row)
    except Error:
        fail('process disappeared during census')
    if before != after:
        fail('process identity changed during census')
    return before, data


def _census_identity(pid, proc):
    """Read only stable identity/relationship fields, never volatile counters."""
    try:
        text = (proc / str(pid) / 'stat').read_text()
        fields = text.rsplit(')', 1)[1].split()
        if int(text.split('(', 1)[0]) != pid or len(fields) <= 19:
            fail('census process stat malformed')
        value = {'pid': pid, 'ppid': int(fields[1]), 'starttime': int(fields[19])}
        if value['ppid'] < 0 or value['starttime'] < 0:
            fail('census process stat malformed')
        return value
    except (OSError, IndexError, ValueError) as exc:
        fail('census process identity unreadable: ' + str(exc))


def _sudo_credentials(text):
    credentials = {}
    for line in text.splitlines():
        key, separator, value = line.partition(':')
        if separator and key in ('Uid', 'Gid'):
            if key in credentials:
                fail('direct sudo parent duplicate credentials')
            fields = value.split()
            if len(fields) != 4 or any(re.fullmatch('[0-9]+', item) is None for item in fields):
                fail('direct sudo parent credentials malformed')
            credentials[key] = tuple(int(item) for item in fields)
    if set(credentials) != {'Uid', 'Gid'}:
        fail('direct sudo parent credentials missing')
    return credentials


def _direct_sudo_parent(proc=Path('/proc')):
    """Admit an exact direct parent and retain both process incarnations.

    Callers must revalidate this token when applying the exemption and at
    census completion. These observations do not constitute an atomic /proc
    proof; the packet's operational exclusion remains required.
    """
    child = _census_identity(os.getpid(), proc)
    ppid = child['ppid']
    if ppid <= 0 or ppid == child['pid']:
        return None
    parent = proc / str(ppid)
    try:
        before = _census_identity(ppid, proc)
        exe = os.readlink(str(parent / 'exe'))
        cmdline = (parent / 'cmdline').read_bytes()
        credentials = _sudo_credentials((parent / 'status').read_text())
        exe_again = os.readlink(str(parent / 'exe'))
        cmdline_again = (parent / 'cmdline').read_bytes()
        credentials_again = _sudo_credentials((parent / 'status').read_text())
        after = _census_identity(ppid, proc)
        child_again = _census_identity(child['pid'], proc)
    except (OSError, IndexError, ValueError) as exc:
        fail('direct sudo parent identity unreadable: ' + str(exc))
    if (before != after or child != child_again or exe_again != exe or
            cmdline_again != cmdline or credentials_again != credentials):
        fail('direct sudo parent identity changed')
    expected = [b'/usr/bin/sudo', b'-A', b'/usr/bin/python3', b'-E', b'-s', b'-B',
                os.fsencode(str(PACKET)), b'--release', os.fsencode(str(EXECUTION_RELEASE))]
    if exe != '/usr/bin/sudo' or cmdline != b'\0'.join(expected) + b'\0':
        return None
    if credentials != {'Uid': (0, 0, 0, 0), 'Gid': (0, 0, 0, 0)}:
        return None
    return {'parent': before, 'child': child}


def _revalidate_sudo_parent(token, proc):
    if _direct_sudo_parent(proc) != token:
        fail('direct sudo parent exemption changed')


def _revalidate_census_identity(identity, proc):
    actual = _census_identity(identity['pid'], proc)
    if actual['starttime'] != identity['starttime']:
        fail('allowed process identity changed')


def _census_allowances(allowed, proc):
    result = {}
    for identity in allowed:
        if (not isinstance(identity, dict) or set(identity) != {'pid', 'starttime'} or
                type(identity['pid']) is not int or identity['pid'] <= 0 or
                type(identity['starttime']) is not int or identity['starttime'] < 0 or
                identity['pid'] in result):
            fail('allowed process identity schema')
        _revalidate_census_identity(identity, proc)
        result[identity['pid']] = dict(identity)
    own = _census_identity(os.getpid(), proc)
    own = {'pid': own['pid'], 'starttime': own['starttime']}
    if own['pid'] in result and result[own['pid']] != own:
        fail('allowed self identity changed')
    result[own['pid']] = own
    return result


def validate_conflicts(proc=Path('/proc'), boot_path=Path('/proc/sys/kernel/random/boot_id'), admitted_boot=None, allowed=(), conflict_basenames=None):
    try:
        boot = boot_path.read_text().strip()
    except OSError as exc:
        fail('boot binding unavailable: ' + str(exc))
    if not boot or admitted_boot is not None and boot != admitted_boot:
        fail('boot binding changed')
    forbidden = {'qemu-system-x86_64', 'qemu-system-aarch64', 'qemu-kvm', 'mcexec',
                 'native_rust_exact_build_container_owner.py', 'native_exact_candidate_retire.py',
                 'native_exact_candidate_quarantine_recover.py', 'native-exact-candidate-retirement-704f6654-1.py',
                 'native-exact-candidate-retirement-704f6654-2.py', 'native-exact-candidate-quarantine-recover-704f6654-1.py',
                 'native-exact-candidate-quarantine-recovery-execution-704f6654-1.sh'}
    if conflict_basenames is not None:
        if not forbidden.issubset(set(conflict_basenames)):
            fail('runtime conflict coverage')
        forbidden = set(conflict_basenames)
    allowed = _census_allowances(allowed, proc)
    direct_sudo = _direct_sudo_parent(proc)
    for row in proc.iterdir():
        if not row.name.isdigit():
            continue
        pid = int(row.name)
        # The sudo proof takes precedence even if a release also names it.
        if direct_sudo is not None and pid == direct_sudo['parent']['pid']:
            _revalidate_sudo_parent(direct_sudo, proc)
            continue
        if pid in allowed:
            _revalidate_census_identity(allowed[pid], proc)
            continue
        result = _proc_cmdline_stable(row)
        if result is None:
            continue
        _start, cmdline = result
        values = cmdline.split(b'\0')
        names = {os.path.basename(value.decode('utf-8', 'surrogateescape')) for value in values if value}
        if forbidden.intersection(names):
            fail('conflicting process or guest')
    for identity in allowed.values():
        _revalidate_census_identity(identity, proc)
    if direct_sudo is not None:
        _revalidate_sudo_parent(direct_sudo, proc)
    return boot


def validate_runtime_admission(runtime, proc=Path('/proc'), boot_path=Path('/proc/sys/kernel/random/boot_id')):
    """Release-bound boot, launcher, conflict, lease and tombstone admission."""
    required = {'boot_id', 'launcher_identities', 'conflict_basenames', 'heavy_lease_paths', 'immutable_tombstone'}
    if not isinstance(runtime, dict) or set(runtime) != required:
        fail('runtime admission schema')
    admitted_boot = boot_path.read_text().strip()
    if runtime['boot_id'] != admitted_boot or not isinstance(runtime['conflict_basenames'], list) or \
            len(runtime['conflict_basenames']) != len(set(runtime['conflict_basenames'])) or not runtime['conflict_basenames']:
        fail('runtime boot/conflict binding')
    forbidden = set(runtime['conflict_basenames'])
    if not {'qemu-system-x86_64', 'qemu-system-aarch64', 'qemu-kvm', 'mcexec'}.issubset(forbidden):
        fail('runtime conflict basename coverage')
    launchers = runtime['launcher_identities']
    if not isinstance(launchers, list) or not launchers:
        fail('runtime launcher identities')
    allowed = []
    for row in launchers:
        if (not isinstance(row, dict) or set(row) != {'pid', 'starttime'} or
                type(row['pid']) is not int or row['pid'] <= 0 or
                type(row['starttime']) is not int or row['starttime'] < 0):
            fail('runtime launcher schema')
        actual = _proc_identity_pid(row['pid'], proc)
        if actual['starttime'] != row['starttime']:
            fail('runtime launcher PID reuse')
        allowed.append(dict(row))
    leases = runtime['heavy_lease_paths']
    tomb = runtime['immutable_tombstone']
    if not isinstance(leases, list) or len(leases) != len(set(leases)) or str(TOMBSTONE) not in leases or not isinstance(tomb, dict):
        fail('runtime heavy lease binding')
    if tomb != {'path': str(TOMBSTONE), 'immutable': True, 'device': 1831, 'inode': 31474,
                'sha256': '482bdf30e7320693c338832695932fdf1be261ed081de225e4cbdaf7e4c2c123'}:
        fail('runtime immutable tombstone binding')
    for item in leases:
        if not isinstance(item, str) or not item.startswith('/'):
            fail('runtime lease path')
        if item != str(TOMBSTONE) and os.path.lexists(item):
            fail('active heavy lease')
    validate_conflicts(proc, boot_path, admitted_boot=admitted_boot, allowed=allowed,
                       conflict_basenames=runtime['conflict_basenames'])
    fd, observed = tombstone_fd()
    failure = None
    try:
        if (observed[0], observed[1], observed[7]) != (tomb['device'], tomb['inode'], tomb['sha256']):
            fail('released tombstone identity/hash mismatch')
        revalidate_tombstone(fd, observed)
    except BaseException as exc:
        failure = exc
    try:
        os.close(fd)
    except BaseException as exc:
        failure = combined(failure, exc)
    if failure is not None:
        raise failure
    return admitted_boot


def exclusive_bytes(path, data):
    fd = exclusive_fd(path)
    failure = None
    try:
        full_write(fd, data)
    except BaseException as exc:
        failure = exc
    for action in (lambda: os.fsync(fd), lambda: os.close(fd), lambda: fsync_dir(Path(path).parent)):
        try:
            action()
        except BaseException as exc:
            failure = combined(failure, exc)
    if failure is not None:
        raise failure


def exclusive_json(path, value):
    exclusive_bytes(path, (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8'))


def append_journal(fd, phase, **fields):
    data = (json.dumps(dict(phase=phase, **fields), sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    failure = None
    try:
        full_write(fd, data)
    except BaseException as exc:
        failure = exc
    try:
        os.fsync(fd)
    except BaseException as exc:
        failure = combined(failure, exc)
    if failure is not None:
        raise failure


def survivor_ledger():
    """Observed, not assumed, post-failure state for the consumed continuation."""
    def observe(path):
        try:
            info = os.lstat(str(path))
        except FileNotFoundError:
            return {'present': False}
        return {'present': True, 'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid,
                'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode), 'type': stat.S_IFMT(info.st_mode)}
    return {'claim': observe(CLAIM), 'journal': observe(JOURNAL), 'output': observe(OUTPUT),
            'originals': {str(path): observe(path) for path in ORIGINALS},
            'quarantines': {str(path): observe(path) for path in QUARANTINES}}


def merged_error(primary, errors):
    errors = [item for item in errors if item is not None]
    if not errors:
        return primary
    return Error(repr(primary) + '; cleanup failures: ' + '; '.join(repr(item) for item in errors))


def close_descriptors(descriptors):
    """Bounded explicit cleanup used after observer/journal failures."""
    failure = None
    for fd in descriptors:
        if fd is None:
            continue
        try:
            os.close(fd)
        except OSError as exc:
            failure = combined(failure, exc)
    if failure is not None:
        raise failure


def _same_member(info, wanted):
    keys = ('device', 'inode', 'uid', 'gid', 'mode', 'kind')
    # POSIX directory st_size changes as children are removed.  It is not an
    # immutable identity field; exact membership/emptiness is proved instead.
    if wanted['kind'] != 'directory':
        keys += ('size',)
    return all(member_identity(info)[key] == wanted[key] for key in keys)


def _verify_delete_entry(parentfd, name, wanted, rel):
    """Rebind name, no-follow descriptor, payload/target and identity immediately before unlink."""
    first = os.stat(name, dir_fd=parentfd, follow_symlinks=False)
    if not _same_member(first, wanted):
        fail('delete identity changed: ' + rel)
    if wanted['kind'] == 'file':
        child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parentfd)
        failure = None
        try:
            if not _same_member(os.fstat(child), wanted):
                fail('delete file descriptor changed: ' + rel)
            os.lseek(child, 0, os.SEEK_SET)
            actual = digest(b''.join(iter(lambda: os.read(child, 1 << 20), b'')))
            if actual != wanted.get('sha256'):
                fail('delete file hash changed: ' + rel)
        except BaseException as exc:
            failure = exc
        try:
            os.close(child)
        except BaseException as exc:
            failure = combined(failure, exc)
        if failure is not None:
            raise failure
    elif wanted['kind'] == 'symlink':
        target = os.readlink(name, dir_fd=parentfd)
        if target != wanted.get('target') or digest(os.fsencode(target)) != wanted.get('sha256'):
            fail('delete symlink target changed: ' + rel)
    elif wanted['kind'] != 'directory':
        fail('delete unsupported type: ' + rel)
    second = os.stat(name, dir_fd=parentfd, follow_symlinks=False)
    if not _same_member(second, wanted):
        fail('delete name rebound: ' + rel)
    return second


def delete_dirfd(fd, expected, journal, root_name, prefix=''):
    """Descriptor-relative depth-first deletion, with durable directory boundaries."""
    names = set(os.listdir(fd))
    direct = {key[len(prefix):].split('/', 1)[0] for key in expected
              if key.startswith(prefix) and key[len(prefix):]}
    if names != direct:
        fail('delete-before-proof membership')
    for name in sorted(names):
        rel = prefix + name
        wanted = expected.get(rel)
        if wanted is None:
            fail('delete-before-proof entry')
        _verify_delete_entry(fd, name, wanted, rel)
        journal('before-entry', root=root_name, path=rel)
        if wanted['kind'] == 'directory':
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            failure = None
            try:
                if not _same_member(os.fstat(child), wanted):
                    fail('delete directory descriptor changed: ' + rel)
                delete_dirfd(child, expected, journal, root_name, rel + '/')
                if os.listdir(child):
                    fail('directory not empty before rmdir: ' + rel)
            except BaseException as exc:
                failure = exc
            try:
                os.close(child)
            except BaseException as exc:
                failure = combined(failure, exc)
            if failure is not None:
                raise failure
            _verify_delete_entry(fd, name, wanted, rel)
            os.rmdir(name, dir_fd=fd)
        else:
            _verify_delete_entry(fd, name, wanted, rel)
            os.unlink(name, dir_fd=fd)
        os.fsync(fd)
        journal('after-entry', root=root_name, path=rel)


def remove_quarantine(quarantine, device, inode, members, journal):
    parent = root = None
    failure = None
    wanted = {'device': device, 'inode': inode, 'uid': 0, 'gid': 0, 'mode': 0o700, 'kind': 'directory'}
    try:
        parent = os.open(str(quarantine.parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        root = os.open(quarantine.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        if not _same_member(os.fstat(root), wanted):
            fail('root changed before deletion')
        _verify_delete_entry(parent, quarantine.name, wanted, str(quarantine))
        delete_dirfd(root, members, journal, quarantine.name)
        journal('before-root', root=str(quarantine))
        # Journal callbacks may fail or be interrupted; the final proofs belong
        # after them, immediately adjacent to the mutation.
        if os.listdir(root) or not _same_member(os.fstat(root), wanted):
            fail('root not empty or descriptor changed')
        _verify_delete_entry(parent, quarantine.name, wanted, str(quarantine))
        os.rmdir(quarantine.name, dir_fd=parent)
        os.fsync(parent)
        journal('after-root', root=str(quarantine))
    except BaseException as exc:
        failure = exc
    for fd in (root, parent):
        if fd is not None:
            try:
                os.close(fd)
            except BaseException as exc:
                failure = combined(failure, exc)
    if failure is not None:
        raise failure


class TerminalSignalLatch:
    """Two fixed slots; counts saturate and explicitly retain overflow."""
    COUNT_LIMIT = 65535

    def __init__(self):
        self.rows = self.empty()

    @staticmethod
    def empty():
        return {signal.SIGTERM: [None, 0, False], signal.SIGINT: [None, 0, False]}

    def record(self, signum):
        row = self.rows[signum]
        if row[0] is None:
            row[0] = Interrupted('signal ' + str(int(signum)))
        if row[1] < self.COUNT_LIMIT:
            row[1] += 1
        else:
            row[2] = True

    def detach(self):
        """Caller blocks TERM/INT; return exactly two slots without draining."""
        snapshot = self.rows
        self.rows = self.empty()
        return snapshot


def execute_final(execution_release):
    """One owner creates OUTPUT; every error consumes and preserves the claim."""
    draft_guard()
    historical_release = validate_authorities()
    admitted_boot = validate_runtime_admission(execution_release['runtime'])
    validate_raw_history()
    tomb_fd, tomb = tombstone_fd()
    journal_fd = None
    failure = None
    output_owned = claim_owned = False
    old_handlers = {}
    terminal_signals = TerminalSignalLatch()
    finishing = [False]
    def interrupted(signum, frame):
        if finishing[0]:
            terminal_signals.record(signum)
        else:
            raise Interrupted('signal ' + str(signum))
    def collect_signals():
        nonlocal failure
        mask = None
        snapshot = {}
        uncertain = False
        try:
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
            snapshot = terminal_signals.detach()
        except BaseException as exc:
            failure = combined(failure, exc)
            uncertain = True
        finally:
            if mask is not None:
                try:
                    signal.pthread_sigmask(signal.SIG_SETMASK, mask)
                except BaseException as exc:
                    failure = combined(failure, exc)
                    uncertain = True
        # The snapshot always has at most two entries. Arrivals after restoring
        # the mask go into the next fixed latch and cannot extend this loop.
        for sig, (first, count, overflow) in snapshot.items():
            if first is not None:
                failure = combined(failure, combined(first, Error(
                    'terminal signal counts ' + json.dumps(
                        {'signal': int(sig), 'count': count, 'overflow': overflow},
                        sort_keys=True, separators=(',', ':')))))
        return uncertain or any(row[0] is not None for row in snapshot.values())
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            old_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, interrupted)
        exclusive_json(CLAIM, {'schema': 'mckernel.quarantine-continuation-claim.v2',
                               'one_shot': True, 'retry': False, 'rollback': False,
                               'tombstone': str(TOMBSTONE)})
        claim_owned = True
        journal_fd = exclusive_fd(JOURNAL)
        append_journal(journal_fd, 'claim-created')
        os.mkdir(str(OUTPUT), 0o700)
        output_owned = True
        fsync_dir(OUTPUT.parent)
        validate_capacity()
        validate_runtime_admission(execution_release['runtime'])
        revalidate_tombstone(tomb_fd, tomb)
        expected = validate_quarantines(historical_release)
        before = docker_census()
        exclusive_json(OUTPUT / 'docker.before.json', docker_safe_summary(before))
        validate_docker(before, execution_release)
        seal_and_run_observer(expected, admitted_boot)
        after = docker_census()
        exclusive_json(OUTPUT / 'docker.after.json', docker_safe_summary(after))
        validate_docker(after, execution_release)
        append_journal(journal_fd, 'proofs-complete')
        for (_original, quarantine, device, inode), members in zip(ROOTS, expected):
            validate_runtime_admission(execution_release['runtime'])
            revalidate_tombstone(tomb_fd, tomb)
            remove_quarantine(quarantine, device, inode, members,
                              lambda phase, **row: append_journal(journal_fd, phase, **row))
        if any(os.path.lexists(str(path)) for path in ORIGINALS + QUARANTINES):
            fail('terminal root absence')
        validate_raw_history()
        revalidate_tombstone(tomb_fd, tomb)
        reopen_tombstone(tomb)
        append_journal(journal_fd, 'terminal-prepared')
    except BaseException as exc:
        failure = exc
    finishing[0] = True
    # No cleanup action can mask or prevent another cleanup action. Keep the
    # journal open until all other cleanup has been attempted.
    for action in (lambda: os.close(tomb_fd),):
        try:
            action()
        except BaseException as exc:
            failure = combined(failure, exc)
    collect_signals()
    if journal_fd is not None:
        try:
            append_journal(journal_fd, 'terminal-success' if failure is None else 'terminal-failure',
                           failure=None if failure is None else error_record(failure),
                           survivors=survivor_ledger())
        except BaseException as exc:
            failure = combined(failure, exc)
        collect_signals()
        for action in (lambda: os.fsync(journal_fd), lambda: os.close(journal_fd)):
            try:
                action()
            except BaseException as exc:
                failure = combined(failure, exc)
            collect_signals()
    # A separate terminal record is written only after all descriptor cleanup.
    # A failure after a success journal entry therefore changes the outcome.
    if output_owned:
        try:
            exclusive_json(OUTPUT / 'terminal.json',
                           {'status': 'PASS' if failure is None else 'FAIL_RETAINED',
                            'failure': None if failure is None else error_record(failure),
                            'survivors': survivor_ledger()})
        except BaseException as exc:
            failure = combined(failure, exc)
        collect_signals()
    if failure is not None:
        # Independent failure sinks: failure of either must not skip the other.
        for path in ((OUTPUT / 'terminal-failure.json',) if output_owned else ()) + (
                SCRATCH / 'native-exact-candidate-quarantine-recovery-704f6654-1.survivors.json',):
            try:
                exclusive_json(path, {'status': 'FAIL_RETAINED', 'failure': error_record(failure),
                                      'survivors': survivor_ledger(), 'claim_created': claim_owned})
            except BaseException as exc:
                failure = combined(failure, exc)
            collect_signals()
    # This is the sole signal-restoration boundary. Block TERM/INT while
    # reconciling pending delivery with the latched handler and durable record.
    # No old/default handler is restored while terminal persistence is active.
    signals = {signal.SIGTERM, signal.SIGINT}
    previous_mask = None
    try:
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, signals)
    except BaseException as exc:
        failure = combined(failure, exc)
    settled = False
    needs_record = failure is not None
    for attempt in range(8):
        if previous_mask is not None:
            try:
                for sig in sorted(signal.sigpending() & signals):
                    event = signal.sigtimedwait({sig}, 0)
                    if event is not None:
                        terminal_signals.record(event.si_signo)
            except BaseException as exc:
                failure = combined(failure, exc)
                needs_record = True
        observed_signals = collect_signals()
        if not observed_signals and not needs_record:
            settled = True
            break
        # Fresh names retain each earlier terminal snapshot. If another signal
        # arrives during this write it remains blocked and is recorded next.
        path = (OUTPUT if output_owned else SCRATCH) / (
            'native-exact-candidate-quarantine-recovery-704f6654-1.terminal-signal-%d.json' % attempt)
        try:
            exclusive_json(path, {'status': 'FAIL_RETAINED', 'failure': error_record(failure),
                                  'survivors': survivor_ledger()})
            needs_record = False
        except BaseException as exc:
            failure = combined(failure, exc)
            needs_record = True
    if not settled:
        # A persistent signal storm cannot authorize restoration to a default
        # exit handler before persistence. The CLI exits with TERM/INT blocked.
        raise combined(failure, Error('terminal signal persistence did not settle; mask retained'))
    for sig, handler in old_handlers.items():
        try:
            signal.signal(sig, handler)
        except BaseException as exc:
            failure = combined(failure, exc)
    if previous_mask is not None:
        try:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        except BaseException as exc:
            failure = combined(failure, exc)
    if failure is not None:
        raise failure
    return 0


def run_released(release_path):
    draft_guard()
    release = admit_execution_release(release_path)
    return execute_final(release)


def main(argv=None):
    draft_guard()
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', required=True)
    args = parser.parse_args(argv)
    run_released(args.release)
    return 0


if __name__ == '__main__':
    sys.exit(main())
