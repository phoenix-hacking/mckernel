"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Parse only the frozen owned read1 and existing pure diagnostic function. No live IO.
"""
from pathlib import Path
import base64,hashlib,importlib.util,json,os
D=Path(__file__).resolve().parent
capture=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/next-live-observation-91c-1/actual-read-1/stdout')
source=Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/next-live-observation-aa5-1/interpret_retained_diagnostics.py')
raw=capture.read_bytes();assert len(raw)==173225 and hashlib.sha256(raw).hexdigest()=='7d4c18d774ace221e7d6fac9391b93b28be309daab7c529bd81ec6d80f93d8d0'
expected_helper=Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/next-live-observation-aa5-1/READY-OBSERVATION-OPERATION.json')
binding=json.loads(expected_helper.read_text())['diagnostic_interpreter'];source_raw=source.read_bytes();assert hashlib.sha256(source_raw).hexdigest()==binding['sha256']
spec=importlib.util.spec_from_file_location('retained_diagnostics_only',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
record=json.loads(raw);facts=m.interpret(record);prefix=base64.b64decode(record['prefix']['base64'],validate=True);end=prefix.rfind(b'\n')+1
lines=prefix[:end].splitlines();tail=lines[-24:]
report=dict(scope=__doc__,status='INTERPRETED_RETAINED_READ1_ONLY',capture=dict(path=str(capture),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)),interpreter_source=dict(path=str(source),sha256=hashlib.sha256(source_raw).hexdigest(),unchanged=True),reader_status=record['status'],anchor_before=record['anchor_before'],anchor_after=record['anchor_after'],anchor_identity_consistent=record['anchor_identity_consistent'],reported_progress=dict(completed_launches=record['producer_reported_completed_launches'],mixed_work_ns=record['producer_reported_mixed_work_ns'],last_complete_progress=record['last_complete_progress'],pending_round_excluded=record['pending_round_excluded'],wire_error=record['wire_error']),diagnostic_serial_facts=facts,bounded_tail=dict(complete_line_count=len(lines),included_last_lines=len(tail),per_line_byte_cap=512,lines=[line[:512].decode('ascii',errors='backslashreplace') for line in tail],truncated_tail_lines=sum(len(line)>512 for line in tail),incomplete_final_tail_bytes=len(prefix)-end,incomplete_final_tail_base64=base64.b64encode(prefix[end:end+512]).decode(),incomplete_final_tail_truncated=len(prefix)-end>512),cause='UNKNOWN: phase identifies an entered boundary; retained failure fields establish reported callback result only, not an unobserved syscall or application cause.',live_filesystem_PROC_root_probe_QMP_signals=0,application_acceptance=False,native_acceptance=False,physical_clearance=False)
out=D/'RETAINED-READ1-DIAGNOSTIC.json';fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC,0o600)
data=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
try:
 pos=0
 while pos<len(data):pos+=os.write(fd,data[pos:])
finally:os.close(fd)
print(json.dumps(dict(report=str(out),sha256=hashlib.sha256(data).hexdigest(),last_phase=facts['last_phase'],failures=facts['failure_records'],aborts=facts['abort_records'],trace_headers=facts['trace_headers'],trace_errors=facts['trace_errors'],parse_errors=facts['diagnostic_parse_errors'],tail=report['bounded_tail']),sort_keys=True))
