"""Functional OS only; no security testing. Read-only exactprofile preflight; no compiler/CPP/guard."""
from pathlib import Path
import hashlib,importlib.util,json
D=Path(__file__).resolve().parent
PROFILE_SHA='54c0fdf186829201af58d96da1eb09de4f72025a5fc18c8a210b1c13b4a9fc3a'
p=D/'PROFILE.NOT-GRANTED.json'
assert hashlib.sha256(p.read_bytes()).hexdigest()==PROFILE_SHA
x=json.loads(p.read_bytes());runner=next(r for r in x['inputs'] if r['path'].endswith('/ordinary-host-new12h-runner-source-1/run_new12h_host.py'))
assert runner['sha256']=='6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34'
spec=importlib.util.spec_from_file_location('retained_ordinary_F06_sourcevalidation_only',runner['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.validate_profile(x);m.verify(x['inputs']+[z['plan'] for z in x['leaves']])
assert len(x['commands'])==6 and x['commands'][2]['argv'][1:3]==['--redefine-sym','obtain_clone_cpuid=original_C_obtain_clone_cpuid']
assert not Path(x['capture_root']).exists() and not Path(x['leaves'][0]['output']).exists()
assert 'vectors=32193 real_ABI8=1' in x['leaves'][0]['expected_stdout']
assert '--cfg' not in x['commands'][0]['argv']
result=dict(decision='PASS_SOURCE_PROFILE_INPUTS_AND_ORDINARY_SCHEMA_ONLY',commands=6,source_algorithm_changes=0,compiler_CPP_guard_calls=0,actual_vectors=0,native_acceptance=False,runtime_authority=None)
print(json.dumps(result))
