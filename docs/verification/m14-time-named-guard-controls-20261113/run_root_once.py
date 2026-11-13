# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# One exact twelve-row pure HOST fixture only; no native/flags/namespace acquisition.
# Rejected worker01a1c48d/turn01a1ce01 signal/frame/xstate task stays excluded.
import ast,datetime,hashlib,json,os,pathlib,re,signal,stat,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');HERE=pathlib.Path(__file__).resolve().parent;OUT=HERE/'execution-1'
REQUEST_SHA256='39bd98c87eaa63e1a3e430c681645b72538419e289f1fa4768b515d31cf158c6'
ROOT_ID='01a18bc3-e072-7810-9426-75101b0856c0'
INVOCATION='20261112T094452Z-12a4bea0'
SOURCE_REVIEW_INVOCATION='20261112T094452Z-12a4bea0'
CREDIT_RUN='7c6ef3604bfb4008a917bba8cfb6cfaa'
GIB=2**30
q=None;expected_owner=None;account_api=None;admitted=False;started=None;created_execution=False
clients=[];pending_calls={};keeper_capture_errors=[];OUTER_RETENTION_ERRORS=[];OUTER_ORIGINAL_WAITS=[]
MAIN_PRIMARY_RAW=None;MAIN_PRIMARY_TB=None
ENV=os.environ.copy()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def identity(st):
    return tuple(getattr(st,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns'))

def pin(item):
    path=pathlib.Path(item['path']);before=path.stat()
    assert path.is_file() and str(path.resolve())==item['resolved'], str(path)
    assert (before.st_size,sha(path))==(item['bytes'],item['sha256']),str(path)
    assert (before.st_dev,before.st_ino,before.st_uid,before.st_gid,oct(stat.S_IMODE(before.st_mode)))==(item['dev'],item['inode'],item['uid'],item['gid'],item['mode']),str(path)
    assert identity(before)==identity(path.stat()),'input changed during full-mode pin'

def read_ref(ref):
    path=pathlib.Path(ref['path']);st=path.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<=2**20
    with path.open('rb') as stream:raw=stream.read(2**20+1)
    assert len(raw)<=2**20 and len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
    assert identity(st)==identity(path.lstat()),'reference changed during read'
    return json.loads(raw)

def save(name,value):
    assert re.fullmatch('[A-Za-z0-9_.-]+',name)
    temporary=OUT/(name+'.pending')
    with temporary.open('x') as stream:
        json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(str(temporary),str(OUT/name))
    for path in OUT.iterdir():
        if path.is_file():
            fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
            try:os.fsync(fd)
            finally:os.close(fd)
    fd=os.open(str(OUT),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:os.fsync(fd)
    finally:os.close(fd)

def state_guard():
    assert expected_owner is not None, 'current owner not loaded'
    state = json.loads((ROOT/'.git/os-autopilot/state.json').read_bytes())
    assert state['phase']=='running' and state['stop_reason'] is None, 'current goal stopped'
    assert state['weekly_usage_error'] is None and state['weekly_confirmation_pending'] is False, 'usage hold'
    assert state.get('auth_mode')=='chatgpt' and state.get('credit_budget_error') is None, 'account hold'
    assert not any(state.get(k) for k in ('service_hold','auth_hold','billing_hold','policy_hold')), 'current service hold'
    for key in ('log_dir','thread_id','worker_pid','worker_start','server_pid','server_start','repo','guardian_run_id'):
        assert state.get(key)==expected_owner[key], 'current owner identity mismatch at '+key
    for kind in ('worker','server'):
        pid = expected_owner[kind+'_pid']
        fields = pathlib.Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()
        assert fields[0] in ('R','S','D','T','t','W','K','P','I'), 'terminal controller owner'
        assert fields[19]==expected_owner[kind+'_start'], 'controller birth mismatch'
    rate = state.get('last_rate_limits')
    assert isinstance(rate,dict) and rate.get('rateLimitReachedType') is None and not rate.get('spendControlReached'), 'usage/spend hold'
    credit = state['credit_budget']
    assert credit['id']==CREDIT_RUN, 'different finite credit run'
    amount = account_api['amount']
    assert amount(credit['budget'],positive=True)==amount(expected_owner['credit_budget'],positive=True), 'budget identity mismatch'
    assert amount(credit['remaining'],positive=True)>0 and amount(credit['spent'])<amount(credit['budget'],positive=True), 'budget exhausted'

def measure():
    available = next(int(line.split()[1])*1024 for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    host = os.statvfs(str(ROOT))
    scratch = os.statvfs('/home/holden/mckernel-work')
    return {'MemAvailable_bytes':available,'host_free_bytes':host.f_bavail*host.f_frsize,'scratch_free_bytes':scratch.f_bavail*scratch.f_frsize}

def inputs():
    pin(q['input_manifest'])
    manifest=json.loads(pathlib.Path(q['input_manifest']['path']).read_bytes())
    for item in manifest['files']:pin(item)
    for item in manifest['host_tools']:pin(item)
    return manifest

def guard():
    state_guard();current=measure()
    assert current['MemAvailable_bytes']>=22*GIB,'execution18+4GiB floor'
    assert current['host_free_bytes']>=16*GIB and current['scratch_free_bytes']>=12*GIB,'execution disk floor'

def selected(item,names):
    raw=pathlib.Path(item['path']).read_bytes()
    assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),item['path'],'exec'),globals())

def verify_grant(grant,review_ref,cap_ref):
    assert set(grant)==set(q['admission_fields'])
    assert grant['schema']=='mckernel.Root-current-HOST-admission.TIME-named-guard-controls.v1'
    assert grant['Root_thread_id']==ROOT_ID and grant['invocation']==INVOCATION and grant['same_Root_finite_credit_run_id']==CREDIT_RUN
    assert grant['request_sha256']==REQUEST_SHA256 and grant['capture_request_sha256']==cap_ref['sha256']
    assert grant['protected_parent_sha256']==sha(__file__) and grant['protected_outer_capture_sha256']==sha(HERE/'capture_root_once.py')
    assert grant['normal_profile_sha256']==q['profile']['sha256'] and grant['runtime_operation_review']==review_ref
    assert grant['source_manifest_sha256']==q['input_manifest']['sha256']
    assert grant['account_consumer_ref']==q['account_consumer_ref'] and grant['current_owner_private_ref']==q['current_owner_private_ref']
    assert grant['source_view_verified'] is True and grant['complete_owner_accounting'] is True and grant['native_and_historical_unknowns_preserved'] is True
    assert grant['no_exclusive_other_owner_scope'] is True
    assert grant['charge']==q['charge'] and grant['new_parent_capture_overhead_reserved_bytes']==0
    assert type(grant['current_HOST_jobs_before']) is int and 0<=grant['current_HOST_jobs_before']<3
    for key in ('other_current_HOST_payload_reserved_bytes','current_owned_controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes'):
        assert type(grant[key]) is int and grant[key]>=0,key
    assert grant['current_HOST_jobs_before']+1<=3
    assert grant['other_current_HOST_payload_reserved_bytes']+grant['current_owned_controller_worker_overhead_bytes']+q['charge']['planning_bytes']<=4*GIB
    assert grant['MemAvailable_bytes']>=26*GIB and grant['host_free_bytes']>=16*GIB+q['capture_headroom_bytes'] and grant['scratch_free_bytes']>=12*GIB+q['capture_headroom_bytes']
    assert 0<=(time.time_ns()-grant['issued_utc_ns'])/1e9<=60 and 0<=(time.monotonic_ns()-grant['issued_mono_ns'])/1e9<=60
    assert grant['host_boot_id']==pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    for key in ('current_owner_validation_ref','scoped_resource_evidence'):read_ref(grant[key])
    refs=grant['actual_source_service_permission_evidence_refs'];assert isinstance(refs,list) and refs
    for item in refs:read_ref(item)
    prior=grant['prerequisite_current_publisher_disposition']
    assert set(prior)==set(q['publisher_prerequisite_fields'])
    for key in ('producer_request_ref','original_terminal_tool_ref'):
        assert prior[key]==q['publisher_expected'][key],key
    for key in ('producer_request_ref','original_terminal_tool_ref','actual_independent_Q_ref','actual_Root_retirement_ref'):
        read_ref(prior[key])
    retired=read_ref(prior['actual_Root_retirement_ref'])
    assert retired['Root_thread_id']==ROOT_ID and retired['invocation']==INVOCATION and retired['same_Root_finite_credit_run_id']==CREDIT_RUN
    assert retired['retired_planning_bytes']==2*GIB and retired['retired_jobs']==1
    assert retired['independent_qualification']==prior['actual_independent_Q_ref']
    for key in ('actual_current_publisher_2GiB_one_job_Root_retired','actual_exclusive_HOST_scope_released','all_other_native_source_runtime_UNKNOWNs_preserved'):
        assert prior[key] is True,key


def main():
    global q,ENV,expected_owner,account_api,admitted,started,created_execution
    global MAIN_PRIMARY_RAW,MAIN_PRIMARY_TB
    assert len(sys.argv)==5 and sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
    q=json.loads((HERE/'REQUEST.FROZEN.json').read_bytes())
    rp=pathlib.Path(sys.argv[1]);review_ref=dict(path=str(rp.resolve()),bytes=rp.stat().st_size,sha256=sys.argv[2]);review=read_ref(review_ref)
    cp=HERE/'CAPTURE-REQUEST.json';cap_ref=dict(path=str(cp),bytes=cp.stat().st_size,sha256=sha(cp));cap=read_ref(cap_ref)
    assert cap['request']['sha256']==REQUEST_SHA256 and cap['parent']['sha256']==sha(__file__) and cap['outer_capture']['sha256']==sha(HERE/'capture_root_once.py')
    assert review['schema']==q['operation_review_schema'] and review['reviewer'].startswith(q['independent_reviewer_prefix'])
    assert review['decision']=='GO_ONE_EXACT_TWELVE_ROW_TIME_GUARD_PURE_HOST_CONTROL_RUN'
    for key,value in {'request_sha256':REQUEST_SHA256,'run_root_once_sha256':sha(__file__),'capture_root_once_sha256':sha(HERE/'capture_root_once.py'),'capture_request_sha256':cap_ref['sha256'],'profile_sha256':q['profile']['sha256'],'control_request_sha256':q['control_request']['sha256'],'control_fixture_sha256':q['control_fixture']['sha256'],'source_control_GO_sha256':q['source_control_GO']['sha256']}.items():assert review[key]==value,key
    ap=pathlib.Path(sys.argv[3]);st=ap.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1 and st.st_size<=2**20
    grant_ref=dict(path=str(ap.resolve()),bytes=st.st_size,sha256=sys.argv[4]);grant=read_ref(grant_ref)
    verify_grant(grant,review_ref,cap_ref);inputs();pin(q['profile'])
    source_GO=read_ref(q['source_control_GO'])
    assert source_GO['schema']=='mckernel.private-unselected-named-TIME-guard-independent-source-control-review.v1'
    assert source_GO['decision']=='GO_PRIVATE_TIME_PAIRED_SOURCE_TYPED_INNER_OWNER_AND_TWELVE_INERT_CONTROLS_ONLY_CONDITIONAL_PROTECTED_HOST_OPERATION'
    assert source_GO['Root_thread_id']==ROOT_ID and source_GO['invocation']==SOURCE_REVIEW_INVOCATION and source_GO['same_Root_finite_credit_run_id']==CREDIT_RUN
    control=read_ref(q['control_request'])
    assert control['fixture']['sha256']==q['control_fixture']['sha256'] and control['subject']['sha256']==q['subject']['sha256']
    assert control['paired_source_caller']['sha256']==q['paired_source_caller']['sha256'] and control['expected_stdout']['sha256']==q['expected_stdout']['sha256']
    assert control['expected_exit']==0 and control['expected_stderr_hex']=='' and len(control['expected_stdout_lines'])==12
    pin(q['account_consumer_ref']);owner_st=pathlib.Path(q['current_owner_private_ref']['path']).lstat()
    assert stat.S_ISREG(owner_st.st_mode) and owner_st.st_uid==1000 and stat.S_IMODE(owner_st.st_mode)==0o600
    account_api={'__name__':'mckernel_time_guard_controls_current_account_consumer','__file__':q['account_consumer_ref']['path']}
    exec(compile(pathlib.Path(q['account_consumer_ref']['path']).read_bytes(),q['account_consumer_ref']['path'],'exec'),account_api)
    expected_owner=read_ref(q['current_owner_private_ref']);assert expected_owner['thread_id']==ROOT_ID
    _,usage,credit,_=account_api['current_account_snapshot'](expected_owner);del credit
    state_guard();current=measure()
    assert current['MemAvailable_bytes']>=26*GIB and current['host_free_bytes']>=16*GIB+q['capture_headroom_bytes'] and current['scratch_free_bytes']>=12*GIB+q['capture_headroom_bytes']
    assert os.getuid()==os.geteuid()==1000 and os.getgid()==os.getegid()==1000 and os.sched_getaffinity(0)=={7}
    assert not OUT.exists();ENV.update(q['host_environment']);os.umask(0o077);OUT.mkdir(mode=0o700);created_execution=True
    started=now();admitted=True
    ps=pathlib.Path('/proc/%d/stat'%os.getpid()).read_text().rsplit(') ',1)[1].split()
    save('PARENT-IDENTITY.json',dict(pid=os.getpid(),birth=ps[19],ppid=os.getppid(),parent_sha256=sha(__file__),external_full_Root_wait='REQUIRED'))
    save('ADMISSION.json',dict(at=now(),external_grant_reference=grant_ref,operation_review_reference=review_ref,source_control_GO=q['source_control_GO'],actual_resources=current,accepted_account_source=usage['source_kind'],accepted_account_method=usage['source_event'],account_received_utc_ns=usage['receipt_received_utc_ns'],account_received_mono_ns=usage['receipt_received_mono_ns'],private_owner_credit_and_publisher_caps_values_saved=False,external_charge_used_not_reissued=True))
    selected(q['qualified_outer_capture'],['call'])
    inputs();guard()
    stdout=call('TIME-named-guard-controls',q['controls_argv'],timeout=120)
    assert len(clients)==1 and not pending_calls
    row=clients[0]
    assert row['exit']==0 and row['direct_wait_joined'] and row['streams_closed'] and row['receipt_persisted'] and row['lifecycle_UNKNOWN'] is False and row['resource_charge_retained'] is False
    assert row['primary_error'] is None and not row['secondary_errors']
    expected=pathlib.Path(q['expected_stdout']['path']).read_bytes()
    assert stdout==expected and len(stdout)==455 and hashlib.sha256(stdout).hexdigest()==q['expected_stdout']['sha256']
    assert not (OUT/'TIME-named-guard-controls.stderr').read_bytes()
    inputs();pin(q['profile']);read_ref(q['source_control_GO'])
    for key in ('producer_request_ref','original_terminal_tool_ref','actual_independent_Q_ref','actual_Root_retirement_ref'):
        read_ref(grant['prerequisite_current_publisher_disposition'][key])
    remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not remaining
    save('RESULT.json',dict(status='PASS_EXACT_TWELVE_PURE_TIME_NAMED_GUARD_CONTROLS',started_at=started,finished_at=now(),request_sha256=REQUEST_SHA256,review_sha256=sys.argv[2],admission_sha256=sys.argv[4],source_control_GO=q['source_control_GO'],control_request=q['control_request'],control_fixture=q['control_fixture'],subject=q['subject'],paired_source_caller=q['paired_source_caller'],clients=clients,rows=control['expected_stdout_lines'],actual_stdout_bytes=len(stdout),actual_stdout_sha256=hashlib.sha256(stdout).hexdigest(),actual_stderr_bytes=0,remaining_direct_children=remaining,input_source_metadata_bookends_positive=True,pure_guard_scope_only=True,no_RootLease_native_acquisition_source_transition_completion_or_retirement_asserted=True,no_Docker_compiler_ABI_staging_or_oracle_rerun=True,no_installed_or_current_repeat_or_TIME_case_selection=True,no_native_operation_or_source_namespace_signal_flags_action=True,no_automatic_resource_retirement=True,full_original_Root_and_independent_actual_Q_required=True,original_TIME_runtime_restoration_or_acceptance=False))
    print(stdout.decode(),end='');return 0

if __name__=='__main__':
    assert sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
    q=json.loads((HERE/'REQUEST.FROZEN.json').read_bytes())
    selected(q['qualified_same_handle_keeper'],['keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody'])
    sys.exit(entry_once_with_original_custody())
