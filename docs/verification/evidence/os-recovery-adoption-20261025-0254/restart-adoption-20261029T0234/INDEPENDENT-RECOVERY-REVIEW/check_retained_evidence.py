"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read retained evidence only. Does not import operation modules or query live actors.
"""
import ast
import hashlib
import json
from pathlib import Path
import signal

D = Path(__file__).resolve().parent
B = D.parent.parent
R = B / 'restart-adoption-20261028T1911/CURRENT118-FAILED-GUARD-RETIREMENT-RELEASE-2'
T = B / 'CURRENT118-postbuild-current-successor-preparation-1/source-2/RECOVERY-ACCEPTANCE-FIELDS.TEMPLATE.NOT-A-PASS.json'
checks = []
refs = []

def need(ok, message):
    if not ok:
        raise AssertionError(message)
    checks.append(message)

def ref(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def auth(row, decode=True):
    actual = ref(row['path'])
    need(actual == row, 'exact retained bytes: ' + row['path'])
    refs.append(row)
    raw = Path(row['path']).read_bytes()
    return json.loads(raw) if decode else raw

def load(path):
    return auth(ref(path))

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'

template = load(T)
release_ref = ref(R / 'ROOT-RELEASE.ACTUAL.json')
release = auth(release_ref)
source_review = auth(release['source_review'])
execution_review = auth(release['execution_review'])
publication = auth(release['source_publication'])
operation = auth(release['current_operation'])
need(release['decision'] == 'GRANT_ONE_EXACT_IDLE_FAILED_HELPER_PIDFD_RETIREMENT'
     and release['maximum_invocations'] == release['signal_budget'] == 1
     and release['container_mutations_allowed'] == 0 and release['records_released'] == [],
     'one consumed exact helper operation; zero container mutations or record release')
need(source_review['independent'] is True and source_review['implementation_ownership'] is False
     and source_review['decision'] == 'PASS_SOURCE' and source_review['files'] == release['files'],
     'independent source approval binds exact released files')
need(execution_review['independent'] is True and execution_review['implementation_ownership'] is False
     and execution_review['decision'] == 'PASS_EXECUTION'
     and execution_review['release_payload_sha256'] == hashlib.sha256(canonical({k:v for k,v in release.items() if k != 'execution_review'})).hexdigest(),
     'independent execution approval binds actual canonical release excluding only execution_review')
need(publication['status'] == 'PASS_FETCHED_EXACT_17_RUNTIME_DEPENDENCIES'
     and publication['commit'] == release['source_checkpoint'] == '5ba7911fdb72f62a118ef85229f9f2dcdb2bfd3a',
     'actual fetched seventeen-file source publication and checkpoint')
published = {r['actual']['path']: r['actual'] for r in publication['rows']}
for row in release['files'].values():
    need(published.get(row['path']) == row, 'published runtime dependency: ' + row['path'])
    auth(row, False)
need(len(release['files']) == 17 and operation['target'] == release['target']
     and operation['operation'] == 'RETIRE_EXACT_FAILED_CURRENT118_IDLE_HELPER_ONLY',
     'seventeen runtime dependencies and exact current operation target')
custody_ref = ref(R / 'POST-RECOVERY-CUSTODY.ACTUAL.json')
custody = auth(custody_ref)
result = auth(custody['recovery_result'])
target = auth(custody['target_parent_join'])
operator = auth(custody['operator_parent_join'])
operator_normalized_ref = dict(path=str(D.parent / 'RECOVERY-OPERATOR-PARENT-JOIN.NORMALIZED.ACTUAL.json'),bytes=2701,sha256='d96fa3941c13ab161505e62eba83996a8194930dd7dab2bcbd0daa43f1ea29e9')
operator_normalized = auth(operator_normalized_ref)
need(operator_normalized['actual_parent_receipt'] == custody['operator_parent_join'],
     'normalized operator receipt preserves exact immutable actual parent evidence1380b2d5')
expected_normalized = dict(operator)
for field in ['birth','parent_birth']:
    need(isinstance(operator[field],str) and operator[field].isdigit()
         and str(int(operator[field])) == operator[field], 'canonical decimal original operator field: '+field)
    expected_normalized[field] = int(operator[field])
need({k:v for k,v in operator_normalized.items() if k not in ['actual_parent_receipt','normalization','recorded_epoch']} == expected_normalized
     and set(operator_normalized) == set(expected_normalized) | {'actual_parent_receipt','normalization','recorded_epoch'}
     and operator_normalized['recorded_epoch'] >= operator['finish_epoch'],
     'normalization changes only the two known decimal birth field types; no join/argv/status/stream alterations')
need(result['schema'] == 'mckernel.current118.failed-idle-helper.retirement-complete.v1'
     and result['status'] == 'COMPLETE_FAILED_HELPER_RETIREMENT_PENDING_PARENT_JOIN'
     and result['release_sha256'] == release_ref['sha256'], 'actual completion binds current consumed release')
need(result['sole_signal'] == dict(returncode=0, signal=9, syscall=424)
     and result['exit_proof']['pidfd_exit_ready'] is True and result['replacement_root_lock'] == [27,4]
     and result['deferred_signals'] == [], 'sole exact pidfd signal, positive exit and same permanent lock inode')
need(result['target']['pid'] == 2232651 and result['target']['starttime'] == '103343097'
     and result['target']['parent'] == 2232650 and result['target']['parent_birth'] == '103343093'
     and result['target']['lock_fd'] == 4, 'exact failed helper identity, parent and FD4')
source = auth(template['recovery_source'], False)
tree = ast.parse(source)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validate_parent_join')
namespace = dict(need=need, signal=signal, G=dict(pid=2232651,starttime='103343097',parent_pid=2232650,parent_birth='103343093'))
exec(compile(ast.Module(body=[fn],type_ignores=[]), template['recovery_source']['path'], 'exec'), namespace)
namespace['validate_parent_join'](target)
target_raw = auth(target['actual_parent_receipt'])
for value in [target_raw, operator]:
    need(value['positive_direct_parent_wait'] is True and value['positive_wait4_join'] is True
         and value['streams_closed'] is True and value['parent_streams_closed'] is True
         and value['process_group_absent'] is True and value['remaining_group_members'] == []
         and value['group_observation_errors'] == [], 'actual direct parent join, closed streams and absent group for ' + str(value['pid']))
    auth(value['stdout'], False)
    need(auth(value['stderr'], False) == b'', 'empty retained parent stderr for ' + str(value['pid']))
need(target_raw['pid'] == 2232651 and str(target_raw['birth']) == '103343097'
     and target_raw['parent_pid'] == 2232650 and str(target_raw['parent_birth']) == '103343093'
     and target_raw['returncode'] == -9 and target['tool_session'] == 90401,
     'original target direct parent result is minus nine, tool90401 complete')
need(operator['pid'] == 2256247 and str(operator['birth']) == '103808273'
     and operator['parent_pid'] == 2256246 and str(operator['parent_birth']) == '103808268'
     and operator['returncode'] == operator['raw_wait_status'] == 0
     and operator['release_sha256'] == release_ref['sha256'], 'recovery operator exact direct parent wait zero')
reply = json.loads(auth(operator['stdout'], False))
need(reply['status'] == result['status'] and reply['receipt'] == custody['recovery_result']['path']
     and reply['receipt_sha256'] == custody['recovery_result']['sha256'] and reply['cleanup_required'] is True,
     'actual operator stdout binds exact complete result')
prepared_ref = ref(Path(template['recovery_source']['path']).parent / 'guard-retirement-root1.prepared.json')
prepared = auth(prepared_ref)
need(prepared_ref['sha256'] == result['prepared_sha256'] and prepared['release_sha256'] == release_ref['sha256']
     and len(prepared['before']) == 2 and all(p['inputs'] == result['after']['inputs'] for p in prepared['before']),
     'durable prepared hash and identical two-before/after protected identities')
expected = {r['path']:r['sha256'] for r in release['protected_inputs']}
need(len(expected) == 62 and expected == result['original_failure_sha256']
     and expected == {p:r['sha256'] for p,r in result['after']['inputs'].items()},
     'all sixty-two original protected digests retained across exact operation')
clients = []
for row in result['after']['command_receipts']:
    client = auth(row)
    need(client['positive_wait4'] is True and client['returncode'] == 0 and client['wait4_status'] == 0
         and client['wait4_pid'] == client['pid'] and client['group_absent'] is True
         and client['group_members'] == [] and client['streams_closed'] is True
         and client['client_retirement_unproven'] is False and client['signals_sent'] == 0,
         'actual positive wait4/stream/group receipt for recovery query ' + str(client['pid']))
    for raw in client['raw'].values():
        auth(raw, False)
    clients.append(dict(pid=client['pid'],birth=client['birth']))
need(len(clients) == len({c['pid'] for c in clients}) == 12, 'all twelve distinct recovery query clients positively joined')
need(custody['actor_absence']['2232651'] is True and custody['actor_absence']['2232650'] is True
     and custody['permanent_mutex']['device'] == 27 and custody['permanent_mutex']['inode'] == 4
     and custody['permanent_mutex']['observed_locks'] == [], 'retained post-join target/parent absence and unchanged unlocked permanent inode')
need(result['current_free'] is custody['current_free'] is target['current_free'] is False
     and result['old_readonly_client_status'] == custody['old_readonly_client_status'] == target['first_readonly_client_status'] == 'UNKNOWN'
     and result['cleanup_required'] is True and result['acceptance_credit'] is False
     and custody['container_retired'] is target['container_retired'] is False,
     'original UNKNOWN preserved; stopped container, current-free and OS/native acceptance remain open')
need(result['after']['container'][0]['Id'] == 'd980474cc189c35f6d78132856be10b6903aac988808336e7d44efcca0f4108f'
     and result['after']['container'][0]['State']['Running'] is False,
     'CURRENT118 stopped container remains present and requires separate ordinary retirement')
acceptance = dict(template)
acceptance.update(independent=True, implementation_ownership=False,
                  decision='PASS_EXACT_CURRENT118_FAILED_HELPER_RETIREMENT',
                  recovery_result=custody['recovery_result'], target_parent_join=custody['target_parent_join'],
                  operator_parent_join=operator_normalized_ref)
need(set(acceptance) == set(template), 'exact existing RECOVERY-ACCEPTANCE-FIELDS template schema')
(D / 'RECOVERY-ACCEPTANCE-FIELDS.ACTUAL.json').write_text(json.dumps(acceptance,indent=2)+'\n')
report = dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
              reviewer='/root/recovery_review', decision=acceptance['decision'], independent=True,
              implementation_ownership=False, checks=checks, input_refs=refs, query_clients=clients,
              acceptance=ref(D / 'RECOVERY-ACCEPTANCE-FIELDS.ACTUAL.json'), post_recovery_custody=custody_ref,
              reviewer_runtime_actions=0, runtime_authority=None, current_free=False,
              old_readonly_client_status='UNKNOWN', container_retired=False, native_acceptance=False,
              operator_parent_normalization='Root d96fa394 normalized only two canonical decimal birth strings to integers; original1380b2d5 retained unchanged and independently checked against every original field. This is data normalization, no new wait or replay.',
              downstream_compatibility_issue=None)
(D / 'REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(decision=acceptance['decision'], checks=len(checks), acceptance=ref(D / 'RECOVERY-ACCEPTANCE-FIELDS.ACTUAL.json'), review=ref(D / 'REVIEW.json')),indent=2))
