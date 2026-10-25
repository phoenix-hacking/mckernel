"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure binding regression: selected constants and four validator functions only.
No owner import, Docker, privilege, compiler, install, CLI or device operation.
"""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import stat

PINS = {'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/target_tools_sdk_owner.py': '2ec8e85696e47f9abcfa2a5eeada22880471ecdd022dc89424480d950184a03f', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/target_tools_sdk_driver.py': 'b15e0a5bc85c8d517c7804aba5e0d0e36ca76231a7dd672221b2839a29f2c328', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json': '6b2ed04a5d0c676dea2f6cea8cb1275ca13cc303ea2a6f3e0d4bb71ef491b7b6', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/READY.SDK-INSTALL-OWNER-FOUR-PHASES.SOURCE-ONLY.NOT-RELEASED.json': 'ff783ff1eb81291dbd9429d96f3349817f9510fa6ad2d6c2ac5730e37401659a', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/TARGET-INSTALL.INPUTS.json': '6ccc4485a58d68ace817ec5fc59b1db98f1fa8b13652dd1534cfa426d87c6ca1', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/preparation.json': '8e7675d63115699d84defd9a5f23a13c0c374f93e529dad8f4e8c6926d1d9d13', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/REQUEST.ROOT.FINAL.json': '74def32a434f42ddeb3abd90ca5c728d43696262fdf387fd4059575533775fea', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/EXACT-FOUR-INSTALL-LOADER-COMMANDS.NOT-RELEASED.json': 'd135c5b83d03e1d9dc3f6761b3e15afae5f306972e91153bc94c5bc298641ecc'}
OWNER = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/target_tools_sdk_owner.py')
SOURCE_MAP = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit('Source only; explicit ordinary root grant required')
    for path, expected in PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('frozen cohort source changed: ' + path)
    tree = ast.parse(OWNER.read_bytes(), str(OWNER))
    names = {'REPO', 'DRIVER', 'SOURCES', 'RUNTIME_SOURCE_PATHS', 'RUNTIME_PARENT'}
    functions = {'need', 'sha', 'safe_path', 'validate_runtime_source_bindings'}
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in names
            or isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
            and target.value.id == 'RUNTIME_SOURCE_PATHS' for target in node.targets
        ):
            nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            nodes.append(node)
    if {n.name for n in nodes if isinstance(n, ast.FunctionDef)} != functions:
        raise ValueError('exact four unchanged source-binding functions required')
    class Refusal(Exception):
        pass
    namespace = {'Path': Path, 'hashlib': hashlib, 'stat': stat,
                 '__file__': str(OWNER), 'Refusal': Refusal}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(OWNER), 'exec'), namespace)
    expected = json.loads(SOURCE_MAP.read_text())['source_sha256']
    observed = namespace['validate_runtime_source_bindings'](expected)
    if observed != expected or len(observed) != 11:
        raise ValueError('positive exact-eleven binding failed')
    rows = [{'case': 'effective-eleven-positive', 'status': 'PASS'}]
    original_paths = copy.deepcopy(namespace['RUNTIME_SOURCE_PATHS'])
    def reject(label, source_map, message, executing=None, paths=None):
        namespace['__file__'] = executing or str(OWNER)
        namespace['RUNTIME_SOURCE_PATHS'] = paths or copy.deepcopy(original_paths)
        try:
            namespace['validate_runtime_source_bindings'](source_map)
        except Refusal as error:
            if str(error) != message:
                raise ValueError(label + ': wrong refusal ' + str(error))
        else:
            raise ValueError(label + ': expected refusal absent')
        rows.append({'case': label, 'status': 'PASS', 'expected_refusal': message})
    missing = dict(expected); missing.pop('scripts/native_running_external_modules_owner.py')
    reject('missing-owner-source', missing, 'complete runtime source closure required')
    extra = dict(expected, extra_source='0' * 64)
    reject('extra-source', extra, 'complete runtime source closure required')
    for name in ('scripts/native_running_external_modules_owner.py',
                 'scripts/native_running_external_modules_offline.py'):
        changed = dict(expected); changed[name] = '0' * 64
        reject('wrong-hash-' + Path(name).stem, changed, 'reviewed source drift')
    old_parent = namespace['RUNTIME_PARENT']
    reject('historical-owner-entry', expected,
           'executing owner differs from installed runtime source',
           executing=str(old_parent / 'native_running_external_modules_owner.py'))
    stale_paths = dict(original_paths)
    stale_paths['scripts/native_running_external_modules_owner.py'] = str(old_parent / 'native_running_external_modules_owner.py')
    reject('missing-final-owner-override', expected,
           'executing owner differs from installed runtime source', paths=stale_paths)
    stale_driver = dict(original_paths)
    stale_driver['scripts/native_running_external_modules_offline.py'] = str(old_parent / 'native_running_external_modules_offline.py')
    reject('missing-final-driver-override', expected, 'reviewed source drift', paths=stale_driver)
    namespace['__file__'] = str(OWNER)
    namespace['RUNTIME_SOURCE_PATHS'] = original_paths
    if namespace['validate_runtime_source_bindings'](expected) != expected:
        raise ValueError('final unchanged positive rejoin failed')
    rows.append({'case': 'final-positive-rejoin', 'status': 'PASS'})
    result = {'scope': __doc__.splitlines()[0], 'status': 'PASS_EFFECTIVE_ELEVEN_SOURCE_BINDING_REGRESSION',
              'cases': rows, 'source_pins': PINS, 'effective_source_sha256': observed,
              'production_source_changed': False, 'runtime_imported': False,
              'native_or_retirement_credit': 0}
    args.output.mkdir(mode=0o700)
    (args.output / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'cases': len(rows), 'sources': len(observed)}))


if __name__ == '__main__':
    main()
