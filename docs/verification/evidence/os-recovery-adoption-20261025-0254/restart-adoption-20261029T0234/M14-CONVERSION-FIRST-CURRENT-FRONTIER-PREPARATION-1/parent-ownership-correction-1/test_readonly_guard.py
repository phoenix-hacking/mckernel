"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure Q semantic-period and actual historical metadata tests. No live guard/proc.
"""
from pathlib import Path
import copy,importlib.util,math
D=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('pure_readonly_guard',D/'readonly_operation_guard.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);fixed=g.fixed_subjects();q=g.load(fixed['guardian'],'pure_weekly_semantic_validator')
def row(reset,used=99):return q.weekly_row(dict(limitId='codex',primary=dict(resetsAt=reset,windowDurationMins=10080,usedPercent=used)))
r=row(g.WEEKLY['resets_at']);state=dict(thread_id=g.THREAD,weekly_confirmed_usage=r,weekly_usage=r,weekly_confirmation_pending=False,weekly_usage_error=None,weekly_effective_end=g.MAXIMUM[0],weekly_effective_monotonic_end=g.MAXIMUM[1],weekly_effective_boot_end=g.MAXIMUM[2]);assert g.confirmed_weekly_ceiling(state,q)==g.MAXIMUM
for delta in (-3,3):
 a=copy.deepcopy(state);a['weekly_confirmed_usage']=a['weekly_usage']=row(g.WEEKLY['resets_at']+delta);assert g.confirmed_weekly_ceiling(a,q)==g.MAXIMUM
ctx={'fixture':'not-real'};op=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',operation=g.OPERATION,window_sha256=g.WINDOW_SHA,first_prepared_window_sha256=g.WINDOW_SHA,weekly_limit_identity=g.WEEKLY,billing_mode='included_only',allow_prepaid_fallback=False,predecessor_cutoffs=None,operation_cutoffs=list(g.MAXIMUM),subjects=fixed,context=ctx,guardian=dict(source=fixed['guardian'],entrypoint='guard'),source_owners=['/root','/root/m14_integration_terra']);review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,implementation_ownership=False,reviewer='/root/fixture-reviewer',operation=g.OPERATION,successor=op)
ceiling=tuple(x-3 for x in g.MAXIMUM);clocks=[x-1 for x in ceiling];assert g.validate_operation(op,review,fixed,ctx,clocks,ceiling)==g.MAXIMUM
n=0
def reject(fn):
 global n
 try:fn()
 except (ValueError,KeyError,TypeError,AssertionError):n+=1;return
 raise AssertionError('invalid fixture accepted')
for i in range(3):
 t=list(clocks);t[i]=ceiling[i];reject(lambda:g.validate_operation(op,review,fixed,ctx,t,ceiling))
for k,v in [('operation','current119-matching-original235-native'),('operation','current119-postjoin-current67'),('billing_mode','credits'),('allow_prepaid_fallback',True),('predecessor_cutoffs',[1,1,1])]:
 a=copy.deepcopy(op);a[k]=v;reject(lambda:g.validate_operation(a,dict(review,successor=a),fixed,ctx,clocks,ceiling))
for k,v in [('usedPercent',100),('usedPercent',None),('usedPercent',math.nan),('resetsAt',None)]:
 a=copy.deepcopy(state);a['weekly_confirmed_usage'][k]=v;a['weekly_usage']=copy.deepcopy(a['weekly_confirmed_usage']);reject(lambda:g.confirmed_weekly_ceiling(a,q))
a=copy.deepcopy(state);a['weekly_confirmed_usage']=a['weekly_usage']=row(g.WEEKLY['resets_at']+604800);reject(lambda:g.confirmed_weekly_ceiling(a,q))
for k,v in [('weekly_confirmation_pending',True),('weekly_usage_error','unknown'),('weekly_usage',None)]:
 a=copy.deepcopy(state);a[k]=v;reject(lambda:g.confirmed_weekly_ceiling(a,q))
reject(lambda:g.validate_operation(op,dict(review,reviewer='/root/m14_integration_terra'),fixed,ctx,clocks,ceiling));reject(lambda:g.validate_operation(op,dict(review,independent=False),fixed,ctx,clocks,ceiling))
# Actual historical refs with in-memory proposed Root authority. No fixture files written.
A=D.parent.parent;historical=g.ref(A/'ROOT68-CURRENT119-ADOPTION-1/ROOT68-NONCE-LEDGER.ACTUAL.json');boundary=g.ref(A/'ROOT68-CURRENT119-ADOPTION-1/ROOT68-CURRENT-BOUNDARY.ACTUAL.json');free=g.ref(A/'CURRENT119-POSTJOIN-CURRENTFREE-PREPARATION-1/actual-acceptance-1/CURRENT-FREE.ACTUAL.json');NP=A/'CURRENT119-MATCHING-NATIVE-PREPARATION-1';stage=g.ref(NP/'ROOT-POST-ROOT68-STAGE-CUSTODY.ACTUAL.json');r1=g.ref(NP/'ROOT-POST-ROOT68-RESOURCE1-CUSTODY.V2.ACTUAL.json')
def fake(name):return dict(path='/fixture/'+name,bytes=1,sha256='a'*64)
source=fake('source');bootstrap=fake('bootstrap');authority=dict(schema='mckernel.root-conversion-frontier-custody.v1',author='/root',decision='BIND_CONVERSION_FRONTIER_READONLY_CUSTODY',runtime_authority=None,current_free=False,historical_ledger=historical,historical_boundary=boundary,historical_free=free,old_readonly_client_status='UNKNOWN',uninstrumented_source_tool_identities='UNKNOWN',no_unlisted_physical_or_custody_operations_since_resource1=True,post_root68_custody_supplement=stage,post_root68_resource1_custody_supplement=r1)
c=dict(current_ledger=historical,current_boundary=boundary,post119_current_free=free,nonce='ab'*16,source_authority=source,armed_controls=g.ARM,bootstrap_caps=bootstrap,readonly_source_closure=dict(observer=g.ref(D/'observe_conversion_frontier.py'),physical_adapter=g.ref(D/'readonly_history_guard.py'),capture_parent=g.ref(D/'root_capture_parent.py')))
oldread,oldauth=g.read,g.auth
def read(r):return authority if r==source else oldread(r)
def auth(r):return Path(r['path']) if r in (source,bootstrap) else oldauth(r)
g.read=read;g.auth=auth;subjects=g.context_subjects(c);assert subjects['root:current_ledger']==historical and subjects['root:post119_current_free']==free
for k,v in [('current_free',True),('old_readonly_client_status','REAPED'),('uninstrumented_source_tool_identities','KNOWN'),('no_unlisted_physical_or_custody_operations_since_resource1',False)]:
 old=authority[k];authority[k]=v;reject(lambda:g.context_subjects(c));authority[k]=old
for value in ('a876915e19964ad8978887961e630f65','dc62394cd7ae43bf8bd1559fd7f5ad20'):
 b=copy.deepcopy(c);b['nonce']=value;reject(lambda:g.context_subjects(b))
b=copy.deepcopy(c);b['readonly_source_closure']['observer']=b['readonly_source_closure']['physical_adapter'];reject(lambda:g.context_subjects(b))
assert not g.BINDING.exists()
print('PASS actual historical Root68/free and two custody refs, synthetic Root readonly context, same-period ±3, Q three-clock min,',n,'negative cases; no live guard/proc')
