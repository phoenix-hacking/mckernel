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
print('PASS 187 exact fixed subjects and',n,'functional negatives; actual guard/owner/proc/query/build calls zero')

# Complete binding_metadata -> confirmed ceiling -> validate_operation path.
# Fixture refs/reviews exist only in memory and do not assert actual authority;
# fixed source subjects and the actual Q period parser remain genuine.
import ast
oldspec=importlib.util.spec_from_file_location('historical_pure_predicate',p.parent.parent/'runtime_guard.py');old=importlib.util.module_from_spec(oldspec);oldspec.loader.exec_module(old)
def fake_ref(name):return dict(path='/fixture/'+name,bytes=1,sha256=('a'*64))
opref=fake_ref('operation');reviewref=fake_ref('review');ledgerref=fake_ref('ledger');requestref=fake_ref('request');bindingsref=fake_ref('current-bindings');bootstrapref=fake_ref('bootstrap')
ctx=dict(request=requestref,nonce='1234567890abcdef1234567890abcdef',current_free=subjects['current_free'],current_ledger=ledgerref,current_bindings=bindingsref,armed_controls=m.ARM,bootstrap_caps=bootstrapref)
fullsubjects=dict(subjects);fullsubjects.update({'root:'+k:ctx[k]for k in ('request','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps')})
op=copy.deepcopy(operation);op.update(context=ctx,subjects=fullsubjects);rev=dict(review,successor=op)
binding=dict(author='/root',decision='BIND_REVIEWED_CURRENT119_PRODUCER_GUARD',runtime_authority=None,source=m.ref(p),successor=opref,independent_review=reviewref)
original_read,original_auth=m.read,m.auth
fixture_values=[(opref,op),(reviewref,rev),(ledgerref,dict(consumed_nonces=[],reserved_abandoned_unconsumed_nonces=[]))]
def read_fixture(r):
 for k,v in fixture_values:
  if r==k:return v
 return original_read(r)
def auth_fixture(r):
 if any(r==ctx[k] for k in ('request','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps')):return Path(r['path'])
 return original_auth(r)
m.read=read_fixture;m.auth=auth_fixture
successor,independent,got_context,got_subjects=m.binding_metadata(binding);assert successor==op and independent==rev and got_context==ctx and got_subjects==fullsubjects
# The raw reset is genuinely parsed by Q as the same authorized period; effective
# UTC/MONO/BOOT have already tightened by three seconds, while operation limits
# remain the immutable original armed/bootstrap maximum.
earlier=copy.deepcopy(state);earlier['weekly_confirmed_usage']=earlier['weekly_usage']=row(m.WEEKLY['resets_at']-3)
for key in ('weekly_effective_end','weekly_effective_monotonic_end','weekly_effective_boot_end'):earlier[key]-=3
ceil=m.confirmed_weekly_ceiling(earlier);assert ceil==tuple(x-3 for x in m.MAXIMUM)
inside=[x-1 for x in ceil]
try:old.validate_operation(successor,independent,got_subjects,got_context,inside,ceil)
except ValueError as error:assert str(error)=='strict operation cutoff inside actual earliest weekly clocks'
else:raise AssertionError('original a3fb false refusal did not reproduce')
assert m.validate_operation(successor,independent,got_subjects,got_context,inside,ceil)==m.MAXIMUM
for i in range(3):
 at=list(inside);at[i]=ceil[i];reject(lambda:m.validate_operation(successor,independent,got_subjects,got_context,at,ceil))
later=copy.deepcopy(state);later['weekly_confirmed_usage']=later['weekly_usage']=row(m.WEEKLY['resets_at']+3)
for key in ('weekly_effective_end','weekly_effective_monotonic_end','weekly_effective_boot_end'):later[key]+=3
assert m.confirmed_weekly_ceiling(later)==m.MAXIMUM
# Exercise only the exact guard's final guardian-clock expression as AST, without
# calling guard() or any live source/owner. Equal at each observed cap refuses.
tree=ast.parse(p.read_bytes());guardfn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='guard');condition=next(x.value.args[0] for x in guardfn.body if isinstance(x,ast.Expr)and isinstance(x.value,ast.Call)and getattr(x.value.func,'id',None)=='need' and 'observed' in ast.unparse(x.value.args[0]));expr=compile(ast.Expression(condition),'<final_guardian_minima>','eval');assert eval(expr,dict(clocks=inside,observed=inside,limits=m.MAXIMUM,ceilings=ceil))
for i in range(3):
 observed=list(inside);observed[i]=ceil[i];assert not eval(expr,dict(clocks=inside,observed=observed,limits=m.MAXIMUM,ceilings=ceil))
print('PASS full in-memory binding_metadata→confirmed period→operation path: earlier effective all-three accepted before minimum; old a3fb refuses; equality rejected on all axes; later cannot extend; final guardian equality rejected')
