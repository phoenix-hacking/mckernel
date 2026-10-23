"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual accepted capture-helper body: scaled ordinary stream-bound observation.
"""
import ast, hashlib, importlib.util, json, os, resource
from pathlib import Path
D=Path(__file__).resolve().parent
P=Path('docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py').resolve()
assert hashlib.sha256(P.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('accepted_capture',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert os.sched_getaffinity(0)=={7}
O=D/'actual-helper-check-1';O.mkdir(mode=0o700)
def limits():
    resource.setrlimit(resource.RLIMIT_FSIZE,(8192,8192))
    resource.setrlimit(resource.RLIMIT_CPU,(2,2))
command={'argv':['/usr/bin/python3','-I','-B','-c','import os; os.write(1,b"a"*16384); os.write(2,b"b"*16384)']}
r=m.owned_capture(command,O,3,limits)
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams']
assert all(r['captures'][n]['size']==8192 for n in ('stdout','stderr'))
# Real LONG arithmetic consumer, without root, capacity reads or workloads.
T=Path('docs/verification/evidence/p12-coupled-resource-review-20261023-1/source/long_transport.py').resolve()
s=importlib.util.spec_from_file_location('capture_transport',T);t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
a=dict(host_floor_bytes=16*2**30,scratch_floor_bytes=12*2**30,remaining_backing_growth_bytes=0,emergency_bytes=1,campaign_bytes=1,scratch_input_growth_bytes=0)
g=t.growth_requirements(a)
assert g['host_required_bytes']==a['host_floor_bytes']+t.TRANSPORT['logical_growth_bytes']+2
result=dict(scope=__doc__.splitlines()[0],status='PASS_ACTUAL_HELPER_AND_GROWTH_CONSUMER_NO_NATIVE',record=r,
    observed_actual_stream_cap=8192,observed_two_stream_total=16384,
    helper_post_capture_validation_bytes=32*2**20,
    long_inherited_fsize_bytes=t.TRANSPORT['file_bytes'],
    direct_helper_long_two_stream_ceiling_bytes=2*t.TRANSPORT['file_bytes'],
    existing_logical_growth_bytes=t.TRANSPORT['logical_growth_bytes'],
    proposed_independent_32MiB_stream_two_capture_addition_bytes=64*2**20,
    proposed_total_preserving_existing_metadata_and_logging_bytes=t.TRANSPORT['logical_growth_bytes']+64*2**20,
    native_credit=0,runtime_release='NOT_RELEASED')
(D/'receipt.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ('status','observed_two_stream_total','direct_helper_long_two_stream_ceiling_bytes','proposed_total_preserving_existing_metadata_and_logging_bytes')}))
