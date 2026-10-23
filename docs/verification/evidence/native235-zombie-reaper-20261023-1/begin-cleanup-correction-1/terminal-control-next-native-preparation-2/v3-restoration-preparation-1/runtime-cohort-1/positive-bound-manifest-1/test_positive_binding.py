"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import argparse, hashlib, json, os
D=Path(__file__).resolve().parent
P=D.parent
# Reuse the eight-fixture importer; import does not execute its unittest main.
import importlib.util
spec=importlib.util.spec_from_file_location('reviewed_cohort_fixtures', P/'test_cohort.py')
tests=importlib.util.module_from_spec(spec); spec.loader.exec_module(tests)
parser=argparse.ArgumentParser();parser.add_argument('--manifest',required=True);parser.add_argument('--manifest-sha256',required=True);args=parser.parse_args()
assert args.manifest=='/home/holden/mckernel-work/scratch/nm05p5a1/m.json'
assert args.manifest_sha256=='8c03e5570b98a99db009f74f6dea9bf27ad9f046abeeea44d66ec561cbe708d7'
owner=tests.load('actual_M05_owner_positive',P/'native_diagnostic_container_owner.py')
runner=tests.load('actual_M05_runner_positive',P/'native_diagnostic_runner.py')
nd,manifest=owner.bound_manifest(args.manifest,args.manifest_sha256)
assert nd.evaluate.__name__=='case_evaluate'
runner_nd,backend=runner._runtime()
runner._bind_m05(runner_nd,manifest,args.manifest)
assert runner_nd.evaluate.__name__=='case_evaluate'
result=dict(scope=__doc__,status='PASS_REAL_BOUND_MANIFEST_AND_RUNNER_HOOK',uid=os.getuid(),manifest=dict(path=args.manifest,sha256=args.manifest_sha256),selected_modules=nd._thaw(manifest['modules']),staging=nd._thaw(manifest['staging']),profile=nd._thaw(manifest['profile']),owner_source_sha256=hashlib.sha256((P/'native_diagnostic_container_owner.py').read_bytes()).hexdigest(),runner_source_sha256=hashlib.sha256((P/'native_diagnostic_runner.py').read_bytes()).hexdigest(),source_map_count=len(owner.SOURCE_HASHES),source_map_sha256=hashlib.sha256(json.dumps(owner.SOURCE_HASHES,sort_keys=True,separators=(',',':')).encode()).hexdigest(),hooks=dict(owner_evaluate=nd.evaluate.__module__+'.'+nd.evaluate.__name__,runner_evaluate=runner_nd.evaluate.__module__+'.'+runner_nd.evaluate.__name__),native_execution=False,restoration_acceptance=None)
(D/'binding-result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,sort_keys=True))
