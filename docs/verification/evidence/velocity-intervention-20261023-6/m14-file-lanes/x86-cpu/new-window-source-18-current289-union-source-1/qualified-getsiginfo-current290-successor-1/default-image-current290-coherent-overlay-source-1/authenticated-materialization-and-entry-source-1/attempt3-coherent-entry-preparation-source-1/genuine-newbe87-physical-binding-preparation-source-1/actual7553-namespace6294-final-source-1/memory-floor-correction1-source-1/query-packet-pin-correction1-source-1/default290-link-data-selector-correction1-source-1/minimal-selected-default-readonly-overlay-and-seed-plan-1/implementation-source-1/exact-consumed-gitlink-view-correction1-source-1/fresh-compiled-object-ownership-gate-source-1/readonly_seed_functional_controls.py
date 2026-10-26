#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Effect-free production-function extraction; no owner import, subprocess or probe.
The seed-copy control writes only its disposable directory. It substitutes only
three fixed container aliases in the extracted production function and mocks
input reauthentication (tested separately through real retained files).
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import tempfile

HERE = Path(__file__).resolve().parent
READY = json.loads((HERE / 'IMPLEMENTED-SUCCESSORS.SOURCE-ONLY.json').read_text())
FIXED = json.loads(Path(READY['inputs']['path']).read_text())
RESULTS = []

def reject(action):
    try:
        action()
    except (RuntimeError, AssertionError, FileNotFoundError):
        return
    raise AssertionError('negative accepted')

def check(name, action):
    action()
    RESULTS.append(dict(name=name, status='PASS'))

def require(value, message='check failed'):
    if not value:
        raise AssertionError(message)

def source(key):
    row = READY[key]
    data = Path(row['path']).read_bytes()
    require(len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'])
    return data.decode()

DRIVER = source('driver')
OWNER = source('owner')

def extract(text, names, scope, transform=None):
    selected = []
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            if transform:
                node = transform.visit(copy.deepcopy(node))
            selected.append(node)
    require({node.name for node in selected} == set(names), 'missing production extraction')
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])), '<actual-production-function-extraction>', 'exec'), scope)

scope = dict(_REUSE_IDENTITY_BASELINE={}, Path=Path, hashlib=hashlib, os=os, json=json, shlex=shlex,
             shutil=shutil, _REUSE_FIXED=FIXED,
             _REUSE_INPUT_SHA256=READY['inputs']['sha256'],
             _REUSE_INPUT_BYTES=READY['inputs']['bytes'])
extract(DRIVER, ['_reuse_require', '_reuse_file', '_reuse_layout', '_reuse_authenticate', '_reuse_mounts', '_reuse_commands'], scope)

def unchanged_ast():
    for old_key, new_text in [('original_driver', DRIVER), ('original_owner', OWNER)]:
        before = ast.parse(source(old_key))
        after = ast.parse(new_text)
        for original in before.body:
            if isinstance(original, (ast.FunctionDef, ast.ClassDef)):
                first = next(node for node in after.body if isinstance(node, type(original)) and node.name == original.name)
                require(ast.dump(first, include_attributes=False) == ast.dump(original, include_attributes=False), original.name + ' original AST changed')
check('all-original-driver-and-owner-function-class-ASTs-preserved', unchanged_ast)
check('actual-frozen-layout', lambda: scope['_reuse_layout'](FIXED))
for key, mutate in [
    ('extra-overlay', lambda value: value['postimages'].append(copy.deepcopy(value['postimages'][0]))),
    ('wrong-overlay-hash', lambda value: value['postimages'][0]['postimage'].update(sha256='0' * 64)),
    ('wrong-overlay-host-path', lambda value: value['postimages'][0]['postimage'].update(path='/arbitrary/input')),
    ('wrong-overlay-target', lambda value: value['postimages'][0].update(container_destination='/work/evil')),
    ('writable-overlay', lambda value: value['postimages'][0].update(readonly=False)),
    ('missing-eleventh-object', lambda value: value['objects'].pop()),
    ('wrong-reused-object-count', lambda value: value['objects'][0].update(replace=True)),
    ('wrong-seed-hash', lambda value: value['objects'][0]['source'].update(sha256='0' * 64)),
    ('escaping-seed-destination', lambda value: value['objects'][0].update(build_relative='../escape')),
    ('wrong-MODULES-END-hash', lambda value: value['configuration'][-2]['source'].update(sha256='0' * 64)),
]:
    def negative(mutate=mutate):
        value = copy.deepcopy(FIXED)
        mutate(value)
        reject(lambda: scope['_reuse_layout'](value))
    check(key, negative)

# Actual retained archive/member/11-object/config/postimage hashes: read only.
check('real-retained-source-archive-11-objects-and-config-authentication', lambda: scope['_reuse_authenticate'](READY['inputs']['path']))

def command_control():
    commands = scope['_reuse_commands']()
    require([phase for phase, _ in commands] == ['recompile-full-Rust', 'recompile-process', 'raw-ld-11-inputs'])
    rust, process, link = [argv for _, argv in commands]
    require(rust[:3] == ['/usr/bin/cmake', '-E', 'env'])
    require('/nightly/bin/rustc' in rust and rust[-1] == '/src/kernel/rust/lib.rs')
    require(not any('codegen-units' in token for token in rust))
    require(process.count('-DMCKERNEL_RUST_PROCESS_GLOBAL_STORAGE') == 1)
    original = shlex.split(FIXED['commands']['process_command_selected_original']['command'])
    require([token for token in process if token != '-DMCKERNEL_RUST_PROCESS_GLOBAL_STORAGE'] == original)
    require(link[0] == '/usr/bin/ld')
    require([token for token in link if token.endswith('.o')] == [row['link_token'] for row in FIXED['objects']])
check('actual-two-compile-commands-plus-ordered-11-input-raw-ld', command_control)

def mount_control():
    mounts = scope['_reuse_mounts'](READY['inputs']['path'])
    require(len(mounts) == 9 and all(readonly is True for _, _, readonly in mounts))
    require({target for _, target, _ in mounts if target.startswith('/src/')} == {row['container_destination'] for row in FIXED['postimages']})
    require('/work' not in {target for _, target, _ in mounts})
    owner_tree = ast.parse(OWNER)
    original_class = next(node for node in owner_tree.body if isinstance(node, ast.ClassDef) and node.name == 'ImageOwner')
    reused_class = [node for node in owner_tree.body if isinstance(node, ast.ClassDef) and node.name == 'ImageOwner'][-1]
    original = next(node for node in original_class.body if isinstance(node, ast.FunctionDef) and node.name == 'run')
    reused = next(node for node in reused_class.body if isinstance(node, ast.FunctionDef) and node.name == '_reuse_run')
    require(any(isinstance(node, ast.Name) and node.id == 'RESOURCE_ARGS' for node in ast.walk(reused)))
    exact_sole_RW = ast.parse("rw_mounts == [(bound['work'], '/work')]", mode='eval').body
    require(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '_fail' and node.args and ast.dump(node.args[0], include_attributes=False) == ast.dump(exact_sole_RW, include_attributes=False) for node in ast.walk(reused)), 'actual sole work RW predicate missing')
    # Remove exactly the two allowed source additions and normalize name.
    normalized = copy.deepcopy(reused)
    normalized.name = 'run'
    additions = []
    for node in ast.walk(normalized):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                kept = []
                for item in value:
                    mount_addition = isinstance(item, ast.Expr) and isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Attribute) and isinstance(item.value.func.value, ast.Name) and item.value.func.value.id == 'mounts' and item.value.func.attr == 'extend' and len(item.value.args) == 1 and isinstance(item.value.args[0], ast.Call) and isinstance(item.value.args[0].func, ast.Name) and item.value.args[0].func.id == '_reuse_mounts'
                    command_addition = isinstance(item, ast.AugAssign) and isinstance(item.target, ast.Name) and item.target.id == 'command' and isinstance(item.op, ast.Add) and isinstance(item.value, ast.List) and len(item.value.elts) == 2 and all(isinstance(element, ast.Constant) for element in item.value.elts) and [element.value for element in item.value.elts] == ['--readonly-reuse-inputs', '/reuse-inputs.json']
                    if mount_addition or command_addition:
                        additions.append(item)
                    else:
                        kept.append(item)
                setattr(node, field, kept)
    require(len(additions) == 2)
    require(ast.dump(normalized, include_attributes=False) == ast.dump(original, include_attributes=False), 'owner engine changed outside mount/argv additions')
check('exact-readonly-mounts-and-owner-engine-AST-only-two-additions', mount_control)


# Exercise the actual host profile predicate and actual image mount predicate;
# imports and all transports remain excluded.
import types
host_path = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py')
host_text = host_path.read_text()
require(hashlib.sha256(host_text.encode()).hexdigest() == '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1')
host_scope = {}
limit_node = next(node for node in ast.parse(host_text).body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'LIMITS' for target in node.targets))
exec(compile(ast.Module(body=[limit_node], type_ignores=[]), '<actual-LIMITS-expression>', 'exec'), host_scope)
extract(host_text, ['check_profile'], host_scope)
profile_scope = dict(_fail=require)
extract(OWNER, ['_check_profile'], profile_scope)
mounts = scope['_reuse_mounts'](READY['inputs']['path']) + [(Path('/future-owner-work'), '/work', False)]
profile = dict(Image='sha256:fixed-test-image', State=dict(Status='created'),
               Config=dict(Labels={'mckernel.owner': 'test-nonce'}, Entrypoint=['/usr/bin/python3'], Cmd=['/driver.py', '--readonly-reuse-inputs', '/reuse-inputs.json'], User='1000:1000'),
               HostConfig=dict(host_scope['LIMITS'], Privileged=False, ReadonlyRootfs=True, CapDrop=['ALL'], SecurityOpt=['no-new-privileges'], Init=True, IpcMode='private', Tmpfs={'/tmp': 'rw,nodev,nosuid,size=256m'}),
               Mounts=[dict(Type='bind', Source=str(source), Destination=target, RW=not readonly) for source, target, readonly in mounts])
def validate_profile(value):
    return profile_scope['_check_profile'](value, 'sha256:fixed-test-image', 'test-nonce', mounts=mounts, command=profile['Config']['Cmd'], user='1000:1000', host_owner=types.SimpleNamespace(check_profile=host_scope['check_profile']))
check('actual-host-and-image-profile-positive-with-only-one-work-RW', lambda: validate_profile(profile))
for name, mutate in [
    ('CPU-affinity-expanded', lambda value: value['HostConfig'].update(CpusetCpus='0-7')),
    ('memory-expanded', lambda value: value['HostConfig'].update(Memory=16 * 2**30)),
    ('swap-expanded', lambda value: value['HostConfig'].update(MemorySwap=16 * 2**30)),
    ('task-cap-expanded', lambda value: value['HostConfig'].update(PidsLimit=1024)),
    ('network-enabled', lambda value: value['HostConfig'].update(NetworkMode='host')),
    ('writable-overlay-profile', lambda value: value['Mounts'][0].update(RW=True)),
    ('extra-bind-profile', lambda value: value['Mounts'].append(dict(Type='bind', Source='/extra', Destination='/extra', RW=False))),
    ('wrong-driver-command-profile', lambda value: value['Config'].update(Cmd=['/other.py'])),
]:
    def negative_profile(mutate=mutate):
        value = copy.deepcopy(profile)
        mutate(value)
        reject(lambda: validate_profile(value))
    check(name, negative_profile)

with tempfile.TemporaryDirectory(prefix='readonly-seed-control-', dir=HERE) as temporary:
    temp = Path(temporary)
    sample = temp / 'sample'
    sample.write_bytes(b'functional seed bytes\n')
    row = dict(bytes=sample.stat().st_size, sha256=hashlib.sha256(sample.read_bytes()).hexdigest())
    check('stable-disposable-input-positive', lambda: scope['_reuse_file'](sample, row))
    check('wrong-disposable-input-hash', lambda: reject(lambda: scope['_reuse_file'](sample, dict(row, sha256='0' * 64))))
    check('wrong-disposable-input-size', lambda: reject(lambda: scope['_reuse_file'](sample, dict(row, bytes=0))))
    missing = temp / 'missing'
    check('missing-disposable-input', lambda: reject(lambda: scope['_reuse_file'](missing, row)))
    link = temp / 'link'
    link.symlink_to(sample)
    check('symlink-disposable-input', lambda: reject(lambda: scope['_reuse_file'](link, row)))

    def seed_copy_control():
        build = temp / 'fresh-build'
        build.mkdir(mode=0o700)
        evidence = temp / 'evidence'
        evidence.mkdir(mode=0o700)
        class AliasOnly(ast.NodeTransformer):
            def visit_Constant(self, node):
                aliases = {'/work/output/build': str(build), '/seed-build': FIXED['seed_root']}
                if isinstance(node.value, str) and node.value in aliases:
                    return ast.copy_location(ast.Constant(aliases[node.value]), node)
                return node
        local = dict(scope)
        local['_reuse_authenticate'] = lambda *args, **kwargs: None
        def atomic(path, value):
            Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
        local['_atomic_json'] = atomic
        extract(DRIVER, ['_reuse_prepare_build'], local, AliasOnly())
        local['_reuse_prepare_build'](build, evidence)
        actual = {str(path.relative_to(build)) for path in build.rglob('*') if path.is_file()}
        expected = {row['build_relative'] for row in FIXED['configuration']} | {row['build_relative'] for row in FIXED['objects'] if not row['replace']}
        require(actual == expected)
        require(not any((build / row['build_relative']).exists() for row in FIXED['objects'] if row['replace']))
        for selected in FIXED['objects']:
            if not selected['replace']:
                scope['_reuse_file'](build / selected['build_relative'], selected['source'])
        database = json.loads((build / 'compile_commands.json').read_text())
        selected = next(row for row in database if row['file'] == '/src/kernel/process.c')
        require(shlex.split(selected['command']) == FIXED['commands']['process_command_expected_argv'])
        derivation = json.loads((evidence / 'readonly-reuse-command-derivation.json').read_text())
        require(derivation['fresh_full_configure'] is False)
        reject(lambda: local['_reuse_prepare_build'](build, evidence))
    check('actual-seed-import-function-disposable-nine-objects-config-and-freshness-negative', seed_copy_control)


# Execute the actual source-view wrapper and actual comparison against real
# disposable trees. Only the independent base-source proof and archive proof
# are replaced; neither view enumeration nor membership/hash/mode/symlink
# validation is mocked. Container alias translation is the only path adapter.
def actual_view_case(mutation=None):
    with tempfile.TemporaryDirectory(prefix='effective-view-control-', dir=HERE) as temporary:
        temporary = Path(temporary)
        base, effective = temporary / 'base', temporary / 'effective'
        base.mkdir(mode=0o700)
        vendor_key = 'executer/user/lib/libdwarf/libdwarf'
        (base / vendor_key).mkdir(mode=0o700, parents=True)
        for relative in ('kernel/CMakeLists.txt', 'kernel/rust/lib.rs', 'kernel/rust/syscall_policy.rs', 'unchanged.txt'):
            path = base / relative
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.write_text('original ' + relative)
        (base / 'ordinary-link').symlink_to('unchanged.txt')
        shutil.copytree(base, effective, symlinks=True)
        postimages = []
        for relative in ('kernel/CMakeLists.txt', 'kernel/rust/lib.rs', 'kernel/rust/syscall_policy.rs'):
            path = effective / relative
            path.write_text('corrected ' + relative)
            postimages.append(dict(relative=relative, postimage=dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())))
        vendor = effective / vendor_key
        (vendor / '.git').mkdir(mode=0o700)
        (vendor / 'vendor.c').write_text('retained vendor bytes')
        (vendor / '.git/HEAD').write_text('retained vendor metadata')
        def snapshot(root):
            rows = {'.': root}
            for parent, dirs, files in os.walk(root, followlinks=False):
                for name in dirs + files:
                    path = Path(parent) / name
                    rows[str(path.relative_to(root))] = path
            result = {}
            for relative, path in rows.items():
                row = dict(mode=path.lstat().st_mode, kind='directory' if path.is_dir() else 'regular')
                if path.is_file():
                    row.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                result[relative] = row
            return result
        base_manifest = temporary / 'base-manifest.json'
        vendor_manifest = temporary / 'vendor-manifest.json'
        base_manifest.write_text('{}\n')
        vendor_manifest.write_text('{}\n')
        file_ref = lambda path: dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        consumed = [dict(path=vendor_key, entries=snapshot(vendor), manifest=file_ref(vendor_manifest))]
        local = dict(scope)
        local['_REUSE_IDENTITY_BASELINE'] = {}
        local['_REUSE_FIXED'] = dict(candidate_sha='fixture-candidate', ihk_sha='fixture-ihk', base_manifest=file_ref(base_manifest), postimages=postimages)
        local['_REUSE_CONSUMED_GITLINK_VIEWS'] = consumed
        aliases = {'/base-src': base, '/src': effective, '/libdwarf-inputs.json': vendor_manifest}
        def alias_path(value):
            return aliases.get(str(value), Path(value))
        local['Path'] = alias_path
        local['_sha256'] = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        base_calls = []
        def base_proof(root, candidate, ihk, manifest, git):
            require(root == base and candidate == 'fixture-candidate' and ihk == 'fixture-ihk' and manifest == base_manifest)
            base_calls.append(root)
            return dict(status='DISPOSABLE_BASE_PROOF_STUB')
        local['_validate_source'] = base_proof
        local['_reuse_authenticate'] = lambda path, **kwargs: require(path == '/reuse-inputs.json' and kwargs == dict(container=True))
        extract(DRIVER, ['_reuse_require', '_reuse_file', '_reuse_view_entries', '_reuse_compare_source_views', '_reuse_validate_source'], local)
        if mutation:
            mutation(base, effective, vendor, consumed)
        observed = local['_reuse_validate_source']('/src', 'fixture-candidate', 'fixture-ihk', base_manifest, None)
        require(observed == dict(status='DISPOSABLE_BASE_PROOF_STUB') and len(base_calls) == 1)
check('actual-production-source-view-positive-exact-vendor-and-three-overlays', actual_view_case)
for name, mutation in [
    ('unrelated-extra-effective-file', lambda base, effective, vendor, consumed: (effective / 'unrelated-extra').write_text('extra')),
    ('ordinary-symlink-target-changed', lambda base, effective, vendor, consumed: ((effective / 'ordinary-link').unlink(), (effective / 'ordinary-link').symlink_to('kernel/CMakeLists.txt'))),
    ('ordinary-source-file-missing', lambda base, effective, vendor, consumed: (effective / 'unchanged.txt').unlink()),
    ('ordinary-source-file-changed', lambda base, effective, vendor, consumed: (effective / 'unchanged.txt').write_text('changed')),
    ('consumed-vendor-tracked-file-changed', lambda base, effective, vendor, consumed: (vendor / 'vendor.c').write_text('wrong vendor bytes')),
    ('consumed-vendor-metadata-changed', lambda base, effective, vendor, consumed: (vendor / '.git/HEAD').write_text('wrong metadata')),
    ('consumed-vendor-file-missing', lambda base, effective, vendor, consumed: (vendor / 'vendor.c').unlink()),
    ('consumed-vendor-extra-file', lambda base, effective, vendor, consumed: (vendor / 'undeclared').write_text('extra')),
    ('consumed-vendor-mount-missing', lambda base, effective, vendor, consumed: shutil.rmtree(vendor)),
    ('wrong-consumed-vendor-root', lambda base, effective, vendor, consumed: consumed[0].update(path='executer/user/lib/other')),
    ('base-consumed-directory-not-empty', lambda base, effective, vendor, consumed: (base / 'executer/user/lib/libdwarf/libdwarf/unexpected').write_text('extra')),
]:
    check(name, lambda mutation=mutation: reject(lambda: actual_view_case(mutation)))


# Run the actual mandatory fresh-object gate on a disposable copy of the
# already qualified real whole-Rust object. No compiler or object execution.
# Only fixed container paths are mapped to retained host inputs/disposables.
import struct
PERF = Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/default290-corrected-real-crate-source-1')
QUALIFIED_OBJECT = PERF / 'output-1/corrected-current290-rust.o'
require(hashlib.sha256(QUALIFIED_OBJECT.read_bytes()).hexdigest() == 'f9d2e56657c47e22dbea5c84df13eea7d04071239b6732e9ab5dae05621c2003')
OLD_OBJECT = Path(FIXED['seed_root']) / 'kernel/rust/mckernel_rust.o'
POLICY = PERF / 'candidate/kernel/rust/syscall_policy.rs'
helper_names = {'_ReuseElf', '_reuse_elf_object_bytes', '_reuse_elf_owning_relocations', '_reuse_elf_cstring', '_reuse_elf_descriptor', '_reuse_elf_function', '_reuse_elf_undefined', '_reuse_elf_panic_targets', '_reuse_validate_changed_rust_object'}
helper_nodes = [node for node in ast.parse(DRIVER).body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in helper_names]
require({node.name for node in helper_nodes} == helper_names)

def actual_object_gate_case(mutation=None, use_old=False):
    with tempfile.TemporaryDirectory(prefix='whole-object-gate-control-', dir=HERE) as temporary:
        temporary = Path(temporary)
        build, evidence = temporary / 'build', temporary / 'evidence'
        target = build / 'kernel/rust/mckernel_rust.o'
        target.parent.mkdir(mode=0o700, parents=True)
        evidence.mkdir(mode=0o700)
        shutil.copyfile(OLD_OBJECT if use_old else QUALIFIED_OBJECT, target)
        local = dict(Path=lambda value: {'/seed-build/kernel/rust/mckernel_rust.o': OLD_OBJECT, '/src/kernel/rust/syscall_policy.rs': POLICY}.get(str(value), Path(value)), struct=struct, hashlib=hashlib,
                     _fail=require, _reuse_require=require)
        def artifact(path, label):
            path = Path(path)
            before = path.stat()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            after = path.stat()
            require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns))
            return dict(path=str(path), size=after.st_size, sha256=digest, inode=after.st_ino, device=after.st_dev, mode=after.st_mode & 0o7777, mtime_ns=after.st_mtime_ns, ctime_ns=after.st_ctime_ns)
        local['_artifact'] = artifact
        local['_atomic_json'] = lambda path, value: Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
        exec(compile(ast.Module(body=helper_nodes, type_ignores=[]), '<actual-mandatory-object-gate-and-qualified-helpers>', 'exec'), local)
        if mutation:
            elf = local['_ReuseElf'](target)
            logger = next(row for row in elf.symbols if 'F06_PROCESS_VM_IOV_LOCAL_DEBUG' in row['name'] and row['type'] == 1)
            raw = bytearray(target.read_bytes())
            mutation(raw, elf, logger)
            target.write_bytes(raw)
        result = local['_reuse_validate_changed_rust_object'](build, evidence)
        require(result['mandatory_fresh_compiled_object_gate'] is True and result['whole_undefined_set_exact_except_removed_panics'] is True and len(result['logger_proof']) == 4)
        require(result['new_Rust_object'] == artifact(target, 'fixture'))
        require(json.loads((evidence / 'fresh-compiled-rust-ownership-proof.json').read_text()) == result)
check('actual-mandatory-whole-Rust-gate-real-f9-disposable-positive', actual_object_gate_case)
check('actual-mandatory-gate-original-panic-object-negative', lambda: reject(lambda: actual_object_gate_case(use_old=True)))
for name, mutation in [
    ('actual-mandatory-gate-GLOBAL-logger-negative', lambda raw, elf, symbol: raw.__setitem__(elf.table['offset'] + symbol['index'] * elf.table['entsize'] + 4, 17)),
    ('actual-mandatory-gate-wrong-visibility-negative', lambda raw, elf, symbol: raw.__setitem__(elf.table['offset'] + symbol['index'] * elf.table['entsize'] + 5, 2)),
    ('actual-mandatory-gate-wrong-whole-record-line-negative', lambda raw, elf, symbol: raw.__setitem__(slice(elf.sections[symbol['shndx']]['offset'] + symbol['value'] + 24, elf.sections[symbol['shndx']]['offset'] + symbol['value'] + 28), bytes(4))),
]:
    check(name, lambda mutation=mutation: reject(lambda: actual_object_gate_case(mutation)))

print(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
                     status='PASS_PURE_SOURCE_AND_DISPOSABLE_SEED_CONTROLS', tests=len(RESULTS), results=RESULTS,
                     actual_owner_imported=False, subprocesses=0, runtime_acceptance=False), sort_keys=True))
