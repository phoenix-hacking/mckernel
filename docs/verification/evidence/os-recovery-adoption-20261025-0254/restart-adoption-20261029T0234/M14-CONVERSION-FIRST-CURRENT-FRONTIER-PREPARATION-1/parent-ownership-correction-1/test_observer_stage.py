"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure metadata/fixture tests only, no live guard or physical observation.
"""
import ast,copy,importlib.util,json
from pathlib import Path
source=Path(__file__).with_name('observe_conversion_frontier.py')
spec=importlib.util.spec_from_file_location('candidate',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checker=m.load(m.CHECKER,'test_current119_metadata_only');capture=m.read(m.CAPTURE);parent=m.read(m.PARENT)
free=json.loads(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-POSTJOIN-CURRENTFREE-PREPARATION-1/actual-acceptance-1/CURRENT-FREE.ACTUAL.json').read_bytes())
actors=m.frontier(checker,free,capture,parent)
supp_path=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-MATCHING-NATIVE-PREPARATION-1/ROOT-POST-ROOT68-STAGE-CUSTODY.ACTUAL.json')
supp_ref=m.ref(supp_path);assert supp_ref['sha256']=='0561e67d9c3169662d3b46fc0aea7c93ce8bcac47fbf17cc40319acd6b78d5bc';supp=m.read(supp_ref);accept=m.read(m.STAGE_ACCEPTANCE);stage=m.read(supp['stage_result']);stage_parent=m.read(supp['stage_parent_join']);grant=m.read(supp['stage_grant'])
context=dict(current_ledger=supp['root68_ledger'],post119_current_free=m.ACCEPTED_FREE);authority=dict(post_root68_custody_supplement=supp_ref)
stage_actors=m.append_post68_stage(actors,supp,supp_ref,authority,context,accept,stage,stage_parent,grant)
assert len(stage_actors)==201 and len({(x['pid'],x['start'])for x in stage_actors})==196 and stage_actors[:199]==actors
assert stage_actors[-2]['pid']==2574948 and stage_actors[-2]['group']==2574948 and stage_actors[-1]['pid']==2574947 and stage_actors[-1]['group'] is None
mutations=[('supp','old_readonly_client_status','known'),('supp','all_post_root68_custody_listed',False),('supp','stage_result',{}),('supp','stage_grant',{}),('authority','post_root68_custody_supplement',{}),('accept','independent',False),('accept','native_acceptance',True),('stage','nonce','fabricated'),('parent','positive_direct_wait_join',False),('parent','process_group_absent',False),('parent','signals_sent',1),('grant','paid_fallback',True)]
for obj,key,value in mutations:
 vals=copy.deepcopy(dict(supp=supp,authority=authority,accept=accept,stage=stage,parent=stage_parent,grant=grant));vals[obj][key]=value
 try:m.append_post68_stage(actors,vals['supp'],supp_ref,vals['authority'],context,vals['accept'],vals['stage'],vals['parent'],vals['grant'])
 except (ValueError,KeyError,AssertionError):continue
 raise AssertionError('accepted mutated stage '+obj+'.'+key)
bad=copy.deepcopy(supp);bad['unmeasured_outer_tool_actor']['birth']=110734865
try:m.append_post68_stage(actors,bad,supp_ref,authority,context,accept,stage,stage_parent,grant)
except (ValueError,KeyError,AssertionError):pass
else:raise AssertionError('invented outer birth accepted')
ledgerpath=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/ROOT68-CURRENT119-ADOPTION-1/ROOT68-NONCE-LEDGER.ACTUAL.json');boundarypath=ledgerpath.with_name('ROOT68-CURRENT-BOUNDARY.ACTUAL.json')
ledger=m.read(m.ref(ledgerpath));boundary=m.read(m.ref(boundarypath));m.validate_adoption(ledger,boundary,m.ref(ledgerpath),m.ACCEPTED_FREE,free,actors)
assert len(actors)==199 and len({(x['pid'],x['start']) for x in actors})==194
assert actors[-1]['pid']==2569587 and actors[-1]['group'] is None and actors[-2]['pid']==2569588 and actors[-2]['group']==2569588
for key,value in [('current_free',False),('independent',False),('implementation_ownership',True),('Root67',{}),('capture_positive_join',{}),('old_readonly_client_status','known')]:
 bad=copy.deepcopy(free);bad[key]=value
 try:m.frontier(checker,bad,capture,parent)
 except (ValueError,AssertionError):continue
 raise SystemExit('not refused '+key)
for key,value in [('positive_wait4_join',False),('process_group_absent',False),('signals_sent',1)]:
 bad=copy.deepcopy(parent);bad[key]=value
 try:m.frontier(checker,free,capture,bad)
 except (ValueError,AssertionError):continue
 raise SystemExit('not refused parent '+key)
tree=ast.parse(source.read_bytes());names={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
assert {'frontier','validate_route','observe'}<=names
assert 'validate_candidate(' not in source.read_text() and 'physical.configure(binding[\'physical_history_binding\'])' in source.read_text()
assert 'checker.BASE.validate_absence_reports([report],actors)' in source.read_text()
print('PASS actual Root68/frontier+0561 stage custody 201 rows/196 identities; 22 negative mutations; unmeasured outer birth preserved; no physical or guard invocation')
