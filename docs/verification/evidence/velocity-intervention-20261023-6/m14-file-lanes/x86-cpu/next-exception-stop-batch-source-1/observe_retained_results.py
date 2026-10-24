"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Pure retained-capture observer for the exact source-bound twenty-command recipe.
No subprocess, compiler, object read/hash, or target execution. Future root-owned
executor supplies original commands and positive h990 results; no fabricated join.
"""
from pathlib import Path


def need(ok, message):
    if not ok:
        raise ValueError(message)


def observe(plan, records):
    need(len(records) == len(plan['commands']) == 20, 'twenty actual commands')
    by_label = {}
    for expected, record in zip(plan['commands'], records):
        command, result = record['command'], record['result']
        need(command['argv'] == expected['argv'] and command['cwd'] == expected['cwd'],
             'exact frozen producer argv/CWD')
        need(result['returncode'] == 0 and result['direct_child_joined']
             and result['group_absent'] and result['closed_streams']
             and not result['timed_out'] and result['error'] is None
             and result['retirement_error'] is None, 'positive owned whole join')
        need(expected['label'] not in by_label, 'unique labels')
        by_label[expected['label']] = result

    def output(label):
        return Path(by_label[label]['captures']['stdout']['path']).read_text()

    def rows(label):
        return [line.split() for line in output(label).splitlines() if line.split()]

    def unique(table, name, kinds):
        matches = [row for row in table if row[-1] == name]
        need(len(matches) == 1 and matches[0][-2] in kinds,
             ('one expected symbol', name, matches))
        return matches[0]

    for variant in plan['variants']:
        label = '04-' + variant + '-controlled-run'
        need(output(label).splitlines() == plan['expected_stdout'][variant],
             'strict actual callback/initialized-state/ABI oracle ' + variant)
        need(by_label[label]['captures']['stderr']['size'] == 0,
             'controlled fixture empty stderr')
    exported = plan['oracles']['leaf_T']
    leaf = rows('05-actual-Rust-symbols')
    selected = rows('09-selected-cpu-ownership')
    fallback = rows('09-fallback-cpu-ownership')
    partial = rows('12-partial-ownership')
    for name in exported:
        unique(leaf, name, {'T'})
    entries = plan['oracles']['selected_C_T_absent']
    for name in entries:
        need(not any(row[-1] == name and row[-2] in {'T', 't'} for row in selected),
             'no selected C entry duplicate ' + name)
        unique(fallback, name, {'T'})
        unique(partial, name, {'T'})
        need(not any(row[-1] == name and row[-2] == 'U' for row in partial),
             'actual partial resolves new entry ' + name)
    for name in ['x86_int3_debug_print_enabled', 'x86_debug_handler_debug_print_enabled']:
        symbol = unique(selected, name, {'R'})
        need(int(symbol[-3], 16) == 4, 'readonly config datum four-byte ABI')
        need(not any(row[-1] == name for row in fallback), 'fallback omits Rust config datum')
        symbol = unique(partial, name, {'R'})
        need(int(symbol[-3], 16) == 4, 'partial retains exact config data provider')
    need(by_label['10-selected-CPU-relocations']['captures']['stdout']['size'] > 0,
         'actual selected C relocation observation retained')
    return {
        'status': 'PASS_ACTUAL_CONTROLLED_EXCEPTION_STOP_LEAF_ABI_AND_SELECTED_GCC9_PARTIAL_ONLY',
        'actual_commands': 20,
        'actual_pairs': 4623,
        'variant_counts': {'undefined': 1541, 'defined-zero': 1541, 'defined-one': 1541},
        'per_variant': {'GPE': 288, 'INT3': 576, 'DEBUG': 672, 'STOP': 5},
        'actual_real_header_ABI_words': 34,
        'all_children_joined_groups_absent_streams_closed': True,
        'target_instructions_executed': False,
        'inherited_NULL_freeze_HOLD': True,
        'default_GCC14_link_native': 'OPEN',
        'engineering_percentage': None,
    }
