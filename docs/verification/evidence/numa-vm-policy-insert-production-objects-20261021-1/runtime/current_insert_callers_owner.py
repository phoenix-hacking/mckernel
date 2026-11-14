#!/usr/bin/env python3
"""One crate-only case using the existing exact compiler-owner transport.

No image build, module install or guest occurs here. The exact accepted SDK
selfretirement path removes only the verified stopped CID and releases its
three archived records; all source/work/output/evidence is retained.
"""
import argparse
import resource
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

def load_transports(request):
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
    return module, retirement

CAPACITY_FSIZE = 32 * 2**20
HOST_GROWTH = 1543503872
SCRATCH_GROWTH = 771751936

def capacity_decision(host_dev, scratch_dev, records, host_paths, docker, limits, free):
    need(host_dev != scratch_dev, 'distinct HOST/SCRATCH devices required')
    need(all(isinstance(x, int) and 0 <= x <= CAPACITY_FSIZE for x in limits), 'bounded soft/hard FSIZE required')
    need(len(records) == 3 and len({r['path'] for r in records}) == 3, 'exact three distinct scratch records')
    need(all(r['device'] == scratch_dev and r['direct_scratch_child'] and not r['symlink'] and not r['escape'] for r in records), 'record escapes SCRATCH device/root')
    need(bool(host_paths) and all(r['device'] == host_dev and not r['symlink'] and not r['escape'] for r in host_paths), 'actual writable/source path outside HOST')
    need(docker['device'] == host_dev and not docker['symlink'] and not docker['escape'], 'Docker data root outside HOST')
    floors = {'host': 16 * 2**30, 'scratch': 12 * 2**30}
    budgets = {'host': HOST_GROWTH, 'scratch': SCRATCH_GROWTH}
    need(all(free[key] >= floors[key] + budgets[key] for key in floors), 'per-filesystem floors plus full declared budgets')
    return {'devices': {'host': host_dev, 'scratch': scratch_dev}, 'free': free, 'floors': floors,
            'budgets': budgets, 'FSIZE': list(limits), 'records': records, 'host_paths': host_paths, 'docker_data': docker}

def checked_location(value):
    path = Path(value)
    need(path.is_absolute() and str(path) == os.path.normpath(str(path)) and '..' not in path.parts, 'absolute canonical path required')
    for item in [path, *path.parents]:
        need(not item.is_symlink(), 'symlink component forbidden: ' + str(item))
    existing = path
    while not existing.exists():
        existing = existing.parent
    need(path.resolve(strict=False) == path, 'path resolution escape')
    return {'path': str(path), 'device': existing.stat().st_dev, 'symlink': False, 'escape': False}

def capacity_snapshot(request, docker_root):
    need(request['disk_budget_bytes'] + request['capture_budget_bytes'] + request['emergency_reserve_bytes'] == HOST_GROWTH and request['emergency_reserve_bytes'] == 640 * 2**20, 'unchanged full HOST and emergency budgets required')
    host = checked_location('/home/holden')
    scratch = checked_location('/home/holden/mckernel-work/scratch')
    record_paths = [request['lease_path'], request['common_exclusion_path'], '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock']
    records = []
    for value in record_paths:
        row = checked_location(value)
        row['direct_scratch_child'] = Path(value).parent == Path(scratch['path'])
        need(not os.path.lexists(value), 'ownership record already exists')
        records.append(row)
    writable = [m for m in request['mounts'] if not m['readonly']]
    need(len(writable) == 1 and writable[0]['target'] == '/work' and writable[0]['source'] == request['work_root'], 'only HOST work container bind may be writable')
    need('--read-only' in request['create_argv'] and '/tmp:rw,nodev,nosuid,size=256m' in request['create_argv'], 'readonly root and RAM tmpfs required')
    paths = [request['mounts'][0]['source'], request['work_root'], request['owner_evidence_root'],
             request['capacity_admission_root'], request['outer_capture_root'], str(Path(request['work_root'])/'output'),
             str(Path(request['work_root'])/'home'), str(Path(request['work_root'])/'tmp'), os.environ.get('TMPDIR', '/tmp'), '/tmp']
    host_paths = [checked_location(value) for value in paths]
    free = {key: os.statvfs(value).f_bavail * os.statvfs(value).f_frsize for key, value in [('host',host['path']),('scratch',scratch['path'])]}
    return capacity_decision(host['device'], scratch['device'], records, host_paths,
                             checked_location(docker_root), resource.getrlimit(resource.RLIMIT_FSIZE), free)

def capacity_before_ownership(request, engine, retirement, role):
    # No ownership record exists yet. The one readonly Docker info client uses
    # the accepted journal/capture/group-retirement implementation on HOST.
    need(role in ('outer', 'inner'), 'fixed capacity observation role')
    base = Path(request['capacity_admission_root'])
    checked_location(str(base))
    root = base/role
    need(not root.exists(), 'fresh capacity admission evidence required')
    # Check all filesystem/budget/FSIZE predicates before even creating logs.
    capacity_snapshot(request, '/home/holden')
    root.mkdir(parents=True, mode=0o700)
    with engine.Signals() as signals:
        docker = retirement.ExternalDocker(root/'docker.log', signals, sudo=True)
        try:
            result = docker.call(['info', '--format', '{{json .DockerRootDir}}'], timeout=30)
            docker_root = json.loads(result.stdout)
            need(isinstance(docker_root, str), 'actual Docker data root required')
            snapshot = capacity_snapshot(request, docker_root)
        finally:
            client_count = retirement.positive_clients(docker, root)
        snapshot['journalled_info_clients'] = client_count
        snapshot['client_groups'] = docker.group_checks
    engine._exclusive_json(root/'capacity.json', snapshot)
    return snapshot

def run(request, engine, retirement, authority_request):
    capacity = capacity_before_ownership(request, engine, retirement, 'inner')
    # Capacity/FSIZE/devices and readonly info client closure precede ownership.
    shared_path, shared_record = engine._SHARED_HEAVY_ENTRY_CONTRACT.acquire_heavy_operation(request, 'build')
    state = json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())
    usage = {'phase': state.get('phase'), 'pause_reason': state.get('pause_reason'),
             'usedPercent': state.get('last_rate_limits', {}).get('primary', {}).get('usedPercent')}
    need(usage['phase'] == 'running' and not usage['pause_reason'] and
         isinstance(usage['usedPercent'], (int, float)) and usage['usedPercent'] < 100, 'usage admission')
    free = capacity['free']
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
    for key in ['driver', 'commands', 'provider', 'capture_helpers', 'prototype_assertions']:
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
               'admission': {'usage': usage, 'free': free, 'MemAvailable': ram, 'time_ns': time.time_ns(), 'capacity': capacity}}
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
                 len(result.get('commands', [])) == len(result.get('artifacts', [])) == len(expected_commands) == 2 and
                 all(row.get('exit_code') == 0 and row.get('direct_wait') is True and
                     row.get('owned_process_group_absent') is True for row in result['commands']),
                 'two real insertion caller results and direct retirement')
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
                need(parsed == row, 'actual ELF64 x86-64 ET_REL and exact boundary export/import obligations')
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
    module, retirement = load_transports(request)
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
