#!/usr/bin/env python3
"""Execute one separately compiled selector through the retained supervisor."""
import argparse, hashlib, importlib.util, json, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
def local(name):
    s = importlib.util.spec_from_file_location('adverse_'+name,HERE/(name+'.py'))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def run_case(case, collector, fixture, root, supervisor):
    p = local('prepare'); oracle = local('oracle'); wire = p.reviewed('run_collector_tests.py').request_wire
    p.require(case in p.CASES and root.is_absolute() and not root.exists(),'fresh bounded case')
    root.mkdir(mode=0o700)
    for name in ('inputs','cwd'): (root/name).mkdir(mode=0o755)
    exe = p.read(fixture); manifest = b'{"kind":"adverse-infrastructure","application_acceptance":false}\n'
    p.atomic_new(root/'inputs/fixture',exe,0o755)
    p.atomic_new(root/'inputs/selected-inputs.json',manifest,0o644)
    request = wire(root/'inputs/fixture',root/'cwd',None,[b'literal-app',b'stdin-devnull'],[],manifest,exe,b'',hashlib.sha256(str(root).encode()).digest()[:16])
    p.atomic_new(root/'inputs/request.bin',request,0o600)
    argv = [str(collector),'--linux-sealed-infrastructure-v1',str(root/'inputs/request.bin'),str(root/'inputs/selected-inputs.json'),str(root/'collection')]
    command = {'argv':argv,'environment':{},'cwd':str(root),'timeout_seconds':40,'cleanup_timeout_seconds':15,
               'collector_sha256':p.digest(p.read(collector)),'fixture_sha256':p.digest(exe),'case':case}
    p.atomic_new(root/'command.json',(json.dumps(command,sort_keys=True)+'\n').encode())
    result = supervisor.run_supervised(argv,cwd=str(root),env={},attempt_dir=root/'outer',timeout_seconds=40,
                                      cleanup_timeout_seconds=15,stdout_limit_bytes=65536,stderr_limit_bytes=65536)
    p.atomic_new(root/'outer-returned.json',(json.dumps(result,sort_keys=True)+'\n').encode())
    oracle.validate_retained(root,case)
    result = {'case':case,'status':'PASS_INSTRUMENTED_LINUX_ONLY','application_acceptance':False,'backend_enabled':False}
    p.atomic_new(root/'result.json',(json.dumps(result,sort_keys=True)+'\n').encode()); return result

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--case',choices=local('prepare').CASES,required=True)
    parser.add_argument('--collector',type=Path,required=True); parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--attempt-root',type=Path,required=True); a = parser.parse_args()
    run_case(a.case,a.collector,a.fixture,a.attempt_root,local('prepare').reviewed('supervisor_host38.py'))
if __name__ == '__main__': main()
