"""Functional OS only; no security testing. Read/hash/parse-only preflight.

No configure/compiler, command runner, admission, resource/account query, device
access, guest, cleanup, or canonical write is performed here.
"""
import ast
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent


def reference(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    p = json.loads((D / 'BOUND-TWO-TARGET-PROFILE.NOT-GRANTED.json').read_bytes())
    for row in p['inputs']:
        assert reference(row['path']) == row, row['path']
    prior = json.loads(Path(next(r['path'] for r in p['inputs'] if r['path'].endswith('/EXACT-NEXT-CONFIGURE-BUILD-OBJECT-COMMANDS.NOT-GRANTED.json'))).read_bytes())
    assert len(p['commands']) == len(prior['commands']) == 3
    for current, old in zip(p['commands'], prior['commands']):
        assert {k: v for k, v in current.items() if k != 'argv_compact_json_LF_sha256'} == old
        assert hashlib.sha256((json.dumps(current['argv'], separators=(',', ':')) + '\n').encode()).hexdigest() == current['argv_compact_json_LF_sha256']
        assert current['cwd'] == '/work'
    assert p['commands'][1]['argv'] == ['/usr/bin/cmake', '--build', '/work/current-bfd-build', '--target', 'mcinspect', 'eclair', '--parallel', '1']
    assert p['resources']['jobs'] == 1 and p['resources']['cpus'] == '2-5'
    assert p['resources']['memory_bytes'] == p['resources']['memory_swap_bytes'] == 12 * 2**30
    assert p['resources']['pids'] == 512 and p['resources']['network'] == 'none'
    assert p['fixed_deadline_UTC'] == '2026-10-28T05:36:09Z'
    assert p['fixed_cutoffs'] == [1793165769.0, 947874.5689514667, 963213.6960030915]
    assert p['expected_project_objects'] == dict(mcinspect=['bfd_accessors.o', 'mcinspect_helpers.o'], eclair=['bfd_accessors.o', 'eclair_helpers.o', 'arch_eclair_x86_64.o'])
    assert p['retained_no_replay']['new_replay_commands'] == 0
    assert all(p[k] is None for k in ['Root_current_closed_source', 'Root_current_adoption', 'Root_actual_boundary', 'Root_grant', 'new_actual_receipts'])
    assert not (D / 'future-work-1').exists() and not Path(p['capture_root']).exists()
    context = json.loads((D / 'VALID-DEVICE-AND-DUMP-CONTEXT.NOT-RELEASED.json').read_bytes())
    for row in context['tool_source_refs']:
        assert reference(row['path']) == row
    assert all(not paths for paths in context['exact_dump_or_kernel_data_paths_in_selected_bank'].values())
    assert context['Root_actual_context'] is context['Root_valid_diagnostic_release'] is context['new_valid_diagnostic_receipts'] is None
    assert len(context['cases']) == 2
    for source in D.glob('*.py'):
        ast.parse(source.read_bytes(), filename=str(source))
    print(json.dumps(dict(decision='PASS_SOURCE_PROFILE_DATA_ONLY_ROOT_BINDINGS_OPEN', commands=3, build_targets=2, build_jobs=1, selected_project_object_counts=[2, 3], actual_commands_run=0, valid_diagnostic_contexts_bound=0)))


if __name__ == '__main__':
    main()
