"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded source derivation from frozen117. No actual bindings/export/runtime.
Do not rerun after the source packet is frozen; original117 remains untouched.
"""
from pathlib import Path
import hashlib
import json

D = Path(__file__).resolve().parent
S = D.parent
E = S.parent
OLD = E / 'current117-next-default-cohort-source-20261028-1'
C = D / 'cohort'
LIMITS = [1793253600.0, 1035704.5689393478, 1051042.6959879305]


def ref(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    with Path(path).open('xb') as stream:
        stream.write(value if isinstance(value, bytes) else (json.dumps(value, indent=2) + '\n').encode())


def text118(text):
    return (text.replace(str(OLD), str(D))
            .replace('CURRENT117-PERFMMAP-VDSO', 'CURRENT118-CLEARPTE-SIGNALFP')
            .replace('current117-build', 'current118-build')
            .replace('CURRENT117', 'CURRENT118').replace('ROOT117', 'ROOT118')
            .replace('current117', 'current118').replace('validate117', 'validate118')
            .replace('1035705.5689454618', '1035704.5689393478')
            .replace('1051043.6959931096', '1051042.6959879305'))


def main():
    C.mkdir(mode=0o700)
    inputs = []
    for path in sorted((OLD / 'cohort').glob('*.py')):
        inputs.append(ref(path))
        write(C / path.name, text118(path.read_text()).encode())
    for path in sorted((OLD / 'cohort').glob('*TEMPLATE*.json')):
        inputs.append(ref(path))
        write(C / path.name, text118(path.read_text()).encode())
    for name in ['current117_guard_adapter.py', 'observe_current61_current117.py',
                 'ROOT117-INPUT.TEMPLATE.NOT-AUTHORITY.json',
                 'ROOT117-OPERATION-SUCCESSOR.TEMPLATE.NOT-AUTHORITY.json',
                 'ROOT61-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json',
                 'DEPENDENCY-REVIEW.TEMPLATE.NOT-AUTHORITY.json',
                 'OBSERVER-SCHEMA.CURRENT117.SOURCE-ONLY.json',
                 'freeze_source_contract.py', 'check_source_contract.py',
                 'test117_pipeline.py']:
        path = OLD / name
        inputs.append(ref(path))
        target = name.replace('117', '118')
        write(D / target, text118(path.read_text()).encode())
    profile = read(C / 'PROFILE.TEMPLATE.SOURCE-ONLY.json')
    recipe = read(S / 'MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json')
    source = read(S / 'SOURCE-MAP-FROM116.json')
    profile['exact_commands'] = recipe['ordered_commands']
    profile['fixed_three_clock_cutoffs'] = LIMITS
    profile.pop('qualified117_source_recipe', None)
    profile['qualified118_source_recipe'] = ref(S / 'MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json')
    changes = {row['relative']: row['postimage'] for row in source['writes']}
    for row in profile['inputs']['postimages']:
        if row['relative'] in changes:
            row['postimage'] = changes[row['relative']]
    profile['producer_contract']['process_delta'] = 'Accepted116 process object retained exactly;118 adds reviewed clear_host_pte/signal-FP atop banked117 perf/VDSO; no new process body.'
    externals = []
    for relative in ['scripts/tests/fixtures/mckernel_guest_sysfs.rs', 'host-kernel/native-rust/abi/vdso.rs', 'host-kernel/native-rust/zero_pages.rs']:
        externals.append(dict(relative=relative, source=ref(Path(profile['inputs']['source6153']) / relative), container_path='/src/' + relative))
    write(D / 'EXTERNAL-THREE-MODULE-INPUTS.json', dict(scope=__doc__.splitlines()[0], runtime_authority=None, external_inputs=externals))
    profile['inputs']['external_relative_modules'] = externals
    (C / 'PROFILE.TEMPLATE.SOURCE-ONLY.json').write_text(json.dumps(profile, indent=2) + '\n')
    reuse = read(OLD / 'cohort/FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json')
    reuse.pop('genuine_new117_origin_required', None)
    reuse.update(actual_commands=recipe['ordered_commands'], genuine_new118_origin_required=True,
                 Rust_source_map=ref(S / 'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json'))
    write(C / 'FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json', reuse)
    proposal = read(S / 'ROOT-ORIGIN-PRODUCER-PROPOSAL.NOT-GRANTED.json')
    proposal['argv'][-1] = str(D / 'ROOT-ACTUAL-ORIGIN-PRODUCER-OUTPUT-1')
    write(C / 'ROOT-ORIGIN-PRODUCER-PROPOSAL.NOT-GRANTED.json', proposal)
    # Preserve the source-only manifest shape; refresh hashes after bounded edits.
    manifest = read(OLD / 'cohort/PREPARATION-MANIFEST.json')
    manifest['files'] = [ref(path) for path in sorted(C.glob('*.py'))]
    manifest['external_inputs'] = [ref(S / name) for name in [
        'SOURCE-MAP-FROM116.json', 'MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json',
        'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json', 'SOURCE-READY.json']]
    write(C / 'PREPARATION-MANIFEST.json', manifest)
    plan = read(OLD / 'cohort/PUBLICATION-ROWS.SOURCE-PLAN.NOT-AUTHORITY.json')
    plan['cached_source_refs'] = []
    for path in sorted(C.glob('*.py')):
        plan['cached_source_refs'].append(dict(actual=ref(path), fetched_equivalent_path=str(path.relative_to(Path('/home/holden/mckernel')))))
    plan['actual123source_rehash'] = False
    plan.pop('actual122source_rehash', None)
    write(C / 'PUBLICATION-ROWS.SOURCE-PLAN.NOT-AUTHORITY.json', plan)
    write(D / 'PREDECESSOR-BYTE-INPUTS.json', dict(scope=__doc__.splitlines()[0], runtime_authority=None,
                                               source_predecessor=str(OLD), inputs=inputs))
    print(json.dumps(dict(status='PRIVATE118_SOURCE_SCAFFOLD_ONLY', source_helpers=len(list(C.glob('*.py'))),
                          actual_export=0, actual_origin=0, actual_materialization=0)))


if __name__ == '__main__':
    main()
