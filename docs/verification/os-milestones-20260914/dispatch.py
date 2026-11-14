#!/usr/bin/env python3
"""Read bounded planning objects; never launch an agent, build, guest or payload."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def read(name):
    return json.loads((HERE / name).read_text())


def one(rows, ident):
    found = [row for row in rows if row['id'] == ident]
    if len(found) != 1:
        raise ValueError('unknown or duplicate ID: ' + ident)
    return found[0]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_binding(record):
    data = (REPO / record['path']).read_bytes()
    require(len(data) == record['size'], 'size changed: ' + record['path'])
    require(hashlib.sha256(data).hexdigest() == record['sha256'],
            'hash changed: ' + record['path'])


def check():
    tasks = read('tasks.json')
    gates = read('gate-map.json')
    cases = read('case-map.json')
    source = read('source-index.json')
    for document in (tasks, gates, cases, source):
        require(document['schema_version'] == 1, 'unknown planning schema')
        require(document['execution_authorized_by_plan'] is False,
                'planning documents must not authorize execution')
    for record in gates['sources'] + cases['sources']:
        check_binding(record)
    check_binding(source['repository_paths'])
    native = gates['native_gates']
    require(len(native) == 130 == len({g['id'] for g in native}), 'native gate coverage')
    require(sum(g['points'] for g in native) == 10000, 'native point total')
    require(sum(g['points'] for g in native if g['recorded_status'] == 'PASS') == 350,
            'baseline points changed; create a fresh versioned planning snapshot')
    require(dict(Counter(g['recorded_status'] for g in native)) == gates['status_counts'],
            'gate status counts differ')
    original_gates = []
    for line in (REPO / 'final-push.txt').read_text().splitlines():
        if line.startswith('GATE|'):
            _, ident, stream, points, status, evidence, contract, owner = line.split('|')
            original_gates.append((ident, stream, int(points), status, evidence, contract, owner))
    indexed_gates = [(g['id'], g['workstream'], g['points'], g['recorded_status'],
                      g['original_evidence'], g['acceptance_contract'], g['original_owner'])
                     for g in native]
    require(indexed_gates == original_gates, 'gate contracts changed in index')
    language = gates['language_gates']
    require({g['id'] for g in language} == {f'MK-LANG-{i:03}' for i in range(1, 8)}
            and len(language) == 7, 'language gate coverage')
    original_language = []
    for line in (REPO / 'docs/verification/mckernel-rust-assembly-completion.md').read_text().splitlines():
        if line.startswith('| MK-LANG-'):
            original_language.append(tuple(part.strip() for part in line.split('|')[1:-1]))
    require([(g['id'], g['acceptance_contract'], g['recorded_state']) for g in language]
            == original_language, 'language contracts changed in index')
    catalog = json.loads((REPO / 'scripts/application-tests/cases.json').read_text())
    queue = json.loads((REPO / 'scripts/application-tests/draft-queue.json').read_text())
    by_case = {c['id']: c for c in cases['cases']}
    require(len(by_case) == 273 == len(cases['cases']), 'case uniqueness/count')
    require(set(by_case) == {c['id'] for c in catalog['cases']}, 'catalog coverage')
    require(len(queue['packets']) == 97, 'packet count')
    require(Counter(cid for p in queue['packets'] for cid in p['case_ids'])
            == Counter({cid: 1 for cid in by_case}), 'packet coverage')
    for index, original in enumerate(catalog['cases']):
        case = by_case[original['id']]
        for key in ('family', 'requires', 'depends_on', 'parameters', 'repeatability'):
            require(case[key] == original[key], 'case field changed: ' + case['id'] + '/' + key)
        require(case['catalog_pointer'] == f'/cases/{index}', 'case pointer mismatch')
        require(case['accepted'] is False and case['runtime_status'] == 'NOT_RUN',
                'planning snapshot cannot acquire runtime credit')
        packet = queue['packets'][case['queue_position'] - 1]
        require(case['id'] in packet['case_ids'] and case['packet_id'] == packet['packet_id']
                and case['packet_path'] == packet['path'], 'packet mapping mismatch')
        check_binding(case['fixture'])
        check_binding(case['oracle'])
    require(dict(Counter(c['family'] for c in by_case.values())) == cases['family_counts'],
            'family counts differ')
    by_task = {t['id']: t for t in tasks['tasks']}
    require(len(by_task) == 68 == len(tasks['tasks']), 'task uniqueness/count')
    require(len(tasks['milestones']) == 14, 'milestone count')
    readme = (HERE / 'README.md').read_text().splitlines()
    declared = {match.group(1) for line in readme
                for match in [re.match(r'^\| (M\d\d-[A-Z]) \|', line)] if match}
    require(declared == set(by_task), 'runbook/task coverage mismatch')
    for item in native + language + list(by_case.values()):
        require(item['primary_milestone'] in tasks['milestones'], 'unknown routed milestone')
    visiting, done = set(), set()

    def visit(ident):
        require(ident in by_task, 'unknown task dependency: ' + ident)
        require(ident not in visiting, 'task dependency cycle: ' + ident)
        if ident in done:
            return
        visiting.add(ident)
        task = by_task[ident]
        require(task['milestone'] in tasks['milestones'], 'task milestone missing')
        line = readme[task['source']['line'] - 1]
        require(line.startswith('| ' + ident + ' | '), 'task source line mismatch')
        require(task['description_and_done_criteria'] in line, 'task criteria mismatch')
        for path in task['starting_read_paths']:
            require((REPO / path).is_file(), 'missing starting file: ' + path)
        for dependency in task['depends_on']:
            visit(dependency)
        visiting.remove(ident)
        done.add(ident)

    for ident in by_task:
        visit(ident)
    return {'status': 'PASS_PLANNING_INDEX', 'milestones': 14, 'tasks': 68,
            'production_gates': 130, 'language_gates': 7, 'logical_cases': 273,
            'packets': 97, 'execution_authorized': False,
            'scope': 'Coverage, routing, dependency DAG and bound original metadata/fixture identities only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['check', 'summary', 'task', 'gate', 'case'])
    parser.add_argument('id', nargs='?')
    parser.add_argument('--full', action='store_true', help='For case only: include its original catalog object')
    args = parser.parse_args()
    if args.kind in ('task', 'gate', 'case') and not args.id:
        parser.error('the selected operation requires an ID')
    if args.kind in ('check', 'summary') and args.id:
        parser.error('this operation takes no ID')
    if args.full and args.kind != 'case':
        parser.error('--full is for a selected case only')
    if args.kind == 'check':
        result = check()
    elif args.kind == 'summary':
        result = {'milestones': read('tasks.json')['milestones'],
                  'current_priority': ['M00-A', 'M01-A', 'M02-A', 'M03-A'],
                  'planning_snapshot': True, 'execution_authorized': False,
                  'counts': {'tasks': 68, 'native_gates': 130, 'language_gates': 7,
                             'cases': 273, 'packets': 97, 'catalog_accepted': 0},
                  'resume': 'Read the live CURRENT.md when present; these are creation-time counts.'}
    elif args.kind == 'task':
        result = one(read('tasks.json')['tasks'], args.id)
    elif args.kind == 'gate':
        data = read('gate-map.json')
        result = one(data['native_gates'] + data['language_gates'], args.id)
    else:
        result = {'routing': one(read('case-map.json')['cases'], args.id)}
        if args.full:
            binding = read('case-map.json')['sources'][0]
            check_binding(binding)
            catalog = json.loads((REPO / binding['path']).read_text())
            result['original_catalog_case'] = one(catalog['cases'], args.id)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError) as exc:
        print('planning index error: ' + str(exc), file=sys.stderr)
        sys.exit(1)
