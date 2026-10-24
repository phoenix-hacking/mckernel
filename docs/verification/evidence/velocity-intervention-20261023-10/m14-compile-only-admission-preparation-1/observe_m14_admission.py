"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One fixed root CPU7 read-only query. Writes only its fresh owned evidence.
No create/start/stop/rm, lock acquisition, lease mutation or release publication.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import resource
import signal
import stat
import sys
import time

D = Path(__file__).resolve().parent
B = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-current-default-compile-only-preparation-1/bounded-provenance-path-correction-1')
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def need(value, message):
    if not value:
        raise RuntimeError(message)

def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def birth(pid):
    need(type(pid) is int and pid > 1, 'exact process identity required')
    fields = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
    need(fields[0] not in ('Z', 'X', 'x'), 'live nonterminal process required')
    return int(fields[19])

def address_space_limits(pid):
    lines = Path('/proc/%d/limits' % pid).read_text().splitlines()
    words = next(line.split() for line in lines if line.startswith('Max address space'))
    need(words[-1] == 'bytes', 'address-space limit units')
    return [int(words[-3]), int(words[-2])]

def limits():
    os.sched_setaffinity(0, {7})
    for number, value in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 30),
                          (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256),
                          (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(number, (value, value))

def root_document(path, expected_sha):
    need(path.resolve(strict=True) == path, 'root context canonical path')
    a = path.lstat()
    need(stat.S_ISREG(a.st_mode) and a.st_uid == 0 and a.st_nlink == 1 and
         not stat.S_IMODE(a.st_mode) & 0o022 and a.st_size <= 1 << 20, 'sealed root context')
    raw = path.read_bytes()
    b = path.lstat()
    need((a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns, a.st_ctime_ns) ==
         (b.st_dev, b.st_ino, b.st_size, b.st_mtime_ns, b.st_ctime_ns) and
         hashlib.sha256(raw).hexdigest() == expected_sha, 'root context hash/identity changed')
    return json.loads(raw)

def pinned_authority(path, expected_sha):
    need(path.resolve(strict=True) == path, 'authority canonical path')
    a = path.lstat()
    need(stat.S_ISREG(a.st_mode) and a.st_nlink == 1 and a.st_size <= 1 << 20,
         'bounded regular authority')
    raw = path.read_bytes()
    b = path.lstat()
    need((a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns, a.st_ctime_ns) ==
         (b.st_dev, b.st_ino, b.st_size, b.st_mtime_ns, b.st_ctime_ns) and
         hashlib.sha256(raw).hexdigest() == expected_sha, 'authority hash/identity changed')
    return json.loads(raw)

def main():
    need(os.getuid() == os.geteuid() == 0 and os.sched_getaffinity(0) == {7}, 'root read-only CPU7 profile')
    need(len(sys.argv) == 3 and all(re.fullmatch('[0-9a-f]{64}', value) for value in sys.argv[1:]), 'profile/context digest argv')
    for number, value in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 30),
                          (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256),
                          (resource.RLIMIT_CORE, 0)):
        need(resource.getrlimit(number) == (value, value), 'exact root query limits')
    profile_path = D / 'READONLY-QUERY-PROFILE.json'
    need(sha(profile_path) == sys.argv[1], 'exact query profile')
    p = json.loads(profile_path.read_text())
    need(sha(Path(__file__).resolve()) == p['query_sha256'] and sha(HELPER) == HELPER_SHA, 'exact query/helper source')
    context = root_document(D / 'ROOT-CONTEXT.ACTUAL.json', sys.argv[2])
    need(context['scope'] == SCOPE and context['operation'] == p['operation'], 'current operation/context')
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    need(context['boot_id'] == boot, 'same current boot')
    for key in ('cpu6_consumer_joined', 'P12_sole_native_heavy', 'controller_allowance_reviewed', 'native_cgroups_unchanged', 'compile_HOST_growth_independently_reviewed'):
        need(context[key] is True, 'root declaration missing: ' + key)
    need(context['P12_owner'] == p['P12_owner'], 'current P12 owner anchor')
    controller = context['P12_capture_controller']
    need(isinstance(controller, dict) and set(controller) == {'pid', 'starttime'} and
         birth(controller['pid']) == controller['starttime'], 'current live P12 capture controller identity required')
    actual_controller_limits = address_space_limits(controller['pid'])
    actual_owner_limits = address_space_limits(p['P12_owner']['pid'])
    need(actual_controller_limits == [512 << 20, 512 << 20] and actual_owner_limits == [2 << 30, 2 << 30],
         'actual current P12 owner/controller AS must match aggregate reservation')
    owner_authority = pinned_authority(Path(p['P12_owner_authority']['path']), p['P12_owner_authority']['sha256'])
    need(owner_authority == {'pid': p['P12_owner']['pid'], 'start': p['P12_owner']['starttime']},
         'exact current started receipt, not retired owner identity')
    for label in ('CPU6_retirement_authority', 'aggregate_authority', 'continuity_authority', 'current_source_and_actual19_authority'):
        row = context[label]
        need(isinstance(row, dict) and set(row) == {'path', 'sha256'}, 'missing root authority: ' + label)
        authority = pinned_authority(Path(row['path']), row['sha256'])
        if label == 'CPU6_retirement_authority':
            need(authority.get('direct_child_joined') is True and authority.get('group_absent') is True and
                 authority.get('closed_streams') is True, 'positive latest CPU6 whole join required')
    aggregate = context['aggregate_reservation']
    component_keys = ('native_bytes', 'compile_bytes', 'P12_owner_AS_bytes', 'P12_capture_controller_AS_bytes',
                      'compile_controller_AS_bytes', 'root_client_coordination_bytes', 'other_active_bytes')
    need(all(type(aggregate[k]) is int and aggregate[k] >= 0 for k in component_keys) and
         aggregate['bytes'] == sum(aggregate[k] for k in component_keys) and
         aggregate['bytes'] <= p['hard_aggregate_bytes'] and type(aggregate['jobs']) is int and 1 <= aggregate['jobs'] <= 7 and
         aggregate['compile_bytes'] == 4 << 30 and aggregate['native_bytes'] == 12 << 30 and
         aggregate['P12_owner_AS_bytes'] == 2 << 30 and aggregate['P12_capture_controller_AS_bytes'] == 512 << 20 and
         aggregate['compile_controller_AS_bytes'] == 2 << 30 and aggregate['root_client_coordination_bytes'] >= 1 << 30 and
         aggregate['query_AS_bytes'] == 2 << 30 and aggregate['query_inside_existing_controller_pool'] is True,
         'actual root aggregate/controller adoption required')
    h = load_module('accepted990_bfd_query_capture', HELPER)
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
        signal.signal(signum, h.stop)
    signal.setitimer(signal.ITIMER_REAL, 66)
    capture = D / 'actual-readonly-query-1'
    capture.mkdir(mode=0o700)
    records = []
    def command(name, argv):
        child = capture / name
        child.mkdir(mode=0o700)
        request = {'purpose': SCOPE + ' Read-only functional admission: ' + name, 'argv': argv}
        h.write(child / 'command.json', request)
        result = h.owned_capture(request, child, 12, limits)
        h.write(child / 'whole-join.json', result)
        records.append({'name': name, 'argv': argv, 'result': result})
        need(result['returncode'] == 0 and result['direct_child_joined'] and result['group_absent'] and
             result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,
             'read-only command/join failed: ' + name)
        need((child / 'stderr').stat().st_size == 0 and (child / 'stdout').stat().st_size <= 4 << 20,
             'bounded clean read-only command streams')
        return (child / 'stdout').read_text()
    result = {'scope': SCOPE, 'status': 'FAIL_RETAINED_NO_RETRY', 'actual_release': None, 'records': records}
    try:
        for filename, expected in p['owner_bindings'].items():
            need(sha(Path(filename)) == expected, 'accepted current M14 source changed: ' + filename)
        prepared_path = Path(p['prepared_request_path'])
        raw_request = prepared_path.read_bytes()
        need(len(raw_request) == p['prepared_request_bytes'] and hashlib.sha256(raw_request).hexdigest() == p['prepared_request_sha256'], 'exact accepted prepared request bytes')
        request = json.loads(raw_request)
        core = canonical({k: v for k, v in request.items() if k != 'compile_only_release'})
        need(request['compile_only_release'] is None and request['compile_operation'] == p['operation'] and request['compile_profile_sha256'] == p['owner_profile_sha256'], 'unreleased accepted M14 request/profile')
        for row in p['namespace_metadata']:
            path = Path(row['path']); info = path.lstat()
            need(stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino, info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) == (row['device'], row['inode'], row['uid'], row['gid'], int(row['mode'], 8)) and sorted(os.listdir(path)) == sorted(row['children']), 'exact fresh compile namespace directories unchanged')
        need(birth(p['P12_owner']['pid']) == p['P12_owner']['starttime'], 'P12 owner birth before query')
        docker = ['/usr/bin/docker', '--host=unix:///var/run/docker.sock']
        rows = json.loads(command('P12-inspect', docker + ['inspect', p['P12_name'][1:]]))
        need(isinstance(rows, list) and len(rows) == 1, 'one exact P12 inspect')
        info = rows[0]
        need(re.fullmatch('[0-9a-f]{64}', info['Id']) and info['Name'] == p['P12_name'] and
             info['Image'] == p['P12_image'] and info['State']['Running'] is True and
             info['Config']['Labels']['mckernel.native-diagnostic.owner'] == p['P12_nonce'], 'current exact P12 identity')
        need(all(info['HostConfig'].get(k) == v for k, v in p['P12_limits'].items()), 'unchanged native resources')
        need(info['HostConfig'].get('CgroupParent') == '/mckernel-dev', 'native container remains in reviewed cgroup parent')
        init_pid = info['State']['Pid']
        init_birth = birth(init_pid)
        init_cgroup = Path('/proc/%d/cgroup' % init_pid).read_text()
        need(len(init_cgroup) <= 65536, 'bounded init cgroup membership')
        cgroups = {path: Path(path).read_text().strip() for path in p['native_cgroups']}
        need(cgroups == p['native_cgroups'], 'native cgroups unchanged')
        lock = Path('/run/lock/mckernel-development.lock').lstat()
        need((lock.st_dev, lock.st_ino, lock.st_uid, lock.st_gid, lock.st_nlink) == (27, 4, 0, 0, 1), 'permanent native mutex27:4 identity')
        lock_key = '%02x:%02x:%d' % (os.major(lock.st_dev), os.minor(lock.st_dev), lock.st_ino)
        locks = [line for line in Path('/proc/locks').read_text().splitlines() if lock_key in line.split()]
        need(len(locks) == 1 and 'FLOCK' in locks[0].split() and 'WRITE' in locks[0].split() and
             str(p['P12_owner']['pid']) == locks[0].split()[4], 'P12 retains sole native flock; no acquire attempted')
        leases = {path: os.path.lexists(path) for path in p['must_remain_absent_ownership_paths']}
        need(not any(leases.values()), 'unexpected existing native/heavy/build lease; retain and reconcile')
        running = command('running-containers', docker + ['ps', '--quiet', '--no-trunc']).splitlines()
        need(running == [info['Id']], 'P12 sole running container')
        own = Path(request['work_root'])
        rw_roots = sorted(set(m['Source'] for m in info['Mounts'] if m.get('RW') is True and m.get('Source', '').startswith('/')))
        need(rw_roots == p['P12_expected_rw_roots'], 'exact source/request-derived P12 writable roots')
        for raw in rw_roots:
            other = Path(raw)
            need(raw == os.path.abspath(raw) and own != other and own not in other.parents and other not in own.parents,
                 'P12 and compile writable domains disjoint')
        scratch = Path('/home/holden/mckernel-work/scratch')
        backing = Path('/home/holden/mckernel-work/scratch.ext4')
        bs = backing.lstat()
        need(stat.S_ISREG(bs.st_mode) and backing.resolve(strict=True) == backing and bs.st_size == 110 << 30,
             'current retained110GiB canonical backing')
        host_device = B.stat().st_dev
        scratch_device = scratch.stat().st_dev
        need(bs.st_dev == host_device and scratch_device != host_device, 'HOST/scratch/backing separation')
        uuid = Path('/dev/disk/by-uuid/' + p['scratch_uuid']).stat()
        need(stat.S_ISBLK(uuid.st_mode) and uuid.st_rdev == scratch_device, 'fresh UUID device matches actual scratch')
        loop_sys = Path('/sys/dev/block/%d:%d/loop/backing_file' % (os.major(scratch_device), os.minor(scratch_device)))
        loop_backing = loop_sys.read_text().strip()
        need(loop_backing == str(backing), 'fresh loop backing match')
        mounted = json.loads(command('scratch-mount', ['/usr/bin/findmnt', '-J', '-o', 'TARGET,SOURCE,FSTYPE,UUID,OPTIONS', '-T', str(scratch)]))['filesystems']
        need(len(mounted) == 1 and mounted[0]['target'] == str(scratch) and mounted[0]['uuid'] == p['scratch_uuid'] and
             mounted[0]['fstype'] == 'ext4' and {'rw','nodev','nosuid'} <= set(mounted[0]['options'].split(',')), 'fresh scratch mount identity')
        gap = max(0, bs.st_size - 512 * bs.st_blocks)
        host = os.statvfs(B)
        scratch_space = os.statvfs(scratch)
        host_available = host.f_bavail * host.f_frsize
        scratch_available = scratch_space.f_bavail * scratch_space.f_frsize
        budgets = context['remaining_storage_reservations']
        need(set(budgets) == {'HOST_other_growth', 'HOST_compile_growth', 'scratch_other_growth', 'scratch_compile_growth', 'emergency'} and
             all(type(v) is int and v >= 0 for v in budgets.values()) and
             budgets['HOST_compile_growth'] >= p['minimum_compile_HOST_growth'] and
             budgets['HOST_other_growth'] >= p['P12_reserved_HOST_growth'] and
             budgets['scratch_other_growth'] >= p['P12_reserved_scratch_growth'] and budgets['scratch_compile_growth'] == 0 and budgets['emergency'] >= 679477248,
             'explicit full remaining growth/emergency reservation required')
        host_required = (16 << 30) + gap + budgets['HOST_other_growth'] + budgets['HOST_compile_growth'] + budgets['emergency']
        scratch_required = (12 << 30) + budgets['scratch_other_growth'] + budgets['scratch_compile_growth'] + budgets['emergency']
        mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
        need(host_available >= host_required and scratch_available >= scratch_required and mem >= 24 << 30,
             'fresh full-gap storage and24GiB memory admission')
        online = Path('/sys/devices/system/cpu/online').read_text().strip()
        cpus = set()
        for item in online.split(','):
            ends = item.split('-')
            cpus.update(range(int(ends[0]), int(ends[-1]) + 1))
        need({2,3,4,5,6,7} <= cpus, 'reviewed CPUs online')
        need(birth(init_pid) == init_birth and birth(p['P12_owner']['pid']) == p['P12_owner']['starttime'] and
             birth(controller['pid']) == controller['starttime'], 'P12 identities unchanged after query')
        final_backing = backing.lstat()
        need((final_backing.st_dev, final_backing.st_ino, final_backing.st_mode, final_backing.st_size, final_backing.st_blocks) ==
             (bs.st_dev, bs.st_ino, bs.st_mode, bs.st_size, bs.st_blocks) and scratch.stat().st_dev == scratch_device,
             'backing/scratch identity and full-gap allocation stable through query')
        # Fresh devices update only a separately retained unreleased request candidate.
        request['disk_admission']['host_device'] = Path(request['disk_admission']['host_root']).stat().st_dev
        request['disk_admission']['scratch_device'] = scratch_device
        final_core = canonical({k: v for k, v in request.items() if k != 'compile_only_release'})
        facts = dict(schema='mckernel.m14-candidate14-dual-container-admission.v1', operation=p['operation'],
            request_core_sha256=final_core, profile_sha256=p['owner_profile_sha256'], boot_id=boot,
            observed_boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME), MemAvailable=mem,
            HOST_available=host_available, HOST_required=host_required, scratch_available=scratch_available, scratch_required=scratch_required,
            compile_limits=p['compile_limits'], P12_limits=p['P12_limits'], P12={'id':info['Id'],'name':info['Name'],
            'owner_label_key':'mckernel.native-diagnostic.owner','owner_label_value':p['P12_nonce'],
            'config_sha256':canonical(info['Config']),'host_config_sha256':canonical(info['HostConfig'])}, P12_rw_roots=rw_roots,
            capacity_verdict='PASS_DUAL_CONTAINER_COMPILE_CPU6_4G',
            **{k:context[k] for k in ('cpu6_consumer_joined','P12_sole_native_heavy','controller_allowance_reviewed','native_cgroups_unchanged')})
        h.write(capture / 'REQUEST-BINDING.UNRELEASED.CANDIDATE.json', dict(scope=SCOPE, status='EXACT_SMALL_BINDING_ONLY_NO_FULL_REQUEST_PUBLICATION', prepared_request_path=str(prepared_path), prepared_request_sha256=p['prepared_request_sha256'], prepared_request_bytes=p['prepared_request_bytes'], prepared_request_core_sha256=core, finalized_request_core_sha256=final_core, finalized_disk_admission=request['disk_admission'], compile_only_release=None))
        h.write(capture / 'ROOT-ADMISSION.CANDIDATE.json', facts)
        result.update(status='PASS_READONLY_M14_ADMISSION_CANDIDATE_ONLY', admission=facts,
            prepared_request_core_sha256=core, finalized_request_core_sha256=final_core,
            observations={'P12_init':{'pid':init_pid,'starttime':init_birth},'init_cgroup':init_cgroup,'native_cgroups':cgroups,
            'native_lock_rows':locks,'ownership_paths':leases,'backing':{'dev':bs.st_dev,'inode':bs.st_ino,'size':bs.st_size,
            'blocks':bs.st_blocks,'full_sparse_gap':gap},'scratch_device':scratch_device,'loop_backing':loop_backing,
            'mount':mounted,'remaining_storage_reservations':budgets,'aggregate_reservation':aggregate,
            'P12_capture_controller':controller,'P12_owner_AS_limits':actual_owner_limits,
            'P12_capture_controller_AS_limits':actual_controller_limits},
            actual_admission_publication=None, actual_release=None, native_acceptance=False)
    except BaseException as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        h.write(capture / 'RESULT.json', result)
    print(json.dumps(result, sort_keys=True))

if __name__ == '__main__':
    main()
