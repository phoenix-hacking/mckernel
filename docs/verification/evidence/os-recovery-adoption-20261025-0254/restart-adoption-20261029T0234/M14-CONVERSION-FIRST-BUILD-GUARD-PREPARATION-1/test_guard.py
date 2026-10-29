"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
In-memory functional negatives only; no actual guard, owner, proc, query or build.
"""
import copy,importlib.util,math
from pathlib import Path
p=Path(__file__).resolve().parent/'runtime_guard.py';spec=importlib.util.spec_from_file_location('functional_guard_only',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
subjects=m.fixed_subjects();assert sum(k.startswith('snapshot:')for k in subjects)==149 and sum(k.startswith('retained_object:')for k in subjects)==9 and sum(k.startswith('config:')for k in subjects)==10
context={'request':{'fixture':'not-authority'},'nonce':'1234567890abcdef1234567890abcdef','current_free':{'fixture':'not-authority'},'current_ledger':{'fixture':'not-authority'},'current_bindings':{'fixture':'not-authority'}}
operation=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',operation='conversion-first-three-command-build',window_sha256=m.WINDOW_SHA,first_prepared_window_sha256=m.WINDOW_SHA,weekly_limit_identity=m.WEEKLY,billing_mode='included_only',allow_prepaid_fallback=False,predecessor_cutoffs=None,operation_cutoffs=list(m.MAXIMUM),subjects=subjects,context=context,guardian=dict(source=subjects['guardian'],entrypoint='guard'),source_owners=['/root','/root/m14_integration_terra'])
review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,implementation_ownership=False,reviewer='/root/fixture-reviewer',operation='conversion-first-three-command-build',successor=operation)
clocks=[m.MAXIMUM[0]-100,m.MAXIMUM[1]-100,m.MAXIMUM[2]-100];assert m.validate_operation(operation,review,subjects,context,clocks,m.MAXIMUM)==m.MAXIMUM
guardian=m.load(m.read(m.FIXED)['guardian'],'pure_q_guardian_fixture')
def row(reset,used=99):return guardian.weekly_row(dict(limitId='codex',primary=dict(resetsAt=reset,windowDurationMins=10080,usedPercent=used)))
base=row(m.WEEKLY['resets_at']);state=dict(thread_id=m.THREAD,weekly_confirmed_usage=base,weekly_usage=base,weekly_confirmation_pending=False,weekly_usage_error=None,weekly_effective_end=m.MAXIMUM[0],weekly_effective_monotonic_end=m.MAXIMUM[1],weekly_effective_boot_end=m.MAXIMUM[2]);assert m.confirmed_weekly_ceiling(state)==m.MAXIMUM
for delta in (-3,3):
 sample=copy.deepcopy(state);sample['weekly_confirmed_usage']=sample['weekly_usage']=row(m.WEEKLY['resets_at']+delta);assert sample['weekly_confirmed_usage']['canonicalResetsAt']==m.WEEKLY['resets_at'] and m.confirmed_weekly_ceiling(sample)==m.MAXIMUM

n=0
def reject(fn):
 global n
 try:fn()
 except (ValueError,KeyError,TypeError):n+=1;return
 raise AssertionError('invalid functional admission accepted')
for key,value in [('operation','current118-postjoin-current64'),('billing_mode','credits'),('allow_prepaid_fallback',True),('predecessor_cutoffs',[1,1,1])]:
 a=copy.deepcopy(operation);a[key]=value;r=dict(review,successor=a);reject(lambda:m.validate_operation(a,r,subjects,context,clocks,m.MAXIMUM))
a=copy.deepcopy(operation);a['credit_ceiling']='100';reject(lambda:m.validate_operation(a,dict(review,successor=a),subjects,context,clocks,m.MAXIMUM))
for i in range(3):
 a=copy.deepcopy(operation);a['operation_cutoffs'][i]=m.MAXIMUM[i]+1;reject(lambda:m.validate_operation(a,dict(review,successor=a),subjects,context,clocks,m.MAXIMUM))
 c=list(clocks);c[i]=m.MAXIMUM[i];reject(lambda:m.validate_operation(operation,review,subjects,context,c,m.MAXIMUM))
reject(lambda:m.validate_operation(operation,dict(review,reviewer='/root/m14_integration_terra'),subjects,context,clocks,m.MAXIMUM));reject(lambda:m.validate_operation(operation,dict(review,independent=False),subjects,context,clocks,m.MAXIMUM));reject(lambda:m.validate_operation(operation,review,dict(subjects,extra={'x':1}),context,clocks,m.MAXIMUM))
for key,val in [('usedPercent',100),('usedPercent',None),('usedPercent',math.nan),('resetsAt',None)]:
 a=copy.deepcopy(state);a['weekly_confirmed_usage'][key]=val;a['weekly_usage']=copy.deepcopy(a['weekly_confirmed_usage']);reject(lambda:m.confirmed_weekly_ceiling(a))
a=copy.deepcopy(state);a['weekly_confirmed_usage']=a['weekly_usage']=row(m.WEEKLY['resets_at']+604800);reject(lambda:m.confirmed_weekly_ceiling(a))
for key,value in [('weekly_confirmation_pending',True),('weekly_usage_error','unknown'),('weekly_usage',None),('thread_id','other')]:
 a=copy.deepcopy(state);a[key]=value;reject(lambda:m.confirmed_weekly_ceiling(a))
# A confirmed earlier cutoff tightens only; a later advisory cannot extend it.
a=copy.deepcopy(state);a['weekly_effective_monotonic_end']-=1;assert m.confirmed_weekly_ceiling(a)[1]==m.MAXIMUM[1]-1
a=copy.deepcopy(state);a['weekly_effective_end']+=3;assert m.confirmed_weekly_ceiling(a)==m.MAXIMUM
assert not m.BINDING.exists(),'no actual operation binding fabricated'
print('PASS',len(subjects),'exact fixed subjects and',n,'functional negatives; actual guard/owner/proc/query/build calls zero')

