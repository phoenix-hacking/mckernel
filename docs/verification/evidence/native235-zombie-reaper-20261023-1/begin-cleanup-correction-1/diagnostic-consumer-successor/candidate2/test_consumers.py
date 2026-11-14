"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual private Python consumer bodies, synthetic observations; no native credit.
"""
import copy,importlib.util,json
from pathlib import Path
F=Path(__file__).resolve().parent
N=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1')
P='os=0 generation=1 pid=259'
def load(name):
 p=N/'diagnostic-consumer-successor'/'candidate2'/name/'native_diagnostic.py'
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
TRACE=[f'application_syscall=delivered {P} worker=1 delivery=1 cpu=0 number=1',f'application_syscall=return_route {P} worker=1 delivery=1 launcher_cpu=1 guest_cpu=0',f'application_syscall=returned {P} worker=1 delivery=1 cpu=0 value=1',f'application_syscall=delivered {P} worker=1 delivery=2 cpu=0 number=231']
ACK=f'IHK-SMP: application cleanup ACK {P} token=7 errno=0 abandoned=1'
INTENT=f'application_process=cleanup_requested {P} intent_errno=0'
RET=f'IHK-SMP: application retirement {P} token=7 errno=0'
BASE=TRACE+[ACK,INTENT,RET]
rows=[]
def check(m,label,fn,passed=True):
 try:fn()
 except m.DiagnosticError:
  if passed:raise
 else:
  if not passed:raise AssertionError(label+' unexpectedly accepted')
 rows.append({'consumer':m.__name__,'fixture':label,'status':'PASS','expected_accept':passed})
for name in ('native','v3'):
 m=load(name)
 def trace(lines):return lambda:m._check_syscall_trace('\n'.join(lines),P,True)
 check(m,'ACK-before-intent-abandoned1-equal-crossnamespace-token',trace(BASE))
 check(m,'intent-before-ACK-abandoned0',trace(TRACE+[INTENT,ACK.replace('abandoned=1','abandoned=0'),RET]))
 check(m,'child-retirement-before-parent-terminal',trace([RET.replace('pid=259','pid=260')]+BASE))
 check(m,'retirement-EAGAIN-bounded-fresh-query',trace(BASE[:-1]+[RET.replace('token=7 errno=0','token=8 errno=-11'),RET]))
 for label,lines in [
  ('intent-only',TRACE+[INTENT]),('missing-ACK',TRACE+[INTENT,RET]),
  ('missing-retirement',TRACE+[ACK,INTENT]),('failed-intent',[x.replace('intent_errno=0','intent_errno=-5') for x in BASE]),
  ('failed-ACK',[x.replace('token=7 errno=0 abandoned=1','token=7 errno=-5 abandoned=1') for x in BASE]),
  ('wrong-ACK-generation',[x.replace('generation=1','generation=2') if 'cleanup ACK ' in x else x for x in BASE]),
  ('wrong-ACK-pid',[x.replace('pid=259','pid=260') if 'cleanup ACK ' in x else x for x in BASE]),
  ('zero-entry-token',[x.replace('token=7','token=0') if 'cleanup ACK ' in x else x for x in BASE]),
  ('zero-query-token',BASE[:-1]+[RET.replace('token=7','token=0')]),
  ('duplicate-query-token',BASE[:-1]+[RET.replace('errno=0','errno=-11'),RET]),
  ('retirement-before-parent-terminal',[ACK,INTENT,RET]+TRACE),
  ('retirement-before-ACK',TRACE+[RET,ACK,INTENT]),
  ('duplicate-ACK',BASE+[ACK]),('duplicate-intent',BASE+[INTENT]),
  ('failed-final-retirement',BASE[:-1]+[RET.replace('errno=0','errno=-11')])]:check(m,label,trace(lines),False)
 legacy=TRACE+[RET,f'application_process=release {P} cleanup_errno=0']
 check(m,'legacy-still-accepts',lambda:m._check_syscall_trace('\n'.join(legacy),P))
 check(m,'legacy-does-not-accept-BEGIN',lambda:m._check_syscall_trace('\n'.join(BASE),P),False)
 profile=json.loads((F/'CLEANUP-PROFILE.TEMPLATE.NOT-RELEASED.json').read_text())
 check(m,'null-actualtuple-refused',lambda:m._validate_cleanup_profile(profile,None),False)
 # Existing app manifests supply exact original bytes and exit; evaluator
 # fixtures bypass staging only, never claim native/manifest acceptance.
 for case in ('235','227'):
  manifest=json.loads((N/'begin-cleanup-native-successor-2'/('case-'+case)/'STRICT-NATIVE-MANIFEST.PENDING.json').read_text())
  manifest['cleanup_profile']=profile
  pay=manifest['payload'];streams={}
  for stream in ('stdout','stderr'):
   data=pay['oracle'][stream+'_hex'];size=len(bytes.fromhex(data))
   streams[stream]=dict(hex=data,eof=True,truncated=False,observed=size,retained=size,discarded=0,limit=pay[stream+'_limit_bytes'],eof_ns=3)
  report=dict(argv=pay['argv'],cwd=pay['cwd'],env=pay['env'],raw_wait_status=pay['oracle']['exit_code']<<8,started_ns=1,reaped_ns=2,finished_ns=3,streams=streams,procfs_empty=True)
  serial=BASE+[f'application SCHEDULE {P} cpu=0',f'application procfs published {P} tid=259',f'application procfs deleted {P} tid=259','ND_PAYLOAD '+json.dumps(report)]
  obs=dict(serial='\n'.join(serial),debugcon='',qmp={'status':'shutdown'},teardown=True,started_at=1,finished_at=2,deadline=3,process_identity=dict(pid=1,pgid=1,sid=1,starttime_ticks=1))
  check(m,case+'-strict-evaluate-BEGIN',lambda:m.evaluate(manifest,obs))
  bad=copy.deepcopy(report);bad['streams']['stdout']['hex']='00'+bad['streams']['stdout']['hex'][2:]
  wrong=dict(obs,serial='\n'.join(serial[:-1]+['ND_PAYLOAD '+json.dumps(bad)]))
  check(m,case+'-wrong-bytes-refused',lambda:m.evaluate(manifest,wrong),False)
  bad=copy.deepcopy(report);bad['raw_wait_status']=1<<8
  check(m,case+'-wrong-exit-refused',lambda:m.evaluate(manifest,dict(obs,serial='\n'.join(serial[:-1]+['ND_PAYLOAD '+json.dumps(bad)]))),False)
  check(m,case+'-deadline-refused',lambda:m.evaluate(manifest,dict(obs,finished_at=3)),False)
 if name=='native':
  check(m,'pair-trace-BEGIN',lambda:m._pair_trace('\n'.join(BASE),259,0,True))
  check(m,'pair-trace-intent-only-refused',lambda:m._pair_trace('\n'.join(TRACE+[INTENT]),259,0,True),False)

CANDIDATE1_ROWS=list(rows)
for name in ('native','v3'):
 m=load(name)
 raw=(F/'retained-actual235-serial.log').read_text()
 check(m,'actual-retained235-parent257-child260-audit',lambda:m._audit_begin_children(raw,'os=0 generation=1 pid=257'))
 parent='os=0 generation=1 pid=259';child='os=0 generation=1 pid=260'
 clone=[f'application_syscall=delivered {parent} worker=2 delivery=3 cpu=0 number=56',f'application_syscall=return_route {parent} worker=2 delivery=3 launcher_cpu=1 guest_cpu=0',f'application_syscall=returned {parent} worker=2 delivery=3 cpu=0 value=260']
 pub=f'application procfs published {child} tid=260'
 childrows=[f'application_syscall=delivered {child} worker=3 delivery=4 cpu=0 number=59',f'application_syscall=return_route {child} worker=3 delivery=4 launcher_cpu=1 guest_cpu=0',f'application_syscall=returned {child} worker=3 delivery=4 cpu=0 value=0']
 terminal=f'application_syscall=delivered {child} worker=3 delivery=5 cpu=0 number=231'
 lines=TRACE[:-1]+clone+[pub]+childrows+[terminal]+TRACE[-1:]+[ACK,INTENT,RET]
 def childtrace(data):return lambda:m._check_syscall_trace('\n'.join(data),P,True,True)
 check(m,'child-exec-and-exit-before-parent-terminal',childtrace(lines))
 check(m,'SIGTERM-child-no-exit231-required',childtrace([x for x in lines if x!=terminal]))
 check(m,'child-before-parent-clone-RET',childtrace(TRACE[:-1]+clone[:2]+[pub]+childrows+[clone[2],terminal]+TRACE[-1:]+[ACK,INTENT,RET]))
 for label,data in [
 ('unlinked-child',[x.replace('value=260','value=-11') if x==clone[2] else x for x in lines]),
 ('missing-child-publication',[x for x in lines if x!=pub]),
 ('wrong-child-generation',[x.replace('generation=1','generation=2') if x==pub else x for x in lines]),
 ('wrong-child-routeCPU',[x.replace('guest_cpu=0','guest_cpu=1') if x==childrows[1] else x for x in lines]),
 ('duplicate-child-delivery',lines+[childrows[0]]),
 ('duplicate-child-return',lines+[childrows[2]]),
 ('missing-child-return',[x for x in lines if x!=childrows[2]]),
 ('unmatched-child-return',lines+[childrows[2].replace('delivery=4','delivery=99')]),
 ('malformed-child-row',lines+[f'application_syscall=returned {child} worker=oops']),
 ('wrong-child-pid',lines+[childrows[0].replace('pid=260','pid=261')]),
 ('child-row-before-publication',TRACE[:-1]+clone+childrows+[pub,terminal]+TRACE[-1:]+[ACK,INTENT,RET]),
 ('parent-oracle-preserved-missing-exit',[x for x in lines if x!=TRACE[-1]])
 ]:check(m,label,childtrace(data),False)
 # Retain the original source failure against observed child rows. This
 # historical failed guest is not promoted to a complete positive app result.
 spec=importlib.util.spec_from_file_location('candidate1_'+name,F.parent/(name+'_native_diagnostic.py'));old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
 try:old._check_syscall_trace(raw,'os=0 generation=1 pid=257',True)
 except old.DiagnosticError as error:
  assert str(error)=='malformed or foreign syscall trace',str(error)
  rows.append({'consumer':name,'fixture':'candidate1-retained235-child-domain-failure','status':'RETAINED_EXPECTED_FAILURE','error':str(error)})
 else:raise AssertionError('candidate1 did not reproduce child rejection')

print(json.dumps({'scope':__doc__.splitlines()[0],'status':'PASS','count':len(rows),'observations':rows,'native_credit':False},sort_keys=True))
