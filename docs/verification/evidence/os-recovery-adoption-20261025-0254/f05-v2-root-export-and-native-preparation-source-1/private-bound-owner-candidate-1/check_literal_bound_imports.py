"""Functional McKernel OS/apps and Rust migration only; no security testing.
Read-only full-module import and exact v2 binding check; no helper main/factory.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
CANONICAL = HERE.parent/'bound-native-runtime-1'
OWNER_PREIMAGE = Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/runtime-provider-rebind-1/native/native_diagnostic_container_owner.py')
EXPECTED = {
    'native_diagnostic_container_owner.py':'af2b1f57a19949e9867de2496b16063859c47298e9cf03b401e95de5bded5a10',
    'native_diagnostic.py':'529830adcd6fafa13979bf6036b2812c88630c5e0112ce4d80f9fc28cc30d4da',
    'native_diagnostic_runner.py':'25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499',
    'native_diagnostic_backend.py':'cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614',
    'qmp_capture.py':'5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741',
}

def load(path, name):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.__file__ == str(path) and module.__spec__.origin == str(path)
    return module

def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--runtime-dir',required=True,type=Path)
    parser.add_argument('--result',required=True,type=Path)
    args = parser.parse_args()
    directory = args.runtime_dir
    assert directory in (HERE,CANONICAL) and directory.resolve(strict=True) == directory
    for name,digest in EXPECTED.items():
        assert hashlib.sha256((directory/name).read_bytes()).hexdigest() == digest
    preimage = OWNER_PREIMAGE.read_bytes()
    assert hashlib.sha256(preimage).hexdigest() == '45010e54e1f78e3efcd6572b71342ee6078abeea98961f2c5d49849575dd5048'
    tree = ast.parse(preimage)
    oldpins = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                   and any(isinstance(t,ast.Name) and t.id == 'SOURCE_HASHES' for t in n.targets))
    assert len(oldpins) == 139
    owner = load(directory/'native_diagnostic_container_owner.py','bound_v2_owner_import_only')
    assert owner.RUNNER == str(CANONICAL/'native_diagnostic_runner.py')
    assert owner.SELF == str(CANONICAL/'native_diagnostic_container_owner.py')
    assert len(owner.SOURCE_HASHES) == 143
    assert all(owner.SOURCE_HASHES[k] == v for k,v in oldpins.items())
    for name,digest in EXPECTED.items():
        if name != 'native_diagnostic_container_owner.py':
            assert owner.SOURCE_HASHES[str(CANONICAL/name)] == digest
    runner = load(directory/'native_diagnostic_runner.py','bound_v2_runner_import_only')
    diagnostic, backend = runner._runtime()
    assert diagnostic.__file__ == str(directory/'native_diagnostic.py')
    assert diagnostic.__spec__.origin == str(directory/'native_diagnostic.py')
    assert backend.__file__ == str(directory/'native_diagnostic_backend.py')
    assert backend.__spec__.origin == str(directory/'native_diagnostic_backend.py')
    binding = diagnostic._f05_binding()
    actual = json.loads((CANONICAL/'V2-BOUND-CONTRACT.json').read_bytes())
    assert binding == actual
    result = dict(scope=__doc__.splitlines()[0],
        status='PASS_LITERAL_BOUND_V2_IMPORTS_AND_BINDING_ONLY_NO_FULL_MANIFEST_STAGE',
        runtime_directory=str(directory),owner_source_pins=143,preserved_original_source_pins=139,
        evaluator_sha256=EXPECTED['native_diagnostic.py'],binding=binding,
        full_manifest_or_owner_bound_manifest_called=False,helper_main_factory_guard_called=False,
        compiler_stage_guest_calls=0,native_acceptance=False)
    with args.result.open('x') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=result['status'],owner_source_pins=143)))

if __name__ == '__main__':
    main()
