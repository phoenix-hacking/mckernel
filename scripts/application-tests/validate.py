#!/usr/bin/env python3
"""Validate planning metadata and emit a bounded draft context. Never runs cases.

This is a metadata check, not a filesystem sandbox or execution authorization.
Runtime manifests, executable oracles and the runner require separate review.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

BASE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative_path(value):
    require(isinstance(value, str) and value and '\x00' not in value, 'invalid path')
    p = PurePosixPath(value)
    require(not p.is_absolute() and '..' not in p.parts and str(p) == value, 'unsafe path: ' + value)
    return p


def positive_integer(value, name, maximum):
    require(type(value) is int and 0 < value <= maximum, 'invalid bound: ' + name)


def argv(value):
    require(isinstance(value, list) and value, 'command must be a nonempty argv array')
    require(all(isinstance(a, str) and '\x00' not in a for a in value), 'invalid argv item')
    require(PurePosixPath(value[0]).name not in ('sh', 'bash', 'dash', 'zsh', 'eval'), 'shell execution is forbidden')


def validate_catalog(catalog):
    require(catalog.get('schema_version') == 1, 'unsupported catalog schema')
    positive_integer(catalog.get('catalog_version'), 'catalog_version', 1000000)
    cases = catalog.get('cases')
    require(isinstance(cases, list) and cases, 'missing cases')
    require(catalog.get('logical_case_count') == len(cases), 'logical count mismatch')
    require(catalog.get('parameter_executions_in_case_count') is False, 'parameter count inflation')
    require(catalog.get('command_templates_are_implemented') is False, 'planning validator cannot authorize runtime')
    capabilities = catalog.get('capabilities')
    require(isinstance(capabilities, dict) and capabilities, 'missing capability contracts')
    for name, cap in capabilities.items():
        require(cap.get('state') in ('blocked', 'historical-baseline-only', 'unsupported'), 'unreviewed capability state: ' + name)
        require(isinstance(cap.get('acceptance'), str) and cap['acceptance'], 'missing capability acceptance: ' + name)
    require(set(catalog.get('global_execution_gates', [])) <= capabilities.keys(), 'unknown global gate')
    by_id = {}
    for case in cases:
        cid = case.get('id')
        require(isinstance(cid, str) and cid and cid not in by_id, 'missing or duplicate case ID')
        relative_path(cid)
        require('/' not in cid, 'case ID contains path separator')
        by_id[cid] = case
        positive_integer(case.get('version'), cid + ':version', 1000000)
        require(case.get('logical_case_count') == 1, cid + ':logical count')
        require(case.get('status') in ('planned', 'blocked'), cid + ':unknown planning state')
        require(case.get('execution_status') == 'blocked' and case.get('acceptance_status') == 'not-verified', cid + ':false acceptance')
        require(case.get('implementation_status') == 'not-created', cid + ':implementation needs separate manifest review')
        require(case.get('mode') in ('differential-guest', 'fault-guest', 'exact-production-fixture', 'bounded-campaign'), cid + ':unknown mode')
        requires = case.get('requires')
        require(isinstance(requires, list) and set(requires) <= capabilities.keys(), cid + ':unknown capability')
        require(isinstance(case.get('depends_on'), list), cid + ':missing dependencies')
        argv(case.get('command_argv'))
        payload = case.get('payload_contract', {})
        require(payload.get('shell_interpretation') is False, cid + ':shell policy')
        if payload.get('build_profile') == 'unchanged-pinned-ELF':
            target = PurePosixPath(payload.get('path', ''))
            require(target.is_absolute() and '..' not in target.parts, cid + ':invalid pinned executable')
            require('pinned-application-inventory' in requires, cid + ':unbound executable gate')
        else:
            relative_path(payload.get('path'))
        require(isinstance(payload.get('operation'), str) and payload['operation'], cid + ':missing operation')
        oracle = case.get('oracle', {})
        require(isinstance(oracle.get('assertions'), list) and oracle['assertions'] and
                all(isinstance(a, str) and a for a in oracle['assertions']), cid + ':missing independent assertions')
        require(oracle.get('readiness') == 'draft-unresolved' and oracle.get('unresolved'), cid + ':unreviewed frozen oracle')
        require(oracle.get('artifact') == 'scripts/application-tests/oracles/' + cid + '.json', cid + ':oracle path mismatch')
        require(oracle.get('independent_source'), cid + ':missing independent oracle source')
        require(oracle.get('normalization_allowlist') == [], cid + ':unreviewed normalization')
        require(isinstance(case.get('evidence'), list) and len(case['evidence']) >= 8, cid + ':missing evidence contract')
        require(case.get('cleanup'), cid + ':missing cleanup')
        limits = case.get('limits', {})
        require(limits.get('container_cpus') == [2, 3, 4, 5], cid + ':CPU bound')
        require(limits.get('container_swap_bytes') == 0, cid + ':swap bound')
        for name, maximum in [('container_memory_bytes', 12 * 1024**3), ('container_tasks', 512),
                              ('linux_memory_bytes', 8 * 1024**3), ('linux_vcpus', 4),
                              ('mckernel_memory_bytes', 128 * 1024**2), ('mckernel_cpus', 2),
                              ('payload_live_allocation_bytes', 32 * 1024**2),
                              ('payload_timeout_seconds', 30), ('cleanup_timeout_seconds', 15),
                              ('qemu_timeout_seconds', 300), ('preparation_timeout_seconds', 120),
                              ('stdout_limit_bytes', 4 * 1024**2), ('stderr_limit_bytes', 65536)]:
            positive_integer(limits.get(name), cid + ':' + name, maximum)
        require(limits['payload_timeout_seconds'] + limits['cleanup_timeout_seconds'] < limits['qemu_timeout_seconds'], cid + ':no watchdog margin')
        require(limits['mckernel_cpus'] == 1 or 'multicore-topology' in requires, cid + ':missing topology gate')
        require(case.get('repeatability', {}).get('fault_cases_fresh_guest_each_attempt') is True, cid + ':fault isolation')
    visiting, visited = set(), set()

    def visit(cid):
        require(cid in by_id, 'unknown dependency: ' + cid)
        require(cid not in visiting, 'dependency cycle: ' + cid)
        if cid in visited:
            return
        visiting.add(cid)
        for dep in by_id[cid]['depends_on']:
            visit(dep)
        visiting.remove(cid)
        visited.add(cid)
    for cid in by_id:
        visit(cid)
    for old in catalog.get('baseline_regressions', []):
        require(old.get('new_case_count') == 0 and old.get('status') == 'historically-accepted-only', 'baseline falsely counted')
    return by_id


def validate_packet(packet, catalog, by_id):
    require(packet.get('schema_version') == 1, 'unsupported packet schema')
    require(packet.get('mode') == 'draft-only' and packet.get('execution_enabled') is False, 'runtime packet needs separate validator')
    require(packet.get('command_templates_are_implemented') is False, 'unimplemented commands claimed')
    ids = packet.get('case_ids', [])
    require(isinstance(ids, list) and 1 <= len(ids) <= 3 and len(ids) == len(set(ids)), 'packet must have1–3 distinct cases')
    require(set(ids) <= by_id.keys(), 'unknown packet case')
    require(set(packet.get('blocked_by', [])) <= catalog['capabilities'].keys(), 'unknown packet gate')
    expected_paths = set()
    for cid in ids:
        if by_id[cid]['payload_contract'].get('build_profile') == 'unchanged-pinned-ELF':
            expected_paths.add('scripts/application-tests/inputs/' + cid + '.json')
        else:
            expected_paths.add('scripts/application-tests/' + by_id[cid]['payload_contract']['path'])
        expected_paths.add('scripts/application-tests/oracles/' + cid + '.json')
    writes = packet.get('write_allowlist', [])
    require(isinstance(writes, list) and set(writes) == expected_paths and len(writes) == len(set(writes)), 'draft writes exceed exact case/oracle paths')
    for path in writes:
        relative_path(path)
    reads = packet.get('read_allowlist', [])
    require(isinstance(reads, list) and reads, 'missing read context')
    selectors = {p.removeprefix('cases.json#') for p in reads if p.startswith('cases.json#')}
    require(selectors == set(ids), 'read context case subset mismatch')
    require('scripts/application-tests/cases.json' not in reads and 'kernel.log' not in reads, 'unbounded context')
    for command in packet.get('permitted_commands', []):
        argv(command)
        require(command == ['git', 'diff', '--check'] or
                (command[:4] == ['python3', '-B', '/workspace/scripts/application-tests/validate.py', '--packet'] and len(command) == 5), 'draft command exceeds validator/diff scope')
    limits = packet.get('limits', {})
    for name, maximum in [('active_cases_max', 3), ('candidate_fix_files_max', 2),
                          ('candidate_fix_changed_lines_max', 80), ('candidate_fix_minutes_max', 15),
                          ('container_memory_bytes', 12 * 1024**3), ('container_tasks', 512)]:
        positive_integer(limits.get(name), name, maximum)
    require(limits.get('container_cpus') == [2, 3, 4, 5] and limits.get('container_network') == 'none'
            and limits.get('host_tests_forbidden') is True, 'packet isolation policy')
    policy = packet.get('candidate_fix_policy', {})
    require(policy.get('max_candidates') == 1 and policy.get('not_automatic_acceptance') is True
            and policy.get('invalidate_previous_binary_coverage') is True, 'candidate review policy')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path)
    parser.add_argument('--emit-context', type=Path, help='Exclusively create JSON containing one draft packet and its selected cases')
    args = parser.parse_args()
    raw = (BASE / 'cases.json').read_bytes()
    catalog = json.loads(raw)
    by_id = validate_catalog(catalog)
    paths = [args.packet] if args.packet else sorted((BASE / 'packets').glob('*.json'))
    packets = []
    for path in paths:
        packet = json.loads(path.read_bytes())
        validate_packet(packet, catalog, by_id)
        packets.append(packet)
    if args.emit_context:
        require(len(packets) == 1 and args.packet is not None, 'context requires exactly one selected packet')
        packet = packets[0]
        cases = [by_id[cid] for cid in packet['case_ids']]
        required = set(packet['blocked_by']) | {cap for case in cases for cap in case['requires']}
        context = dict(schema_version=1, mode='draft-only', execution_enabled=False,
                       catalog_sha256=hashlib.sha256(raw).hexdigest(), packet=packet, cases=cases,
                       capability_contracts={key: catalog['capabilities'][key] for key in sorted(required)},
                       execution_inputs='UNRESOLVED; no runtime authorization',
                       notice='Metadata/context restriction is not an operating-system sandbox. No case has passed.')
        with args.emit_context.open('x') as stream:
            json.dump(context, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps(dict(status='PASS', scope='planning metadata only', logical_cases=len(by_id),
                          packets_checked=len(packets), runtime_authorized=False, application_tests_passed=0), sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise SystemExit('FAIL: ' + str(error))
