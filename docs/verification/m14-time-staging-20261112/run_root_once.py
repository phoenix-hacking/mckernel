# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Existing exact4fa named CLI once, then existing214d time DATAmanifest validation only.
# Excluded worker01a1c48d/turn01a1ce01 signal/frame/xstate task stays excluded.
import ast,datetime,hashlib,importlib.util,json,os,pathlib,re,signal,stat,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');HERE=pathlib.Path(__file__).resolve().parent;OUT=HERE/'execution-1'
REQUEST_SHA256='7284a666f702868c1f559ba805f6e1d85ca90c99d4bcad1682b3eb854844a274'
ROOT_ID='01a18bc3-e072-7810-9426-75101b0856c0'
INVOCATION='20261112T094452Z-12a4bea0'
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
    assert stat.S_ISREG(before.st_mode) and before.st_nlink==1
    assert str(path.resolve(strict=True))==item.get('resolved',str(path))
    assert (before.st_size,sha(path))==(item.get('bytes',item.get('size')),item['sha256'])
    for key,field in (('dev','st_dev'),('inode','st_ino'),('uid','st_uid'),('gid','st_gid')):
        if key in item:assert getattr(before,field)==item[key]
    if 'mode' in item:
        mode=item['mode']
        assert stat.S_IMODE(before.st_mode)==(int(mode,8) if isinstance(mode,str) else stat.S_IMODE(mode))
    assert identity(before)==identity(path.stat()),'input changed during pin'

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

def native_ref(path):
    p=pathlib.Path(path);st=p.stat()
    assert stat.S_ISREG(st.st_mode) and st.st_uid==1000 and st.st_gid==1000
    return dict(path=str(p.resolve()),size=st.st_size,sha256=sha(p),mode=st.st_mode)

def verify_grant(grant,review_ref,cap_ref):
    assert set(grant)==set(q['admission_fields'])
    assert grant['schema']=='mckernel.Root-current-HOST-admission.TIME4FA-staging.v1'
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
    prior=grant['prerequisite_current29ed_disposition']
    assert set(prior)==set(q['current29ed_prerequisite_fields'])
    for key in ('source_request_ref','private_admission_ref','original_terminal_tool_ref'):
        assert prior[key]==q['current29ed_expected'][key],key
    # Private dynamic admission is a reference identity only. Never open, copy,
    # print or publish its contents or a capability value from that file.
    for key in ('source_request_ref','original_terminal_tool_ref','actual_independent_Q_ref','actual_Root_retirement_ref'):
        read_ref(prior[key])
    for key in ('actual_HOST_scope_closed_and_independently_qualified','actual_current_2GiB_one_job_Root_retired','actual_exclusive_HOST_scope_released','all_other_native_source_runtime_UNKNOWNs_preserved'):
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
    assert review['decision']=='GO_ONE_EXISTING_EXACT_TIME4FA_NAMED_STAGING_ONLY'
    for key,value in {'request_sha256':REQUEST_SHA256,'run_root_once_sha256':sha(__file__),'capture_root_once_sha256':sha(HERE/'capture_root_once.py'),'capture_request_sha256':cap_ref['sha256'],'profile_sha256':q['profile']['sha256'],'stager_sha256':q['stager']['sha256'],'time_Q_sha256':q['actual_time_Q']['sha256'],'time_source_GO_sha256':q['actual_time_source_GO']['sha256']}.items():assert review[key]==value,key
    ap=pathlib.Path(sys.argv[3]);st=ap.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1 and st.st_size<=2**20
    grant_ref=dict(path=str(ap.resolve()),bytes=st.st_size,sha256=sys.argv[4]);grant=read_ref(grant_ref)
    verify_grant(grant,review_ref,cap_ref);inputs();pin(q['profile'])
    qualification=read_ref(q['actual_time_Q']);handoff=read_ref(q['actual_time_handoff'])
    assert qualification['decision']==q['expected_time_Q_decision']
    assert read_ref(q['actual_time_source_GO'])['decision']==q['expected_time_source_GO_decision']
    artifacts={row['path']:row for row in handoff['artifacts']}
    for key in ('payload','collector'):
        row=artifacts[q[key]['path']]
        assert row['sha256']==q[key]['sha256'] and row['bytes']==q[key]['bytes'] and row['mode']=='0o755'
    pin(q['account_consumer_ref']);owner_st=pathlib.Path(q['current_owner_private_ref']['path']).lstat()
    assert stat.S_ISREG(owner_st.st_mode) and owner_st.st_uid==1000 and stat.S_IMODE(owner_st.st_mode)==0o600
    account_api={'__name__':'mckernel_time4fa_staging_account_consumer','__file__':q['account_consumer_ref']['path']}
    exec(compile(pathlib.Path(q['account_consumer_ref']['path']).read_bytes(),q['account_consumer_ref']['path'],'exec'),account_api)
    expected_owner=read_ref(q['current_owner_private_ref']);assert expected_owner['thread_id']==ROOT_ID
    _,usage,credit,_=account_api['current_account_snapshot'](expected_owner);del credit
    state_guard();current=measure()
    assert current['MemAvailable_bytes']>=26*GIB and current['host_free_bytes']>=16*GIB+q['capture_headroom_bytes'] and current['scratch_free_bytes']>=12*GIB+q['capture_headroom_bytes']
    assert os.sched_getaffinity(0)=={0} and not OUT.exists()
    assert not pathlib.Path(q['stage_directory']).exists()
    ENV.update(q['host_environment'])
    os.umask(0o077);OUT.mkdir(mode=0o700);created_execution=True
    started=now();admitted=True
    ps=pathlib.Path('/proc/%d/stat'%os.getpid()).read_text().rsplit(') ',1)[1].split()
    save('PARENT-IDENTITY.json',dict(pid=os.getpid(),birth=ps[19],ppid=os.getppid(),parent_sha256=sha(__file__),external_full_Root_wait='REQUIRED'))
    save('ADMISSION.json',dict(at=now(),external_grant_reference=grant_ref,operation_review_reference=review_ref,actual_resources=current,accepted_account_source=usage['source_kind'],accepted_account_method=usage['source_event'],account_received_utc_ns=usage['receipt_received_utc_ns'],account_received_mono_ns=usage['receipt_received_mono_ns'],private_owner_credit_and29ed_capability_values_saved=False,external_charge_used_not_reissued=True))
    selected(q['qualified_outer_capture'],['call'])
    inputs();guard()
    save('STAGER-CUSTODY.json',dict(status='ONE_STAGER_CREATION_ATTEMPT_PENDING',argv=q['protected_stager_argv'],resource_charge_retained=True,original_Popen_handle_custody='EXISTING_E088_AND_NONESCAPING_KEEPER'))
    stdout=call('TIME-stage',q['protected_stager_argv'],timeout=300)
    assert len(clients)==1 and not pending_calls
    row=clients[0]
    assert row['exit']==0 and row['direct_wait_joined'] and row['streams_closed'] and row['receipt_persisted'] and row['lifecycle_UNKNOWN'] is False and row['resource_charge_retained'] is False
    assert row['primary_error'] is None and not row['secondary_errors']
    assert len(stdout)<=q['stager_stdout_limit_bytes'] and not (OUT/'TIME-stage.stderr').read_bytes()
    stage_result=json.loads(stdout)
    result_path=pathlib.Path(q['stage_directory'])/'RESULT.json'
    result_ref=dict(path=str(result_path),bytes=result_path.stat().st_size,sha256=sha(result_path))
    assert read_ref(result_ref)==stage_result, 'original named-stage stdout/result identity'
    assert stage_result['status']=='PASS_REAL_NAMED_ARTIFACT_BASE_OVERLAY_AND_MANIFEST_ONLY'
    assert stage_result['input_sha256']==q['named_inputs']['sha256']
    assert stage_result['materialized_base_files']==43 and stage_result['strict_collector_ELF_guard_ran_in_real_overlay'] is True
    assert stage_result['native_or_control_action'] is False
    manifest_path=pathlib.Path(q['native_manifest_output'])
    assert stage_result['native_manifest']==native_ref(manifest_path)
    pin(q['diagnostic_metadata_consumer'])
    spec=importlib.util.spec_from_file_location('existing_time_named_metadata_consumer',q['diagnostic_metadata_consumer']['path'])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    validated=module.load_manifest(str(manifest_path))
    assert validated['case_id']==q['expected_case_id'] and validated['payload']==q['expected_payload']
    assert validated['staging']['collector']['sha256']==q['collector']['sha256']
    assert validated['artifacts']['payload']['sha256']==q['payload']['sha256']
    assert validated['artifacts']['mckernel_image']['sha256']==q['baseline']['image']['sha256']
    assert validated['artifacts']['libc']['sha256']==q['baseline']['libc']['sha256'] and validated['artifacts']['loader']['sha256']==q['baseline']['loader']['sha256']
    assert {pathlib.Path(x['path']).name:x['sha256'] for x in validated['modules']}==q['expected_module_hashes']
    rows_path=pathlib.Path(q['stage_directory'])/'STAGED-REGULAR-SOURCE-ROWS.json'
    rows_ref=dict(path=str(rows_path),bytes=rows_path.stat().st_size,sha256=sha(rows_path))
    rows=read_ref(rows_ref)
    assert rows==stage_result['native_consumed_regular_files']
    assert all(row['target']==row['host'] and row['host'].startswith(q['stage_directory']+'/') and sha(row['host'])==row['content_sha256'] for row in rows)
    inputs();pin(q['profile'])
    for key in ('source_request_ref','original_terminal_tool_ref','actual_independent_Q_ref','actual_Root_retirement_ref'):
        read_ref(grant['prerequisite_current29ed_disposition'][key])
    assert not pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
    products=[native_ref(pathlib.Path(q['derived_archive'])),native_ref(manifest_path),native_ref(result_path),native_ref(rows_path)]
    save('STAGER-CUSTODY.json',dict(status='ONE_ORIGINAL_NAMED_STAGER_WAIT_STREAMS_AND_METADATA_JOIN_POSITIVE',clients=clients,products=products,resource_retirement='NONE_BY_PARENT',full_Root_and_independent_Q_required=True))
    save('RESULT.json',dict(status='PASS_ONE_EXISTING_EXACT_TIME4FA_NAMED_STAGING_AND_METADATA_ONLY',started_at=started,finished_at=now(),request_sha256=REQUEST_SHA256,review_sha256=sys.argv[2],admission_sha256=sys.argv[4],clients=clients,products=products,remaining_direct_children=[],all_input_artifact_bookends_positive=True,actual_named_stage_result=stage_result,existing_time_manifest_consumer_passed=True,named_branch_owned_FD_closure_basis='Pinned4fa bound-input branch ExitStack authenticates/rechecks sources; uses in-process9eb archive/gzip/overlay and214d metadata only, no legacy cpio/gzip subprocess route. Original namedstager wait0 closes processFDs.',firstrepeat_c964_a2f_f133_unchanged=True,compiler_passive_oracle_or_ABI_rerun=False,payload_or_collector_or_native_executed=False,current_named_case_or_globaldraft_enabled=False,automatic_resource_retirement=False,full_Root_and_independent_actual_Q_required=True,original_TIME_mapping_timepage_TSC_lifetime_acceptance=False))
    print(json.dumps(dict(status='PASS_ONE_EXISTING_EXACT_TIME4FA_NAMED_STAGING_AND_METADATA_ONLY',products=4,stager_invocations=1,native_executed=False,original_acceptance=False),sort_keys=True));return 0


if __name__=='__main__':
    assert sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
    q=json.loads((HERE/'REQUEST.FROZEN.json').read_bytes())
    selected(q['qualified_same_handle_keeper'],['keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody'])
    sys.exit(entry_once_with_original_custody())
