"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Executor-only source/adoption/authentication preflight. Never enters owner execution.
No clock, lock, query, nonce generation, subprocess, container or filesystem mutation.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import mcexec_contract as mc

def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--print-source-map',action='store_true')
    mode.add_argument('--adoption-only',action='store_true')
    for name in ('request','request-sha256','release','release-sha256'):p.add_argument('--'+name)
    a=p.parse_args()
    spec=importlib.util.spec_from_file_location('actual_executor_owner',HERE/'mcexec_owner.py')
    owner=importlib.util.module_from_spec(spec);sys.modules[spec.name]=owner;spec.loader.exec_module(owner)
    source_map={name:owner.sha(Path(owner.RUNTIME_SOURCE_PATHS.get(name,str(owner.REPO/name))).read_bytes()) for name in owner.SOURCES}
    owner.validate_runtime_source_bindings(source_map)
    if a.print_source_map:
        if any((a.request,a.request_sha256,a.release,a.release_sha256)):p.error('source-map observation is separate from authentication')
        print(json.dumps(dict(status='OBSERVED_EXECUTOR_RUNTIME_SOURCE_MAP_ONLY',source_sha256=source_map,execution_authority=False),sort_keys=True));return
    if a.adoption_only and any((a.request,a.request_sha256,a.release,a.release_sha256)):p.error('adoption observation does not accept execution references')
    if not a.adoption_only and not all((a.request,a.request_sha256,a.release,a.release_sha256)):p.error('actual authentication needs four exact existing Root references')
    # The literal driver configuration API is extracted without evaluating its
    # module timer, operational main or any capture helper.
    import ast
    node=next(n for n in ast.parse((HERE/'mcexec_driver.py').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='configuration_api')
    ns={'mc':mc};exec(compile(ast.Module(body=[node],type_ignores=[]),'literal-driver-configuration-api','exec'),ns)
    ns['configuration_api'](mc.prep())
    owner.validate_preparation(mc.prep())
    if a.adoption_only:
        print(json.dumps(dict(status='PASS_EXECUTOR_SOURCE_ADOPTION_ONLY',source_sha256=source_map,execution_authority=False,admission_or_clock_started=False),sort_keys=True));return
    request,release=owner.authenticate(Path(a.request),a.request_sha256,Path(a.release),a.release_sha256)
    print(json.dumps(dict(status='PASS_EXECUTOR_SOURCE_ADOPTION_AUTHENTICATION_ONLY',request=release['request'],source_sha256=source_map,execution_authority=False,admission_or_clock_started=False),sort_keys=True))

if __name__=='__main__':main()
