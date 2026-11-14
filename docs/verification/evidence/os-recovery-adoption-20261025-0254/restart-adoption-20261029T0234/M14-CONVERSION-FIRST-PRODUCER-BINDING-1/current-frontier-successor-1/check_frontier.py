#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic in-memory frontier checks; no actual controls, guards or processes.
"""
import ast,copy,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent
old=(P/'seal_root_conversion_inputs.py').read_text();new=(D/'seal_root_conversion_inputs.py').read_text()
def node(text,name):
 t=ast.parse(text);return next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==name)
for name in ('cutoffs','origin','render_sources','main'):
 assert ast.dump(node(old,name),include_attributes=False)==ast.dump(node(new,name),include_attributes=False)
for f in ('accepted_bindings.py','run_build_only.template.py','build_only_worker.template.py','hold_and_run_build_only.py'):
 assert (D/f).read_bytes()==(P/f).read_bytes()
assert new.count('accepted.accepted_metadata(oldq,oldfree,oldledger); accepted.accepted_chain(oldq)')==1
n=node(new,'validate_latest_frontier');m=ast.Module(body=[n],type_ignores=[]);ast.fix_missing_locations(m)
def r(name):return {'path':'/synthetic/'+name,'bytes':1,'sha256':name}
rootfree=r('old-free');rootledger=r('old-ledger');rootboundary=r('old-boundary')
refs={name:r(name) for name in ('bundle','ledger','boundary','review','free','observe','caller')}
history={'consumed_nonces':[format(i,'032x') for i in range(73)],'reserved_abandoned_unconsumed_nonces':[format(1000,'032x')]}
ledger={'author':'/root','complete_within_declared_current_boundary':True,'root_attests_no_unlisted_post_boundary_execution_or_custody_operation':True,'current_physical_clearance_pending':False,'latest_accepted_free_boundary':refs['free'],'consumed_nonces':history['consumed_nonces']+[format(80,'032x')],'reserved_abandoned_unconsumed_nonces':history['reserved_abandoned_unconsumed_nonces'][:],'reserved_unused_nonces':[format(90,'032x')]}
boundary={'schema':'mckernel.root-current-frontier-boundary.v1','author':'/root','decision':'ADOPT_EXACT_CURRENT_FRONTIER','nonce_ledger':refs['ledger'],'native_custody_clearance':refs['free'],'predecessor_boundary':rootboundary,'actual_frontier_observation':refs['observe'],'actual_caller_closure':refs['caller'],'retained_actor_rows':207,'distinct_actor_identities':202,'root_attests_exact_current_boundary':True,'root_attests_no_unlisted_post_boundary_execution_or_custody_operation':True,'runtime_authority':None}
checks={k:True for k in ('full_73_nonce_history_preserved','all_unknown_outcomes_preserved','all_later_custody_accounted','current_frontier_and_caller_closure_exact','independent_free_and_no_pending_custody','root_boundary_current_and_acyclic')}
review={'schema':'mckernel.independent-current-frontier-review.v1','decision':'PASS_EXACT_CURRENT_FRONTIER_ADOPTION','independent':True,'implementation_ownership':False,'reviewer':'/root/synthetic_reviewer','runtime_authority':None,'nonce_ledger':refs['ledger'],'current_boundary':refs['boundary'],'independent_current_free':refs['free'],'predecessor_boundary':rootboundary,'actual_frontier_observation':refs['observe'],'actual_caller_closure':refs['caller'],'checks':checks}
bundle={'schema':'mckernel.root-current-frontier-bundle.v1','author':'/root','decision':'BIND_REVIEWED_CURRENT_FRONTIER','ledger':refs['ledger'],'boundary':refs['boundary'],'independent_adoption_review':refs['review'],'runtime_authority':None}
free={'independent':True,'implementation_ownership':False,'current_free':True,'runtime_authority':None}
fixtures={refs['bundle']['path']:bundle,refs['ledger']['path']:ledger,refs['boundary']['path']:boundary,refs['review']['path']:review,refs['free']['path']:free,refs['observe']['path']:{},refs['caller']['path']:{},rootfree['path']:free,rootledger['path']:ledger,rootboundary['path']:boundary}
q={'current_bindings':refs['bundle'],'current_ledger':refs['ledger'],'current_free':refs['free'],'nonce':format(110,'032x')}
state={'docs':fixtures}
def auth(row):
 assert row['path'] in state['docs'];return row['path']
def read(path):return state['docs'][path]
ns={'read':read,'auth':auth,'re':re,'ROOT68_FREE':rootfree,'ROOT68_LEDGER':rootledger,'ROOT68_BOUNDARY':rootboundary}
exec(compile(m,'<pure-synthetic-frontier>','exec'),ns)
assert ns['validate_latest_frontier'](q,history)==ledger
reject=[]
def test(name,mutate):
 data=copy.deepcopy(fixtures);query=copy.deepcopy(q);mutate(data,query);state['docs']=data
 try:ns['validate_latest_frontier'](query,history)
 except (AssertionError,KeyError,TypeError,ValueError):reject.append(name)
 else:raise AssertionError(name+' was accepted')
finally_reset=lambda:None
test('stale Root68 free',lambda d,q:q.__setitem__('current_free',rootfree))
test('stale Root68 ledger',lambda d,q:(q.__setitem__('current_ledger',rootledger),d[refs['bundle']['path']].__setitem__('ledger',rootledger)))
test('wrong typed review',lambda d,q:d[refs['review']['path']].__setitem__('decision','PASS_OTHER'))
test('not independent',lambda d,q:d[refs['review']['path']].__setitem__('independent',False))
test('wrong reviewer owner',lambda d,q:d[refs['review']['path']].__setitem__('reviewer','/root/f03_munmap_terra'))
test('wrong free pointer',lambda d,q:d[refs['ledger']['path']].__setitem__('latest_accepted_free_boundary',r('other')))
test('pending custody',lambda d,q:d[refs['ledger']['path']].__setitem__('current_physical_clearance_pending',True))
test('changed old nonce',lambda d,q:d[refs['ledger']['path']]['consumed_nonces'].__setitem__(4,format(400,'032x')))
test('duplicate nonce',lambda d,q:d[refs['ledger']['path']]['consumed_nonces'].append(format(4,'032x')))
test('consumed new nonce',lambda d,q:q.__setitem__('nonce',format(80,'032x')))
test('reserved new nonce',lambda d,q:q.__setitem__('nonce',format(90,'032x')))
test('later custody unknown not reviewed',lambda d,q:d[refs['review']['path']]['checks'].__setitem__('all_later_custody_accounted',False))
test('boundary embeds review',lambda d,q:d[refs['boundary']['path']].__setitem__('independent_adoption_review',refs['review']))
test('boundary observation aliases review',lambda d,q:d[refs['boundary']['path']].__setitem__('actual_frontier_observation',refs['review']))
test('review wrong boundary pointer',lambda d,q:d[refs['review']['path']].__setitem__('current_boundary',r('other')))
state['docs']=fixtures
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_SYNTHETIC_ONLY_CURRENT_FRONTIER_PREDICATE','positive_synthetic_frontier':True,'negative_cases':reject,'unchanged_functions':['cutoffs','origin','render_sources','main'],'unchanged_producer_bytes':['accepted_bindings.py','run_build_only.template.py','build_only_worker.template.py','hold_and_run_build_only.py'],'actual_current_files_created':False,'guard_calls':0,'compiler_calls':0,'runtime_authority':None}
(D/'SYNTHETIC-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],len(reject),'negative cases')
