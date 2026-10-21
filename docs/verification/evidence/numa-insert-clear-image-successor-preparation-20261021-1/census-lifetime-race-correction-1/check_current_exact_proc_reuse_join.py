"""Necessary current byte/AST reuse join plus original negative only; no15replay.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import ast,hashlib,io,json,os,traceback,types
from pathlib import Path
PINS={'current': {'bytes': 90010, 'path': '/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/cleanup_pass_image.py', 'sha256': '86654275eced623bb15ce289ca6555264b2820b56336e629fe084cb9aed96ce0'}, 'candidate': {'bytes': 91157, 'path': '/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/census-lifetime-race-correction-1/cleanup_pass_image.PROC-CORRECTED.py', 'sha256': 'b8c7d0f6ff3dc7303ca2063575c1affe0b63a4b283b0cc3223c4f3a11f93d80a'}, 'prior_failed_proc': {'bytes': 3564, 'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/cleanup-census-failure-repair-1/PROC_CODE.before.py', 'sha256': '986e64c50fd8d78bbe3c23e86a690e67b51255ab03c9f03f29db30ee50891532'}, 'prior_accepted_proc': {'bytes': 4636, 'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/cleanup-census-failure-repair-1/PROC_CODE.proposed.py', 'sha256': '24e27a493a84a1ab6c3d22a5248ae456288fa590fc93e31b3fb5a0a29d8659af'}, 'prior_accepted_engine': {'bytes': 89439, 'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/cleanup-census-failure-repair-1/cleanup_pass_image.proposed.py', 'sha256': '5f6716a8914564cfae06693931033fa2efacae49aaf2e21f18600463b376d21d'}, 'prior_actual_acceptance': {'bytes': 4074, 'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/cleanup-census-failure-repair-1/ROOT-RECORDED-INDEPENDENT-ACTUAL-SYNTHETIC-BODY-ACCEPTANCE-1.json', 'sha256': '8dd59ea8e695ffb97231de280225d52b339ae37cc8356e7d8addf5c3f6994cc5'}, 'qualified_fixture': {'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/cleanup-census-failure-repair-1/propose_snapshot_actual_body_check.py', 'sha256': '86dcff5d63887f9af4dfd4f326c1042ecc8a0e176cc0d78ff542b63699e1dc0d', 'bytes': 7492}}
def read(ref):
    raw=Path(ref['path']).read_bytes()
    assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
    return raw
def proc(tree):
    return ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='PROC_CODE' for x in n.targets)))
def other(tree):
    return [ast.dump(n,include_attributes=False) for n in tree.body if not (isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='PROC_CODE' for x in n.targets))]
def validator(tree):
    return ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_process_report'),include_attributes=False)
a=ast.parse(read(PINS['current']));b=ast.parse(read(PINS['candidate']));prior=ast.parse(read(PINS['prior_accepted_engine']))
before=proc(a);after=proc(b)
assert before.encode()==read(PINS['prior_failed_proc']) and after.encode()==read(PINS['prior_accepted_proc'])
assert other(a)==other(b) and validator(a)==validator(prior)==validator(b)
acceptance=json.loads(read(PINS['prior_actual_acceptance']))
assert acceptance['status']=='PASS_ACTUAL_PRODUCER_BODY_RACE_AND_STRICT_PREDICATES_ONLY' and acceptance['checks']==15
assert acceptance['candidate']==PINS['prior_accepted_engine']
fixture_tree=ast.parse(read(PINS['qualified_fixture']));names={'stat_bytes','process','ProcFixture'};fixture_nodes=[]
for node in fixture_tree.body:
    if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names:fixture_nodes.append(node)
    elif isinstance(node,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='BASE' for x in node.targets):fixture_nodes.append(node)
assert len(fixture_nodes)==4
ns=dict(io=io,os=os,types=types);exec(compile(ast.Module(body=fixture_nodes,type_ignores=[]),'<qualified synthetic fixture bodies>','exec'),ns)
fixture=ns['ProcFixture']('benign-first-stat');tree=ast.parse(before)
nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in ('publisher','snapshot')) or (isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='heavy' for x in n.targets))]
assert len(nodes)==3
label=PINS['current']['path']+'::<original PROC_CODE>'
body_ns=dict(os=fixture,open=fixture.open,caller=[10,'100'],caller_parent=1)
exec(compile(ast.Module(body=nodes,type_ignores=[]),label,'exec'),body_ns)
try:body_ns['snapshot']()
except FileNotFoundError as error:
    frames=[f for f in traceback.extract_tb(error.__traceback__) if f.filename==label]
    assert error.filename=='/proc/30/stat' and fixture.attempt==1 and frames[-1].name=='snapshot' and frames[-1].lineno==23
    negative={'type':type(error).__name__,'synthetic_path':error.filename,'function':frames[-1].name,'PROC_CODE_line':frames[-1].lineno,'same_actual_failure_callsite':True}
else:raise AssertionError('original first-stat negative not reproduced')
print(json.dumps(dict(status='PASS_CURRENT_PROC_EXACT_ACCEPTED_REUSE_JOIN_AND_ORIGINAL_NEGATIVE_ONLY',checks=4,current_failed_proc_sha256=hashlib.sha256(before.encode()).hexdigest(),reused_candidate_proc_sha256=hashlib.sha256(after.encode()).hexdigest(),all_other_AST_identical=True,validator_AST_equals_prior_accepted=True,original_negative=negative,prior15_replayed=False,candidate_functions_executed=False,real_proc_reads=False,engine_imported=False,root_or_census_or_cleanup_or_signals_or_locks=False),sort_keys=True,separators=(',',':')))
