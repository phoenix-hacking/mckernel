# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# One missing generic Linux-init HOSTstaticcompile plus three unstartedpassivechecks.
# No payload/collector main, kernel build, staging, native or case-selection action.
# Excluded worker01a1c48d/turn01a1ce01 signal/frame/xstate task stays excluded.
import ast,datetime,hashlib,importlib.util,json,os,pathlib,re,shlex,shutil,signal,stat,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');HERE=pathlib.Path(__file__).resolve().parent;OUT=HERE/'execution-1'
REQUEST_SHA256='c6ee4db6d7b6a30cc9970eae7ed54b6c855e9118f984e248659071163a863140'
ROOT_ID='01a18bc3-e072-7810-9426-75101b0856c0'
INVOCATION='invocation20261112T094452Z-12a4bea0'
CREDIT_RUN='7c6ef3604bfb4008a917bba8cfb6cfaa'
GIB=2**30
attempts=[];containers=[];owner=None;phase=None;current_argv=None
q=None;expected_owner=None;account_api=None;admitted=False;started=None;created_execution=False
MAIN_PRIMARY_RAW=None;MAIN_PRIMARY_TB=None
OWNER_CALL_PENDING=None;OWNER_CALL_COMPLETED=[];OWNER_CUSTODY_ERRORS=[]
ENV=os.environ.copy()


def current_Owner_call_closed(context,result):
    try:
        rows=context['owner'].records
        if len(rows)!=context['record_index']+1:return False
        row=rows[context['record_index']]
        return (row['label']==context['label'] and type(row['leader']) is int and row['leader']>0 and
            str(row['leader_birth']).isdigit() and int(row['leader_birth'])>0 and
            row['leader_parent_joined'] is True and row['whole_descendants_joined'] is True and
            row['streams_closed'] is True and type(row['status']) is int and
            row['status']==result.returncode and row['remaining_direct_children']==[] and
            row['error'] is None and row['timed_out'] is False and
            row['leader_group_signalled'] is False and row['adopted_reaps']==[] and row['adopted_kills']==[])
    except BaseException:
        return False

def retain_current_Owner_context_nonescaping():
    # Only the SAME possibly-created call and its original raw TB/context.
    # No new Popen, signal, kill, numeric wait, replacement, retry or report gate.
    while True:
        try:
            if OWNER_CALL_PENDING is None:return
            try:signal.pause()
            except BaseException as error:
                try:OWNER_CUSTODY_ERRORS.append((error,BaseException.__dict__['__traceback__'].__get__(error,type(error))))
                except BaseException:pass
        except BaseException:
            pass

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

def cli(label,argv,timeout=30):
    global current_argv,OWNER_CALL_PENDING
    guard();current_argv=argv
    attempt=dict(index=len(attempts),label=label,phase=phase,argv=argv,at=now(),
        creation_attempted=True,lifecycle_UNKNOWN=True,resource_charge_retained=True)
    attempts.append(attempt);save('ATTEMPTS.json',attempts)
    context=dict(owner=owner,label=label,argv=argv,record_index=len(owner.records),
        original_raw_error=None,original_raw_tb=None,returned_result=None,positive_closed_record=None)
    OWNER_CALL_PENDING=context
    try:
        result=owner.run(argv,env=ENV,cwd=str(ROOT),timeout=timeout,label=label)
    except BaseException as error:
        context['original_raw_error']=error
        context['original_raw_tb']=BaseException.__dict__['__traceback__'].__get__(error,type(error))
        raise
    context['returned_result']=result
    assert current_Owner_call_closed(context,result),'current original Owner closure UNKNOWN'
    context['positive_closed_record']=owner.records[context['record_index']]
    OWNER_CALL_COMPLETED.append(context)
    OWNER_CALL_PENDING=None
    record=owner.records[-1]
    assert int(record['leader'])>0 and int(record['leader_birth'])>0
    assert record['leader_parent_joined'] and record['whole_descendants_joined'] and record['streams_closed']
    assert not record['timed_out'] and not record['leader_group_signalled']
    assert not record['adopted_reaps'] and not record['adopted_kills'] and not record['remaining_direct_children']
    assert record['error'] is None and result.returncode==record['status']
    assert len(result.stdout)<=q['client_stdout_limit_bytes'] and len(result.stderr)<=q['client_stderr_limit_bytes']
    attempt.update(exit=result.returncode,ownership=record,lifecycle_UNKNOWN=False,
        direct_client_closed_only_full_container_and_Root_closure_still_required=True)
    save('ATTEMPTS.json',attempts)
    assert result.returncode==0,(label,result.returncode)
    return result

def inspect(label,cid):
    result=cli(label,q['docker']+['inspect',cid]);records=json.loads(result.stdout)
    assert len(records)==1 and records[0]['Id']==cid
    save(label+'.json',records[0]);return records[0]

def profile(info,item,cid,lifecycle):
    assert info['Id']==cid and info['Name']=='/'+item['name'] and info['Image']==q['image']
    expected_config=dict(item['expected_config']);expected_config['Hostname']=cid[:12]
    actual_config=dict(info['Config'])
    for config in (actual_config,expected_config):
        env=config['Env'];values=dict(value.split('=',1) for value in env)
        assert len(values)==len(env),'duplicate environment key'
        config['Env']=values
    assert actual_config==expected_config,'complete Config mismatch'
    actual_host=dict(info['HostConfig']);expected_host=dict(item['expected_host_config'])
    for host in (actual_host,expected_host):
        host['Mounts']=sorted(host['Mounts'],key=lambda m:(m['Source'],m['Target']))
    assert actual_host==expected_host,'complete HostConfig mismatch'
    for key,value in q['expected_profile_fields_by_lifecycle'][lifecycle].items():assert info[key]==value,key
    rows=[[m['Type'],m['Source'],m['Destination'],not m['RW'],m['Propagation']] for m in info['Mounts']]
    assert sorted(rows)==sorted(item['expected_mounts']),'exact five-field mount rows mismatch'

def guard():
    state_guard();current=measure()
    assert current['MemAvailable_bytes']>=22*GIB,'execution18+4GiB floor'
    assert current['host_free_bytes']>=16*GIB and current['scratch_free_bytes']>=12*GIB,'execution disk floor'

def verify_grant(grant,review_ref,cap_ref):
    assert set(grant)==set(q['admission_fields'])
    assert grant['schema']=='mckernel.Root-current-HOST-admission.TLS-missing-static-and-passive.v1'
    assert grant['Root_thread_id']==ROOT_ID and grant['invocation']==INVOCATION and grant['same_Root_finite_credit_run_id']==CREDIT_RUN
    assert grant['request_sha256']==REQUEST_SHA256 and grant['capture_request_sha256']==cap_ref['sha256']
    assert grant['protected_parent_sha256']==sha(__file__) and grant['protected_outer_capture_sha256']==sha(HERE/'capture_root_once.py')
    assert grant['normal_profile_sha256']==q['profile']['sha256'] and grant['runtime_operation_review']==review_ref
    assert grant['source_manifest_sha256']==q['input_manifest']['sha256']
    assert grant['account_consumer_ref']==q['account_consumer_ref'] and grant['current_owner_private_ref']==q['current_owner_private_ref']
    assert grant['source_view_verified'] is True and grant['complete_owner_accounting'] is True and grant['native_and_historical_unknowns_preserved'] is True
    assert grant['charge']==q['charge'] and grant['new_parent_capture_overhead_reserved_bytes']==0
    assert grant['no_exclusive_other_owner_scope'] is True,'another exclusive owner scope is still held'
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
    prior=grant['prerequisite_terminal_cleanup']
    assert set(prior)==set(q['cleanup_prerequisite_fields'])
    assert prior['CID']==q['cleanup_contract']['CID'] and prior['cleanup_request_sha256']==q['cleanup_contract']['request']['sha256']
    assert prior['actual_cleanup_full_Root_and_independent_Q_verified'] is True and prior['old_TLS_and_new_cleanup_scoped_Root_retired'] is True and prior['native12_source_all_other_UNKNOWN_unchanged'] is True
    for key in ('actual_result_ref','actual_full_Root_ref','independent_Q_ref','scoped_Root_retirement_ref'):pin(prior[key])
    assert prior['failed_no_Popen_768MiB_scoped_Root_retired'] is True
    for key in ('failed_no_Popen_scope_independent_Q_ref','failed_no_Popen_scope_Root_retirement_ref'):pin(prior[key])
    assert prior['actual_result_ref']['path']==q['cleanup_contract']['actual_RESULT_path']
    result=json.loads(pathlib.Path(prior['actual_result_ref']['path']).read_bytes())
    assert result['status']=='PASS_EXACT_TLS_5645_TERMINAL_CONTAINER_CLEANUP_ONLY' and result['request_sha256']==prior['cleanup_request_sha256'] and result['CID']==prior['CID']
    assert len(result['containers'])==1 and result['containers'][0]['removed'] is True and result['containers'][0]['lifecycle_UNKNOWN'] is False
    assert len(result['client_ownership'])==3 and not result['remaining_direct_children']
    for row in result['client_ownership']:
        assert row['status']==0 and row['leader_parent_joined'] and row['whole_descendants_joined'] and row['streams_closed'] and row['error'] is None
        assert not row['timed_out'] and not row['leader_group_signalled'] and not row['adopted_kills'] and not row['adopted_reaps'] and not row['remaining_direct_children']
    pin(q['cleanup_contract']['request'])

def full_pin(path):
    p=pathlib.Path(path);st=p.stat()
    assert stat.S_ISREG(st.st_mode) and st.st_uid==1000 and st.st_gid==1000 and st.st_size>0
    return dict(path=str(p),resolved=str(p.resolve()),bytes=st.st_size,sha256=sha(p),dev=st.st_dev,inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=oct(stat.S_IMODE(st.st_mode)))

def host_selected_inputs():
    selected=[];transient=[]
    dep=pathlib.Path(q['HOST_output'])/'collector.d'
    logical=dep.read_text().replace('\\\n',' ');target,sep,rest=logical.partition(':')
    assert sep and target.strip()==str(pathlib.Path(q['HOST_output'])/'collector')
    for name in dict.fromkeys(shlex.split(rest)):
        p=pathlib.Path(name);assert p.is_absolute() and p.is_file()
        selected.append(dict(path=str(p),resolved=str(p.resolve()),bytes=p.stat().st_size,sha256=sha(p),kind='actual-default-collector-depfile'))
    text=(pathlib.Path(q['HOST_output'])/'collector.link.map').read_text()
    loads=list(dict.fromkeys(re.findall(r'^LOAD (/.+)$',text,re.M)))
    assert loads and any(pathlib.Path(s).name=='libc.a' for s in loads)
    for name in loads:
        if (pathlib.Path(name).parent==pathlib.Path(q['HOST_output'])/'tmp' and
                re.fullmatch(r'cc[A-Za-z0-9]+\.o',pathlib.Path(name).name)):
            transient.append(dict(path=name,kind='actual-temporary-translation-output',
                persistent_provider=False,retained_bytes_and_hash='UNPROVED_IF_ALREADY_REMOVED'))
            continue
        p=pathlib.Path(name);assert p.is_file()
        selected.append(dict(path=str(p),resolved=str(p.resolve()),bytes=p.stat().st_size,sha256=sha(p),kind='actual-default-collector-link-map'))
    actual_libc=[r for r in selected if pathlib.Path(r['path']).name=='libc.a']
    assert actual_libc and all(r['sha256']=='f9831edeccd3a87eb3fbba795f92bfa83409b3951f05ec40ca5df432b8699127' for r in actual_libc)
    manifest=json.loads(pathlib.Path(q['input_manifest']['path']).read_bytes())
    pinned={item['resolved']:item for item in manifest['files']}
    for item in selected:
        assert item['resolved'] in pinned,'actual selected HOST input lacks a before/after source pin'
        assert (item['bytes'],item['sha256'])==(pinned[item['resolved']]['bytes'],pinned[item['resolved']]['sha256'])
    return selected,transient

def main():
    global q,owner,ENV,expected_owner,account_api,admitted,started,created_execution,phase
    assert len(sys.argv)==5 and sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
    q=json.loads((HERE/'REQUEST.FROZEN.json').read_bytes())
    rp=pathlib.Path(sys.argv[1]);review_ref=dict(path=str(rp.resolve()),bytes=rp.stat().st_size,sha256=sys.argv[2]);review=read_ref(review_ref)
    cp=HERE/'CAPTURE-REQUEST.json';cap_ref=dict(path=str(cp),bytes=cp.stat().st_size,sha256=sha(cp));cap=read_ref(cap_ref)
    assert cap['request']['sha256']==REQUEST_SHA256 and cap['parent']['sha256']==sha(__file__) and cap['outer_capture']['sha256']==sha(HERE/'capture_root_once.py')
    assert review['schema']==q['operation_review_schema'] and review['reviewer'].startswith(q['independent_reviewer_prefix'])
    assert review['decision']=='GO_TLS_MISSING_STATIC_HOST_COLLECTOR_AND_THREE_PASSIVE_STEPS_ONLY'
    for key,value in {'request_sha256':REQUEST_SHA256,'run_root_once_sha256':sha(__file__),'capture_root_once_sha256':sha(HERE/'capture_root_once.py'),'capture_request_sha256':cap_ref['sha256'],'passive_batch_sha256':q['passive_batch']['sha256'],'passive_plan_sha256':q['passive_plan']['sha256'],'profile_sha256':q['profile']['sha256'],'provider_contract_sha256':q['provider_contract']['sha256']}.items():assert review[key]==value,key
    ap=pathlib.Path(sys.argv[3]);st=ap.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1 and st.st_size<=2**20
    grant_ref=dict(path=str(ap.resolve()),bytes=st.st_size,sha256=sys.argv[4]);grant=read_ref(grant_ref)
    verify_grant(grant,review_ref,cap_ref);inputs();pin(q['profile']);pin(q['provider_contract'])
    pin(q['account_consumer_ref']);private_st=pathlib.Path(q['current_owner_private_ref']['path']).lstat()
    assert stat.S_ISREG(private_st.st_mode) and private_st.st_uid==1000 and stat.S_IMODE(private_st.st_mode)==0o600
    account_api={'__name__':'mckernel_tls_residual_current_account_consumer','__file__':q['account_consumer_ref']['path']}
    exec(compile(pathlib.Path(q['account_consumer_ref']['path']).read_bytes(),q['account_consumer_ref']['path'],'exec'),account_api)
    expected_owner=read_ref(q['current_owner_private_ref']);assert expected_owner['thread_id']==ROOT_ID
    _,usage,credit,_=account_api['current_account_snapshot'](expected_owner);del credit
    state_guard();current=measure()
    assert current['MemAvailable_bytes']>=26*GIB and current['host_free_bytes']>=16*GIB+q['capture_headroom_bytes'] and current['scratch_free_bytes']>=12*GIB+q['capture_headroom_bytes']
    assert os.sched_getaffinity(0)=={0} and not OUT.exists()
    ENV.update(q['host_environment']);ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
    os.umask(0o077);OUT.mkdir(mode=0o700);created_execution=True
    pathlib.Path(q['HOST_output']).mkdir(mode=0o700);(pathlib.Path(q['HOST_output'])/'tmp').mkdir(mode=0o700)
    pathlib.Path(q['passive_output']).mkdir(mode=0o700)
    started=now();admitted=True
    ps=pathlib.Path('/proc/%d/stat'%os.getpid()).read_text().rsplit(') ',1)[1].split()
    save('PARENT-IDENTITY.json',dict(pid=os.getpid(),birth=ps[19],ppid=os.getppid(),parent_sha256=sha(__file__),external_full_Root_wait='REQUIRED'))
    save('ADMISSION.json',dict(at=now(),external_grant_reference=grant_ref,operation_review_reference=review_ref,actual_resources=current,accepted_account_source=usage['source_kind'],accepted_account_method=usage['source_event'],account_received_utc_ns=usage['receipt_received_utc_ns'],account_received_mono_ns=usage['receipt_received_mono_ns'],private_owner_and_credit_values_saved=False,external_charge_used_not_reissued=True))
    spec=importlib.util.spec_from_file_location('qualified_tls_residual_owner',q['ownership_helper']['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);owner=module.Owner(OUT)
    phase='HOST-default-static-collector'
    result=cli('generic-collector-HOST-static-compile',q['HOST_compiler_argv'],timeout=120)
    artifact=full_pin(pathlib.Path(q['HOST_output'])/'collector')
    selected,transient=host_selected_inputs();inputs()
    produced=dict(artifact=artifact,source_sha256=q['collector_source']['sha256'],compiler_argv=q['HOST_compiler_argv'],compiler_exit=0,ownership=owner.records[-1],selected_actual_inputs=selected,actual_transient_translation_outputs=transient,payload_or_collector_executed=False)
    host_record=pathlib.Path(q['HOST_output'])/'COLLECTOR.ACTUAL.json'
    with host_record.open('x') as stream:
        json.dump(produced,stream,indent=2,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    produced_pin=full_pin(host_record);save('HOST-COLLECTOR-OUTPUT.json',produced)
    phase='passive-only'
    running=cli('running-preflight',q['docker']+['ps','--no-trunc','-q']);assert not running.stdout.strip()
    names=cli('names-preflight',q['docker']+['ps','-a','--format','{{.Names}}']).stdout.decode().splitlines();item=q['phase'];assert item['name'] not in names
    inputs();pin(artifact);pin(produced_pin);guard()
    custody=dict(phase=phase,name=item['name'],owner_label=q['owner_label'],image=q['image'],exact_create_argv=item['create_argv'],CID=None,state='CREATION_ATTEMPT_PENDING',lifecycle_UNKNOWN=True,resource_charge_retained=True,removed=False)
    containers.append(custody);save('CONTAINER-CUSTODY.json',containers)
    cid=cli('passive-create',item['create_argv']).stdout.decode().strip();assert re.fullmatch('[0-9a-f]{64}',cid)
    custody.update(CID=cid,state='CREATED_REQUIRES_PROFILE');save('CONTAINER-CUSTODY.json',containers)
    created=inspect('passive-created-profile',cid);profile(created,item,cid,'created')
    assert created['State']['Status']=='created' and not created['State']['Running'] and created['State']['Pid']==0
    custody.update(created=created['Created'],state='PROFILE_VERIFIED_NOT_STARTED');save('CONTAINER-CUSTODY.json',containers)
    cli('passive-start',q['docker']+['start',cid]);custody['state']='STARTED_OUTCOME_PENDING';save('CONTAINER-CUSTODY.json',containers)
    wait=cli('passive-container-wait',q['docker']+['wait',cid],timeout=300);text=wait.stdout.decode().strip();assert re.fullmatch('[0-9]+',text)
    logs=cli('passive-logs',q['docker']+['logs',cid]);terminal=inspect('passive-terminal-profile',cid);profile(terminal,item,cid,'terminal');state=terminal['State']
    assert not state['Running'] and state['Pid']==0 and state['Status']=='exited' and int(text)==state['ExitCode']
    custody.update(state='TERMINAL_LOGS_WAITER_JOINED',exit=state['ExitCode'],OOMKilled=state['OOMKilled']);save('CONTAINER-CUSTODY.json',containers)
    assert state['ExitCode']==0 and state['OOMKilled'] is False and not state['Error'] and not logs.stderr
    summary=json.loads(logs.stdout);assert summary['status']=='PASS_TLS_THREE_PREVIOUSLY_UNSTARTED_PASSIVE_STEPS_ONLY' and summary['commands']==3 and summary['payload_or_collector_executed'] is False
    batch_path=pathlib.Path(q['passive_output'])/'capture/RESULT.json';assert sha(batch_path)==summary['capture_result_sha256']
    batch=json.loads(batch_path.read_bytes());assert batch['status']==summary['status'] and batch['command_plan_sha256']==q['passive_plan']['sha256']
    assert len(batch['commands'])==len(batch['ownership'])==3
    plan=json.loads(pathlib.Path(q['passive_plan']['path']).read_bytes());assert [r['argv'] for r in batch['commands']]==[r['argv'] for r in plan['commands']]
    for row in batch['commands']:assert row['exit']==0 and row['lifecycle_UNKNOWN'] is False
    inputs();pin(artifact);pin(produced_pin)
    for row in selected:
        p=pathlib.Path(row['path']);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
    removed=cli('passive-owned-terminal-remove',q['docker']+['rm',cid]);assert removed.stdout.decode().strip()==cid
    custody.update(state='VERIFIED_TERMINAL_OWNED_REMOVED',removed=True,lifecycle_UNKNOWN=False,resource_charge_retained=False,full_Root_completion_still_required=True);save('CONTAINER-CUSTODY.json',containers)
    remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not remaining and len(owner.records)==10
    save('RESULT.json',dict(status='PASS_TLS_MISSING_HOST_STATIC_COLLECTOR_AND_THREE_PASSIVE_ONLY',started_at=started,finished_at=now(),request_sha256=REQUEST_SHA256,review_sha256=sys.argv[2],admission_sha256=sys.argv[4],client_ownership=owner.records,containers=containers,HOST_collector=produced,HOST_collector_record=produced_pin,batch_result_reference=dict(path=str(batch_path),bytes=batch_path.stat().st_size,sha256=sha(batch_path)),remaining_direct_children=remaining,first_three_TLS_commands_recompiled=False,old_green_collector_or_case_rerun=False,payload_or_collector_executed=False,staging_or_native_executed=False,automatic_resource_retirement=False,full_Root_and_independent_actual_Q_required=True,original_acceptance=False))
    print(json.dumps(dict(status='PASS_TLS_MISSING_HOST_STATIC_COLLECTOR_AND_THREE_PASSIVE_ONLY',missing_HOST_compile_commands=1,missing_passive_commands=3,original_acceptance=False),sort_keys=True));return 0


def entry():
    global MAIN_PRIMARY_RAW,MAIN_PRIMARY_TB
    result=None;primary=None;tb=None
    try:result=main()  # Exactly once, no failed command or main replay.
    except BaseException as exc:
        primary=exc;tb=BaseException.__dict__['__traceback__'].__get__(exc,type(exc))
        MAIN_PRIMARY_RAW=exc;MAIN_PRIMARY_TB=tb
        if created_execution:
            try:save('RESULT.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_RETRY',started_at=started,at=now(),admitted=admitted,error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),phase=phase,argv=current_argv,attempts=attempts,containers=containers,ownership=owner.records if owner else [],automatic_container_kill_remove_or_resource_release=False,original_acceptance=False))
            except BaseException:pass
    finally:
        # Missing records and report failures cannot bypass original custody.
        while True:
            try:
                if OWNER_CALL_PENDING is None:break
                retain_current_Owner_context_nonescaping()
            except BaseException as custody_error:
                try:OWNER_CUSTODY_ERRORS.append((custody_error,BaseException.__dict__['__traceback__'].__get__(custody_error,type(custody_error))))
                except BaseException:pass
    if primary is not None:raise BaseException.with_traceback(primary,tb)
    return result

if __name__=='__main__':
    sys.exit(entry())
