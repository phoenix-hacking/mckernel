# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# CURRENT64017 metadata reader only; no original disposition/failed-row replay.
# Rejected worker01a1c48d/turn01a1ce01 signal/frame/xstate task remains excluded.
import ast,datetime,hashlib,json,os,pathlib,re,signal,stat,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel')
HERE=pathlib.Path(__file__).resolve().parent
OUT=HERE/'execution-1'
ROOT_ID='01a18bc3-e072-7810-9426-75101b0856c0'
INVOCATION='20261112T094452Z-12a4bea0'
CREDIT_RUN='7c6ef3604bfb4008a917bba8cfb6cfaa'
REQUEST_SHA256='fea247de40e806c555849a78686750a4525a362e61cf5535d02cb68bd4906bee'
GIB=1024**3
q=None;ENV=os.environ.copy();expected_owner=None;account_api=None
clients=[];pending_calls={};keeper_capture_errors=[]
OUTER_RETENTION_ERRORS=[];OUTER_ORIGINAL_WAITS=[]
admitted=False;started=None;created_execution=False
MAIN_PRIMARY_RAW=None;MAIN_PRIMARY_TB=None

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
    assert grant['schema']=='mckernel.Root-current-HOST-admission.current64017-readonly.v1'
    assert grant['Root_thread_id']==ROOT_ID and grant['invocation']==INVOCATION and grant['same_Root_finite_credit_run_id']==CREDIT_RUN
    assert grant['request_sha256']==REQUEST_SHA256 and grant['capture_request_sha256']==cap_ref['sha256']
    assert grant['protected_parent_sha256']==sha(HERE/'run_root_once.py') and grant['protected_outer_capture_sha256']==sha(HERE/'capture_root_once.py')
    assert grant['normal_profile_sha256']==q['profile']['sha256'] and grant['runtime_operation_review']==review_ref
    assert grant['source_manifest_sha256']==q['input_manifest']['sha256']
    assert grant['account_consumer_ref']==q['account_consumer_ref'] and grant['current_owner_private_ref']==q['current_owner_private_ref']
    assert grant['source_view_verified'] is True and grant['complete_owner_accounting'] is True and grant['native_and_historical_unknowns_preserved'] is True
    # This means no OTHER exclusive owner forbids this exact read-only reader;
    # the explicitly accounted original64017 target remains held and untouched.
    assert grant['no_exclusive_other_owner_scope'] is True
    assert grant['charge']==q['charge'] and grant['new_parent_capture_overhead_reserved_bytes']==0
    assert type(grant['current_HOST_jobs_before']) is int and 1<=grant['current_HOST_jobs_before']<3
    for key in ('other_current_HOST_payload_reserved_bytes','current_owned_controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes'):
        assert type(grant[key]) is int and grant[key]>=0,key
    assert grant['other_current_HOST_payload_reserved_bytes']>=1610612736
    assert grant['current_HOST_jobs_before']+1<=3
    assert grant['other_current_HOST_payload_reserved_bytes']+grant['current_owned_controller_worker_overhead_bytes']+q['charge']['planning_bytes']<=4*GIB
    assert grant['MemAvailable_bytes']>=26*GIB and grant['host_free_bytes']>=16*GIB+q['capture_headroom_bytes'] and grant['scratch_free_bytes']>=12*GIB+q['capture_headroom_bytes']
    assert 0<=(time.time_ns()-grant['issued_utc_ns'])/1e9<=60 and 0<=(time.monotonic_ns()-grant['issued_mono_ns'])/1e9<=60
    assert grant['host_boot_id']==pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    for key in ('current_owner_validation_ref','scoped_resource_evidence'):read_ref(grant[key])
    refs=grant['actual_source_service_permission_evidence_refs'];assert isinstance(refs,list) and refs
    for item in refs:read_ref(item)
    assert grant['original64017_scope_preserved']==q['original64017_scope_preserved']

def review_binding(review,cap_ref):
    assert review['schema']==q['operation_review_schema'] and review['reviewer'].startswith(q['independent_reviewer_prefix'])
    assert review['decision']==q['operation_review_decision']
    wanted=dict(request_sha256=REQUEST_SHA256,run_root_once_sha256=sha(HERE/'run_root_once.py'),capture_root_once_sha256=sha(HERE/'capture_root_once.py'),capture_request_sha256=cap_ref['sha256'],collector_sha256=q['collector']['sha256'],profile_sha256=q['profile']['sha256'],input_manifest_sha256=q['input_manifest']['sha256'],source_path_bindings_sha256=q['source_path_bindings']['sha256'])
    for key,value in wanted.items():assert review[key]==value,key

def main():
    global q,ENV,expected_owner,account_api,admitted,started,created_execution
    global MAIN_PRIMARY_RAW,MAIN_PRIMARY_TB
    assert len(sys.argv)==5 and sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
    q=json.loads((HERE/'REQUEST.FROZEN.json').read_bytes())
    rp=pathlib.Path(sys.argv[1]);review_ref=dict(path=str(rp.resolve()),bytes=rp.stat().st_size,sha256=sys.argv[2]);review=read_ref(review_ref)
    cp=HERE/'CAPTURE-REQUEST.json';cap_ref=dict(path=str(cp),bytes=cp.stat().st_size,sha256=sha(cp));cap=read_ref(cap_ref)
    assert cap['request']['sha256']==REQUEST_SHA256 and cap['parent']['sha256']==sha(__file__) and cap['outer_capture']['sha256']==sha(HERE/'capture_root_once.py')
    assert cap['collector']['sha256']==q['collector']['sha256']
    review_binding(review,cap_ref)
    ap=pathlib.Path(sys.argv[3]);st=ap.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1 and st.st_size<=2**20
    grant_ref=dict(path=str(ap.resolve()),bytes=st.st_size,sha256=sys.argv[4]);grant=read_ref(grant_ref)
    verify_grant(grant,review_ref,cap_ref);inputs();pin(q['profile'])
    pin(q['account_consumer_ref']);owner_st=pathlib.Path(q['current_owner_private_ref']['path']).lstat()
    assert stat.S_ISREG(owner_st.st_mode) and owner_st.st_uid==1000 and stat.S_IMODE(owner_st.st_mode)==0o600
    account_api={'__name__':'mckernel_current64017_readonly_current_account_consumer','__file__':q['account_consumer_ref']['path']}
    exec(compile(pathlib.Path(q['account_consumer_ref']['path']).read_bytes(),q['account_consumer_ref']['path'],'exec'),account_api)
    expected_owner=read_ref(q['current_owner_private_ref']);assert expected_owner['thread_id']==ROOT_ID
    _,usage,credit,_=account_api['current_account_snapshot'](expected_owner);del credit
    state_guard();current=measure()
    assert current['MemAvailable_bytes']>=26*GIB and current['host_free_bytes']>=16*GIB+q['capture_headroom_bytes'] and current['scratch_free_bytes']>=12*GIB+q['capture_headroom_bytes']
    assert os.getuid()==os.geteuid()==1000 and os.getgid()==os.getegid()==1000 and os.sched_getaffinity(0)=={0}
    assert not OUT.exists() and not (HERE/q['private_output_directory_name']).exists()
    ENV.update(q['host_environment']);ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
    os.umask(0o077);OUT.mkdir(mode=0o700);created_execution=True;started=now();admitted=True
    ps=pathlib.Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split()
    save('PARENT-IDENTITY.json',dict(pid=os.getpid(),birth=ps[19],ppid=os.getppid(),parent_sha256=sha(__file__),external_full_Root_wait='REQUIRED'))
    save('ADMISSION.json',dict(at=now(),external_grant_reference=grant_ref,operation_review_reference=review_ref,actual_resources=current,accepted_account_source=usage['source_kind'],accepted_account_method=usage['source_event'],account_received_utc_ns=usage['receipt_received_utc_ns'],account_received_mono_ns=usage['receipt_received_mono_ns'],private_owner_credit_originalcaps_and_account_values_saved=False,external_charge_used_not_reissued=True,original_scope_retained=q['original64017_scope_preserved']))
    selected(q['qualified_outer_capture'],['call'])
    inputs();guard()
    argv=q['actor_argv_prefix']+[str(HERE/'REQUEST.FROZEN.json'),REQUEST_SHA256,str(rp),sys.argv[2],sys.argv[3],sys.argv[4]]
    save('ACTUAL-READER-ARGV.json',dict(argv=argv,expected_exit=0,current_snapshot_not_failure_instant=True))
    stdout=call('current64017-UID0-readonly-reader',argv,timeout=120)
    assert len(clients)==1 and not pending_calls
    row=clients[0]
    assert row['exit']==0 and row['direct_wait_joined'] and row['streams_closed'] and row['receipt_persisted'] and row['lifecycle_UNKNOWN'] is False and row['resource_charge_retained'] is False
    assert row['primary_error'] is None and not row['secondary_errors']
    assert not (OUT/'current64017-UID0-readonly-reader.stderr').read_bytes()
    summary=json.loads(stdout)
    assert summary['status']==q['expected_public_status'] and summary['own_input_and_output_FDs_all_closed'] is True and summary['own_close_errors']==0 and summary['remaining_collector_direct_children']==[]
    assert summary['original64017_1_5GiB_native12_runtime_source_allUNKNOWNs_retained'] is True and summary['no_parser_replay_no_failedinstant_reconstruction_no_original_release'] is True
    record=summary['raw_private_record']
    assert record['path']==str(HERE/q['private_output_directory_name']/q['private_output_file_name']) and 0<record['bytes']<=q['bounds']['private_DATA_bytes_max']
    assert record['identity']['uid']==record['identity']['gid']==0 and record['identity']['mode']==0o600 and record['identity']['nlink']==1 and record['Root_uid0_mode0600_directory0700'] is True
    inputs();pin(q['profile'])
    remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not remaining
    save('RESULT.json',dict(status='PASS_CURRENT64017_READONLY_READER_OWN_CLOSURE_ONLY',started_at=started,finished_at=now(),request_sha256=REQUEST_SHA256,review_sha256=sys.argv[2],admission_sha256=sys.argv[4],clients=clients,reader_argv=argv,reader_summary=summary,actual_stdout_bytes=len(stdout),actual_stdout_sha256=hashlib.sha256(stdout).hexdigest(),actual_stderr_bytes=0,remaining_direct_children=remaining,input_source_metadata_bookends_positive=True,private_Root_DATA_contents_not_opened_by_parent=True,original_scope_retained=q['original64017_scope_preserved'],no_automatic_resource_retirement=True,full_original_Root_and_independent_actual_Q_required=True,original_native_runtime_or_restoration_acceptance=False))
    print(stdout.decode(),end='');return 0

if __name__=='__main__':
    assert sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
    q=json.loads((HERE/'REQUEST.FROZEN.json').read_bytes())
    selected(q['qualified_same_handle_keeper'],['keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody'])
    sys.exit(entry_once_with_original_custody())
