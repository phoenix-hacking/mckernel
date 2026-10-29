"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
In-memory functional negatives only; no actual guard, owner, proc, query or build.
"""
import copy,importlib.util,math
from pathlib import Path
p=Path(__file__).resolve().parent/'runtime_guard.py';spec=importlib.util.spec_from_file_location('functional_guard_only',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
subjects=m.fixed_subjects();assert sum(k.startswith('canonical:')for k in subjects)==18 and sum(k.startswith('export:')for k in subjects)==133 and sum(k.startswith('retained_object:')for k in subjects)==8
context={'request':{'fixture':'not-authority'},'nonce':'1234567890abcdef1234567890abcdef','current_free':subjects['current_free'],'current_ledger':{'fixture':'not-authority'},'current_bindings':{'fixture':'not-authority'}}
operation=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',operation='current119-build',window_sha256=m.WINDOW_SHA,first_prepared_window_sha256=m.WINDOW_SHA,weekly_limit_identity=m.WEEKLY,billing_mode='included_only',allow_prepaid_fallback=False,predecessor_cutoffs=None,operation_cutoffs=list(m.MAXIMUM),subjects=subjects,context=context,guardian=dict(source=subjects['guardian'],entrypoint='guard'),source_owners=['/root','/root/m14_integration_terra'])
review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,implementation_ownership=False,reviewer='/root/fixture-reviewer',operation='current119-build',successor=operation)
clocks=[m.MAXIMUM[0]-100,m.MAXIMUM[1]-100,m.MAXIMUM[2]-100];assert m.validate_operation(operation,review,subjects,context,clocks,m.MAXIMUM)==m.MAXIMUM
state=dict(thread_id=m.THREAD,weekly_confirmed_usage=dict(resetsAt=m.WEEKLY['resets_at'],windowDurationMins=10080,usedPercent=99),weekly_effective_end=m.MAXIMUM[0],weekly_effective_monotonic_end=m.MAXIMUM[1],weekly_effective_boot_end=m.MAXIMUM[2]);assert m.confirmed_weekly_ceiling(state)==m.MAXIMUM
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
for key,val in [('usedPercent',100),('usedPercent',None),('usedPercent',math.nan),('resetsAt',m.WEEKLY['resets_at']+1),('resetsAt',None)]:
 a=copy.deepcopy(state);a['weekly_confirmed_usage'][key]=val;reject(lambda:m.confirmed_weekly_ceiling(a))
assert not m.BINDING.exists(),'no actual operation binding fabricated'
print('PASS 187 exact fixed subjects and',n,'functional negatives; actual guard/owner/proc/query/build calls zero')
