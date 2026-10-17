#!/usr/bin/env python3
"""Source-only scratch22-authority3 build-release template; no authority is embedded here.

An external, digest-bound independent execution release must bind the actual
prepared artifacts, prerequisites, live identities and this exact source. Only
the dispatcher may invoke --execute after that review. Never replay scratch21.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import time

REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
SELF = 'scripts/native_exact_scratch22_authority3_build_wrapper.py'
TEST = 'scripts/tests/test_native_exact_scratch22_authority3_build_wrapper.py'
ADAPTER = 'scripts/prepare_native_exact_scratch22_authority3.py'
# Source candidate only. Actual adapter/repair/cleanup/recovery contracts must be
# integrated and independently reviewed before a new source release can change
# these values. No CLI option, environment variable or release JSON enables it.
EXECUTION_ENABLED = False
ADAPTER_SHA256 = '1f6aa36d4cf64d03ea62989248ed522b8575b1ab56d66cc66c211e9a8260fbf5'
ANCESTOR = 'docs/verification/evidence/native-exact-candidate-delta-preparation-scratch18-20261001.py'
CANDIDATE = ROOT / 'mckernel-exact-candidate-scratch-22-authority3'
PREP = ROOT / 'native-exact-delta-request-scratch-22-authority3.json'
MANIFEST = ROOT / 'native-exact-inputs-scratch-22-authority3.json'
EXECUTION = ROOT / 'native-exact-build-request-scratch-22-authority3.execution.json'
WRAPPER = CANDIDATE / 'scripts/native_rust_exact_disk_build_wrapper.py'
OUTPUT = ROOT / 'mckernel-exact-candidate-scratch-22-authority3-output'
EVIDENCE = ROOT / 'mckernel-exact-candidate-scratch-22-authority3-evidence'
LEASE = ROOT / 'native-exact-build-lease-scratch-22-authority3.json'
# This retained name is the exact candidate owner's ABI, not a reused request.
EXCLUSION = ROOT / 'native-exact-candidate-operational-exclusion-scratch18.json'
SHARED = ROOT / 'mckernel-heavy-operation.lock'
LOCK = Path('/run/lock/mckernel-development.lock')
STDOUT = ROOT / 'native-exact-scratch-22-authority3-heavy-build.stdout'
STDERR = ROOT / 'native-exact-scratch-22-authority3-heavy-build.stderr'
TERMINAL = ROOT / 'native-exact-scratch-22-authority3-heavy-build.terminal.json'
QUARANTINE = ROOT / 'native-exact-scratch-22-authority3-heavy-build.root-lock-quarantine.json'
PREP_TERMINAL = ROOT / 'native-exact-candidate-delta-preparation-scratch-22-authority3-terminal.json'
PREP_LOG = ROOT / 'native-exact-candidate-delta-preparation-scratch-22-authority3.log'
LIMITS = dict(NanoCpus=4000000000, CpusetCpus='2-5', Memory=12 * 2**30,
              MemorySwap=12 * 2**30, PidsLimit=512, NetworkMode='none')
MAX_CAPTURE = 16 << 20
MAX_LARGE_CAPTURE = 128 << 20
FLAGS = dict(preparation_only=True, executable=False,
             execution_released=False, release_required=True)
DEFERRED_SIGNALS = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM, signal.SIGQUIT)


class Refusal(RuntimeError):
    pass


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode() + b'\n'


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refusal('duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refusal('nonfinite JSON')))


def stable_regular(path, expected=None, maximum=MAX_CAPTURE):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise Refusal('noncanonical file path')
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise Refusal('invalid regular file: ' + str(path))
        raw = bytearray()
        while len(raw) <= before.st_size:
            block = os.read(fd, min(65536, before.st_size + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_uid,
                              s.st_gid, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if (identity(before) != identity(os.fstat(fd)) or
                identity(before) != identity(os.stat(path, follow_symlinks=False)) or
                len(raw) != before.st_size):
            raise Refusal('file changed during read: ' + str(path))
        raw = bytes(raw)
        if expected is not None and sha(raw) != expected:
            raise Refusal('hash mismatch: ' + str(path))
        return raw
    finally:
        os.close(fd)


def exact_sha(value, length=64):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{%d}' % length, value):
        raise Refusal('exact external digest required')
    return value


def require_released_adapter():
    if EXECUTION_ENABLED is not True or ADAPTER_SHA256 is None:
        raise Refusal('NOT_RELEASED: actual authority3 adapter, repair and cleanup/recovery bindings required')
    stable_regular(REPO / ADAPTER, exact_sha(ADAPTER_SHA256), 1 << 20)


def stable_large_capture(path, expected=None):
    """Large stream/terminal evidence only; authority/source defaults stay small."""
    return stable_regular(path, expected, maximum=MAX_LARGE_CAPTURE)


def bound_json(pointer):
    raw = stable_regular(Path(pointer['path']), exact_sha(pointer['sha256']), 1 << 20)
    value = strict(raw)
    if not isinstance(value, dict):
        raise Refusal('authority object required')
    return value


def git(args, cwd=REPO):
    env = dict(PATH='/usr/bin:/bin', HOME='/nonexistent', LANG='C', LC_ALL='C',
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_SYSTEM='/dev/null',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_NO_REPLACE_OBJECTS='1', GIT_TERMINAL_PROMPT='0')
    result = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-C', str(cwd), *args],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if result.returncode:
        raise Refusal('Git binding failed')
    return result.stdout


def bind_release(path, checksum, commit):
    release = bound_json(dict(path=str(path), sha256=checksum))
    exact_sha(commit, 40)
    if (release.get('schema') != 'scratch22-authority3.build-execution-release.v1' or
            release.get('status') != 'PASS_EXECUTION_RELEASE' or
            release.get('attempt') != 'scratch22-authority3' or
            type(release.get('execution_count')) is not int or release['execution_count'] != 1):
        raise Refusal('fresh scratch22-authority3 one-shot execution release required')
    ref = release['fetched_ref']
    if not isinstance(ref, str) or not ref.startswith('refs/remotes/origin/'):
        raise Refusal('fetched origin ref required')
    if git(['rev-parse', '--verify', ref + '^{commit}']).decode().strip() != commit:
        raise Refusal('release commit is not fetched ref')
    paths = [SELF, TEST, ADAPTER, ANCESTOR]
    release_rel = Path(path).relative_to(REPO).as_posix()
    paths.append(release_rel)
    for rel in paths:
        if git(['show', commit + ':' + rel]) != stable_regular(REPO / rel):
            raise Refusal('release blob mismatch: ' + rel)
    for rel in (SELF, TEST, ADAPTER, ANCESTOR):
        if sha(stable_regular(REPO / rel)) != release['source_sha256'][rel]:
            raise Refusal('released source hash mismatch: ' + rel)
    review = bound_json(release['execution_review'])
    payload = {key: value for key, value in release.items() if key != 'execution_review'}
    if (review.get('decision') != 'PASS_EXECUTION' or
            review.get('implementation_ownership') is not False or
            not release.get('author') or not review.get('reviewer') or
            review['reviewer'] == release['author'] or
            review.get('reviewed_release_payload_sha256') != sha(canonical(payload))):
        raise Refusal('independent exact prepared-artifact/execution review required')
    return release


def identity(meta):
    return dict(device=meta.st_dev, inode=meta.st_ino, uid=meta.st_uid,
                gid=meta.st_gid, mode=stat.S_IMODE(meta.st_mode), nlink=meta.st_nlink)


def acquire_development_lock(release):
    fd = os.open(str(LOCK), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        meta = os.fstat(fd)
        if (not stat.S_ISREG(meta.st_mode) or identity(meta) != release['live_binding']['root_lock'] or
                identity(os.stat(LOCK, follow_symlinks=False)) != identity(meta)):
            raise Refusal('development lock identity mismatch')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def bound_artifact(release, key, expected_path):
    pointer = release['artifacts'][key]
    if pointer['path'] != str(expected_path):
        raise Refusal('fresh artifact path mismatch: ' + key)
    raw = stable_regular(expected_path, exact_sha(pointer['sha256']))
    if identity(os.stat(expected_path, follow_symlinks=False)) != pointer['identity']:
        raise Refusal('artifact identity mismatch: ' + key)
    return raw


def adapter_module():
    spec = importlib.util.spec_from_file_location('_scratch22-authority3_build_preparation', REPO / ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def derive(prepared, expected_sha256):
    if any(prepared.get(key) is not value for key, value in FLAGS.items()):
        raise Refusal('prepared flags mismatch')
    result = dict(prepared)
    result.update(preparation_only=False, executable=True,
                  execution_released=True, release_required=False)
    raw = canonical(result)
    if sha(raw) != exact_sha(expected_sha256):
        raise Refusal('derived request mismatch')
    return result, raw


def preflight(release):
    adapter = adapter_module()
    preparation = bound_json(release['preparation_release'])
    if (preparation.get('schema') != 'scratch22-authority3.preparation-release.v1' or
            preparation.get('status') != 'PASS_PREPARATION_EXECUTION_RELEASE' or
            preparation.get('attempt') != 'scratch22-authority3' or
            preparation.get('execution_released') is not False):
        raise Refusal('actual scratch22-authority3 preparation execution authority required')
    # Consume the actual producer contracts, without normalizing their statuses.
    adapter.validate_cleanup(preparation)
    adapter.validate_authority1_retirement(preparation)
    adapter.validate_authority2_retirement(preparation)
    adapter.validate_source_authority(REPO, preparation)
    adapter.validate_authority_review(REPO, preparation)
    # The preparation controller may now be an ancestor of the build checkpoint.
    # Recheck its exact immutable blobs, not its historical HEAD observation.
    controller = exact_sha(preparation['controller'], 40)
    keys = {'script_sha256': ADAPTER, 'tests_sha256': 'scripts/tests/test_prepare_native_exact_scratch22_authority3.py',
            'ancestor_sha256': ANCESTOR}
    reviewed = {}
    for key, rel in keys.items():
        reviewed[key] = sha(stable_regular(REPO / rel))
        if reviewed[key] != preparation[key] or sha(git(['show', controller + ':' + rel])) != reviewed[key]:
            raise Refusal('original preparation controller source mismatch')
    reviewed.update({key + '_sha256': preparation[key]['sha256'] for key in
                    ('cleanup', 'cleanup_release', 'cleanup_postflight', 'source_checks', 'source_review',
                     'authority_review', 'repair_review', 'authority1_recovery',
                     'authority1_recovery_review', 'authority1_cleanup', 'authority1_cleanup_review',
                     'current_source_checks', 'authority2_terminal', 'authority2_receipt',
                     'authority2_cleanup', 'authority2_cleanup_review')})
    prep_review = bound_json(preparation['preparation_review'])
    if (prep_review.get('decision') != 'PASS_PREPARATION_EXECUTION' or
            not preparation.get('author') or not prep_review.get('reviewer') or
            prep_review['reviewer'] == preparation['author'] or
            prep_review.get('implementation_ownership') is not False or
            prep_review.get('reviewed_inputs_sha256') != reviewed or
            prep_review.get('target') != preparation['target'] or
            prep_review.get('target_tree') != preparation['target_tree']):
        raise Refusal('original preparation execution review mismatch')
    if (release['candidate_sha'] != preparation['target'] or
            release['candidate_tree'] != preparation['target_tree']):
        raise Refusal('prepared candidate source mismatch')
    adapter.live_preparation_boundary(ROOT, dict(live_binding=release['live_binding']))
    if identity(os.stat(CANDIDATE, follow_symlinks=False)) != release['live_binding']['candidate']:
        raise Refusal('candidate directory identity mismatch')
    for revision, expected in (('HEAD', release['candidate_sha']), ('HEAD^{tree}', release['candidate_tree'])):
        if git(['rev-parse', '--verify', revision], CANDIDATE).decode().strip() != expected:
            raise Refusal('candidate Git binding mismatch')
    prepared_raw = bound_artifact(release, 'prepared_request', PREP)
    prepared = strict(prepared_raw)
    if prepared_raw != canonical(prepared):
        raise Refusal('prepared request is not canonical')
    terminal = strict(bound_artifact(release, 'preparation_terminal', PREP_TERMINAL))
    prep_log = bound_artifact(release, 'preparation_log', PREP_LOG)
    if (terminal.get('phase') != 'complete' or terminal.get('returncode') != 0 or
            terminal.get('exception') is not None or terminal.get('preparation_only') is not True or
            terminal.get('log') != str(PREP_LOG) or terminal.get('log_sha256') != sha(prep_log)):
        raise Refusal('actual preparation terminal/log incomplete')
    required = dict(source_root=str(CANDIDATE), input_manifest=str(MANIFEST),
                    output_root=str(OUTPUT), evidence_root=str(EVIDENCE), lease_path=str(LEASE),
                    candidate_sha=release['candidate_sha'], image_id=release['image_id'],
                    operational_exclusion_path=str(EXCLUSION), operational_exclusion_consumed=False,
                    limits=LIMITS, timeout=19800)
    if any(prepared.get(key) != value for key, value in required.items()):
        raise Refusal('prepared runtime/source profile mismatch')
    if prepared.get('operational_exclusion_consumed') is not False:
        raise Refusal('prepared exclusion was already consumed')
    if (type(prepared.get('host_floor')) is not int or prepared['host_floor'] < 16 * 2**30 or
            type(prepared.get('scratch_floor')) is not int or prepared['scratch_floor'] < 12 * 2**30 or
            prepared.get('launcher_aggregate_memory_gib') != release['launcher_aggregate_memory_gib']):
        raise Refusal('prepared resource floors/budget mismatch')
    for key, path, request_key in (
            ('manifest', MANIFEST, 'input_manifest'),
            ('owner', CANDIDATE / 'scripts/native_rust_exact_build_container_owner.py', 'owner_path'),
            ('driver', CANDIDATE / 'scripts/native_rust_exact_build_offline.py', 'driver_path')):
        raw = bound_artifact(release, key, path)
        if prepared.get(request_key) != str(path) or prepared.get(request_key + '_sha256') != sha(raw):
            raise Refusal('prepared authenticated input mismatch: ' + key)
    bound_artifact(release, 'disk_wrapper', WRAPPER)
    adapter.validate_prepared_request(CANDIDATE, PREP)
    for key, path in (('output', OUTPUT), ('evidence', EVIDENCE)):
        fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            if (identity(os.fstat(fd)) != release['live_binding'][key] or os.listdir(fd) or
                    identity(os.stat(path, follow_symlinks=False)) != identity(os.fstat(fd))):
                raise Refusal('fresh output/evidence directory mismatch')
        finally:
            os.close(fd)
    for path in (EXECUTION, LEASE, EXCLUSION, SHARED, STDOUT, STDERR, TERMINAL, QUARANTINE):
        if os.path.lexists(path):
            raise Refusal('fresh path occupied: ' + str(path))
    return derive(prepared, release['derived_request_sha256'])


def publish(path, raw, expected_sha256=None, *, maximum=MAX_CAPTURE):
    if maximum not in (MAX_CAPTURE, MAX_LARGE_CAPTURE) or len(raw) > maximum:
        raise Refusal('publication exceeds finite capture bound')
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            if count <= 0:
                raise Refusal('short publication')
            offset += count
        os.fsync(fd)
    finally:
        os.close(fd)
    if stable_regular(path, expected_sha256 or sha(raw), maximum=maximum) != raw:
        raise Refusal('published bytes changed')


def run_checked(command, lockfd):
    outfd = errfd = None
    try:
        outfd = os.open(str(STDOUT), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        errfd = os.open(str(STDERR), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        # No outer timeout: only the authenticated owner may retire its container.
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=outfd, stderr=errfd,
                                close_fds=True, pass_fds=(lockfd,),
                                env=dict(PATH='/usr/bin:/bin', HOME='/home/holden', LANG='C', LC_ALL='C',
                                         SUDO_ASKPASS=os.environ.get('SUDO_ASKPASS', '')))
        os.fsync(outfd)
        os.fsync(errfd)
        return result.returncode
    finally:
        for fd in (outfd, errfd):
            if fd is not None:
                os.close(fd)


def retirement_proven(result):
    return (isinstance(result, dict) and result.get('retired') is True and
            result.get('client_retirement_unproven') is not True and
            result.get('cleanup_separately_required') is True and
            result.get('terminal_container_retained') is True and
            result.get('terminal_container_info') is not None and
            result.get('terminal_container_info_current') is True)


def quarantine_wait():
    while True:
        try:
            time.sleep(60)
        except BaseException:
            # Interrupted waits and diagnostic failures cannot surrender the lock.
            # SIGKILL cannot preserve a live flock; persistent exclusions survive.
            pass


def quarantine_root_lock(lockfd, reason):
    try:
        record = dict(schema='scratch22-authority3.root-lock-quarantine.v1', status='QUARANTINED',
                      pid=os.getpid(), reason=reason, root_lock=identity(os.fstat(lockfd)),
                      starttime=Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19],
                      boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        if not os.path.lexists(QUARANTINE):
            publish(QUARANTINE, canonical(record))
    except BaseException:
        # No evidence or stdout failure can release an uncertain live owner.
        pass
    quarantine_wait()


def execute(path, checksum, commit):
    require_released_adapter()
    release = bind_release(path, checksum, commit)
    requested, old_handlers = [], {}
    lockfd = None
    build_started, safe_to_release = False, True
    def defer(signum, _frame):
        if not requested:
            requested.append(signum)
    # Install all ordinary termination handlers atomically before ownership or
    # mutation. Restore the caller mask before spawning the canonical child so
    # its signal behavior and requested[] reporting remain unchanged.
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, DEFERRED_SIGNALS)
    try:
        for signum in DEFERRED_SIGNALS:
            old_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, defer)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        lockfd = acquire_development_lock(release)
        request, raw = preflight(release)
        base = ['/usr/bin/python3', '-B', str(WRAPPER), str(PREP),
                '--launcher-aggregate-gib', release['launcher_aggregate_memory_gib']]
        for options, status in ((['--validate-only'], 'PASS_COMPATIBILITY_ONLY'),
                                (['--census-only', '--request-sha256',
                                  release['artifacts']['prepared_request']['sha256']], 'PASS_READ_ONLY')):
            checked = subprocess.run(base + options, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
            if checked.returncode or strict(checked.stdout).get('status') != status:
                raise Refusal('read-only compatibility/census refused')
        if requested:
            raise Refusal('signal received before request publication')
        request2, raw2 = preflight(release)
        if request2 != request or raw2 != raw or requested:
            raise Refusal('preflight changed or signal received')
        publish(EXECUTION, raw, release['derived_request_sha256'])
        if requested:
            raise Refusal('signal received during request publication; request retained')
        build_started, safe_to_release = True, False
        code = run_checked(['/usr/bin/python3', '-B', str(WRAPPER), str(EXECUTION),
                            '--launcher-aggregate-gib', release['launcher_aggregate_memory_gib']], lockfd)
        stdout, stderr = stable_large_capture(STDOUT), stable_regular(STDERR)
        try:
            result = strict(stdout.strip().splitlines()[-1])
        except (IndexError, ValueError, TypeError) as exc:
            raise Refusal('wrapper terminal output malformed') from exc
        terminal = dict(schema='scratch22-authority3.heavy-build-terminal.v1', release_commit=commit,
                        release_sha256=checksum, request_sha256=release['derived_request_sha256'],
                        returncode=code, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr),
                        deferred_signals=requested, wrapper_result=result)
        publish(TERMINAL, canonical(terminal), maximum=MAX_LARGE_CAPTURE)
        safe_to_release = retirement_proven(result)
        if not safe_to_release:
            raise Refusal('terminal retirement is uncertain')
        if code or result.get('status') != 'PASS':
            raise Refusal('heavy build failed after positive retirement')
        if os.path.lexists(LEASE) or not all(os.path.lexists(p) for p in (EXCLUSION, SHARED)):
            raise Refusal('terminal lease/exclusion retention mismatch')
        if requested:
            raise Refusal('signal received during build; retirement preserved')
        return dict(status='PASS_EXECUTED', release_commit=commit, release_sha256=checksum,
                    request_sha256=release['derived_request_sha256'], wrapper_result=result,
                    terminal_sha256=sha(stable_large_capture(TERMINAL)))
    finally:
        if lockfd is not None:
            if build_started and not safe_to_release:
                quarantine_root_lock(lockfd, 'build-started-without-positive-terminal-retirement')
            fcntl.flock(lockfd, fcntl.LOCK_UN)
            os.close(lockfd)
        signal.pthread_sigmask(signal.SIG_BLOCK, DEFERRED_SIGNALS)
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--release-sha256', required=True)
    parser.add_argument('--release-commit', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        if not args.execute:
            raise Refusal('--execute and fresh independent release required')
        print(json.dumps(execute(args.release, args.release_sha256, args.release_commit), sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps(dict(status='REFUSED', reason=str(exc)), sort_keys=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
