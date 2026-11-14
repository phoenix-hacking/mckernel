"""Helper-only AST fixture. Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Do not run until independent source check releases the one observation.
No owner imports, authenticate, admission, main, build, or runtime activation.
"""
from pathlib import Path
import ast
import hashlib
import json
import os
import resource
import stat
import traceback

P = Path(__file__).resolve().parent
OWNER_KEY = 'scripts/native_running_external_modules_owner.py'
TEST_KEY = 'scripts/tests/test_native_running_external_modules_owner.py'
HELPERS = {'Refusal', 'need', 'safe_path', 'sha', 'validate_runtime_source_bindings'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def observe(result):
    manifest = json.loads((P / 'INPUT-MANIFEST.json').read_text())
    roles, expected = manifest['roles'], manifest['expected']
    assert len(roles) == len(expected) == 11 and set(roles) == set(expected)
    # Check all retained inputs before creating the exclusive fixture or executing helpers.
    for name, pin in manifest['inputs'].items():
        raw = Path(name).read_bytes()
        assert len(raw) == pin['bytes'] and digest(raw) == pin['sha256'], name
    proposal_source = Path(roles[OWNER_KEY])
    candidate_tree = ast.parse(proposal_source.read_bytes(), filename=str(proposal_source))
    assignments = {n.targets[0].id: n for n in candidate_tree.body
                   if isinstance(n, ast.Assign) and len(n.targets) == 1
                   and isinstance(n.targets[0], ast.Name)}
    sources = ast.literal_eval(assignments['SOURCES'].value)
    assert len(sources) == 11 and len(set(sources)) == 11 and set(sources) == set(roles)
    for key in sources:
        assert digest(Path(roles[key]).read_bytes()) == expected[key], key
    assert expected[TEST_KEY] == '7076a5e1b8c20a0dc7bf6b12be42e884e85feaa0fdbcdf315bd49bbd1d40aab7'
    assert expected[OWNER_KEY] != expected[TEST_KEY]
    cohort = Path(manifest['fixture'])
    assert cohort == P / 'private-installed-cohort'
    cohort.mkdir(mode=0o700)  # Exclusive creation; retain on any subsequent failure.
    for key in sources:
        destination = cohort / key
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(Path(roles[key]).read_bytes())
    observed = {key: digest((cohort / key).read_bytes()) for key in sources}
    assert observed == expected
    assert digest((cohort / OWNER_KEY).read_bytes()) == expected[OWNER_KEY]
    assert digest((cohort / TEST_KEY).read_bytes()) == expected[TEST_KEY]
    result.update(cohort=str(cohort), copied_sha256=observed, fixture_substitutions=manifest['substitutions'])
    # Parse copied owner, preserving its true origin for __file__ and compilation.
    installed = cohort / OWNER_KEY
    tree = ast.parse(installed.read_bytes(), filename=str(installed))
    selected = []
    definitions = set()
    configurations = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in HELPERS:
            selected.append(node)
            definitions.add(node.name)
        elif (isinstance(node, ast.Assign) and len(node.targets) == 1
              and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {'REPO', 'SOURCES'}):
            selected.append(node)
            configurations.add(node.targets[0].id)
    assert definitions == HELPERS and configurations == {'REPO', 'SOURCES'}
    copied_assignments = {n.targets[0].id: n for n in selected if isinstance(n, ast.Assign)}
    assert ast.dump(copied_assignments['REPO']) == ast.dump(assignments['REPO'])
    ns = {'Path': Path, 'hashlib': hashlib, 'stat': stat, '__file__': str(installed)}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(installed), 'exec'), ns)
    assert ns['REPO'] == cohort and ns['SOURCES'] == sources
    for name in HELPERS - {'Refusal'}:
        assert ns[name].__code__.co_filename == str(installed)
    result.update(extraction='AST selected five helpers plus original REPO and literal SOURCES assignments',
                  helper_code_filename=ns['validate_runtime_source_bindings'].__code__.co_filename,
                  parsed_source_origin=str(installed), original_repo_expression=ast.unparse(copied_assignments['REPO'].value),
                  derived_repo=str(ns['REPO']))
    validate = ns['validate_runtime_source_bindings']
    assert validate(expected) == expected
    result['checks'].append('complete exact11 copied cohort accepted')

    def reject(pins, message):
        try:
            validate(pins)
        except ns['Refusal'] as exc:
            assert message in str(exc), (message, str(exc))
            result['refusals'].append(str(exc))
        else:
            raise AssertionError('expected refusal: ' + message)

    missing = dict(expected)
    missing.pop(TEST_KEY)
    reject(missing, 'complete runtime source closure')
    result['checks'].append('missing key rejected')
    extra = dict(expected)
    extra['scripts/explicit-extra-negative.py'] = '0' * 64
    reject(extra, 'complete runtime source closure')
    result['checks'].append('extra key rejected')
    try:
        ns['__file__'] = str(proposal_source)  # Explicit simulated executing-origin negative.
        reject(expected, 'executing owner differs')
    finally:
        ns['__file__'] = str(installed)
        assert ns['__file__'] == str(installed)
    assert validate(expected) == expected
    result['checks'].append('simulated executing path mismatch rejected and restored')
    leaf = cohort / TEST_KEY
    original = leaf.read_bytes()
    try:
        leaf.write_bytes(original + b'\n# deliberate fixture byte-drift negative\n')
        reject(expected, 'reviewed source drift')
    finally:
        leaf.write_bytes(original)
        assert leaf.read_bytes() == original and digest(leaf.read_bytes()) == expected[TEST_KEY]
    assert validate(expected) == expected
    assert {key: digest((cohort / key).read_bytes()) for key in sources} == expected
    result['checks'].append('byte drift with unchanged pins rejected; mutated leaf restored and exact11 reverified')
    result['status'] = 'PASS_AST_EXTRACTED_HELPER_ONLY'


if __name__ == '__main__':
    result = dict(status='FAIL', checks=[], refusals=[],
                  scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
                  whole_owner_imported=False, authenticate_invoked=False, admission_invoked=False,
                  owner_main_invoked=False, cohort_is_repository_publication=False,
                  installed_consumer_acceptance=None, loaded_dependency_origin_acceptance=None,
                  actual_module_acceptance=None, native_acceptance=None, rust_retirement_acceptance=None,
                  affinity=sorted(os.sched_getaffinity(0)),
                  limits={'AS': list(resource.getrlimit(resource.RLIMIT_AS)),
                          'CPU': list(resource.getrlimit(resource.RLIMIT_CPU))})
    try:
        assert result['affinity'] == [6]
        assert resource.getrlimit(resource.RLIMIT_AS) == (1073741824, 1073741824)
        assert resource.getrlimit(resource.RLIMIT_CPU) == (20, 20)
        observe(result)
    except BaseException as exc:
        result.update(error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        with (P / 'HELPER-CHECK-RESULT.json').open('x') as stream:
            stream.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
        print(json.dumps(result, sort_keys=True), flush=True)
