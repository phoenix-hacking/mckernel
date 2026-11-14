"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One pending read-only P12 inspect and exact compile-owner admission assembly.
No lease, container lifecycle, root document publication or build operation.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

D = Path(__file__).resolve().parent
B = D.parent
PROFILE_SHA = '9b78e4ec49f163a333a3fd7e9cf0dc6b05dbdc097a0b785c20cf741aaa6e23fa'
CORE_SHA = '1a93ac79346055cff43e18afa9b4f358cc9ff9f9328976d37c724b28b020ab2c'
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def birth(pid):
    assert type(pid) is int and pid > 1
    fields = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
    return int(fields[19])


def main():
    assert os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {0}
    assert sys.version_info[:3] == (3, 9, 12) and len(sys.argv) == 3
    context_path = Path(sys.argv[1])
    assert context_path.parent == D and context_path.name == 'ROOT-CONTEXT.ACTUAL.json'
    assert re.fullmatch('[0-9a-f]{64}', sys.argv[2])
    raw = context_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sys.argv[2]
    context = json.loads(raw)
    # Root declarations are inputs; observations cannot manufacture ownership or release.
    for key in ('cpu6_consumer_joined', 'P12_sole_native_heavy', 'controller_allowance_reviewed', 'native_cgroups_unchanged'):
        assert context[key] is True, key
    assert context['reservation_adopted'] == '19GiB_7jobs_P12_12G_compile4G_controller2G_client_coord1G'
    assert context['boot_id'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    expected = context['P12']
    assert set(expected) == {'id', 'name', 'owner_label_key', 'owner_label_value', 'config_sha256', 'host_config_sha256'}
    assert re.fullmatch('[0-9a-f]{64}', expected['id'])
    assert expected['name'].startswith('/') and expected['owner_label_key'] and expected['owner_label_value']
    assert all(re.fullmatch('[0-9a-f]{64}', expected[k]) for k in ('config_sha256', 'host_config_sha256'))
    assert context['actual_P12_authority'] and context['CPU6_retirement_authority'] and context['root_continuity_authority']
    for filename, sha in (('compile_image_owner.py', '8cd5a1948fc973461e15c17cdea604932b723f839f00646ec7df35c31647d555'),
                          ('compile_host_helper.py', '8ffc9a09e2f2e9e9c9cc09af559d707bf6c4b989fc4f9d3ad51fe88a8e5b6083'),
                          ('COMPILE-PROFILE.json', PROFILE_SHA)):
        assert hashlib.sha256((B / filename).read_bytes()).hexdigest() == sha
    profile = json.loads((B / 'COMPILE-PROFILE.json').read_text())
    before_births = {k: birth(context[k]['pid']) for k in ('P12_owner', 'P12_container_init')}
    assert all(before_births[k] == context[k]['starttime'] for k in before_births)
    helper_raw = HELPER.read_bytes()
    assert hashlib.sha256(helper_raw).hexdigest() == HELPER_SHA
    functions = {'need', 'write', 'hashed', 'stop', 'cpu_used', 'members', 'process_start', 'terminal_unreaped', 'wait_terminal', 'owned_capture'}
    assignments = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
    body = []
    for node in ast.parse(helper_raw, str(HELPER)).body:
        if isinstance(node, (ast.Import, ast.ImportFrom)) or isinstance(node, ast.FunctionDef) and node.name in functions or isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assignments for t in node.targets):
            body.append(node)
    ns = {'__file__': str(HELPER)}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(HELPER), 'exec'), ns)
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
        signal.signal(signum, ns['stop'])
    capture = D / 'actual-readonly-admission-1'
    capture.mkdir(mode=0o700)
    command = {'purpose': __doc__, 'argv': ['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host=unix:///var/run/docker.sock', 'inspect', expected['id']]}
    ns['write'](capture / 'command.json', command)

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        resource.setrlimit(resource.RLIMIT_FSIZE, (33554432, 33554432))
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    result = ns['owned_capture'](command, capture, 30, limits)
    ns['write'](capture / 'whole-join.json', result)
    assert result['returncode'] == 0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams']
    assert result['error'] is None and result['retirement_error'] is None
    rows = json.loads((capture / 'stdout').read_text())
    assert isinstance(rows, list) and len(rows) == 1
    info = rows[0]
    assert info['Id'] == expected['id'] and info['Name'] == expected['name'] and info['State']['Running'] is True
    assert info['Config']['Labels'][expected['owner_label_key']] == expected['owner_label_value']
    assert canonical(info['Config']) == expected['config_sha256'] and canonical(info['HostConfig']) == expected['host_config_sha256']
    assert all(info['HostConfig'].get(k) == v for k, v in profile['reserved_native_profile'].items())
    assert info['State']['Pid'] == context['P12_container_init']['pid']
    assert all(birth(context[k]['pid']) == before_births[k] for k in before_births)
    rw_roots = sorted(set(m['Source'] for m in info['Mounts'] if m.get('RW') is True and m.get('Source', '').startswith('/')))
    assert rw_roots and rw_roots == context['P12_rw_roots']
    own = Path(profile['namespace']) / 'owner-work'
    for raw_root in rw_roots:
        other = Path(raw_root)
        assert raw_root == os.path.abspath(raw_root) and other != own and own not in other.parents and other not in own.parents
    host = os.statvfs(B)
    scratch = os.statvfs('/home/holden/mckernel-work/scratch')
    backing = os.stat('/home/holden/mckernel-work/scratch.ext4')
    assert backing.st_size == 118111600640
    gap = max(0, backing.st_size - 512 * backing.st_blocks)
    host_required = 17179869184 + gap + 16106090496 + 377487360 + 679477248
    scratch_required = 12884901888 + 67108864 + 679477248
    host_available = host.f_bavail * host.f_frsize
    scratch_available = scratch.f_bavail * scratch.f_frsize
    mem = int(next(row.split()[1] for row in Path('/proc/meminfo').read_text().splitlines() if row.startswith('MemAvailable:'))) * 1024
    assert host_available >= host_required and scratch_available >= scratch_required and mem >= 25769803776
    facts = dict(schema='mckernel.m14-candidate14-dual-container-admission.v1', operation=profile['operation'], request_core_sha256=CORE_SHA, profile_sha256=PROFILE_SHA,
                 boot_id=context['boot_id'], observed_boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME), MemAvailable=mem,
                 HOST_available=host_available, HOST_required=host_required, scratch_available=scratch_available, scratch_required=scratch_required,
                 compile_limits=profile['limits'], P12_limits=profile['reserved_native_profile'], P12=expected, P12_rw_roots=rw_roots,
                 capacity_verdict='PASS_DUAL_CONTAINER_COMPILE_CPU6_4G',
                 **{k: context[k] for k in ('cpu6_consumer_joined', 'P12_sole_native_heavy', 'controller_allowance_reviewed', 'native_cgroups_unchanged')})
    ns['write'](capture / 'ROOT-ADMISSION.CANDIDATE.json', facts)
    ns['write'](capture / 'OBSERVATION-SIDECAR.json', dict(scope=__doc__, input_sha256=sys.argv[2], context=context, P12_births_before_after=before_births,
               backing_size=backing.st_size, backing_blocks=backing.st_blocks, full_sparse_gap=gap, root_publication=None, release=None))
    print(json.dumps(facts, sort_keys=True))


if __name__ == '__main__':
    main()
