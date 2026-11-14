#!/usr/bin/env python3
"""One crate-only case using the existing exact compiler-owner transport.

No image build, module install or guest occurs here. The exact accepted SDK
selfretirement path removes only the verified stopped CID and releases its
three archived records; all source/work/output/evidence is retained.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import stat
import sys
import time
import types
from pathlib import Path

def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()

def need(value, message):
    if not value:
        raise RuntimeError(message)

def bound(row):
    path = Path(row['path'])
    need(path.is_absolute() and path.is_file() and not path.is_symlink(), 'regular bound input')
    need(path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], 'bound input drift')
    return path

def run(request, engine, retirement, authority_request):
    # Actual accepted shared heavy exclusion is acquired before owner resources.
    shared_path, shared_record = engine._SHARED_HEAVY_ENTRY_CONTRACT.acquire_heavy_operation(request, 'build')
    state = json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())
    usage = {'phase': state.get('phase'), 'pause_reason': state.get('pause_reason'),
             'usedPercent': state.get('last_rate_limits', {}).get('primary', {}).get('usedPercent')}
    need(usage['phase'] == 'running' and not usage['pause_reason'] and
         isinstance(usage['usedPercent'], (int, float)) and usage['usedPercent'] < 100, 'usage admission')
    free = {key: os.statvfs(path).f_bavail * os.statvfs(path).f_frsize for key, path in
            [('host', '/home/holden'), ('scratch', '/home/holden/mckernel-work/scratch')]}
    growth = request['disk_budget_bytes'] + request['capture_budget_bytes'] + request['emergency_reserve_bytes']
    need(free['host'] >= 16 * 2**30 + growth and free['scratch'] >= 12 * 2**30 + growth, 'storage floors and growth')
    ram = int(next(row.split()[1] for row in Path('/proc/meminfo').read_text().splitlines()
                   if row.startswith('MemAvailable:'))) * 1024
    need(ram >= 18 * 2**30, '12GiB compiler plus 2GiB controller plus 4GiB host reserve')
    source_path = bound(request['source'])
    manifest = json.loads(source_path.read_bytes())
    source = Path(request['mounts'][0]['source'])
    for row in manifest['rows']:
        path = source / row['relative']
        need(path.is_file() and not path.is_symlink() and path.stat().st_size == row['bytes'] and
             digest(path) == row['sha256'], 'complete current source closure drift')
    for key in ['driver', 'commands', 'provider', 'capture_helpers']:
        bound(request[key])
    driver_inspection = types.ModuleType('_crate_object_inspection')
    driver_inspection.__file__ = request['driver']['path']
    exec(compile(Path(request['driver']['path']).read_bytes(), request['driver']['path'], 'exec'), driver_inspection.__dict__)
    capture_inspection = types.ModuleType('_accepted_stream_inspection')
    capture_inspection.__file__ = request['capture_helpers']['path']
    exec(compile(Path(capture_inspection.__file__).read_bytes(), capture_inspection.__file__, 'exec'), capture_inspection.__dict__)
    expected_commands = json.loads(Path(request['commands']['path']).read_bytes())
    provider = json.loads(Path(request['provider']['path']).read_bytes())
    bound(provider['rustc'])
    old_path = Path(request['compiler_basis_request']['path'])
    need(digest(old_path) == request['compiler_basis_request']['sha256'], 'compiler basis request drift')
    basis = json.loads(old_path.read_bytes())
    nightly = next(row for row in basis['toolchain_roots'] if row['container_path'] == '/nightly')
    need(nightly['host_path'] == provider['nightly_root'], 'same accepted nightly root')
    # This is tool input validation at execution, never cached source/ABI output.
    for relative, row in nightly['inventory'].items():
        if row.get('type') == 'file':
            path = Path(nightly['host_path']) / relative
            need(path.is_file() and not path.is_symlink() and path.stat().st_size == row['size'] and
                 digest(path) == row['sha256'], 'accepted nightly closure drift')
    evidence = Path(request['owner_evidence_root'])
    need(not evidence.exists(), 'fresh owner evidence')
    work = Path(request['work_root'])
    need({path.name for path in work.iterdir()} == {'output', 'home', 'tmp'} and
         all(path.is_dir() and not any(path.iterdir()) for path in work.iterdir()), 'fresh configured work roots')
    common = engine.CommonExclusion(request['common_exclusion_path'], request)
    common.acquire()
    evidence.mkdir(mode=0o700)
    lease = engine.Lease(request['lease_path'], request['container_name'])
    lease.acquire()
    receipt = {'schema': 'mckernel.current-guest-fullcrate-owner-receipt.v1', 'status': 'FAIL',
               'scope': 'two complete current Rust crate objects only', 'image_or_guest_acceptance': False,
               'container_name': request['container_name'], 'owner_nonce': request['nonce'],
               'container_id': None, 'cleanup_separately_required': True,
               'terminal_container_retained': False, 'terminal_container_info': None,
               'terminal_container_info_current': False,
               'shared_heavy_operation': {'path': str(shared_path), 'record': shared_record},
               'common_exclusion': {'path': str(common.path), 'record': common.record},
               'lease': {'path': str(lease.path), 'record': lease.record},
               'admission': {'usage': usage, 'free': free, 'MemAvailable': ram, 'time_ns': time.time_ns()}}
    attempted = False
    with engine.Signals() as signals:
        docker = retirement.ExternalDocker(evidence / 'docker.log', signals, sudo=True)
        try:
            image = json.loads(docker.call(['image', 'inspect', request['image_id']]).stdout)[0]
            need(image.get('Id') == request['image_id'] and image.get('Architecture') == 'amd64', 'actual pinned compiler image')
            attempted = True
            created = docker.call(request['create_argv'])
            receipt['container_id'] = created.stdout.strip()
            info = engine._inspect(docker, request['container_name'])
            need(info.get('Id') == receipt['container_id'], 'exact created CID')
            mounts = [(Path(row['source']), row['target'], row['readonly']) for row in request['mounts']]
            engine._check_profile(info, request['image_id'], request['nonce'], mounts,
                                  request['command'], '1000:1000')
            docker.call(['start', request['container_name']])
            waited = docker.call(['wait', request['container_name']], timeout=request['timeout_seconds'])
            receipt['wait_exit_code'] = int(waited.stdout.strip())
            need(receipt['wait_exit_code'] == 0, 'crate driver failed; preserved first compiler diagnostics')
            result_path = work / 'output/build/current-guest-control-fullcrate-1/result.json'
            result = json.loads(result_path.read_bytes())
            need(result.get('status') == 'CRATE_OBJECT_COMPILE_PASS' and
                 result.get('source_identity') == manifest['source_identity'] and
                 result.get('image_or_guest_acceptance') is False and
                 len(result.get('commands', [])) == len(result.get('artifacts', [])) == 2 and
                 all(row.get('exit_code') == 0 and row.get('direct_wait') is True and
                     row.get('owned_process_group_absent') is True for row in result['commands']),
                 'two real complete crate results and direct retirement')
            for actual, expected in zip(result['commands'], expected_commands):
                need(actual['argv'] == expected['argv'] and actual['cwd'] == expected['cwd'] and
                     actual['child']['argv'] == expected['argv'] and actual['child']['starttime'] and
                     actual['child']['pid'] == actual['child']['process_group'], 'exact compiler command and start identity')
                for stream in actual['streams'].values():
                    path = work / Path(stream['path']).relative_to('/work')
                    current = capture_inspection.hashed(path, 32*2**20)
                    stable = {key: value for key, value in current.items() if key not in ('path', 'sha256')}
                    need(stream['closed'] is True and stable == stream['stable_fd'] and
                         current['size'] == stream['bytes'] and current['sha256'] == stream['sha256'] and
                         stream['stable_fields'] == list(capture_inspection.FIELDS),
                         'closed compiler stream stable9 FD fields and bytes')
            for relative, row in zip(request['expected_artifacts'], result['artifacts']):
                path = work / relative
                need(path.is_file() and not path.is_symlink() and path.stat().st_size == row['bytes'] > 0 and
                     digest(path) == row['sha256'], 'actual crate object bytes')
                parsed = driver_inspection.object_info(path)
                parsed['path'] = '/work/' + relative
                need(parsed == row, 'actual ELF64 x86-64 ET_REL and five emitted internal symbols')
            receipt['driver_result'] = result
            receipt['status'] = 'PASS'
        except BaseException as error:
            receipt['error'] = repr(error)
        finally:
            signals.cleaning = True
            if attempted:
                try:
                    terminal = engine._retire(docker, request['container_name'], request['nonce'])
                    actual_cid = terminal.get('Id')
                    need(isinstance(actual_cid, str) and len(actual_cid) == 64 and
                         all(char in '0123456789abcdef' for char in actual_cid) and
                         terminal.get('Image') == request['image_id'] and
                         (receipt['container_id'] is None or actual_cid == receipt['container_id']) and
                         terminal.get('State', {}).get('OOMKilled') is False, 'exact terminal compiler container')
                    receipt['container_id'] = actual_cid
                    receipt.update(terminal_container_retained=True,
                                   terminal_container_info=terminal, terminal_container_info_current=True)
                    docker.call(['logs', request['container_name']], check=False)
                except BaseException as error:
                    receipt['status'] = 'FAIL'
                    receipt['retirement_error'] = repr(error)
            try:
                receipt['client_count_before_cleanup'] = retirement.positive_clients(docker, evidence)
                if attempted:
                    need(receipt['terminal_container_retained'] is True and
                         receipt['terminal_container_info_current'] is True, 'stopped exact CID before removal')
                    removed = docker.call(['rm', receipt['container_id']], timeout=30)
                    need(removed.stdout.strip() == receipt['container_id'], 'exact owned terminal removal result')
                empty = retirement.absence(docker, request['container_name'], request['nonce'], receipt['container_id'])
                receipt['client_count'] = retirement.positive_clients(docker, evidence)
                proof = {'schema': 'mckernel.current-guest-fullcrate.postflight.v1',
                         'container_absent': True, 'all_clients_reaped': True, 'absence': empty,
                         'compiler_status': receipt['status'], 'client_group_checks': list(docker.group_checks)}
                retirement.guard._write_json(evidence / 'postflight-proof.json', proof)
                authority = {'request': authority_request, 'source_sha256': {
                    'crate_owner': digest(__file__), 'crate_driver': request['driver']['sha256'],
                    'retirement_transport': request['retirement_transport']['sha256'],
                    'image_transport': request['existing_transport']['image_owner']['sha256'],
                    'capture_helpers': request['capture_helpers']['sha256']}}
                retirement.release_owned_records(request,
                    {Path(request['lease_path']): lease.record, Path(request['common_exclusion_path']): common.record,
                     Path(shared_path): shared_record}, evidence, proof, authority)
                receipt.update(cleanup_status='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE', retired=True,
                               cleanup_separately_required=False, terminal_container_retained=False,
                               terminal_container_info=None, terminal_container_info_current=True, postflight=proof)
            except BaseException as error:
                receipt.update(status='FAIL', cleanup_status='UNCERTAIN_RECORDS_RETAINED',
                               retirement_error=repr(error), retired=False)
            receipt['client_group_checks'] = list(docker.group_checks)
            receipt['client_retirement_unproven'] = docker.client_retirement_unproven
            if docker.client_retirement_unproven:
                receipt['status'] = 'FAIL'
            engine._exclusive_json(evidence / 'owner-receipt.json', receipt)
    # Accepted SDK archive/readback/authorized release handles only these records.
    return 0 if receipt['status'] == 'PASS' else 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--request-sha256', required=True)
    parser.add_argument('--release', required=True)
    parser.add_argument('--release-sha256', required=True)
    args = parser.parse_args()
    need(os.geteuid() == 1000, 'unprivileged owner identity')
    need(digest(args.request) == args.request_sha256 and digest(args.release) == args.release_sha256,
         'exact request and independent execution release')
    request = json.loads(Path(args.request).read_bytes())
    release = json.loads(Path(args.release).read_bytes())
    need(release.get('schema') == 'mckernel.current-guest-fullcrate-execution-release.v1' and
         release.get('status') == 'PASS' and release.get('request_sha256') == args.request_sha256 and
         release.get('owner_sha256') == digest(__file__), 'exact finite owner release')
    engine_path = bound(request['existing_transport']['image_owner'])
    module = types.ModuleType('_accepted_current_crate_transport')
    module.__file__ = str(engine_path)
    exec(compile(engine_path.read_bytes(), str(engine_path), 'exec'), module.__dict__)
    for row in request['retirement_import_closure']:
        bound(row)
    retirement_path = bound(request['retirement_transport'])
    need(not (retirement_path.parent / '__pycache__').exists(), 'fresh source-only retirement import closure')
    previous_path = list(sys.path)
    try:
        sys.path.insert(0, str(retirement_path.parent))
        spec = importlib.util.spec_from_file_location('_accepted_sdk_record_retirement', retirement_path)
        retirement = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(retirement)
    finally:
        sys.path[:] = previous_path
    retirement.ROOT = Path('/home/holden/mckernel-work/scratch')
    retirement.LEASE = Path(request['lease_path'])
    retirement.COMMON = Path(request['common_exclusion_path'])
    need({path.parent for path in (retirement.LEASE, retirement.COMMON,
         Path(retirement.shared.SHARED_HEAVY_LOCK_PATH))} == {retirement.ROOT}, 'three exact scratch parents')
    authority_request = {'path': args.request, 'sha256': args.request_sha256,
                         'bytes': Path(args.request).stat().st_size}
    root_lock = Path('/run/lock/mckernel-development.lock')
    fd = os.open(root_lock, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        lock = os.fstat(fd)
        need(stat.S_ISREG(lock.st_mode) and (lock.st_dev, lock.st_ino) == (27, 4) and
             (lock.st_uid, lock.st_gid, stat.S_IMODE(lock.st_mode), lock.st_nlink, lock.st_size) ==
             (0, 0, 0o644, 1, 0), 'actual development flock identity')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        linked = root_lock.lstat()
        need((linked.st_dev, linked.st_ino) == (lock.st_dev, lock.st_ino), 'development flock pathname drift')
        return run(request, module, retirement, authority_request)
    finally:
        os.close(fd)

if __name__ == '__main__':
    sys.exit(main())
