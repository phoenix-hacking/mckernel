"""Only new nsfs-root parser controls; no live process/FD/native observation.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The rejected collector worker/turn/request remains excluded and is never loaded.
NOT EXECUTED by its source author. Root owns review and actual HOST admission.
"""
import ast
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).parent
GRAPH = HERE / 'graph_observations.PROPOSED.py'
GRAPH_SHA = '507337063a7be9d5d709b3fae3a811b1f7675a97e0fa82fd6749b044a583cdd8'
SNAPSHOT = pathlib.Path('/home/holden/mckernel-work/resume-reconciliation-20261112T094452Z-12a4bea0/ACTUAL-PROVIDER-1837769-MOUNTINFO.SNAPSHOT')
SNAPSHOT_SHA = 'f79321b4dceb28ae7d58684102dfc8123829a2fc9d12b65bf301a018cecc71d6'
NAMES = {'require', 'decode_path', '_mount_covers', 'MountTable', 'parse_mountinfo'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def changed_row(raw, row_index, changes):
    # These are explicit synthetic parser-input mutations of the saved DATA.
    # No actual mount table or process is changed.
    lines = raw.decode().splitlines()
    fields = lines[row_index].split(' ')
    for index, value in changes.items():
        fields[index] = value
    lines[row_index] = ' '.join(fields)
    return ('\n'.join(lines) + '\n').encode()


def main():
    source = GRAPH.read_bytes()
    assert digest(source) == GRAPH_SHA
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
             and n.name in NAMES]
    assert {n.name for n in nodes} == NAMES and len(nodes) == len(NAMES)
    namespace = {'__name__': 'actual_nsfs_parser_projection', 're': re,
                 'PurePosixPath': pathlib.PurePosixPath}
    # Only the five pure parser definitions are executed. No package import,
    # main/provider/Root/account/process/source FD/native entry is reachable.
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(GRAPH), 'exec'), namespace)
    parse = namespace['parse_mountinfo']
    raw = SNAPSHOT.read_bytes()
    assert digest(raw) == SNAPSHOT_SHA and len(raw) == 9496
    expected_raw = (HERE / 'EXPECTED-ACTUAL-ROWS.DATA.json').read_bytes()
    expected = json.loads(expected_raw)
    raw_rows = [line.split(' ') for line in raw.decode().splitlines()]
    index = next(i for i, row in enumerate(raw_rows)
                 if row[row.index('-') + 1] == 'nsfs')
    row = raw_rows[index]
    sep = row.index('-')
    observations = []

    table = parse(raw)
    assert len(table.by_id) == expected['actual_row_count'] == 91
    assert digest(canonical(table.all_rows)) == expected['actual_all_rows_canonical_sha256']
    assert sorted(table.by_id) == sorted(int(row[0]) for row in raw_rows)
    selected = []
    for fields in expected['actual_nsfs_rows']:
        entry = table.by_id[int(fields[0])]
        assert entry['fields'] == tuple(fields) and entry['root'] == fields[3]
        assert entry['point'] == fields[4] and entry['point'].startswith('/')
        visible = table.resolve(fields[4])
        assert visible['mount_id'] == int(fields[0])
        assert table[fields[4]] == {'mount_id': int(fields[0]),
                                  'parent_mount_id': int(fields[1]), 'access': 'rw'}
        selected.append(int(fields[0]))
    observations.append({'id': 'actual-f793-all91-and-four-nsfs-preserved',
                         'result': 'PASS', 'raw_rows': len(table.by_id),
                         'nsfs_ids': sorted(selected), 'all_fields_equal': True})

    changed = parse(changed_row(raw, index, {3: 'mnt:[4026532663]'}))
    assert dict(table) == dict(changed) and table != changed and not table == changed
    assert changed.by_id[int(row[0])]['root'] == 'mnt:[4026532663]'
    observations.append({'id': 'nsfs-root-change-visible-map-equal-full-table-unequal',
                         'result': 'PASS'})

    maximum = parse(changed_row(raw, index, {3: 'mnt:[4294967295]'}))
    assert len(maximum.by_id) == 91
    assert maximum.by_id[int(row[0])]['root'] == 'mnt:[4294967295]'
    observations.append({'id': 'canonical-positive-uint32-boundary', 'result': 'PASS'})

    def refuse(name, value, message):
        try:
            parse(value)
        except ValueError as error:
            assert str(error) == message, (name, type(error).__name__, str(error))
        else:
            raise AssertionError((name, 'unexpected parser acceptance'))
        observations.append({'id': name, 'result': 'REFUSED', 'message': message})

    refuse('tagged-root-on-ordinary-filesystem',
           changed_row(raw, index, {sep + 1: 'tmpfs'}), 'mount path fields')
    refuse('ordinary-relative-root-remains-refused',
           changed_row(raw, index, {3: 'relative/path', sep + 1: 'tmpfs'}), 'mount path fields')
    malformed = [
        ('relative-nsfs-path', 'relative/path'),
        ('empty-inode', 'mnt:[]'),
        ('zero-inode', 'mnt:[0]'),
        ('negative-inode', 'mnt:[-1]'),
        ('leading-zero-inode', 'mnt:[01]'),
        ('nondigit-inode', 'mnt:[1x]'),
        ('missing-bracket', 'mnt:[123'),
        ('other-unqualified-tag', 'net:[4026532662]'),
        ('uint32-overflow', 'mnt:[4294967296]'),
        ('oversized-decimal', 'mnt:[999999999999999999999999999]'),
    ]
    for name, value in malformed:
        refuse(name, changed_row(raw, index, {3: value}), 'mount path fields')
    refuse('tagged-nsfs-relative-covering-mountpoint',
           changed_row(raw, index, {4: 'run/snapd/ns/cups.mnt'}), 'mount path fields')
    refuse('tagged-nsfs-ambiguous-access',
           changed_row(raw, index, {5: 'ro,rw'}), 'ambiguous mount access')
    refuse('tagged-nsfs-invalid-mount-id',
           changed_row(raw, index, {0: '0'}), 'duplicate or invalid mount id')
    refuse('tagged-nsfs-missing-nonroot-parent',
           changed_row(raw, index, {1: '999999999'}), 'mount parent outside visible root')
    refuse('duplicate-nsfs-raw-row-not-filtered',
           raw + (' '.join(row) + '\n').encode(), 'duplicate or invalid mount id')
    second = list(row)
    second[0] = str(max(int(item[0]) for item in raw_rows) + 1)
    refuse('nsfs-visible-same-parent-point-ambiguity-not-filtered',
           raw + (' '.join(second) + '\n').encode(), 'ambiguous visible mount stack')

    assert digest(GRAPH.read_bytes()) == GRAPH_SHA
    expected_observations = json.loads((HERE / 'EXPECTED-CONTROLS.DATA.json').read_bytes())
    assert observations == expected_observations['observations']
    print(json.dumps({'scope': 'NEW_NSFS_ROOT_PARSER_CONTROLS_ONLY',
                      'source_sha256': GRAPH_SHA, 'snapshot_sha256': SNAPSHOT_SHA,
                      'observations': observations,
                      'all91_raw_rows_and_four_tagged_roots_preserved': True,
                      'old22_mount_10_receipt_provider_keeper_transport_diagnostic_tests_rerun': False,
                      'native_process_FD_root_flags_sudo_test_package_or_main_actions': False,
                      'no_acceptance_or_runtime_or_native_release': True}, sort_keys=True))


if __name__ == '__main__':
    main()
