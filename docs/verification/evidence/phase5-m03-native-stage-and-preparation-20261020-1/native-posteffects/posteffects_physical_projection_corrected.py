"""Pure, exact-kind current205 terminal-cleanup physical receipt decoder.
No snapshot/root/guest operations. Full authoritative descriptors retained.
"""
from pathlib import Path
import hashlib,json,os,stat
SCHEMA='mckernel.independent-current205-cleanup-physical-release-review.v1'
STATUS='PASS_ACTUAL_CURRENT205_CLEANUP_POSTJOIN_AND_POSITIVE_PHYSICAL_RETIREMENT'
TRANSACTION_FIELDS={'path','sha256','size','device','inode','uid','gid','mode','nlink'}
def need(ok,why):
 if not ok:raise ValueError(why)
COMPACT_FIELDS = {'path', 'sha256', 'bytes'}
IDENTITY_FIELDS = {'path', 'sha256', 'size', 'device', 'inode', 'uid', 'gid',
                   'mode', 'nlink', 'mtime_ns', 'ctime_ns'}
STREAM_FIELDS=(IDENTITY_FIELDS-{'size'})|{'bytes'}
STAT_FIELDS = ('st_dev', 'st_ino', 'st_uid', 'st_gid', 'st_mode', 'st_nlink',
               'st_size', 'st_mtime_ns', 'st_ctime_ns')

def no_duplicates(pairs):
 result = {}
 for key, value in pairs:
  need(key not in result, 'duplicate physical JSON key')
  result[key] = value
 return result

def checked_bytes(r, limit=4<<20):
 """Read one known full descriptor through a stable, bounded regular-file FD."""
 need(isinstance(r, dict) and set(r) in (COMPACT_FIELDS, TRANSACTION_FIELDS, IDENTITY_FIELDS, STREAM_FIELDS),
      'known full authoritative descriptor shape')
 p = Path(r['path'])
 need(p.is_absolute() and p.resolve(strict=True) == p and not p.is_symlink(),
      'canonical physical descriptor')
 expected = r['bytes'] if set(r) in (COMPACT_FIELDS,STREAM_FIELDS) else r['size']
 need(type(expected) is int and 0 <= expected <= limit, 'bounded physical descriptor size')
 fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
 try:
  before = os.fstat(fd)
  need(stat.S_ISREG(before.st_mode) and before.st_size == expected,
       'bounded regular physical descriptor')
  raw = bytearray()
  while len(raw) <= expected:
   block = os.read(fd, min(65536, expected + 1 - len(raw)))
   if not block:
    break
   raw.extend(block)
  after = os.fstat(fd)
  linked = p.lstat()
  need(all(getattr(before, k) == getattr(after, k) == getattr(linked, k)
           for k in STAT_FIELDS), 'stable physical descriptor FD/path identity')
  need(len(raw) == expected and hashlib.sha256(raw).hexdigest() == r['sha256'],
       'exact physical descriptor bytes')
  if set(r) in (TRANSACTION_FIELDS, IDENTITY_FIELDS, STREAM_FIELDS):
   actual = dict(device=after.st_dev, inode=after.st_ino, uid=after.st_uid,
                 gid=after.st_gid, mode=oct(stat.S_IMODE(after.st_mode)),
                 nlink=after.st_nlink, size=after.st_size,
                 mtime_ns=after.st_mtime_ns, ctime_ns=after.st_ctime_ns,bytes=after.st_size)
   need(all(r[k] == actual[k] for k in r if k not in ('path','sha256')), 'full actual transaction/raw record identity')
  return bytes(raw)
 finally:
  os.close(fd)

def parsed(raw):
 return json.loads(raw, object_pairs_hook=no_duplicates)
def checked(r, limit=4<<20):
 return parsed(checked_bytes(r,limit))
def compact(r):
 need(type(r) is dict and set(r)==COMPACT_FIELDS,'complete compact authority descriptor')
 need(type(r['path']) is str and Path(r['path']).is_absolute() and type(r['bytes']) is int and r['bytes']>=0,'compact descriptor path/length')
 need(type(r['sha256']) is str and len(r['sha256'])==64 and all(c in '0123456789abcdef' for c in r['sha256']),'compact SHA256')
 return r


CURRENT_EXECUTION_REF=dict(path='/home/holden/mckernel-work/host-preparation/phase5-opt-in-production-link-image-independent-review-20261020-1/CURRENT-PASS-IMAGE-EXACT-TWO-PHASE-CLEANUP-EXECUTION-REVIEW.json',sha256='4ef55e8e1d523edfc901c0d004620c22bd100cc3ace78c3e392dd61886b75445',bytes=386966)
CURRENT_EXECUTION_SCHEMA='mckernel.independent-current-image.successor-cleanup-exact-conditional-execution-review.v1'
CURRENT_EXECUTION_DECISION='PASS_EXACT_SUCCESSOR_READ_ONLY_PREFLIGHT_THEN_CONDITIONAL_CLEANUP_AND_POSTJOIN'

def execution_join(execution, execution_ref, release):
 """Two explicit existing kinds; current release uses exact reviewed body+inline."""
 compact(execution_ref)
 if execution['schema']==CURRENT_EXECUTION_SCHEMA:
  need(execution_ref==CURRENT_EXECUTION_REF,'exact complete current execution review descriptor')
  need(execution['status']=='PASS_EXECUTION' and execution['decision']==CURRENT_EXECUTION_DECISION and execution['implementation_ownership'] is False and execution['reviewer']=='/root/owned_offload_review' and execution['payload_author']=='/root','exact independent current successor execution tuple')
  payload=execution['cleanup_payload_without_execution_review']
  raw=(json.dumps(payload,sort_keys=True,separators=(',',':'))+'\n').encode()
  expected='c4ae495a8e52ef4d8e670bfb5032a90f00f4ba8acbf0fc0dcdb278ceab497c60'
  need(hashlib.sha256(raw).hexdigest()==expected==execution['reviewed_cleanup_payload_sha256'] and len(raw)==execution['reviewed_cleanup_payload_bytes']==264956,'whole reviewed current cleanup payload compact JSON plus LF')
  payload_ref=compact(execution['reviewed_payload_without_execution_review'])
  need(payload_ref['sha256']==expected and payload_ref['bytes']==264956 and checked_bytes(payload_ref)==raw,'full actual reviewed body descriptor and bytes')
  need(set(release)==set(payload)|{'execution_review'} and {k:v for k,v in release.items() if k!='execution_review'}==payload,'release differs from exact reviewed body only by execution_review')
  inline=execution['execution_review_inline_fields']
  need(set(inline)=={'evidence_sha256','implementation_ownership','reviewed_cleanup_payload_sha256','reviewer','status'} and inline['evidence_sha256']=='REPLACE_WITH_ACTUAL_SHA256_OF_THIS_REPORT_AFTER_WRITE','exact documented current inline slots')
  expected_inline=dict(inline,evidence_sha256=execution_ref['sha256'])
  need(release['execution_review']==expected_inline and expected_inline['status']=='PASS' and expected_inline['implementation_ownership'] is False and expected_inline['reviewed_cleanup_payload_sha256']==expected and expected_inline['reviewer']==execution['reviewer'],'exact actual full current inline review SHA and payload ownership')
  return payload['observation']['target']
 need(execution['schema']=='mckernel.independent-exact-terminal-cleanup-execution-review.v1' and execution['status']=='PASS' and execution['decision']=='PASS_EXACT_CURRENT_CONTAINER_JOURNALED_CLEANUP_AND_CONDITIONAL_POSTJOIN_ONLY' and execution['native_authorized'] is False and execution['implementation_ownership'] is False,'exact independent legacy terminal execution review')
 need(release['execution_review']['execution_review']==execution_ref and release['execution_review']['evidence_sha256']==execution_ref['sha256'],'full legacy cleanup execution authority descriptor')
 return execution['target']

"""Source-only exact-kind POSTEFFECTS adapter; actual role contract unbound.
Functional OS/apps plus Rust cutover. No effects, snapshots or runtime authority.
Never interprets this scope as completed cleanup or PRECOMMON recovery.
"""
SCHEMA = 'mckernel.independent-current-image.quarantine-recovery-physical.v1'
STATUS = 'PASS'
DECISION = 'PASS_PHYSICAL_RETIREMENT_ONLY'
SCOPE = 'CURRENT_IMAGE_POST_EFFECTS_QUARANTINE_RECOVERY_ONLY'
PRODUCER_BINDINGS=dict(path='/home/holden/mckernel-work/host-preparation/phase5-current-pass-image-terminal-20261020-1/post-effects-quarantine-recovery-preparation-1/FINAL-PRODUCER-ROLE-BINDINGS.json',sha256='7276b8ff03cffcc7e0444f695ea5e32d36a70689f4fabec88abf1f4883ddfba2',bytes=9378)
COMPACT_FIELDS = {'path', 'sha256', 'bytes'}
SINGLE_AUTHORITY_ROLES = (
    'case', 'execution_release', 'independent_execution_review', 'recovery_source',
    'target_pidfd_retirement', 'positive_parent_joins_and_same_mutex',
    'original_tool_join', 'original_outer_status', 'record_release_evidence',
    'source_request', 'cleanup_release', 'cleanup_execution_review', 'post_effects_state_before_retirement',
    'post_effects_state_after_retirement',
)

def authority_roles(report):
    """Validate explicit agreed full-role descriptors; retain whole rows."""
    refs = [report[key] for key in SINGLE_AUTHORITY_ROLES]
    modes = report['recovery_mode_statuses']
    need(type(modes) is list and len(modes) == 2,
         'exact current two recovery mode status roles')
    archives = report['protected_raw_archives']
    need(type(archives) is list and len(archives) > 0,
         'complete retained protected raw archive roles')
    need(len(archives)==7, 'seven complete retained raw archive authority refs')
    refs += modes + archives
    for row in refs:
        need(type(row) is dict and set(row) == COMPACT_FIELDS,
             'complete exact three-field authoritative role')
        need(type(row['path']) is str and row['path'].startswith('/')
             and type(row['bytes']) is int and row['bytes'] >= 0
             and type(row['sha256']) is str and len(row['sha256']) == 64
             and all(c in '0123456789abcdef' for c in row['sha256']),
             'concrete full authority path/hash/length')
    return refs

def report_conditions(report):
    kind(report)
    for key in ('container_created', 'container_absent', 'record_release_complete',
                'quarantine_retained'):
        need(report[key] is True, 'actual POSTEFFECTS condition ' + key)
    for key in ('journal_complete', 'transaction_complete', 'cleanup_replayed'):
        need(report[key] is False, 'truthful incomplete nonreplayed transaction ' + key)
    need(report['preservation']['all_rows_exact_pre_cleanup'] is True,
         'independent exact preservation finding')
    text = report['preservation']['source_build_evidence_inventories_preserved']
    need(type(text) is str and bool(text), 'actual preservation scope text')
    return authority_roles(report)


def need(ok, reason):
    if not ok:
        raise ValueError(reason)

def kind(report):
    need(type(report) is dict, 'whole recovery report object required')
    need(report.get('schema') == SCHEMA and report.get('status') == STATUS
         and report.get('decision') == DECISION and report.get('scope') == SCOPE,
         'exact explicit POSTEFFECTS recovery kind; no completed or PRECOMMON substitution')

import base64

STATE_CHECKS = {'actual_mount_binding', 'actual_protected_files',
    'all_finite_74_unchanged', 'all_selected_78_unchanged',
    'both_complete_inventories_unchanged', 'exact_eight_event_journal_no_complete',
    'original_two_record_archive_identities'}
STATE_FILES = {'capture', 'common_archive', 'journal', 'plan', 'quarantine',
               'shared_archive', 'transaction_mutex'}
STATE_SOURCE = dict(path='/home/holden/mckernel-work/host-preparation/phase5-current-pass-image-terminal-20261020-1/post-effects-quarantine-recovery-preparation-1/observe_exact_post_effect_quarantine.py',sha256='439db32bb9e3c4dadeea880d159592659f402e0bc3e90dd5a2fbb9c2ae0b0a76',bytes=10080)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def saved_file(row):
    # These root-read FD rows are authenticated inside the complete saved state.
    # Keep their full eleven fields; do not reinterpret them as current user FDs.
    need(type(row) is dict and set(row)=={'fd','raw_base64'}, 'exact saved root FD/raw pair')
    fd=row['fd']
    need(set(fd)==IDENTITY_FIELDS and type(fd['size']) is int and 0<=fd['size']<=4<<20,
         'complete bounded original root FD identity')
    raw=base64.b64decode(row['raw_base64'], validate=True)
    need(len(raw)==fd['size'] and hashlib.sha256(raw).hexdigest()==fd['sha256'],
         'saved FD full exact raw bytes')
    return raw

def state_join(state, release, request, after=False):
    expected='READ_ONLY_POST_EFFECT_QUARANTINE_STATE_AFTER_RETIREMENT' if after else 'READ_ONLY_POST_EFFECT_QUARANTINE_STATE'
    need(state['status']==expected, 'exact actual readonly state kind')
    need(state['mutation_performed'] is False and state['mutex_acquired'] is False
         and state['signals_sent']==0 and state['terminal_completion_claim'] is False
         and state['original_inner_failure_cause_recovered'] is False,
         'readonly state grants no mutation, completion or inferred cause')
    need(set(state['checks'])==STATE_CHECKS and all(v=={'passed':True} for v in state['checks'].values()),
         'seven exact completed readonly checks')
    need(set(state['files'])==STATE_FILES, 'seven complete original saved FD roles')
    raw={key:saved_file(row) for key,row in state['files'].items()}
    plan=parsed(raw['plan']);obs=release['observation'];target=obs['target']
    need(plan==state['plan'] and raw['plan']==canonical(plan)+b'\n'
         and hashlib.sha256(canonical(plan)).hexdigest()==state['plan_sha256'],
         'whole saved canonical plan and source hash')
    need(state['release_canonical_sha256']==plan['release_sha256']==hashlib.sha256(canonical(release)).hexdigest(),
         'internal complete release noLF hash distinct from external file hash')
    need(plan['schema']=='fp-save-image.terminal-cleanup.v1'
         and plan['container']==[target['container_id'],target['container_name'],target['owner_nonce']]
         and state['boot_id']==obs['boot_id'] and plan['filesystem_uuid']=='2a5768c8-718d-4914-bdc0-6b32c5a92a52',
         'whole actual source/plan target and fixed filesystem identity')
    need(state['selected_files']==obs['selected_files'] and len(state['selected_files'])==78
         and state['inventories']==obs['inventories'] and sorted(map(len,state['inventories'].values()))==[4,577],
         'full selected78 and both complete4/577 inventories unchanged')
    selected={r['path']:r for r in state['selected_files']}
    finite=state['finite_objects']
    need(len(selected)==78 and len(finite)==74 and len({r['path'] for r in finite})==74
         and all(set(r)==TRANSACTION_FIELDS and r==selected.get(r['path']) for r in finite),
         'full unique finite74 exact subset of selected78')
    rows=parsed(b'['+b','.join(raw['journal'].splitlines())+b']')
    events=[(event,index) for index in range(2) for event in
            ('before_exchange','after_exchange','release','after_release')]
    need(rows==state['journal_events'] and len(rows)==8, 'exact retained eight-event journal; no complete')
    previous=state['plan_sha256'];pid=state['files']['plan']['fd']
    for sequence,(row,(event,index)) in enumerate(zip(rows,events)):
        body={k:row[k] for k in ('event','index','sequence','plan_sha256','previous','plan_identity')}
        need(set(row)==set(body)|{'hash'} and body==dict(event=event,index=index,sequence=sequence,
             plan_sha256=state['plan_sha256'],previous=previous,plan_identity=[pid['device'],pid['inode']])
             and row['hash']==hashlib.sha256(canonical(body)).hexdigest(), 'exact original incomplete journal chain')
        previous=row['hash']
    need(raw['journal']==b''.join(canonical(r)+b'\n' for r in rows), 'whole canonical eight-row journal')
    paths=[request['lease_path'],request['common_exclusion_path'],
           '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock']
    need(state['active_name_states']==[dict(path=x,absent=True,errno=2) for x in paths],
         'exact three active names absent; quarantine is retained separately')
    need(state['files']['quarantine']['fd']['path']==release['transaction_paths'][4],
         'retained exact current quarantine full FD, never absence')
    inspect=state['container_inspect'];cid=target['container_id']
    need(set(inspect)=={'argv','direct_child_joined','returncode','stderr_base64','stdout_base64'}
         and inspect['direct_child_joined'] is True and inspect['returncode']==1
         and inspect['argv']==['/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect','--type','container',cid]
         and base64.b64decode(inspect['stdout_base64'],validate=True)==b'[]\n'
         and base64.b64decode(inspect['stderr_base64'],validate=True)==('Error response from daemon: No such container: '+cid+'\n').encode(),
         'actual exact CID absence closed Docker inspect')
    need(len(plan['records'])==2, 'exact original ownership pair in incomplete plan')
    for original,role,record in zip(paths[1:],('common_archive','shared_archive'),plan['records']):
        descriptor=state['files'][role]['fd'];value=parsed(raw[role])
        need(record==[original,str(Path(descriptor['path']).parent),Path(descriptor['path']).name,descriptor['sha256'],descriptor['inode'],descriptor['size']],
             'exact complete original/archive assignment despite incomplete final journal')
        need(value['boot_id']==state['boot_id'] and value['pid']==target['owner_pid']
             and value['starttime']==target['owner_starttime'] and value['inode']==descriptor['inode'],
             'original ownership record exact target and inode')
    need(parsed(raw['common_archive'])['schema']=='mckernel.native-exact-operational-exclusion.v1'
         and parsed(raw['shared_archive'])['schema']=='mckernel.heavy-operation.v1', 'exact original record kinds')
    terminal=plan['terminal'];rows=[r for r in selected.values() if
        [Path(r['path']).name,r['sha256'],r['inode'],r['size']]==terminal]
    need(type(terminal) is list and len(terminal)==4 and terminal[0]=='owner-receipt.json'
         and len(rows)==1, 'unique actual selected successful owner receipt tuple')
    receipt=checked(rows[0])
    need(receipt['schema']=='mckernel.native-exact-mckernel-image-container-receipt.v1'
         and receipt['status']=='PASS' and receipt['container_id']==target['container_id']
         and receipt['owner_nonce']==target['owner_nonce'], 'successful retained build receipt distinct from cleanup retirement')
    return dict(plan=plan, target=target, retained_quarantine=state['files']['quarantine']['fd'])


def normalized_identity(row):
    # Two source-declared serializations retain the same complete native FD.
    need(set(row) in (TRANSACTION_FIELDS, IDENTITY_FIELDS), 'complete native identity keys')
    result=dict(row)
    mode=row['mode']
    need(type(mode) is int or (type(mode) is str and mode.startswith('0o')), 'known producer permission representation')
    result['mode']=int(mode,8) if type(mode) is str else mode
    return result

def read_native(row):
    # checked_bytes accepts the exact octal-string transport; only the mode
    # scalar is represented canonically for comparison, all fields are retained.
    canonical_row=dict(row)
    if type(canonical_row['mode']) is int: canonical_row['mode']=oct(canonical_row['mode'])
    return checked(canonical_row)

def recovery_join(report, roles, before, after):
    case=checked(compact(roles['case']));review=checked(compact(roles['independent_execution_review']))
    release=checked(compact(roles['execution_release']))
    need(review['schema']=='mckernel.independent-current-image.cleanup-holder-pidfd-execution-review.v1'
         and review['status']=='PASS' and review['decision']=='PASS_EXECUTION'
         and review['implementation_ownership'] is False, 'exact independent recovery execution tuple')
    need(release['schema']=='mckernel.phase5.cleanup-holder-pidfd-release.v1'
         and release['status']=='PASS_EXECUTION_RELEASE' and release['execution_review']==roles['independent_execution_review']
         and release['case']==review['case']==roles['case'] and release['source']==review['source']==roles['recovery_source'],
         'complete distinct recovery release/review/case/source authority chain')
    reviewed=review['payload_without_execution_review'];raw=canonical(reviewed)+b'\n'
    need(checked_bytes(compact(review['reviewed_payload']))==raw
         and len(raw)==review['reviewed_release_payload_bytes']
         and hashlib.sha256(raw).hexdigest()==review['reviewed_release_payload_sha256']
         and {k:v for k,v in release.items() if k!='execution_review'}==reviewed
         and set(release)==set(reviewed)|{'execution_review'}, 'whole exact reviewed recovery payload plus LF')
    need(release['cleanup_replay_authorized'] is False and release['shared_release_authorized'] is False
         and release['fetched_source_verified'] is False and release['source_checkpoint'] is None
         and release['execution_count']==1 and release['signal_budget']==1,
         'bounded source-bound recovery; no cleanup replay or record mutation')
    checked_bytes(compact(roles['recovery_source']));checked_bytes(compact(review['after_state_source']))
    need(case['schema']=='mckernel.phase5.exact-cleanup-holder-retirement-case.v1'
         and case['request']==roles['source_request'] and case['prior_cleanup_release']==roles['cleanup_release']
         and case['prior_cleanup_execution_review']==roles['cleanup_execution_review'], 'complete case original authority joins')
    classification=checked(compact(case['closed_census'][2]))
    need(case['closed_census'][0]==roles['post_effects_state_before_retirement'] and classification['state_source']==STATE_SOURCE
         and classification['actual_state']==roles['post_effects_state_before_retirement'], 'complete original actual-state/source classification authority')
    checked_bytes(STATE_SOURCE)
    need(case['after_state_source']==review['after_state_source'], 'full exact actual after-state source authority')
    need(case['root_lock']==dict(device=27,fd=3,inode=4,path='/run/lock/mckernel-development.lock')
         and case['transaction_lock']['device']==before['files']['transaction_mutex']['fd']['device']
         and case['transaction_lock']['inode']==before['files']['transaction_mutex']['fd']['inode'], 'authenticated source-bound lock identities')
    need(case['original_processes']=={str(before[name]['pid']):dict(parent=before[name]['parent'],starttime=before[name]['starttime']) for name in ('parent','holder')}, 'entire authenticated original PID/start/PPID set')
    need(case['saved_child']==before['holder'] and case['saved_parent']==before['parent']
         and case['boot_id']==before['boot_id'] and case['quarantine_retained'] is True
         and case['journal_complete'] is False and case['transaction_complete'] is False,
         'exact authenticated original holder/parent and incomplete quarantine case')
    need(case['full_original_state_file_descriptors']=={k:v['fd'] for k,v in before['files'].items()},
         'all seven original complete FD identities bound to saved state')
    expected_modes={'argv','cpu7_released','direct_child_joined','elapsed_seconds','pid','proc_start_ticks','process_group_absent','returncode','status','stderr','stdout','streams_closed'}
    outputs=[]
    for reference in roles['recovery_mode_statuses']:
        capture=checked(compact(reference))
        need(set(capture)==expected_modes and capture['status']=='PASS' and capture['returncode']==0
             and all(capture[k] is True for k in ('cpu7_released','direct_child_joined','process_group_absent','streams_closed')),
             'exact closed successful recovery mode capture')
        for name in ('stdout','stderr'):
            need(set(capture[name])==STREAM_FIELDS, 'complete captured recovery FD identity')
            checked_bytes(capture[name])
        need(capture['stderr']['bytes']==0, 'empty recovery mode stderr')
        outputs.append(parsed(checked_bytes(capture['stdout'])))
    first,second=outputs
    need(first==checked(compact(roles['target_pidfd_retirement']))
         and second==checked(compact(roles['positive_parent_joins_and_same_mutex'])), 'whole exact mode result roles')
    need(first['status']=='TARGET_PIDFD_EXIT_READY_PARENT_JOINS_REQUIRED'
         and first['case_sha256']==roles['case']['sha256'] and first['exit_proof']['pidfd_exit_ready'] is True
         and first['sole_signal']==dict(syscall=424,signal=9,returncode=0)
         and first['parent_direct_join_claim'] is False and first['permanent_mutex_reacquisition_claim'] is False,
         'genuine selected pidfd exit; first mode does not claim parent/mutex completion')
    need(second['status']=='EXACT_HOLDER_PIDFD_EXIT_PARENT_JOINS_BOTH_MUTEXES_REACQUIRED_NO_RECORD_RELEASE'
         and second['case_sha256']==roles['case']['sha256']
         and second['permanent_mutex']==[27,4]
         and second['transaction_mutex']==[before['files']['transaction_mutex']['fd']['device'],before['files']['transaction_mutex']['fd']['inode']],
         'actual enclosing recovery mode reacquired both unchanged mutexes')
    for result in (first,second):
        need(result['quarantine_retained'] is True and result['transaction_complete'] is False
             and result['cleanup_replay_authorized'] is False and result['shared_release_authorized'] is False,
             'recovery keeps quarantine and incomplete transaction truthfully')
    need(second['journal_complete'] is False and second['cleanup_replayed'] is False
         and second['container_removal_authorized'] is False, 'no cleanup/container replay in recovery')
    need(second['protected_raw_records']==first['protected_raw_records']==[r['fd'] for r in roles['protected_raw_archives']]
         and case['protected_raw_fd_records']==roles['protected_raw_archives'],
         'all seven original protected raw/archive roles retained exactly')
    for row in roles['protected_raw_archives']:
        need(normalized_identity(row['fd'])==normalized_identity(before['files'][row['role']]['fd'])
             and checked_bytes(compact(row['raw_archive']))==saved_file(before['files'][row['role']]),
             'complete original FD identity and exact preserved raw archive bytes')
    encoded=base64.b64decode(second['post_effects_state_after_retirement_raw_base64'],validate=True)
    need(encoded==checked_bytes(compact(roles['post_effects_state_after_retirement']))
         and hashlib.sha256(encoded).hexdigest()==second['post_effects_state_after_retirement_sha256'],
         'whole actual after-state byte equality; no JSON reencoding')
    for name in ('holder','parent','outer'):
        need(after[name]==dict(pid=before[name]['pid'],absent=True), 'source-bound actual original process absence '+name)
    need(after['files']==before['files'] and after['selected_files']==before['selected_files']
         and after['finite_objects']==before['finite_objects'] and after['inventories']==before['inventories'],
         'complete before/after full identity and preservation equality')
    direct=read_native(second['direct_wait']);outer=read_native(second['outer_status'])
    need(second['direct_wait']['path']==case['old_direct_join']
         and second['outer_status']['path']==case['old_outer_status']==roles['original_outer_status']['path']
         and outer==checked(compact(roles['original_outer_status'])), 'exact whole original parent capture ancestry')
    need(direct['direct_child_joined'] is True and direct['returncode']==-9
         and direct['pid']==before['parent']['pid'] and str(direct['proc_start_ticks'])==before['parent']['starttime']
         and outer['direct_child_joined'] is True and outer['process_group_absent'] is True
         and outer['streams_closed'] is True and outer['returncode']==-9 and outer['status']=='FAIL_PRESERVED_STOPPED',
         'positive parent join and group retirement preserve original failure')
    tool=checked(compact(roles['original_tool_join']))
    need(tool['schema']=='mckernel.root-original-tool-wholejoin.v1' and tool['whole_join_observed'] is True
         and tool['session_id']==case['root_original_session_required']==second['root_original_session_required_whole_joined']
         and type(tool['tool_response']['exit_code']) is int and tool['transaction_complete'] is False,
         'root original tool positively whole joined; no transaction success inferred')
    return case

def project(report, physical_ref):
    need(report==checked(compact(physical_ref)), 'whole actual independent recovery report')
    report_conditions(report)
    roles=checked(PRODUCER_BINDINGS)
    need(set(roles)==set(SINGLE_AUTHORITY_ROLES)|{'recovery_mode_statuses','protected_raw_archives'}
         and all(report[k]==v for k,v in roles.items() if k!='protected_raw_archives')
         and report['protected_raw_archives']==[r['raw_archive'] for r in roles['protected_raw_archives']], 'all sixteen actual complete producer roles and canonical raw archive refs unchanged')
    need(report['implementation_ownership'] is False and report['retired'] is True
         and report['all_owned_groups_empty'] is True, 'independent physical retirement and empty groups')
    release=checked(compact(roles['cleanup_release']))
    need(roles['cleanup_execution_review']==CURRENT_EXECUTION_REF, 'complete original cleanup execution review authority')
    target=execution_join(checked(CURRENT_EXECUTION_REF),CURRENT_EXECUTION_REF,release)
    request_identity=release['observation']['request']
    need(request_identity['path']==roles['source_request']['path']
         and request_identity['sha256']==roles['source_request']['sha256']
         and request_identity['size']==roles['source_request']['bytes'], 'whole source request descriptor join')
    request=checked(request_identity,64<<20)
    before=checked(compact(roles['post_effects_state_before_retirement']))
    after=checked(compact(roles['post_effects_state_after_retirement']))
    for state,is_after in ((before,False),(after,True)):
        need(state['release_file_sha256']==roles['cleanup_release']['sha256'], 'external original cleanup release file hash')
        need(state_join(state,release,request,is_after)['target']==target, 'actual saved state target equality')
    need(set(report['protected_transaction_files'])==STATE_FILES and all(normalized_identity(report['protected_transaction_files'][k])==normalized_identity(before['files'][k]['fd']) for k in STATE_FILES), 'all seven independent report full original FD rows unchanged')
    recovery_join(report,roles,before,after)
    need(roles['record_release_evidence']==roles['post_effects_state_before_retirement'], 'record release proof uses genuine post-effects archive state')
    need(target['container_id']==report['container_id'] and target['owner_nonce']==report['owner_nonce']
         and report['boot_id']==before['boot_id'], 'whole current report original target identity')
    paths=[r['path'] for r in after['active_name_states']]
    for path in paths: need(not os.path.lexists(path), 'released active name currently absent')
    quarantine=after['files']['quarantine']['fd'];current=Path(quarantine['path']).lstat()
    need(current.st_dev==quarantine['device'] and current.st_ino==quarantine['inode']
         and current.st_size==quarantine['size'] and current.st_uid==quarantine['uid']
         and current.st_gid==quarantine['gid'] and stat.S_IMODE(current.st_mode)==int(quarantine['mode'],8),
         'current quarantine full stable identity remains retained')
    return dict(boot_id=report['boot_id'],filesystem_uuid='2a5768c8-718d-4914-bdc0-6b32c5a92a52',
                container_id=target['container_id'],owner_nonce=target['owner_nonce'],
                lease_path=paths[0],common_exclusion=paths[1],shared_heavy=paths[2])
