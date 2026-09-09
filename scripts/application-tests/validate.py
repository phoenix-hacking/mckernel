#!/usr/bin/env python3
"""Validate planning metadata and emit a bounded draft context. Never runs cases.

This is a metadata check, not a filesystem sandbox or execution authorization.
Runtime manifests, executable oracles and the runner require separate review.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

BASE = Path(__file__).resolve().parent
REPORT_ROOT = '/work/application-test-drafts-20260909/{fresh_queue_run_id}'
GLOBAL_GATES = {'current-inputs', 'runner-contract', 'runtime-transport-fault-injection'}
VECTOR_FEATURE_VERSION = 2
# Reviewed planning predicates, independent of the editable embedded copies.
VECTOR_FEATURE_SHA256 = 'f32c23dcdc9b5f5fab3675fe96c2c1b749086167dd07b5864feeb3c5eb553e46'
VECTOR_CASE_FEATURE_SHA256 = '7eb205d1bdc5df55828241c8d8079f53a33e62aad8696a53872c3e27a200972c'
VECTOR_BASELINE_FLAGS = ['-march=x86-64', '-mtune=generic', '-mno-avx', '-mno-avx2', '-mno-avx512f']
VECTOR_REFERENCE_FLAGS = ['-fno-tree-vectorize', '-fno-tree-slp-vectorize', '-ffp-contract=off', '-fno-fast-math']


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


def strings(value, name, allow_empty=False):
    require(isinstance(value, list) and (allow_empty or value), 'missing list: ' + name)
    require(all(isinstance(item, str) and item and '\x00' not in item for item in value), 'invalid list: ' + name)
    require(len(value) == len(set(value)), 'duplicate list item: ' + name)
    return set(value)


def json_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load_json(raw):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique_pairs)


def hexadecimal(value, name, bits, nonzero=False):
    require(isinstance(value, str) and re.fullmatch(r'0x[0-9a-f]+', value), 'invalid hex: ' + name)
    number = int(value, 16)
    require(int(nonzero) <= number < 1 << bits, 'invalid mask: ' + name)
    return number


def validate_feature_table(contracts):
    require(isinstance(contracts, dict) and contracts, 'missing reviewed vector feature table')
    parents = {}
    for feature, contract in contracts.items():
        require(isinstance(contract, dict), 'invalid feature contract: ' + feature)
        parents[feature] = strings(contract.get('all_of'), feature + ':all_of', allow_empty=True)
        require(parents[feature] <= contracts.keys(), 'unknown feature dependency: ' + feature)
        require(contract.get('missing_result') == 'BLOCKED' and contract.get('never_enable_from_host_cpuinfo') is True
                and contract.get('both_engines_required') is True, 'unsafe feature authorization: ' + feature)
        conditions = contract.get('cpuid_all_bits')
        require(isinstance(conditions, list), 'missing CPUID predicates: ' + feature)
        for condition in conditions:
            require(isinstance(condition, dict) and condition.get('register') in ('eax', 'ebx', 'ecx', 'edx'), 'CPUID register')
            hexadecimal(condition.get('leaf'), feature + ':leaf', 32)
            hexadecimal(condition.get('subleaf'), feature + ':subleaf', 32)
            hexadecimal(condition.get('mask'), feature + ':mask', 32, nonzero=True)
        enabled = hexadecimal(contract.get('xcr0_all_bits'), feature + ':XCR0', 64)
        supported = hexadecimal(contract.get('cpuid_d_0_xcr0_supported_all_bits'), feature + ':CPUID0xD', 64)
        require(enabled & supported == enabled, 'required state unsupported: ' + feature)
    visiting, visited = set(), set()

    def visit(feature):
        require(feature not in visiting, 'feature dependency cycle: ' + feature)
        if feature in visited:
            return
        visiting.add(feature)
        for parent in parents[feature]:
            visit(parent)
        visiting.remove(feature)
        visited.add(feature)
    for feature in contracts:
        visit(feature)
    require(json_sha256(contracts) == VECTOR_FEATURE_SHA256, 'reviewed vector feature predicates changed')


def argv(value):
    require(isinstance(value, list) and value, 'command must be a nonempty argv array')
    require(all(isinstance(a, str) and '\x00' not in a for a in value), 'invalid argv item')
    require(PurePosixPath(value[0]).name not in ('sh', 'bash', 'dash', 'zsh', 'eval'), 'shell execution is forbidden')


def validate_catalog(catalog):
    require(isinstance(catalog, dict), 'invalid catalog object')
    require(catalog.get('schema_version') == 1, 'unsupported catalog schema')
    positive_integer(catalog.get('catalog_version'), 'catalog_version', 1000000)
    require(catalog['catalog_version'] == VECTOR_FEATURE_VERSION, 'catalog needs reviewed vector predicate version')
    validate_feature_table(catalog.get('vector_feature_contracts'))
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
    gates = strings(catalog.get('global_execution_gates'), 'global execution gates')
    require(gates == GLOBAL_GATES and gates <= capabilities.keys(), 'missing or changed global execution gates')
    by_id = {}
    vector_bindings = {}
    for case in cases:
        cid = case.get('id')
        require(isinstance(cid, str) and cid and cid not in by_id, 'missing or duplicate case ID')
        relative_path(cid)
        require(re.fullmatch(r'[a-z]+\.[a-z0-9-]+', cid), 'invalid case ID')
        require(case.get('family') == cid.split('.', 1)[0], cid + ':family identity')
        by_id[cid] = case
        positive_integer(case.get('version'), cid + ':version', 1000000)
        require(case.get('logical_case_count') == 1, cid + ':logical count')
        require(case.get('status') in ('planned', 'blocked'), cid + ':unknown planning state')
        require(case.get('execution_status') == 'blocked' and case.get('acceptance_status') == 'not-verified', cid + ':false acceptance')
        require(case.get('implementation_status') == 'not-created', cid + ':implementation needs separate manifest review')
        require(case.get('mode') in ('differential-guest', 'fault-guest', 'exact-production-fixture', 'bounded-campaign'), cid + ':unknown mode')
        requires = case.get('requires')
        require(strings(requires, cid + ':requires') <= capabilities.keys(), cid + ':unknown capability')
        strings(case.get('depends_on'), cid + ':depends_on', allow_empty=True)
        argv(case.get('command_argv'))
        payload = case.get('payload_contract', {})
        require(payload.get('shell_interpretation') is False, cid + ':shell policy')
        profile = payload.get('build_profile')
        if profile == 'unchanged-pinned-ELF':
            target = PurePosixPath(payload.get('path', ''))
            require(target.is_absolute() and '..' not in target.parts, cid + ':invalid pinned executable')
            require('pinned-application-inventory' in requires, cid + ':unbound executable gate')
        elif profile == 'exact-production-rust-fixture':
            require(payload.get('path') == 'fixtures/' + cid + '.rs', cid + ':fixture write scope')
        else:
            extensions = {'ordinary-dynamic-etexec-c11': '.c', 'generic-dispatch-isolated-target-assembly': '.c',
                          'minimal-static-first-entry-assembly': '.c', 'disassembly-only-selected-binaries': '.py'}
            require(profile in extensions, cid + ':unknown build profile')
            expected = 'cases/' + case['family'] + '/' + cid + extensions[profile]
            require(payload.get('path') == expected, cid + ':payload write scope')
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
                              ('application_threads', 8), ('thread_stack_bytes', 256 * 1024),
                              ('case_file_bytes', 4 * 1024**2),
                              ('payload_timeout_seconds', 30), ('cleanup_timeout_seconds', 15),
                              ('qemu_timeout_seconds', 300), ('preparation_timeout_seconds', 120),
                              ('stdout_limit_bytes', 4 * 1024**2), ('stderr_limit_bytes', 65536)]:
            positive_integer(limits.get(name), cid + ':' + name, maximum)
        require(limits['payload_timeout_seconds'] + limits['cleanup_timeout_seconds'] < limits['qemu_timeout_seconds'], cid + ':no watchdog margin')
        require(limits['mckernel_cpus'] == 1 or 'multicore-topology' in requires, cid + ':missing topology gate')
        children = limits.get('application_children')
        require(type(children) is int and 0 <= children <= 1, cid + ':application child bound')
        repetition = case.get('repeatability', {})
        require(repetition.get('fault_cases_fresh_guest_each_attempt') is True, cid + ':fault isolation')
        require(type(repetition.get('same_os_repeats')) is int and repetition['same_os_repeats'] == 3
                and type(repetition.get('fresh_guest_repeats')) is int and repetition['fresh_guest_repeats'] == 1, cid + ':repeat bounds')
        expected_command = ['python3', '-B', '/workspace/scripts/application-tests/run.py', '--inputs', '{input_manifest}',
                            '--case', cid, '--attempt', '{fresh_attempt}', '--profile',
                            'reviewed-2cpu' if limits['mckernel_cpus'] == 2 else 'baseline-root-1cpu', '--mode', case['mode']]
        require(case['command_argv'] == expected_command, cid + ':unreviewed command template')
        if case.get('family') == 'vector':
            vector = payload.get('vector_contract', {})
            require(vector.get('host_instruction_execution_forbidden') is True, cid + ':host vector execution')
            require(vector.get('missing_feature_status') == 'BLOCKED', cid + ':missing vector feature passes')
            require(vector.get('baseline_dispatch_flags') == VECTOR_BASELINE_FLAGS, cid + ':unreviewed baseline ISA flags')
            require(vector.get('scalar_reference_flags') == VECTOR_REFERENCE_FLAGS, cid + ':unreviewed scalar reference flags')
            strings(vector.get('required_instructions'), cid + ':required instruction proof')
            positive_integer(vector.get('xsave_observation_buffer_max_bytes'), cid + ':xsave buffer bound', 16384)
            contracts = vector.get('feature_contracts', {})
            features = vector.get('features', [])
            require(isinstance(contracts, dict) and strings(features, cid + ':features') <= contracts.keys(), cid + ':missing feature contract')
            for feature, contract in contracts.items():
                require(contract == catalog.get('vector_feature_contracts', {}).get(feature), cid + ':changed feature predicate')
                require(isinstance(contract, dict) and set(contract['all_of']) <= contracts.keys(), cid + ':missing transitive feature gate')
            parameters = case.get('parameters', {})
            require(isinstance(parameters, dict), cid + ':invalid parameters')
            forms = parameters.get('forms', [])
            require(isinstance(forms, list), cid + ':invalid parameter forms')
            for form in forms:
                require(isinstance(form, dict) and strings(form.get('features'), cid + ':parameter features') <= contracts.keys(), cid + ':unknown parameter feature')
            vector_bindings[cid] = {'features': features, 'parameter_features': [form['features'] for form in forms]}
    require(json_sha256(vector_bindings) == VECTOR_CASE_FEATURE_SHA256, 'reviewed case-to-feature bindings changed')
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
    require(isinstance(packet, dict), 'invalid packet object')
    require(packet.get('schema_version') == 1, 'unsupported packet schema')
    pid = packet.get('packet_id')
    require(isinstance(pid, str) and re.fullmatch(r'packet-[0-9]{3}', pid) and int(pid[7:]) > 0, 'invalid packet ID')
    positive_integer(packet.get('version'), 'packet version', 1000000)
    require(packet.get('status') == 'planned', 'unreviewed packet status')
    require(packet.get('mode') == 'draft-only' and packet.get('execution_enabled') is False, 'runtime packet needs separate validator')
    require(packet.get('command_templates_are_implemented') is False, 'unimplemented commands claimed')
    ids = packet.get('case_ids', [])
    require(isinstance(ids, list) and 1 <= len(ids) <= 3 and len(ids) == len(set(ids)), 'packet must have1–3 distinct cases')
    require(set(ids) <= by_id.keys(), 'unknown packet case')
    gates = strings(packet.get('blocked_by'), 'packet execution gates')
    require(GLOBAL_GATES <= gates <= catalog['capabilities'].keys(), 'missing or unknown packet execution gate')
    inputs = packet.get('inputs', {})
    require(inputs == {'capability_manifest': '{reviewed_capability_manifest}', 'input_manifest': '{reviewed_input_manifest}',
                       'case_subset_only': True, 'catalog': 'scripts/application-tests/cases.json'}, 'unreviewed packet input scope')
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
    actual_reads = strings(reads, 'packet reads')
    expected_reads = {'scripts/application-tests/README.md', 'scripts/application-tests/packets/' + pid + '.json',
                      '{reviewed_capability_manifest}', '{reviewed_input_manifest}'} | {'cases.json#' + cid for cid in ids}
    if any(by_id[cid]['family'] == 'vector' for cid in ids):
        expected_reads.add('docs/verification/ultra-vector-test-plan-20260909.md')
    require(actual_reads == expected_reads, 'read context exceeds exact packet subset')
    commands = packet.get('permitted_commands')
    require(isinstance(commands, list) and commands, 'missing permitted commands')
    for command in commands:
        argv(command)
        require(command == ['git', 'diff', '--check'] or
                command == ['python3', '-B', '/workspace/scripts/application-tests/validate.py', '--packet',
                            '/workspace/scripts/application-tests/packets/' + pid + '.json'], 'draft command exceeds validator/diff scope')
    limits = packet.get('limits', {})
    for name, maximum in [('active_cases_max', 3), ('candidate_fix_files_max', 2),
                          ('candidate_fix_changed_lines_max', 80), ('candidate_fix_minutes_max', 15),
                          ('container_memory_bytes', 12 * 1024**3), ('container_tasks', 512)]:
        positive_integer(limits.get(name), name, maximum)
    require(limits.get('container_cpus') == [2, 3, 4, 5] and limits.get('container_network') == 'none'
            and limits.get('host_tests_forbidden') is True, 'packet isolation policy')
    require(len(ids) <= limits['active_cases_max'], 'packet exceeds declared active case bound')
    policy = packet.get('candidate_fix_policy', {})
    require(policy.get('max_candidates') == 1 and policy.get('not_automatic_acceptance') is True
            and policy.get('invalidate_previous_binary_coverage') is True, 'candidate review policy')
    prohibited = strings(policy.get('prohibited'), 'candidate prohibited operations')
    require({'oracle weakening', 'allowed-errno widening', 'hidden retry', 'kernel or launcher change in a draft-only packet',
             'changing baseline fixtures', 'rewriting failed evidence'} <= prohibited, 'candidate policy weakened')
    reporting = packet.get('reporting', {})
    require(reporting.get('report_path') == REPORT_ROOT + '/' + pid + '/report.json', 'report write scope')
    require(reporting.get('failure_log_path') == REPORT_ROOT + '/failures.jsonl', 'failure log write scope')
    require(reporting.get('failure_artifact_directory') == REPORT_ROOT + '/' + pid + '/failures/', 'failure artifact write scope')
    require(reporting.get('test_pass_status_forbidden') is True, 'draft report claims test acceptance')
    require(strings(reporting.get('draft_statuses'), 'draft statuses') == {'DRAFTED', 'DRAFTED_WITH_UNRESOLVED', 'BLOCKED', 'FAILED'}, 'draft result statuses')
    require({'schema_version', 'queue_run_id', 'queue_sha256', 'packet_id', 'packet_version', 'context_sha256', 'started_utc',
             'finished_utc', 'draft_status', 'cases', 'changed_files_with_sha256', 'commands_and_outcomes', 'unresolved_oracles',
             'blocked_execution_capabilities', 'first_failure_event', 'max_escalation', 'next_packet_id'} <=
            strings(reporting.get('required_report_fields'), 'report fields'), 'missing draft report evidence')
    require({'schema_version', 'sequence', 'utc', 'queue_run_id', 'packet_id', 'case_ids', 'stage', 'exact_command_argv_or_tool_action',
             'environment_summary', 'error', 'original_artifact_paths_and_sha256', 'source_and_context_sha256', 'max_escalation_required'} <=
            strings(reporting.get('required_failure_event_fields'), 'failure fields'), 'missing original failure evidence')


def validate_queue(queue, catalog, by_id, directory):
    require(isinstance(queue, dict) and queue, 'missing mandatory draft queue')
    require(queue.get('schema_version') == 1 and queue.get('queue_version') == 1, 'unknown draft queue schema')
    require(queue.get('execution_enabled') is False and queue.get('mode') == 'draft-only', 'queue enables runtime')
    require(queue.get('review_state') in ('pending-root-validation-and-verified-checkpoint', 'released-for-drafting'), 'unknown review state')
    rows = queue.get('packets', [])
    require(isinstance(rows, list), 'invalid queue rows')
    require(queue.get('packet_count') == len(rows) and rows, 'queue count mismatch')
    require(queue.get('logical_case_count') == len(by_id), 'queue case count mismatch')
    require(queue.get('catalog_version') == catalog['catalog_version'], 'stale queue catalog')
    require(queue.get('catalog') == 'scripts/application-tests/cases.json' and queue.get('parameter_executions_in_case_count') is False, 'queue catalog/count scope')
    context = queue.get('context_policy', {})
    require(context.get('active_packets') == 1 and context.get('active_cases_max') == 3, 'queue context expansion')
    failure = queue.get('failure_policy', {})
    require(failure.get('append_only_original_failure_log') is True and failure.get('hidden_retry') is False
            and failure.get('production_changes_allowed') is False and failure.get('oracle_weakening_allowed') is False, 'queue failure policy weakened')
    reporting = queue.get('reporting', {})
    require(reporting.get('root') == REPORT_ROOT and reporting.get('failure_log_path') == REPORT_ROOT + '/failures.jsonl'
            and reporting.get('summary_path') == REPORT_ROOT + '/queue-summary.json', 'queue report write scope')
    seen = set()
    packets = {}
    for index, row in enumerate(rows, 1):
        pid = 'packet-%03d' % index
        require(row.get('packet_id') == pid and row.get('path') == 'scripts/application-tests/packets/' + pid + '.json', 'noncanonical queue path/order')
        path = directory / 'packets' / (pid + '.json')
        require(not path.is_symlink(), 'canonical packet is a symlink')
        raw = path.read_bytes()
        packet = load_json(raw)
        validate_packet(packet, catalog, by_id)
        require(packet['packet_id'] == pid, 'packet ID differs from canonical filename/queue')
        require(row.get('case_ids') == packet['case_ids'], 'queue/packet case mismatch')
        cursor = packet.get('queue', {})
        require(cursor == {'path': 'scripts/application-tests/draft-queue.json', 'position': index,
                           'next_packet_id': 'packet-%03d' % (index + 1) if index < len(rows) else None,
                           'advance_only_when_queue_reviewed': True, 'new_user_permission_per_packet_required': False,
                           'active_case_limit': 3}, 'packet queue cursor/scope mismatch')
        packets[pid] = (packet, raw)
        for cid in row['case_ids']:
            require(cid not in seen, 'case assigned more than once: ' + cid)
            require(set(by_id[cid]['depends_on']) <= seen, 'draft dependency order: ' + cid)
            seen.add(cid)
    require(seen == by_id.keys(), 'queue does not cover complete catalog')
    require({path.name for path in (directory / 'packets').glob('*.json')} == {pid + '.json' for pid in packets}, 'unqueued packet file')
    return rows, packets


def selected_packet(path, packets, directory):
    pid = path.stem
    require(pid in packets and path.name == pid + '.json', 'selected packet is not queued')
    canonical = directory / 'packets' / (pid + '.json')
    require(not path.is_symlink() and path.resolve(strict=True) == canonical.resolve(strict=True), 'selected packet is not canonical queued path')
    packet, raw = packets[pid]
    require(path.read_bytes() == raw, 'selected packet changed after queue validation')
    return packet, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path)
    parser.add_argument('--emit-context', type=Path, help='Exclusively create JSON containing one draft packet and its selected cases')
    args = parser.parse_args()
    raw = (BASE / 'cases.json').read_bytes()
    catalog = load_json(raw)
    by_id = validate_catalog(catalog)
    queue_path = BASE / 'draft-queue.json'
    require(queue_path.is_file() and not queue_path.is_symlink(), 'missing mandatory canonical draft queue')
    queue_raw = queue_path.read_bytes()
    queue = load_json(queue_raw)
    queued, packets = validate_queue(queue, catalog, by_id, BASE)
    selected = selected_packet(args.packet, packets, BASE) if args.packet else None
    if args.emit_context:
        require(selected is not None, 'context requires exactly one selected packet')
        packet, packet_raw = selected
        cases = [by_id[cid] for cid in packet['case_ids']]
        required = GLOBAL_GATES | set(packet['blocked_by']) | {cap for case in cases for cap in case['requires']}
        cursor = next(i for i, row in enumerate(queued) if row['packet_id'] == packet['packet_id'])
        context = dict(schema_version=1, mode='draft-only', execution_enabled=False,
                       catalog_sha256=hashlib.sha256(raw).hexdigest(), packet_sha256=hashlib.sha256(packet_raw).hexdigest(), packet=packet, cases=cases,
                       capability_contracts={key: catalog['capabilities'][key] for key in sorted(required)},
                       execution_inputs='UNRESOLVED; no runtime authorization',
                       queue_cursor=dict(queue_sha256=hashlib.sha256(queue_raw).hexdigest(),
                           index=cursor + 1, total=len(queued), review_state=queue['review_state'],
                           next_packet_id=queued[cursor + 1]['packet_id'] if cursor + 1 < len(queued) else None),
                       notice='Metadata/context restriction is not an operating-system sandbox. No case has passed.')
        with args.emit_context.open('x') as stream:
            json.dump(context, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps(dict(status='PASS', scope='planning metadata only', logical_cases=len(by_id),
                          packets_checked=1 if selected else len(packets), queue_packets_checked=len(queued), runtime_authorized=False, application_tests_passed=0), sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise SystemExit('FAIL: ' + str(error))
