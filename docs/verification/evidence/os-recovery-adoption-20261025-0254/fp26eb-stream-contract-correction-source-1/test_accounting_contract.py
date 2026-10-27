"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact pinned consumer loop and saved-trace checks. Synthetic producer controls
are explicitly models; original captured metadata/result remain unchanged FAIL.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,re
R=Path(__file__).resolve().parent;E=R.parent
source=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/runtime-provider-rebind-1/native/native_diagnostic.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='f368324242bfdfb0ad1f3f524a906dcf51730ef0beb311315e6b66f5d585748c'
spec=importlib.util.spec_from_file_location('unchanged_fp_consumer',source);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
text=source.read_text();loop=text[text.index('    _keys(report["streams"],'):text.index('    schedules =',text.index('    _keys(report["streams"],'))]
# Execute the actual unmodified consumer statements, not a parallel oracle.
loop='\n'.join(line[4:] if line.startswith('    ') else line for line in loop.splitlines())
manifest=json.loads((E/'five26eb-fp-image-composition-static-source-1/offline-materialization-1/manifest.HOST-STATIC.json').read_bytes());actual=json.loads((R/'ACTUAL.ND_PAYLOAD.json').read_bytes())
def check(report):exec(loop,dict(report=report,manifest=manifest,re=re,_keys=v._keys,_need=v._need,_check_typed_futex_stderr=v._check_typed_futex_stderr))
try:check(copy.deepcopy(actual))
except v.DiagnosticError as e:assert str(e)=='stream accounting'
else:raise AssertionError('original actual report must remain rejected')
assert actual['streams']['stdout']['limit']==actual['streams']['stderr']['limit']==1024
assert actual['streams']['stdout']['hex']==manifest['payload']['oracle']['stdout_hex'] and actual['streams']['stderr']['hex']=='' and actual['raw_wait_status']==0 and actual['procfs_empty'] is True
model=copy.deepcopy(actual)
for stream in model['streams'].values():stream['limit']=4096
check(model);checks=2
for field,value,error in [('limit',1024,'stream accounting'),('eof',False,'incomplete stream'),('truncated',True,'incomplete stream'),('observed',255,'stream accounting'),('retained',253,'stream accounting'),('discarded',1,'stream accounting'),('eof_ns',model['finished_ns']+1,'EOF timestamp'),('hex','00'+model['streams']['stdout']['hex'][2:],'wrong payload bytes')]:
 bad=copy.deepcopy(model);bad['streams']['stdout'][field]=value
 try:check(bad)
 except v.DiagnosticError as e:assert str(e)==error
 else:raise AssertionError('negative stream control accepted: '+field)
 checks+=1
serial=(R/'ACTUAL.serial.log').read_text();rawline=next(l for l in serial.splitlines() if l.startswith('ND_PAYLOAD '));assert rawline.count('"limit":1024')==2
frame=rawline.replace('"limit":1024','"limit":4096')+'\n';assert len(frame.encode())<8192
full=copy.deepcopy(model);full['streams']['stdout'].update(hex='51'*4096,observed=4096,retained=4096)
assert len(('ND_PAYLOAD '+json.dumps(full,separators=(',',':'))+'\n').encode())>8192;checks+=1
ids=re.findall(r'application SCHEDULE os=0 generation=1 pid=(\d+) cpu=0\b',serial);assert len(ids)==1
prefix='os=0 generation=1 pid='+ids[0];v._check_syscall_trace(serial,prefix,True,False)
terminal=next(i for i,l in enumerate(serial.splitlines()) if 'application_syscall=delivered '+prefix+' ' in l and l.endswith('number=231'))
begin=v._check_begin_cleanup(serial,prefix,terminal)
result=dict(scope=__doc__.splitlines()[0],decision='PASS_CONTRACT_REPAIR_NEGATIVE_CONTROLS_NOT_NATIVE_ACCEPTANCE',checks=checks,original_actual_report='FAIL_stream_accounting_preserved',original_limit=4096,captured_limit=1024,synthetic_4096_model='consumer-loop PASS only; NOT actual report/result',actual_partial_stdout_bytes=254,actual_partial_stderr_bytes=0,actual_partial_exit0=True,actual_partial_procfs_empty=True,modeled_FP_frame_bytes=len(frame.encode()),modeled_frame_limit=8192,full_capacity_frame_overflow_rejected_by_proposed_exact_C_fixture=True,actual_unchanged_trace_and_BEGIN0_subchecks='PASS_PARTIAL_ONLY',actual_BEGIN=begin,actual_pid=ids[0],native_acceptance=False,actual_result_unchanged=True,new_guest_runs=0,runtime_authority=None)
print(json.dumps(result))
