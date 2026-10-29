"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure TEST_ONLY metadata/effect-leaf fixtures; never call guard/observe/Popen/leases.
"""
from pathlib import Path
import ast,copy,importlib.util,json,sys
from datetime import datetime
D=Path(__file__).resolve().parent
A=D.parents[1];E=A.parent
OLD=A/'M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/expert-census-observer-consumer-source-1'
W=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1')
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def j(p):return json.loads(p.read_bytes())
def reject(f):
 try:f()
 except (ValueError,AssertionError,KeyError):return
 raise AssertionError('negative metadata accepted')
checks=[]
def passed(x):checks.append(x);print('PASS',x)
g=load(D/'guardian_guard.py','pure_weekly_guard')
armed=j(W/'ACTUAL-CONTROLS-ARMED.json');g.validate_armed_metadata(armed)
for key,val in [('status','LIVE_SAME_WINDOW_M14_EXCLUSIVE_CONTROLS'),('thread_id','old'),('native_release',True)]:
 bad=copy.deepcopy(armed);bad[key]=val;reject(lambda:g.validate_armed_metadata(bad))
passed('actual weekly receipt metadata accepted; old status/wrongRoot/nativeclaim refused')
# Substituted account/process leaves: this is not an actual control guard result.
wall=1793253000.0
usage=dict(slot='primary',usedPercent=27,windowDurationMins=10080,resetsAt=1793774133)
state=dict(thread_id=g.THREAD,phase='running',goal=dict(status='active'),worker_pid=g.INITIAL['worker'][0],worker_start=g.INITIAL['worker'][1],server_pid=g.INITIAL['server'][0],server_start=g.INITIAL['server'][1],heartbeat_at=datetime.fromtimestamp(wall).astimezone().isoformat(),settings=dict(billing=copy.deepcopy(armed['billing'])),credit_budget=dict(historical_only=True),weekly_usage=usage,weekly_usage_observation_at=datetime.fromtimestamp(wall).astimezone().isoformat(),weekly_usage_worker_pid=g.INITIAL['worker'][0],weekly_usage_worker_start=g.INITIAL['worker'][1],weekly_usage_thread_id=g.THREAD,last_rate_limits=dict(limitId='codex',primary={k:v for k,v in usage.items()if k!='slot'},secondary=None))
g.validate_weekly_account(state,wall)
for name,edit in [('exhausted',lambda s:s['last_rate_limits']['primary'].update(usedPercent=100)),('reset',lambda s:s['last_rate_limits']['primary'].update(resetsAt=1793774134)),('worker',lambda s:s.update(weekly_usage_worker_pid=1)),('error',lambda s:s.update(weekly_usage_error='unknown')),('paid',lambda s:s['settings']['billing'].update(mode='prepaid_credits')),('ambiguous',lambda s:s['last_rate_limits'].update(secondary=copy.deepcopy(s['last_rate_limits']['primary'])))]:
 bad=copy.deepcopy(state);edit(bad);reject(lambda:g.validate_weekly_account(bad,wall))
reject(lambda:g.validate_weekly_account(state,wall+120))
passed('exact controller weekly_row, currentworker, fresh120s and includedonly; exhaustion/reset/ambiguity/stale/error/paid negatives')
observed={v['pid']:dict(v,state='S')for v in armed['actors'].values()};observed[1311]=dict(pid=1311,start='596',ppid=1,state='S',comm='systemd')
journal=j(W/'armed-controller/journal.json');receipt=j(W/'armed-controller/bridge-start.json');window=j(W/'ACTUAL-WINDOW.json')
assert g.validate(window,journal,receipt,state,dict(watcher_pid=g.INITIAL['watcher'][0]),observed.get,[wall,1040000.0,1050000.0],g.BOOT_ID,armed)==[wall,1040000.0,1050000.0]
for key in ['service_hold','transport_uncertain','checkpoint_requested']:
 bad=copy.deepcopy(state);bad[key]=True;reject(lambda:g.validate(window,journal,receipt,bad,dict(watcher_pid=g.INITIAL['watcher'][0]),observed.get,[wall,1040000.,1050000.],g.BOOT_ID,armed))
passed('full pure guardian validates substituted livechain leaves; inherited service/uncertainty/checkpoint vetoes retained')
subjects=[(2320122,27,123),(2320168,27,124),(2320169,27,125)]
rows=[str(i)+': FLOCK ADVISORY WRITE '+str(pid)+' 00:1b:'+str(ino)+' 0 EOF'for i,(pid,dev,ino)in enumerate(subjects)]
assert g.validate_lease_rows(rows,subjects)
reject(lambda:g.validate_lease_rows(rows[:-1],subjects));reject(lambda:g.validate_lease_rows([x.replace('2320122','999')for x in rows],subjects))
passed('pure exact dedicated lease owner/device/inode matcher; absent/wrongowner negatives')
shared=load(D/'operation_window_guard.py','pure_weekly_shared')
cuts=shared.RUNTIME_BINDINGS['operation_cutoffs'];source=shared.RUNTIME_BINDINGS['guardian']
for op in ['current118-postjoin-current64','bfd-postjoin-current62']:
 successor=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',operation=op,decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',window_sha256=shared.WINDOW_SHA256,first_prepared_window_sha256=shared.WINDOW_SHA256,predecessor_cutoffs=None,weekly_limit_identity=shared.WEEKLY_IDENTITY,billing_mode='included_only',allow_prepaid_fallback=False,operation_cutoffs=cuts,subjects=dict(guardian=source),source_owners=['/root'],guardian=dict(source=source,entrypoint='guard'))
 review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,reviewer='/root/TEST_ONLY_effect_leaf',operation=op,successor=successor)
 assert list(shared.validate_operation(successor,review,op,successor['subjects'],[0,0,0]))==cuts
 reject(lambda:shared.validate_operation(successor,review,op,successor['subjects'],cuts))
 bad=copy.deepcopy(successor);bad['credit_run_id']='historical';reject(lambda:shared.validate_operation(bad,dict(review,successor=bad),op,bad['subjects'],[0,0,0]))
passed('both separately reviewed operationinterfaces, strictatdeadline and activecreditfields refusal')
outer=load(D/'observe_current64_current118_postjoin.py','pure_weekly_outer');retained=outer.validate_retained();outer.attach_custody(dict(custody_supplement=outer.ref(A/'ROOT-CUSTODY-SUPPLEMENT.ACTUAL.json')),retained)
assert len(retained['actors'])==132
note=json.loads(outer.checked(outer.PINS['post_root4_pending'])['note']);_,receipts,rows=outer.validate_retirement(retained,note['closed_current118_root4_retirement']['result'],outer.PINS['root4_parent_normalized']);assert len(rows)==15 and len(receipts)==14
assert len(outer.checked(outer.PINS['post_root4_pending'])['consumed_nonces'])==72
assert any(r['role'].endswith('readonly_client_UNKNOWN')for r in retained['actors'])
passed('actual authenticated132retained+15cleanup=147,72nonces and originalUNKNOWN unchanged')
# Historical adoption is validated by the complete frozen old source. New live
# guard/config/review fields are a distinct data overlay; old boundary not relabeled.
base=load(Path(outer.PINS['base_source']['path']),'pure_historical_da5a');bindings=outer.checked(outer.PINS['base_bindings']);bindings.update(guard_configuration=None,independent_review=None)
assert base.validate_current_adoption(bindings,base.validate_retained())['pids_current']==0
passed('complete frozen historicalRoot63 adoption accepts unchanged history separately from live guard overlay')
def funcs(p):return {n.name:n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
old=funcs(OLD/'observe_current64_current118_postjoin.py');new=funcs(D/'observe_current64_current118_postjoin.py')
for name in old:
 if name not in ['source_subjects','capture_scope','runtime_dependencies','observe']:assert ast.dump(old[name],include_attributes=False)==ast.dump(new[name],include_attributes=False),name
B=Path(outer.PINS['base_source']['path']).parent
old=funcs(B/'observe_current62_bfd_postjoin.py');new=funcs(D/'recursive-current62/observe_current62_bfd_postjoin.py')
for name in old:
 if name!='observe':assert ast.dump(old[name],include_attributes=False)==ast.dump(new[name],include_attributes=False),name
for name in ['bind_history.py','history/observe_bfd_root59_history.py','history/observe_bfd_current60_history.py']:assert (B/name).read_bytes()==(D/'recursive-current62'/name).read_bytes()
passed('all physical/retirement/ledger/adoption validators unchanged; typedfiller+history59/60 bytes reused')
helper=load(D/'current119/accepted_bindings.py','pure_weekly119_metadata')
assert helper.armed_metadata(armed,outer.ref(W/'armed-controller/FROZEN-PACKET.json'),g.THREAD,j(W/'EARLIEST-CONTROL-CAPS.json'))==cuts
reject(lambda:helper.armed_metadata(armed,outer.ref(W/'armed-controller/FROZEN-PACKET.json'),'wrong',j(W/'EARLIEST-CONTROL-CAPS.json')))
passed('119 exactweekly armedmetadata and componentminimum clamps; wrongRoot refused')
print(json.dumps(dict(status='PASS_PURE_WEEKLY_SOURCE_ONLY',groups=len(checks),checks=checks,actual_guard_calls=0,proc_reads=0,controller_mutations=0,subprocess_payloads=0,retained=132,cleanup=15,total=147)))
