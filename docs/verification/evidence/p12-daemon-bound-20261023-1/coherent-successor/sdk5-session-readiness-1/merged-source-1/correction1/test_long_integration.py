"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic wire integration through actual merged LONG evaluator and real _pair_body.
"""
from pathlib import Path
import hashlib,importlib.util,json,traceback,sys
H=Path(__file__).resolve().parent;S=H/'source'
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def frame(name,obj):return name+' '+json.dumps(obj,separators=(',',':'))+'\n'
d=load(S/'native_diagnostic.py','correction1_real_native');t=load(S/'long_transport.py','correction1_real_transport');l=load(S/'p12_long_session.py','correction1_real_LONG');manifest=dict(case_id='controlled-P205-LONG',cleanup_profile={'fixture':'enabled'},pair_long_session=dict(t.PROFILE),pair={'apps':[dict(argv=['/bin/a'],cwd='/work/a',env={},oracle=dict(stdout_hex=b'fixture-A\n'.hex(),stderr_hex='')),dict(argv=['/bin/b'],cwd='/work/b',env={},oracle=dict(stdout_hex=b'fixture-B\n'.hex(),stderr_hex=''))]})
# The strict pair checker only uses cleanup_profile presence here; its source-profile
# validator was exercised separately with real current source refs in the 8-case suite.
startup=['NATIVE_PAIR_CPU os=0 generation=1 assigned_host=1,2 logical=0,1 default_ikc_linux=0\n']
for i in (0,1):startup.append('control accepted os=0 generation=1 port=501 guest_cpu=%d linux_cpu=%d cookie=%d receive=%x send=%x bytes=16384 reference=1 remote_cookie=%x\n'%(i,i+1,i+11,0x100000+i*0x200000,0x200000+i*0x200000,i+1))
reports=[];traces=[];base=1000000000;total=0;first=base;last=None
for r in range(400):
 start=base-1;end=base+9000000002;apps=[];lines=[]
 for i,expected in enumerate(manifest['pair']['apps']):
  pid=10000+r*2+i;prefix='os=0 generation=1 pid='+str(pid);worker=pid*10;started=base+i;reaped=base+9000000000;finished=reaped+1;streams={}
  for stream in ('stdout','stderr'):
   data=bytes.fromhex(expected['oracle'][stream+'_hex']);streams[stream]=dict(hex=data.hex(),eof=True,truncated=False,observed=len(data),retained=len(data),discarded=0,limit=1024,eof_ns=reaped)
  apps.append(dict(id=i,pid=pid,cpu=i,cwd=expected['cwd'],argv=expected['argv'],env=expected['env'],raw_wait_status=0,clean=1,fault=0,timeout=0,started_ns=started,reaped_ns=reaped,finished_ns=finished,streams=streams))
  lines += ['application procfs published '+prefix+' tid='+str(pid)+'\n','application SCHEDULE '+prefix+' cpu='+str(i)+'\n','application_syscall=delivered '+prefix+' worker=%d delivery=1 cpu=%d number=1\n'%(worker,i),'application_syscall=return_route '+prefix+' worker=%d delivery=1 launcher_cpu=%d guest_cpu=%d\n'%(worker,1-i,i),'application_syscall=returned '+prefix+' worker=%d delivery=1 cpu=%d value=9\n'%(worker,i),'application_syscall=delivered '+prefix+' worker=%d delivery=2 cpu=%d number=231\n'%(worker,i),'application_process=cleanup_requested '+prefix+' intent_errno=0\n','application cleanup ACK '+prefix+' token=%d errno=0 abandoned=0\n'%(pid*4+1),'application retirement '+prefix+' token=%d errno=0\n'%(pid*4+2),'application procfs deleted '+prefix+' tid='+str(pid)+'\n']
 total+=9000000000;report=dict(os=0,generation=1,host_cpus=[1,2],cpus=[0,1],procfs_empty=True,apps=apps);reports.extend([frame('ND_PAIR_ROUND_START',dict(round=r,time_ns=start,procfs_empty=True)),frame('ND_PAIR',report),frame('ND_PAIR_ROUND_END',dict(round=r,time_ns=end,procfs_empty=True)),frame('ND_PAIR_LONG_PROGRESS',dict(round=r,work_ns=9000000000,cumulative_work_ns=total,launches=(r+1)*2))]);traces+=lines;last=reaped;base=end+2
trace=''.join(startup+traces)
def observation(trace_text):
 size=len(trace_text);serial=frame('ND_PAIR_LONG_PROFILE',t.PROFILE)+''.join(reports)+frame('ND_PAIR_LONG_TRACE_BEGIN',dict(bytes=size))+trace_text+frame('ND_PAIR_LONG_TRACE_END',dict(bytes=size))+frame('ND_PAIR_LONG_COMPLETE',dict(rounds=400,launches=800,work_ns=total,elapsed_ns=last-first,trace_bytes=size,os=0,generation=1,procfs_empty=True));return dict(serial=serial,debugcon='',stdout='',stderr='',qmp={'status':'shutdown'},teardown=True)
result=dict(scope=__doc__.splitlines()[0],python=sys.version,real_pair_checker_source_sha256=hashlib.sha256((S/'native_diagnostic.py').read_bytes()).hexdigest(),geometry='LONG source requires142GiB growth acceptance;110GiB context is not supportedLONGadmission',actual142_capacity=None,EXTERNAL_CAPTURE_BINDING=None,HOST4GiB='reviewed arithmetic only; not observedlivebound',root=0,Docker=0,guest=0,compiler=0)
try:
 # Demonstrate the preserved first merge rejects the valid BEGIN trace because
 # its projection drops intent/ACK. This is an expected regression control.
 old=load(H.parent/'source/p12_long_session.py','preserved_pre_correction_LONG');baseline_error=None
 try:old.check_long_session(manifest,observation(trace),pair_check=d._pair_body)
 except ValueError as exc:baseline_error=str(exc)
 assert baseline_error is not None and 'BEGIN'in baseline_error
 passed=d._evaluate_long_transport(manifest,observation(trace));assert passed['status']=='PROTOCOL_PASS'and passed['guest_report']['successful_rounds']==400 and passed['guest_report']['successful_launches']==800 and passed['guest_report']['actual_mixed_work_ns']==3600000000000
 rejections=[]
 for name,mutated in [('missing_ACK',trace.replace('application cleanup ACK os=0 generation=1 pid=10000 token=40001 errno=0 abandoned=0\n','',1)),('foreign_generation_ACK',trace.replace('application cleanup ACK os=0 generation=1 pid=10000','application cleanup ACK os=0 generation=2 pid=10000',1)),('duplicate_ACK',trace.replace('application cleanup ACK os=0 generation=1 pid=10000 token=40001 errno=0 abandoned=0\n','application cleanup ACK os=0 generation=1 pid=10000 token=40001 errno=0 abandoned=0\n'*2,1))]:
  error=None
  try:d._evaluate_long_transport(manifest,observation(mutated))
  except ValueError as exc:error=str(exc)
  assert error is not None;rejections.append(dict(case=name,error=error))
 result.update(status='PASS_REAL_LONG_EVALUATOR_THROUGH_UNMODIFIED_STRICT_PAIR_CHECKER',accepted_rounds=400,accepted_launches=800,synthetic_work_ns=3600000000000,trace_bytes=len(trace),baseline_expected_rejection=baseline_error,negative_controls=rejections,strict_pair_checker_stubbed=False,oracles_weakened=False)
except BaseException:result.update(status='FAIL_BOUNDED_CORRECTION1_INTEGRATION_REQUIRES_EXPERT',traceback=traceback.format_exc())
with(H/'LONG-INTEGRATION-RESULT.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result));raise SystemExit(0 if result['status'].startswith('PASS')else 1)
