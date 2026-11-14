"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import importlib.util,json,os
from pathlib import Path
D=Path(__file__).resolve().parent
assert os.sched_getaffinity(0)=={7}
s=importlib.util.spec_from_file_location('private_accounting',D/'long_transport.accounting-proposal.py');t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
assert t.TRANSPORT['external_capture_bytes']==768*2**20
assert t.TRANSPORT['logical_growth_bytes']==4*2**30
assert t.TRANSPORT['metadata_bytes']==32*2**20
assert t.file_limit(True)==384*2**20
assert t.TRANSPORT['external_capture']==dict(command_count=1,stream_slots=2,retained_copies=1,stream_file_bytes=384*2**20)
a=dict(host_floor_bytes=16*2**30,scratch_floor_bytes=12*2**30,remaining_backing_growth_bytes=0,emergency_bytes=1,campaign_bytes=1,scratch_input_growth_bytes=0)
assert t.growth_requirements(a)['host_required_bytes']==20*2**30+2
try:t.validate_release(None,None,None,None,None)
except ValueError as e:assert str(e)=='final external capture wrapper/argv/paths/copy count not bound; execution blocked'
else:raise AssertionError('unbound release accepted')
r=dict(status='PASS_PRIVATE_ACCOUNTING_AND_UNBOUND_RELEASE_REFUSAL',logical_growth_bytes=t.TRANSPORT['logical_growth_bytes'],external_capture_bytes=t.TRANSPORT['external_capture_bytes'],failed_candidates=0,bounded_corrections=0,runtime_release='NOT_RELEASED',native_credit=0)
(D/'accounting-receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
