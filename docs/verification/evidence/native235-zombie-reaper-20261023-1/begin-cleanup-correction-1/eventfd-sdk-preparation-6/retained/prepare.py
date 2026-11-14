"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare one private coherent SDK successor. No staging, compiler, root or Docker.
"""
from pathlib import Path
import ast
import copy
import difflib
import hashlib
import json
import stat
import time
import uuid

R = Path('/home/holden/mckernel')
E = Path(__file__).resolve().parent / 'metadata'
OLD = Path('/home/holden/mckernel-work/host-preparation/native235-procfs-delete-sdk-preparation-20261023-5/prepared-sdk')
H = Path('/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/eventfd-sdk-preparation-6/prepared-sdk')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
ALLOWED_CHANGED_SOURCES = {'smp_service.rs'}
EXPECTED = None  # Bound only from genuine accepted SOURCE-ACCEPTANCE.INPUT.json at main().

OLD_PINS = {'preparation.json': 'b04df1ec9d82ea0b5eff91ba1570ab1abf5d2035fbe3be9962c893eac37936d5', 'derived-runtime/native_running_external_modules_offline.py': 'bdcdd52cceb789778ab1c1b6ceedc743d030e64241f8a32dc674f60eb5230f1f', 'derived-runtime/native_running_external_modules_owner.py': '67aa07243f6f7e07afdc988b28c5de383cb2da07151886e67b1f6c7e8480f72b'}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def plain(path, private=True):
    assert all(not item.is_symlink() for item in (path, *path.parents)), str(path)
    meta = path.stat()
    assert stat.S_ISREG(meta.st_mode) and (not private or meta.st_nlink == 1), str(path)
    return path

def ref(path):
    return dict(path=str(path), sha256=digest(path), bytes=path.stat().st_size)

def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    path.chmod(0o600)

def write(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
    path.chmod(0o600)
    plain(path)

def pure_namespace(text, functions):
    """Execute selected actual pure bodies, never owner/container entry points."""
    tree = ast.parse(text)
    nodes = [n for n in tree.body if isinstance(n, (ast.Assign, ast.FunctionDef))
             and (isinstance(n, ast.Assign) or n.name in functions)]
    # Constant assignment statements only; do not evaluate imported runtime objects.
    nodes = [n for n in nodes if isinstance(n, ast.FunctionDef) or all(
        isinstance(t, ast.Name) and t.id in {
            'PREPARATION_SHA256', 'SOURCE_CANDIDATE_SHA', 'BASELINE_SOURCE_SHA',
            'EXACT_SOURCE_MAP', 'EXACT_DEPENDENCIES', 'REPLACEMENTS', 'KERNEL',
            'RELEASE', 'MODULES', 'SOURCE_CANDIDATE', 'CANDIDATE', 'IMAGE'}
        for t in n.targets)]
    namespace = dict(Path=Path, hashlib=hashlib, json=json, stat=stat)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<actual-pure-bodies>', 'exec'), namespace)
    return namespace

def main():
    started = time.time()
    for name, sha in OLD_PINS.items():
        assert digest(plain(OLD / name)) == sha, name
    old = json.loads((OLD / 'preparation.json').read_text())
    assert old['closure_files'] == len(old['closure']) == 68
    gate_path = E.parent / 'SOURCE-ACCEPTANCE.INPUT.json'
    gate = json.loads(plain(gate_path).read_text())
    assert gate['status'] == 'ACCEPTED_FROZEN_SOURCE_READY_FOR_SDK_PREPARATION'
    candidates = gate['candidates']
    assert type(candidates) is dict and candidates and set(candidates) <= ALLOWED_CHANGED_SOURCES
    selected = {}
    for relative, candidate in candidates.items():
        assert set(candidate) == {'path', 'sha256', 'bytes'}
        candidate_path = plain(Path(candidate['path']))
        assert digest(candidate_path) == candidate['sha256'] and candidate_path.stat().st_size == candidate['bytes']
        selected[relative] = candidate_path
    review_ref = gate['independent_source_review']
    assert set(review_ref) == {'path', 'sha256'}
    review_path = plain(Path(review_ref['path']))
    assert digest(review_path) == review_ref['sha256']
    review = json.loads(review_path.read_text())
    assert review['status'] == 'PASS' and review['decision'] == 'PASS_SOURCE'
    assert review['reviewer'] and review['implementation_ownership'] is False
    global EXPECTED
    EXPECTED = {relative: candidate['sha256'] for relative, candidate in candidates.items()}
    assert review['candidate_sha256_by_relative'] == EXPECTED
    assert gate['actual_tests'] is not None and set(gate['actual_tests']) == {'path', 'sha256'}
    assert digest(plain(Path(gate['actual_tests']['path']))) == gate['actual_tests']['sha256']
    E.mkdir(mode=0o700, exist_ok=False)
    H.mkdir(mode=0o700, exist_ok=False)
    for name in ('source-modules', 'prepared-inputs', 'derived-runtime'):
        (H / name).mkdir(mode=0o700)
    p = copy.deepcopy(old)
    deltas = []
    rows = []
    for row in p['closure']:
        source = plain(Path(row['origin']))
        assert digest(source) == row['sha256'] and source.stat().st_size == row['bytes']
        source = selected.get(row['path'], source)
        dest = H / 'source-modules' / row['path']
        write(dest, source.read_bytes())
        before = row['sha256']
        row.update(origin=str(dest), sha256=digest(dest), bytes=dest.stat().st_size)
        if before != row['sha256']:
            deltas.append(dict(relative=row['path'], old=before, new=row['sha256'], bytes=row['bytes']))
        rows.append(dict(relative=row['path'], source=ref(dest)))
    assert {row['relative'] for row in deltas} == set(EXPECTED)
    identity_rows = sorted([[r['path'], r['sha256'], r['bytes']] for r in p['closure']])
    identity = hashlib.sha256(json.dumps(identity_rows, separators=(',', ':')).encode()).hexdigest()
    input_map = dict(status='PREPARED_EXACT68_PROCFS_DELETE_SUCCESSOR_NOT_RELEASED',
                     source_identity=identity, source_identity_rows=identity_rows,
                     source_identity_encoding='SHA256 compact JSON sorted [relative,sha256,bytes] triples; retained accepted encoding',
                     rows=rows, source_files=68, source_bytes=sum(r['bytes'] for r in p['closure']),
                     logical_changed_sources=sorted(EXPECTED), changed_relative_rows=sorted(EXPECTED),
                     predecessor_preparation=ref(OLD / 'preparation.json'), predecessor_recorded_identity=old['source_identity'],
                     source_acceptance=None, execution_release=None)
    map_path = H / 'CURRENT68-PROCFS-DELETE-INPUT-MAP.json'
    save(map_path, input_map)
    p.update(source_identity=identity, source_candidate_sha=identity, current_closure_ref=ref(map_path),
             closure_bytes=input_map['source_bytes'])
    for row in p['references'].values():
        source = plain(Path(row['retained_copy']))
        assert digest(source) == row['sha256'] and source.stat().st_size == row['bytes']
        dest = H / 'prepared-inputs' / source.name
        write(dest, source.read_bytes())
        row['retained_copy'] = str(dest)
    prep = H / 'preparation.json'
    save(prep, p)
    write(H / 'prepared-inputs/preparation.json', prep.read_bytes())
    assert len(list((H / 'prepared-inputs').iterdir())) == 15
    new_map = {r['path']: [r['sha256'], r['bytes']] for r in p['closure']}
    replacement_map = {r['path']: r['sha256'] for r in p['closure'] if r['reviewed_replacement']}
    patches = []
    for name in ('native_running_external_modules_offline.py', 'native_running_external_modules_owner.py'):
        source = OLD / 'derived-runtime' / name
        before = source.read_text()
        after = before.replace(str(OLD), str(H)).replace(old['source_identity'], identity).replace(
            OLD_PINS['preparation.json'], digest(prep)).replace(str(old['closure_bytes']), str(p['closure_bytes']))
        lines = after.splitlines()
        for i, line in enumerate(lines):
            if line.startswith('EXACT_SOURCE_MAP = '):
                lines[i] = 'EXACT_SOURCE_MAP = ' + repr(new_map)
            if line.startswith('REPLACEMENTS = '):
                lines[i] = 'REPLACEMENTS = ' + repr(replacement_map)
        after = '\n'.join(lines) + '\n'
        ast.parse(after)
        write(H / 'derived-runtime' / name, after.encode())
        patches.append(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                   fromfile=str(source), tofile=str(H / 'derived-runtime' / name))))
    write(E / 'DERIVED-RUNTIME.patch', '\n'.join(patches).encode())
    cohort = json.loads((OLD / 'RUNTIME-COHORT.json').read_text())
    for name, row in cohort.items():
        source = plain(Path(row['path']), private=False)
        assert digest(source) == row['sha256'] and source.stat().st_size == row['bytes']
        cohort[name] = ref(H / 'derived-runtime' / source.name) if source.parent == OLD / 'derived-runtime' else row
    save(H / 'RUNTIME-COHORT.json', cohort)
    request = json.loads((OLD / 'REQUEST.TEMPLATE.PENDING-LIVE-IDENTITIES.json').read_text())
    nonce = uuid.uuid4().hex
    output = '/home/holden/mckernel-work/host-preparation/native-running-modules-host-output/'
    request.update(nonce=nonce, request_path=str(H / 'request.json'),
                   preparation=dict(path=str(prep), sha256=digest(prep)),
                   driver=dict(path=str(H / 'derived-runtime/native_running_external_modules_offline.py'),
                               sha256=digest(H / 'derived-runtime/native_running_external_modules_offline.py')),
                   candidate_root=output + 'native-running-modules-candidate-' + nonce,
                   owner_evidence_root=output + 'native-running-modules-owner-' + nonce,
                   input_root='/home/holden/mckernel-work/scratch/native-running-modules-inputs-' + nonce)
    for key in ('candidate_identity', 'input_identity', 'backing_identity', 'basis_identity', 'output_parent_identity'):
        request[key] = None
    template = H / 'REQUEST.TEMPLATE.PENDING-LIVE-IDENTITIES.json'
    save(template, request)
    stage_source = Path('/home/holden/mckernel-work/host-preparation/native235-procfs-delete-sdk-preparation-20261023-5/metadata/stage_bound_successor.py')
    stage = stage_source.read_text().replace(str(OLD), str(H)).replace(OLD_PINS['preparation.json'], digest(prep)).replace(
        '9c96ba665d8d4ef19f81420e9fe33814', nonce).replace(
        'a54063def7631367ef32427b9c730a3d68ad37c1344e0a338eb8f1dadecd0719', digest(template))
    ast.parse(stage)
    write(E / 'stage_bound_successor.py', stage.encode())
    write(E / 'MATERIALIZER.patch', ''.join(difflib.unified_diff(
        stage_source.read_text().splitlines(True), stage.splitlines(True),
        fromfile=str(stage_source), tofile=str(E / 'stage_bound_successor.py'))).encode())
    driver_text = (H / 'derived-runtime/native_running_external_modules_offline.py').read_text()
    pure = pure_namespace(driver_text, {'require', 'digest', 'plain', 'load_preparation',
                                      'source_provenance', 'adoption_compile_mode', 'plan'})
    loaded = pure['load_preparation'](prep)
    plan = pure['plan'](loaded)
    assert plan['argv'] == old['proposed_external_command'] and plan['argv'][-3:] == ['--jobserver-style=pipe', '-j2', 'modules']
    owner_text = (H / 'derived-runtime/native_running_external_modules_owner.py').read_text()
    owner_pure = pure_namespace(owner_text, {'validate_preparation'})
    def need(condition, message):
        assert condition, message
    owner_pure['need'] = need
    owner_pure['validate_preparation'](p)
    assert 'meta.st_size == 110 * 2**30' in owner_text
    assert old['source_dependency_sets'] == p['source_dependency_sets']
    # All executable bodies except the exact closure-byte predicates remain identical.
    ast_checks = []
    for name in ('native_running_external_modules_offline.py', 'native_running_external_modules_owner.py'):
        before = (OLD / 'derived-runtime' / name).read_text().replace(str(OLD), str(H)).replace(
            str(old['closure_bytes']), str(p['closure_bytes']))
        after = (H / 'derived-runtime' / name).read_text()
        bodies = lambda text: [ast.dump(n, include_attributes=False) for n in ast.parse(text).body
                               if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        assert bodies(before) == bodies(after), name
        ast_checks.append(name + ': all executable function/class AST bodies unchanged except exact source-byte predicate')
    assert (H / 'source-modules/mcctrl.rs').read_bytes() == (H / 'source-modules/mcctrl_rust.rs').read_bytes()
    for name in ('current_fork_control.rs', 'mcctrl_vm.rs', 'mcctrl_process.rs', 'mcctrl.rs', 'mcctrl_rust.rs', 'mcctrl_vm_write_compat.c', 'mcctrl_vm_write_compat.h'):
        assert (H / 'source-modules' / name).read_bytes() == (OLD / 'source-modules' / name).read_bytes()
    for name, sha in OLD_PINS.items():
        assert digest(OLD / name) == sha
    summary = dict(scope=SCOPE, status='HOST_SOURCE_AND_DERIVED_RUNTIME_PREPARED_NO_BUILD_NO_RELEASE',
                   host_root=str(H), source_identity=identity, predecessor_identity=old['source_identity'],
                   source_files=68, source_bytes=p['closure_bytes'], deltas=deltas,
                   nonce_reserved_not_executed=nonce, preparation=ref(prep),
                   derived_driver=ref(H / 'derived-runtime/native_running_external_modules_offline.py'),
                   derived_owner=ref(H / 'derived-runtime/native_running_external_modules_owner.py'),
                   runtime_cohort=ref(H / 'RUNTIME-COHORT.json'), request_template=ref(template),
                   materializer=ref(E / 'stage_bound_successor.py'),
                   external_command=p['proposed_external_command'],
                   source_acceptance=None, source_review=dict(path=str(review_path), sha256=digest(review_path)), execution_release=None, compiler_runs=0, root_operations=0,
                   Docker_operations=0, scratch_writes=0,
                   profile_unchanged=dict(container_CPUs='2-5', container_memory_bytes=12*1024**3,
                                          container_swap=0, container_tasks=512, make_jobs=2, network='none', backing_GiB=110),
                   expected_binary_delta=dict(ihk='stable expected; verify actual build', ihk_smp_x86_64='change expected iff accepted smp_application.rs/smp_service.rs/procfs_objects.rs provider delta; actual artifact proof required', mcctrl='stable06e8 expected; actual artifact proof required'),
                   required_next=['independent coherent SDK preparation review',
                                  'root source/input staging and fresh live identities/capacity/leases',
                                  'independent exact execution release', 'actual module build and artifact/physical review'])
    save(H / 'PREPARATION-RESULT.json', summary)
    save(E / 'PREPARATION-RESULT.json', summary)
    validation = dict(scope=SCOPE, status='PASS_PURE_DERIVED_DRIVER_AND_OWNER_PREPARATION_CHECKS',
                      actual_pure_bodies=['driver.load_preparation', 'driver.plan', 'owner.validate_preparation'],
                      checks=ast_checks + ['exact independently accepted nonempty selected subset of smp_application.rs/smp_service.rs/procfs_objects.rs only; current_fork_control812/mcctrl_vmba95/WAIT8bf and entry aliases unchanged', '15 exact small prepared inputs',
                                            'unchanged source dependency sets', 'unchanged compatibility MM sources and all runtime check bodies',
                                            'unchanged110GiB owner geometry; fresh nonce/output roots', 'accepted predecessor pins unchanged'],
                      plan=plan, elapsed_seconds=time.time()-started, staging_executed=False,
                      execution_release=False, compiler_runs=0, root_operations=0, Docker_operations=0)
    save(H / 'PURE-PREPARATION-VALIDATION.json', validation)
    save(E / 'PURE-PREPARATION-VALIDATION.json', validation)
    next_command = ['/usr/bin/taskset', '-c', '0', '/usr/bin/prlimit', '--as=2147483648:2147483648',
                    '--cpu=30:30', '--fsize=134217728:134217728', '--nofile=256:256', '--core=0:0', '--',
                    '/usr/bin/timeout', '--signal=TERM', '--kill-after=3', '35',
                    '/home/holden/anaconda3/bin/python3', '-I', '-B', str(E / 'stage_bound_successor.py'), '--execute']
    save(E / 'REVIEW-READY-NEXT-COMMAND.json', dict(scope=SCOPE, status='READY_FOR_INDEPENDENT_REVIEW_NO_EXECUTION_RELEASE',
         preparation=ref(prep), result=ref(E / 'PREPARATION-RESULT.json'), validation=ref(E / 'PURE-PREPARATION-VALIDATION.json'),
         exact_next_staging_argv=next_command, staging_owner='root dispatcher only; CPU slot must be coordinated',
         actual_build_requires='fresh root identities and reviewed one-shot release; request template is not live authority',
         geometry='110GiB frozen accepted profile; reconcile separately if scratch growth precedes build'))
    print(json.dumps({key:summary[key] for key in ['status', 'source_identity', 'source_files', 'source_bytes',
                                                  'nonce_reserved_not_executed', 'preparation', 'derived_driver', 'derived_owner']}, indent=2))

if __name__ == '__main__':
    main()
