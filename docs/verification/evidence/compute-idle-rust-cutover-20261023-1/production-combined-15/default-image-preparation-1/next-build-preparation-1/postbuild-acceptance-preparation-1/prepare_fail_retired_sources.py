"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Metadata/source preparation only; never invokes observer, cleanup, Docker or probes.
"""
from pathlib import Path
import ast, hashlib, json, difflib

P = Path(__file__).resolve().parent / 'bound-fail-retired-source-pending-1'
N = Path(__file__).resolve().parent.parent
OLD = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-5/actual-owner-consumer-correction-1/next-build-preparation-1/post-ten-build-admission-preparation-1/normal-build-retirement-preparation-1/bound-current-normal-image-source-1')

def read(path):
    return json.loads(Path(path).read_bytes())

def ref(path):
    path = Path(path)
    assert path.stat().st_size < 200000, 'No large artifact hashing in this preparation'
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def write(name, value):
    with (P / name).open('x') as out:
        out.write(value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True) + '\n')

def assign(text, name, value):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name)
    lines = text.splitlines(keepends=True)
    lines[node.lineno-1:node.end_lineno] = [name + ' = ' + value + '\n']
    return ''.join(lines)

def replace_function(text, name, replacement):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    lines = text.splitlines(keepends=True)
    lines[node.lineno-1:node.end_lineno] = [replacement.strip() + '\n']
    return ''.join(lines)

assert not P.exists()
P.mkdir(mode=0o700)
request = read(N / 'image-request.PREPARED.json')
operation = read(N / 'NEXT-BUILD-OPERATION.READY-FOR-REVIEW.json')
outer_path = N / 'actual-build-owner-capture-1'
owner = read(outer_path / 'stdout')
outer = read(outer_path / 'status.json')
join_path = Path(__file__).resolve().parent / 'ACTUAL-CLOSED-FAILED-BUILD-AND-RETAINED-OWNERSHIP.json'
join = read(join_path)
assert owner['status'] == 'FAIL' and owner['retired'] is True and owner['terminal_container_retained'] is True
assert outer['status'] == 'FAIL_PRESERVED_STOPPED' and outer['returncode'] == 1
assert outer['pid'] == 3980236 and outer['proc_start_ticks'] == '59610555'
work, evidence = Path(request['work_root']), Path(request['owner_evidence_root'])
namespace = evidence.parent
target = {key: owner[key] for key in ('container_id', 'container_name', 'owner_nonce')}
target.update(owner_pid=outer['pid'], owner_starttime=outer['proc_start_ticks'], exit_code=1, image_id=owner['terminal_container_info']['Image'])
typed = {key: request[key] for key in ('candidate_identity_scope', 'candidate_sha', 'materialization_sha256', 'source_derivative_sha256', 'source_identity', 'source_root')}
roles = dict(request=operation['request'], owner_receipt=ref(evidence / 'owner-receipt.json'), driver_receipt=ref(Path(request['evidence_root']) / 'receipt.json'), guard_result=ref(outer_path / 'status.json'), outer_status=ref(outer_path / 'status.json'), outer_stdout=ref(outer_path / 'stdout'), outer_stderr=ref(outer_path / 'stderr'), image_owner=operation['owner'], artifact_acceptance=ref(join_path), materialization=ref(Path(request['source_root']).parent / 'MATERIALIZATION-RESULT.json'))
# This NULL is genuine. The prepared observer refuses before any root operation.
inspect_ref = dict(path=str(Path(__file__).resolve().parent / 'actual-readonly-terminal-inspect-1/stdout'), sha256=None, bytes=None)
roles['terminal_inspection'] = inspect_ref
for key in ('driver_path', 'provenance_path', 'host_owner_path', 'source_manifest', 'toolchain_manifest', 'gitlink_manifest'):
    sha_key = key.replace('_path', '') + '_sha256' if key.endswith('_path') else key + '_sha256'
    roles[key] = dict(path=request[key], sha256=request[sha_key], bytes=Path(request[key]).stat().st_size)
roles['container_log'] = ref(evidence / 'attempt/container.log')
clients, log = [], None
for i, path in enumerate(sorted((evidence / 'attempt').glob('command-*/status.json'))):
    status = read(path)
    assert status['state'] == 'exited' and status['exit_code'] == 0 and not status.get('client_retirement_unproven')
    client = dict(pid=status['pid'], birth_starttime=None, status=ref(path), stdout=ref(path.parent / 'stdout'), stderr=ref(path.parent / 'stderr'))
    clients.append(client)
    for name in ('status', 'stdout', 'stderr'):
        roles['client:%d:%s' % (i, name)] = client[name]
    if 'logs' in status['argv']:
        log = {name: client['status' if name == 'status.json' else name] for name in ('status.json', 'stdout', 'stderr')}
assert len(clients) == 7 and log
hold = dict(status='HOLD_RETAINED_FAILED_BUILD_OWNERSHIP', container_id=target['container_id'], controller_joined_group_absent_streams_closed=True, container_retained=True, shared_heavy_token_retained=True, normal_cleanup_required=True, physical_clearance=False, actual_owner_status='FAIL', actual_outer_status='FAIL_PRESERVED_STOPPED')
write('CURRENT-LIVE-POSTJOIN.HOLD.json', hold)
roles['guard_postjoin'] = ref(P / 'CURRENT-LIVE-POSTJOIN.HOLD.json')
ancestry = []
for path in reversed((namespace, *namespace.parents)):
    s = path.lstat()
    ancestry.append(dict(path=str(path), device=s.st_dev, inode=s.st_ino, uid=s.st_uid, gid=s.st_gid, mode=s.st_mode))
ns = {k: v for k, v in ancestry[-1].items() if k != 'path'}
retirement = dict(schema='mckernel.m14.normal-image.closed-retained-build-authority.v1', status='HOLD_RETAINED_BUILD_OWNERSHIP', source_identity=typed, target=target, owner_receipt=roles['owner_receipt'], guard_result=roles['guard_result'], outer_status=roles['outer_status'], terminal_fresh_inspect=inspect_ref, artifact_acceptance=roles['artifact_acceptance'], current_live_postjoin=roles['guard_postjoin'], shared_record_from_actual_owner=owner['shared_heavy_operation'], physical_release=False, cleanup_authorized=False)
write('CURRENT-RETAINED-BUILD-AUTHORITY.HOLD.json', retirement)
roles['retained_review'] = ref(P / 'CURRENT-RETAINED-BUILD-AUTHORITY.HOLD.json')
case = dict(schema='mckernel.m14.current-normal-image.finite-terminal-case.v1', status='ACTUAL_CLOSED_FAILED_IMAGE_INPUTS_NO_PHYSICAL_RELEASE', target=target, request=roles['request'], source_identity=typed, namespace=str(namespace), namespace_binding=ns, namespace_ancestry=ancestry, guard_capture=str(evidence / 'attempt'), current_live_postjoin=roles['guard_postjoin'], artifact_acceptance=roles['artifact_acceptance'], finite_roles=roles, finite_role_count=len(roles), finite_unique_paths=sorted({x['path'] for x in roles.values()}), finite_unique_path_count=len({x['path'] for x in roles.values()}), successful_artifacts_required=False, execution_authorized=False, physical_release=False, cleanup_release=None, cleanup_result=None, client_ledger=clients)
write('FAILED-CASE-STATIC.PENDING.json', case)
engine_old = (OLD / 'cleanup_pass_image.py').read_text()
engine = engine_old
values = dict(SOURCE_REFS=repr(roles), CURRENT_TYPED_REQUEST=repr(typed), PUBLISHED_SCRIPT=repr('docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-15/default-image-preparation-1/next-build-preparation-1/postbuild-acceptance-preparation-1/bound-fail-retired-source-pending-1/cleanup_pass_image.py'), NAMESPACE='Path(' + repr(str(namespace)) + ')', NAMESPACE_ANCESTRY=repr(ancestry), NAMESPACE_BINDING=repr(ns), PREFIX=repr('m14-failed-retired-image-terminal-candidate15-1'), ATTEMPT='Path(' + repr(request['common_exclusion_path']) + ')', REQUEST='Path(' + repr(str(N / 'image-request.PREPARED.json')) + ')', LEASE='Path(' + repr(request['lease_path']) + ')', OUTPUT='Path(' + repr(str(work)) + ')', EVIDENCE='Path(' + repr(str(evidence)) + ')', KNOWN_TARGET=repr({k: v for k, v in target.items() if k != 'image_id'}), REQUEST_SHA=repr(roles['request']['sha256']), IMAGE_CANDIDATE=repr(request['candidate_sha']), PASS_LOG_CHANNELS=repr(log))
for name, value in values.items():
    engine = assign(engine, name, value)
# Only the two closed-receipt predicates and literal current capture paths change.
engine = engine.replace("receipt.get('status') != 'PASS'", "receipt.get('status') != 'FAIL' or receipt.get('exit_code') != 1 or receipt.get('error') != 'offline image driver failed'")
engine = engine.replace("guard.get('status')!='PASS' or guard.get('returncode')!=0", "guard.get('status')!='FAIL_PRESERVED_STOPPED' or guard.get('returncode')!=1")
engine = engine.replace("target['exit_code']!=0", "target['exit_code']!=1")
old_n = str(OLD.parent.parent.parent)
old_capture = str(OLD.parent.parent / 'actual-build-owner-capture-1/status.json')
assert old_capture in engine
engine = engine.replace(old_capture, str(outer_path / 'status.json'))
old_attempt = '/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-5/actual-owner-consumer-correction-1/next-build-preparation-1/pinned-full-image-attempt-2/owner-evidence/attempt'
engine = engine.replace(old_attempt, str(evidence / 'attempt'))
ast.parse(engine)
write('cleanup_pass_image.py', engine)
observer_old = (OLD / 'observe_current_pass_image_retirement.py').read_text()
observer = observer_old
ov = dict(FAILURE_CASE='Path(' + repr(str(P / 'FAILED-CASE-STATIC.PENDING.json')) + ')', FAILURE_CASE_SHA=repr(ref(P / 'FAILED-CASE-STATIC.PENDING.json')['sha256']), PREP='Path(' + repr(str(P)) + ')', CASE='Path(' + repr(str(namespace)) + ')', CAPTURE='Path(' + repr(str(evidence / 'attempt')) + ')', SOURCE='Path(' + repr(str(P / 'cleanup_pass_image.py')) + ')', SOURCE_SHA=repr(ref(P / 'cleanup_pass_image.py')['sha256']), RETIREMENT='Path(' + repr(str(P / 'CURRENT-RETAINED-BUILD-AUTHORITY.HOLD.json')) + ')', RETIREMENT_SHA=repr(ref(P / 'CURRENT-RETAINED-BUILD-AUTHORITY.HOLD.json')['sha256']), NONCE=repr('m14-failed-retired-image-observation-candidate15-1'), BOOT=repr(owner['shared_heavy_operation']['record']['boot_id']), PIDS=repr(tuple(c['pid'] for c in clients)), TERMINAL_INSPECTION_SHA='None', CURRENT_EXPECTED_SOURCE=repr(typed), PENDING_BINDINGS=repr(('fresh_exact_CID_inspection_ref',)))
for name, value in ov.items():
    observer = assign(observer, name, value)
observer = replace_function(observer, 'current_pass_prerequisites', '''
def current_pass_prerequisites(retirement,case,root_join,artifact):
    # Exact failed owner/driver evidence, never production/default-link acceptance.
    need(retirement['schema']=='mckernel.m14.normal-image.closed-retained-build-authority.v1' and
         retirement['status']=='HOLD_RETAINED_BUILD_OWNERSHIP' and retirement['physical_release'] is False and
         retirement['cleanup_authorized'] is False and case['execution_authorized'] is False and
         case['successful_artifacts_required'] is False,'exact failed-retired retained case required')
    need(retirement['target']==case['target'] and case['source_identity']==CURRENT_EXPECTED_SOURCE and
         retirement['source_identity']==CURRENT_EXPECTED_SOURCE,'exact current target/source authority')
    for key in ('owner_receipt','guard_result','outer_status','artifact_acceptance'):
        need(retirement[key]==case['finite_roles'][key],'exact failed closed role:'+key)
    need(retirement['terminal_fresh_inspect']==case['finite_roles']['terminal_inspection'] and
         retirement['current_live_postjoin']==case['current_live_postjoin'],'exact fresh inspection/HOLD refs')
    need(artifact['status']=='ACTUAL_FAILED_BUILD_CLOSED_NORMAL_OWNER_RETIRED_CONTAINER_RETAINED_PHYSICAL_PENDING' and
         {k:artifact['owner']['ref'][k] for k in ('path','sha256','bytes')}==case['finite_roles']['owner_receipt'] and
         {k:artifact['driver']['ref'][k] for k in ('path','sha256','bytes')}==case['finite_roles']['driver_receipt'] and
         {k:artifact['outer']['ref'][k] for k in ('path','sha256','bytes')}==case['finite_roles']['outer_status'],'exact failed receipt authority')
    need(artifact['owner']['status']=='FAIL' and artifact['owner']['exit_code']==1 and
         artifact['owner']['retired'] is True and artifact['owner']['terminal_container_retained'] is True and
         artifact['driver']['status']=='FAIL' and artifact['driver']['phase']=='artifact-validation' and
         artifact['driver']['error']=='M14 observer failed: successor-real-ABI-arch-x86_64-kernel-cpu-c' and
         artifact['outer']['result']['status']=='FAIL_PRESERVED_STOPPED' and
         artifact['outer']['result']['returncode']==1,'original exact failure retained')
    need(root_join['status']=='HOLD_RETAINED_FAILED_BUILD_OWNERSHIP' and
         root_join['container_id']==case['target']['container_id'] and
         root_join['controller_joined_group_absent_streams_closed'] is True and
         root_join['container_retained'] is True and root_join['shared_heavy_token_retained'] is True and
         root_join['normal_cleanup_required'] is True and root_join['physical_clearance'] is False,
         'closed controller is physical HOLD only')
''')
observer = observer.replace('successful_artifacts_required=True', 'successful_artifacts_required=False')
ast.parse(observer)
write('observe_current_pass_image_retirement.py', observer)
def functions(text):
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(text).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
ef, en, of, on = functions(engine_old), functions(engine), functions(observer_old), functions(observer)
ed = [k for k in ef if ef[k] != en[k]]
od = [k for k in of if of[k] != on[k]]
assert ed == ['image_owner_receipt_binding', 'image_receipt_binding', 'configure'], ed
assert od == ['current_pass_prerequisites', 'main'], od
write('cleanup_pass_image.py.diff', ''.join(difflib.unified_diff(engine_old.splitlines(True), engine.splitlines(True), fromfile=str(OLD / 'cleanup_pass_image.py'), tofile=str(P / 'cleanup_pass_image.py'))))
write('observe_current_pass_image_retirement.py.diff', ''.join(difflib.unified_diff(observer_old.splitlines(True), observer.splitlines(True), fromfile=str(OLD / 'observe_current_pass_image_retirement.py'), tofile=str(P / 'observe_current_pass_image_retirement.py'))))
write('SOURCE-DELTA-AND-PENDING-FACTS.json', dict(scope=__doc__, engine_functions_changed=ed, observer_functions_changed=od, unchanged_engine_function_class_AST=[k for k in ef if ef[k] == en[k]], unchanged_observer_function_class_AST=[k for k in of if of[k] == on[k]], exact_failure_preserved=True, client_births='NULL; legacy original capture records no birth ticks', future_fresh_inspect=None, future_physical_observation=None, future_root_cleanup_release=None, execution_authorized=False, pending_source_refuses_at_main=True, current_artifact_acceptance=False))
write('SOURCE-PINS.json', {path.name: ref(path) for path in P.iterdir() if path.is_file()})
print(json.dumps(dict(source=ref(P / 'cleanup_pass_image.py'), observer=ref(P / 'observe_current_pass_image_retirement.py'), delta=ref(P / 'SOURCE-DELTA-AND-PENDING-FACTS.json'), engine_changed=ed, observer_changed=od, actual_queries=False, actual_cleanup=False)))
