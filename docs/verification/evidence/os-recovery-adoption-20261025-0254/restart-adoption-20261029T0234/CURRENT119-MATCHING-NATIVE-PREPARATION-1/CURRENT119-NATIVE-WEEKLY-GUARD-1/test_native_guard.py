"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure operation and in-memory context fixtures; no actual guard, proc or native call.
"""
from pathlib import Path
import copy,importlib.util,math
D=Path(__file__).resolve().parent;p=D/'native_operation_guard.py';s=importlib.util.spec_from_file_location('native_guard_fixture',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);fixed=m.fixed_subjects();assert len(fixed)==27
q=m.load(fixed['guardian'],'pure_confirmed_period')
def row(reset,used=99):return q.weekly_row(dict(limitId='codex',primary=dict(resetsAt=reset,windowDurationMins=10080,usedPercent=used)))
r=row(m.WEEKLY['resets_at']);state=dict(thread_id=m.THREAD,weekly_confirmed_usage=r,weekly_usage=r,weekly_confirmation_pending=False,weekly_usage_error=None,weekly_effective_end=m.MAXIMUM[0],weekly_effective_monotonic_end=m.MAXIMUM[1],weekly_effective_boot_end=m.MAXIMUM[2]);assert m.confirmed_weekly_ceiling(state,q)==m.MAXIMUM
for delta in (-3,3):
 a=copy.deepcopy(state);a['weekly_confirmed_usage']=a['weekly_usage']=row(m.WEEKLY['resets_at']+delta);assert m.confirmed_weekly_ceiling(a,q)==m.MAXIMUM
ctx={'fixture':'not-real'};subjects=fixed;op=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',operation=m.OPERATION,window_sha256=m.WINDOW_SHA,first_prepared_window_sha256=m.WINDOW_SHA,weekly_limit_identity=m.WEEKLY,billing_mode='included_only',allow_prepaid_fallback=False,predecessor_cutoffs=None,operation_cutoffs=list(m.MAXIMUM),subjects=subjects,context=ctx,guardian=dict(source=fixed['guardian'],entrypoint='guard'),source_owners=['/root','/root/m14_integration_terra']);review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,implementation_ownership=False,reviewer='/root/fixture-reviewer',operation=m.OPERATION,successor=op)
ceiling=tuple(x-3 for x in m.MAXIMUM);clocks=[x-1 for x in ceiling];assert m.validate_operation(op,review,subjects,ctx,clocks,ceiling)==m.MAXIMUM
n=0
def reject(fn):
 global n
 try:fn()
 except (ValueError,KeyError,TypeError):n+=1;return
 raise AssertionError('invalid native operation accepted')
for i in range(3):
 t=list(clocks);t[i]=ceiling[i];reject(lambda:m.validate_operation(op,review,subjects,ctx,t,ceiling))
 t=copy.deepcopy(op);t['operation_cutoffs'][i]=m.MAXIMUM[i]+1;reject(lambda:m.validate_operation(t,dict(review,successor=t),subjects,ctx,clocks,ceiling))
for k,v in [('operation','current119-build'),('operation','current119-postjoin-current67'),('billing_mode','credits'),('allow_prepaid_fallback',True),('predecessor_cutoffs',[1,1,1])]:
 a=copy.deepcopy(op);a[k]=v;reject(lambda:m.validate_operation(a,dict(review,successor=a),subjects,ctx,clocks,ceiling))
for k,v in [('usedPercent',100),('usedPercent',None),('usedPercent',math.nan),('resetsAt',None)]:
 a=copy.deepcopy(state);a['weekly_confirmed_usage'][k]=v;a['weekly_usage']=copy.deepcopy(a['weekly_confirmed_usage']);reject(lambda:m.confirmed_weekly_ceiling(a,q))
a=copy.deepcopy(state);a['weekly_confirmed_usage']=a['weekly_usage']=row(m.WEEKLY['resets_at']+604800);reject(lambda:m.confirmed_weekly_ceiling(a,q))
for k,v in [('weekly_confirmation_pending',True),('weekly_usage_error','unknown'),('weekly_usage',None)]:
 a=copy.deepcopy(state);a[k]=v;reject(lambda:m.confirmed_weekly_ceiling(a,q))
reject(lambda:m.validate_operation(op,dict(review,reviewer='/root/m14_integration_terra'),subjects,ctx,clocks,ceiling));reject(lambda:m.validate_operation(op,dict(review,independent=False),subjects,ctx,clocks,ceiling))
assert not m.BINDING.exists(),'no actual native operation binding fabricated'
print('PASS 27 exact native subjects, same-period ±3, earlier 3-axis min and',n,'functional negatives; no actual guard/proc/native')

# Complete in-memory Root-context -> subjects -> native-operation path. No fake
# files or approval receipts are written; source/manifest inputs remain genuine.
def fake(name):return dict(path='/fixture/'+name,bytes=1,sha256='a'*64)
c=dict(post119_current_free=fake('free'),current_ledger=fake('ledger'),current_boundary=fake('boundary'),nonce='ab'*16,source_authority=fake('authority'),case_capability=fake('capability'),staged_manifest=fixed['manifest'],armed_controls=m.ARM,bootstrap_caps=fake('bootstrap'),native_source_closure={k:fake(k)for k in ('root_once_startup_entry.py','bind_startup_resource.py','capture_fresh_startup_resource.py','prepare_startup_bindings.py','run_native_startup_capture.py','run_startup_resource_once.py')})
buildnonce='dc62394cd7ae43bf8bd1559fd7f5ad20';free=dict(independent=True,implementation_ownership=False,current_free=True,decision='PASS_FIXTURE',old_readonly_client_status='UNKNOWN');build=dict(nonce=buildnonce,container='593abb2a8d66817d66c6a530341db17fa7873a42f390d3693792556f4b15cd24',normal_retirement_pending=False,current_physical_clearance_pending=False,current_free=c['post119_current_free'],actual_outputs=[dict(sha256=fixed['image']['sha256'],bytes=fixed['image']['bytes'])]);ledger=dict(author='/root',complete_within_declared_current_boundary=True,root_attests_no_unlisted_post_boundary_execution_or_custody_operation=True,current_physical_clearance_pending=False,latest_accepted_free_boundary=c['post119_current_free'],consumed_nonces=[buildnonce]+['%032x'%i for i in range(1,73)],reserved_abandoned_unconsumed_nonces=[],current119_build=build);boundary=dict(author='/root',nonce_ledger=c['current_ledger'],native_custody_clearance=c['post119_current_free'],root_attests_exact_current_boundary=True)
original_read,original_auth=m.read,m.auth
fixture=[(c['post119_current_free'],free),(c['current_ledger'],ledger),(c['current_boundary'],boundary)]
def fixture_read(r):
 for k,v in fixture:
  if r==k:return v
 return original_read(r)
def fixture_auth(r):
 if any(r==c[k]for k in ('post119_current_free','current_ledger','current_boundary','source_authority','case_capability','staged_manifest','armed_controls','bootstrap_caps')) or r in c['native_source_closure'].values():return Path(r['path'])
 return original_auth(r)
m.read=fixture_read;m.auth=fixture_auth;resolved=m.context_subjects(c);full=copy.deepcopy(op);full.update(subjects=resolved,context=c);fullreview=dict(review,successor=full);assert m.validate_operation(full,fullreview,resolved,c,clocks,ceiling)==m.MAXIMUM
for target,key,val in [(free,'current_free',False),(free,'old_readonly_client_status','REAPED'),(ledger,'current_physical_clearance_pending',True),(build,'normal_retirement_pending',True),(boundary,'root_attests_exact_current_boundary',False)]:
 before=target[key];target[key]=val;reject(lambda:m.context_subjects(c));target[key]=before
bad=copy.deepcopy(c);bad['nonce']=buildnonce;reject(lambda:m.context_subjects(bad))
print('PASS in-memory post119 free/retirement/ledger -> native context -> operation; six invalid-context cases rejected; no live checks')

# Reuse the original native entry_clamps AST with only AUTHORIZED_FIXED_LIMITS
# projected to current weekly maxima; no entry module or live guard is executed.
import ast
p115=Path(fixed['prior_template:run_native_startup_capture.py']['path']);tree=ast.parse(p115.read_bytes());nodes=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ('cutoff_triplet','entry_clamps')];assert len(nodes)==2
ns={'math':math,'AUTHORIZED_FIXED_LIMITS':m.MAXIMUM};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p115)+':pure_original_entry_clamps','exec'),ns)
resource=list(m.MAXIMUM);observed=[x-2 for x in clocks];clamped=ns['entry_clamps'](clocks,observed,resource,resource,ceiling);assert clamped['effectiveCutoffs']==list(ceiling)
for i in range(3):
 bad=list(clocks);bad[i]=ceiling[i];reject(lambda:ns['entry_clamps'](bad,observed,resource,resource,ceiling))
print('PASS original native entry_clamps with current effective minima; equality on three axes refused')
