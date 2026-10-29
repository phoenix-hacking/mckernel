from pathlib import Path
import json,ast,copy,hashlib
P=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1');D=P/'recovery-quota-confirmation-binding-1';O=D/'actual-control-binding-1';Q=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1');ns={'__file__':str(O/'guardian_guard.py')};exec(compile((O/'guardian_guard.py').read_text(),'actual_guard_source','exec'),ns)
a=json.loads((Q/'ACTUAL-CONTROLS-ARMED.json').read_text());ns['require_live_binding']();ns['validate_armed_metadata'](a);ns['validate_control_config'](json.loads((Q/'armed-controller/CONFIG.json').read_text()))
live={v['pid']:v for v in a['actors'].values()};live[1311]=dict(pid=1311,start='596',ppid=1,comm='systemd',state='S');ns['validate_armed'](a,live.get)
def reject(f):
 try:f()
 except (ValueError,KeyError,TypeError):return
 raise AssertionError('unexpected acceptance')
b=copy.deepcopy(a);b['actors']['worker']['start']='retired';reject(lambda:ns['validate_armed'](b,live.get))
b=copy.deepcopy(a);b['caps']['boot_deadline']+=1;reject(lambda:ns['validate_armed_metadata'](b))
for reset in [1793774131,1793774132,1793774133,1793774134,1793774135]:
 row=ns['weekly_row'](dict(limitId='codex',primary=dict(usedPercent=32,windowDurationMins=10080,resetsAt=reset)));ns['validate_confirmed_row'](row);assert row['canonicalResetsAt']==1793774133
b=copy.deepcopy(a);b['weekly_usage']['usedPercent']=100;reject(lambda:ns['validate_armed_metadata'](b))
b=copy.deepcopy(a);b['weekly_usage']['resetsAt']=1793251609;reject(lambda:ns['validate_armed_metadata'](b))
C=P/'common-routing-data-correction-source-1';T=O/'routing'
for f in T.glob('*.py'):assert f.read_bytes()==(C/f.name).read_bytes()
for f in (T/'recursive-current62').glob('*.py'):assert f.read_bytes()==(C/'recursive-current62'/f.name).read_bytes()
for f in (T/'recursive-current62/history').glob('*.py'):assert f.read_bytes()==(C/'recursive-current62/history'/f.name).read_bytes()
for f in ['INPUTS.json','recursive-current62/INPUTS.json']:
 d=json.loads((T/f).read_text());assert d['guardian']['path']==str(O/'guardian_guard.py')and d['shared_guard']['path']==str(O/'operation_window_guard.py')
x=json.loads((O/'BATCH-PHYSICAL.PROPOSED.json').read_text());y=json.loads((C/'BATCH-PHYSICAL.PENDING-REVIEW.json').read_text());assert {k:v for k,v in x.items()if k!='guard_config'}=={k:v for k,v in y.items()if k!='guard_config'}
checks=['genuine receipt/config pure predicates and fake actor census pass','stale birth and increased receipt caps refuse','same-period reporting corrections accepted canonical unchanged','exhaustion and different period refuse','all copied observer/history/formatter Python bytes exact','outer/recursive INPUTS live guardian/shared refs exact','physical proposal changes guard_config only; completed physical evidence untouched']
(O/'PURE-TEST.json').write_text(json.dumps(dict(status='PASS_PURE_SOURCE_ONLY',checks=checks,live_guard_invocations=0,live_process_observations=0),indent=2)+'\n');print('PASS',len(checks))
