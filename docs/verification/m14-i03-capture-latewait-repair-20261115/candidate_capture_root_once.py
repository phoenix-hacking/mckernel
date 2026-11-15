# Functional McKernel OS/apps/Rust M15-F06 supplier only; NO SECURITY TESTING.
# Rejected worker01a1c48d / turn01a1ce01 collector and equivalents stay excluded.
import ctypes, datetime, hashlib, json, os, pathlib, re, selectors, signal
import stat, subprocess, sys, time, traceback
clients=[];pending_calls={};RAW_ERRORS=[];ACTIVE_CONTEXTS=[];DATA_CONTEXTS=[];HELD_CONTAINERS=[]
CREATED_OUTPUT=False

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()

def save(name,value):
    assert re.fullmatch('[A-Za-z0-9_.-]+',name)
    temporary=OUT/(name+'.pending')
    context=dict(kind='same-report-FD-custody',stream=None,current_fd=None,primary_raw=None,primary_tb=None,secondary_raw=[])
    DATA_CONTEXTS.append(context)
    try:
        stream=temporary.open('x');context['stream']=stream
        json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        stream.close();context['stream']=None
        os.replace(str(temporary),str(OUT/name))
        for path in OUT.iterdir():
            if path.is_file():
                context['current_fd']=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
                os.fsync(context['current_fd'])
                os.close(context['current_fd']);context['current_fd']=None
        context['current_fd']=os.open(str(OUT),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
        os.fsync(context['current_fd'])
        os.close(context['current_fd']);context['current_fd']=None
        DATA_CONTEXTS.remove(context)
    except BaseException as error:
        context['primary_raw']=error
        context['primary_tb']=BaseException.__dict__['__traceback__'].__get__(error,type(error))
        record_raw('same-report-primary',error)
        # No close retry, new persistence attempt or formatting condition may
        # discard this exact FD/stream/raw error context; entry keeps it held.
        raise

def subreaper():
    libc=ctypes.CDLL(None,use_errno=True)
    libc.prctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong]
    if libc.prctl(36,1,0,0,0)!=0:raise OSError(ctypes.get_errno(),'supplier subreaper admission')

# Supplier-operation-specific adaptation of E088 FILE capture and the retained
# Root compound spawn_step/join_step. Not a selected/general command runner.
def record_raw(label, error):
    try:
        RAW_ERRORS.append((label, error, BaseException.__dict__['__traceback__'].__get__(error, type(error))))
    except BaseException:
        pass

def retain_supplier_context_nonescaping():
    # No replacement Popen, retry, signal, kill, numeric wait or close retry.
    # Keep the exact process, pipe/file FDs, raw primary/TB and all CID records.
    while True:
        try:
            if not ACTIVE_CONTEXTS and not DATA_CONTEXTS and not HELD_CONTAINERS:
                return
            try:
                signal.pause()
            except BaseException as error:
                record_raw('same-supplier-context-retention', error)
        except BaseException as error:
            record_raw('outermost-supplier-context-retention', error)

def write_exact(fd, data):
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError('nonpositive capture write')
        view = view[written:]

def query(label, argv, timeout=30, stdout_limit=65536, stderr_limit=65536):
    # This operation has only the fixed passive RPM/readelf or owned Docker
    # metadata/lifecycle arrays validated by its actor/parent. No API fallback.
    assert re.fullmatch('[A-Za-z0-9_.-]+', label)
    assert type(stdout_limit) is int and 0 < stdout_limit <= 2**21
    assert type(stderr_limit) is int and 0 < stderr_limit <= 2**21
    row = dict(attempt_id=len(clients), label=label, argv=argv,
        creation_attempted=False, popen_returned=False, pid=None, birth=None,
        exit='UNKNOWN', direct_wait_joined=False, streams_closed=False,
        input_FD_closed=False, capture_FDs_closed=False, captures_fsynced=False,
        stdout_limit_bytes=stdout_limit, stderr_limit_bytes=stderr_limit,
        stdout_bytes=0, stderr_bytes=0, primary_error=None, secondary_errors=[],
        receipt_persisted=False, lifecycle_UNKNOWN=True, resource_charge_retained=True)
    clients.append(row)
    context = dict(record=row, process=None, selector=None, capture_fds={},
        pipe_streams={}, input_fd=None, primary_raw=None, primary_tb=None,
        secondary_raw=[], original_owner_frame_retained=True)
    # Publish the SAME owning context before any FD/Popen operation. A failure
    # before a complete row is not treated as evidence that nothing was created.
    ACTIVE_CONTEXTS.append(context)
    try:
        save('CLIENTS.json', clients)
        for stream_name in ('stdout', 'stderr'):
            path = OUT/(label+'.'+stream_name)
            context['capture_fds'][stream_name] = os.open(str(path),
                os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC, 0o600)
        context['input_fd'] = os.open('/dev/null', os.O_RDONLY|os.O_CLOEXEC)
        row['creation_attempted'] = True
        save('CLIENTS.json', clients)
        process = subprocess.Popen(argv, stdin=context['input_fd'], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=ENV, cwd=str(ROOT), start_new_session=True)
        context['process'] = process
        pending_calls[row['attempt_id']] = process
        row.update(popen_returned=True, pid=process.pid)
        # The direct child is still unreaped; even a quick exit retains /proc.
        fields = pathlib.Path('/proc/%d/stat'%process.pid).read_text().rsplit(') ', 1)[1].split()
        assert fields[19].isdigit() and int(fields[19]) > 0
        row['birth'] = fields[19]
        save('CLIENTS.json', clients)
        selector = selectors.DefaultSelector()
        context['selector'] = selector
        for name, stream in (('stdout', process.stdout), ('stderr', process.stderr)):
            context['pipe_streams'][name] = stream
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        deadline = time.monotonic()+timeout
        limits = dict(stdout=stdout_limit, stderr=stderr_limit)
        while selector.get_map():
            remaining_time = deadline-time.monotonic()
            if remaining_time <= 0:
                raise TimeoutError('original supplier child deadline expired: '+label)
            for key, _ in selector.select(min(remaining_time, 0.1)):
                name = key.data
                remaining = limits[name]-row[name+'_bytes']
                # Read at most the remaining allowed bytes plus ONE detection
                # byte. Never communicate(), an unbounded read or post-buffer cap.
                try:
                    chunk = os.read(key.fileobj.fileno(), min(65536, remaining+1))
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                if len(chunk) > remaining:
                    raise OverflowError('hard '+name+' capture bound exceeded: '+label)
                write_exact(context['capture_fds'][name], chunk)
                row[name+'_bytes'] += len(chunk)
        remaining_time = deadline-time.monotonic()
        if remaining_time <= 0:
            raise TimeoutError('original supplier wait deadline expired: '+label)
        status = process.wait(timeout=remaining_time)
        row.update(exit=status, direct_wait_joined=True)
        assert all(stream.closed for stream in context['pipe_streams'].values())
        selector.close()
        row['streams_closed'] = True
        os.close(context['input_fd'])
        context['input_fd'] = None
        row['input_FD_closed'] = True
        for name, fd in list(context['capture_fds'].items()):
            os.fsync(fd)
            os.close(fd)
            del context['capture_fds'][name]
        row.update(capture_FDs_closed=True, captures_fsynced=True)
        children = pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
        row['remaining_direct_children'] = children
        assert not children, 'unexpected supplier descendant: original context retained'
        row.update(lifecycle_UNKNOWN=False, resource_charge_retained=False, receipt_persisted=True)
        save('CLIENTS.json', clients)
        # Only positive original wait, both pipe EOF/closure, input/capture FD
        # closure, durable receipt and empty children can remove this context.
        pending_calls.pop(row['attempt_id'])
        ACTIVE_CONTEXTS.remove(context)
        stdout = (OUT/(label+'.stdout')).read_bytes()
        stderr = (OUT/(label+'.stderr')).read_bytes()
        assert len(stdout) == row['stdout_bytes'] <= stdout_limit
        assert len(stderr) == row['stderr_bytes'] <= stderr_limit
        if status != 0:
            raise AssertionError((label, status))
        return stdout, stderr
    except BaseException as error:
        context['primary_raw'] = error
        context['primary_tb'] = BaseException.__dict__['__traceback__'].__get__(error, type(error))
        record_raw('original-supplier-query', error)
        if context in ACTIVE_CONTEXTS:
            row.update(lifecycle_UNKNOWN=True, resource_charge_retained=True)
        try:
            row['primary_error'] = type(error).__name__+': '+str(error)
            save('CLIENTS.json', clients)
        except BaseException as report_error:
            context['secondary_raw'].append((report_error, BaseException.__dict__['__traceback__'].__get__(report_error, type(report_error))))
            record_raw('supplier-query-report', report_error)
        raise

def finish_late_original_capture(context):
    # Only this original timed-out query and its positive original-Popen wait.
    # Every fallible completion step is attempted at most once; no FD retry.
    row=context['record'];process=context['process']
    if context.get('late_capture_completion_attempted') or process is None:return False
    primary=context.get('primary_raw')
    if not isinstance(primary,(TimeoutError,subprocess.TimeoutExpired)) or row.get('direct_wait_joined') is not False:return False
    if isinstance(primary,TimeoutError) and str(primary) not in ('original supplier child deadline expired: '+row['label'],'original supplier wait deadline expired: '+row['label']):return False
    late=('late_original_direct_wait_joined','late_original_exit')
    if row.get(late[0]) is not True:late=('outermost_original_direct_wait_joined','outermost_original_exit')
    if row.get(late[0]) is not True or type(row.get(late[1])) is not int:return False
    if process.returncode!=row[late[1]] or DATA_CONTEXTS:return False
    context['late_capture_completion_attempted']=True
    try:
        status=process.wait(timeout=0)
        assert status==row[late[1]] and process.pid==row['pid']
        assert pending_calls.get(row['attempt_id'],process) is process
        children=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
        assert not children, 'late original child joined but descendants remain'
        selector=context['selector'];assert selector is not None
        while selector.get_map():
            ready=selector.select(0)
            assert ready, 'late original pipe EOF remains unconfirmed'
            for key,_ in ready:
                name=key.data;remaining=row[name+'_limit_bytes']-row[name+'_bytes']
                chunk=os.read(key.fileobj.fileno(),min(65536,remaining+1))
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                assert len(chunk)<=remaining, 'late original capture exceeds original bound'
                write_exact(context['capture_fds'][name],chunk);row[name+'_bytes']+=len(chunk)
        assert all(stream.closed for stream in context['pipe_streams'].values())
        selector.close();row['streams_closed']=True
        os.close(context['input_fd']);context['input_fd']=None;row['input_FD_closed']=True
        for name,fd in list(context['capture_fds'].items()):
            os.fsync(fd);os.close(fd);del context['capture_fds'][name]
        row.update(capture_FDs_closed=True,captures_fsynced=True)
        children=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
        row['remaining_direct_children']=children
        assert not children, 'late original descendants remain'
        row.update(late_original_capture_completed=True,receipt_persisted=True,
                   lifecycle_UNKNOWN=False,resource_charge_retained=False)
        save('CLIENTS.json',clients)
        if pending_calls.get(row['attempt_id']) is process:pending_calls.pop(row['attempt_id'])
        del ACTIVE_CONTEXTS[next(index for index,value in enumerate(ACTIVE_CONTEXTS) if value is context)]
        return True
    except BaseException as error:
        row.update(late_original_capture_completed=False,receipt_persisted=False,lifecycle_UNKNOWN=True,resource_charge_retained=True)
        context['secondary_raw'].append((error,BaseException.__dict__['__traceback__'].__get__(error,type(error))))
        record_raw('late-original-capture-completion',error)
        return False

def supplier_entry_once():
    primary = None
    primary_tb = None
    result = None
    try:
        result = main()
    except BaseException as error:
        primary = error
        primary_tb = BaseException.__dict__['__traceback__'].__get__(error, type(error))
        record_raw('original-main-primary', error)
        try:
            if CREATED_OUTPUT:
                save('RESULT.json', dict(status='FAILED_SUPPLIER_SCOPE_PRESERVED_NO_RETRY',
                    error_type=type(error).__name__, error=str(error),
                    traceback=''.join(traceback.format_exception(type(error), error, primary_tb)),
                    clients=clients, containers=HELD_CONTAINERS,
                    pending_attempts=list(pending_calls), automatic_signal_or_remove=False,
                    automatic_resource_retirement=False, original_acceptance=False))
        except BaseException as report_error:
            record_raw('original-main-report', report_error)
    finally:
        # Formatting/persistence/FD failures cannot escape the original owning
        # frame. No signal authority is assumed: this path retains, never cancels.
        while True:
            try:
                if not ACTIVE_CONTEXTS and not DATA_CONTEXTS and not HELD_CONTAINERS:
                    break
                retain_supplier_context_nonescaping()
            except BaseException as custody_error:
                record_raw('supplier-entry-finally', custody_error)
    if primary is not None:
        raise BaseException.with_traceback(primary, primary_tb)
    return result

import ast
ROOT=pathlib.Path('/home/holden/mckernel')
HERE=pathlib.Path(__file__).resolve().parent
OUT=pathlib.Path('/home/holden/mckernel-work/m14-i03-paired-module-link-20261115/operation-binding-1/root-capture-2')
REQUEST_SHA256='1e1715466a5d11b466a11666aa16a8eaac871038a60736c9cbb0762a394ccc2c'
ENV=os.environ.copy()
keeper_capture_errors=[];OUTER_RETENTION_ERRORS=[];OUTER_ORIGINAL_WAITS=[]

def selected(item,names):
    raw=pathlib.Path(item['path']).read_bytes()
    assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),item['path'],'exec'),globals())

def identity(st):
    return tuple(getattr(st,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns'))

def read_ref(ref):
    path=pathlib.Path(ref['path']);st=path.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and 0<st.st_size<=2**20
    with path.open('rb') as stream:raw=stream.read(2**20+1)
    assert len(raw)==st.st_size and len(raw)<=2**20 and hashlib.sha256(raw).hexdigest()==ref['sha256']
    if 'bytes' in ref:assert type(ref['bytes']) is int and ref['bytes']>0 and len(raw)==ref['bytes']
    assert identity(st)==identity(path.lstat()),'reference changed during read'
    return json.loads(raw)

# Required fresh Root inputs. No SourceGO or four-test output is supplied here.
def verify_pending_consumer_qualification(q,grant):
    proof=grant['account_consumer_qualification']
    assert set(proof)=={'consumer_sha256','independent_source_GO_ref','focused_four_tests_ref',
        'independent_source_GO_verified','four_tests_PASS_verified','tests_count'}
    assert proof['consumer_sha256']==q['account_consumer_ref']['sha256']
    assert proof['independent_source_GO_ref']['path']==q['account_consumer_source_GO_ref']['path']
    assert proof['independent_source_GO_ref']['sha256']==q['account_consumer_source_GO_ref']['sha256']
    assert proof['independent_source_GO_verified'] is True
    assert proof['four_tests_PASS_verified'] is True
    assert type(proof['tests_count']) is int and proof['tests_count']==4
    # Actual full-file refs are issued only after the separate helper review and
    # tests qualify. UNISSUED/missing/null/string slots cannot pass read_ref.
    read_ref(proof['independent_source_GO_ref'])
    assert proof['focused_four_tests_ref']['path']==q['account_consumer_tests_ref']['path']
    assert proof['focused_four_tests_ref']['sha256']==q['account_consumer_tests_ref']['sha256']
    read_ref(proof['focused_four_tests_ref'])

def verify_module_actual_inputs(q,grant):
    proof=grant['paired_module_actual_input_qualification']
    assert set(proof)=={'IHK_finalized_object_ref','IHK_actual_depfile_ref','IHK_source_cohort_sha256',
        'IHK_actual_artifact_Q_ref','IHK_actual_family_Q_ref','IHK_Root_scoped_retirement_ref',
        'IHK_source_objtool_artifact_verified','retained_kernel_input_refs','retained_kernel_qualified_evidence_ref',
        'retained_kernel_inputs_verified','SDK_tool_profile_evidence_ref','SDK_tool_profile_verified',
        'all_other_holds_preserved','no_failed_scope_replay_verified'}
    for key in ('IHK_source_objtool_artifact_verified','retained_kernel_inputs_verified',
        'SDK_tool_profile_verified','all_other_holds_preserved','no_failed_scope_replay_verified'):
        assert proof[key] is True
    assert proof['IHK_source_cohort_sha256']==q['IHK_expected_source_cohort_sha256']
    for key in ('IHK_finalized_object_ref','IHK_actual_depfile_ref'):
        for field,value in q['observed_IHK_producer_inputs'][key].items():assert proof[key][field]==value
    for key in ('IHK_actual_artifact_Q_ref','IHK_actual_family_Q_ref','IHK_Root_scoped_retirement_ref',
        'retained_kernel_qualified_evidence_ref','SDK_tool_profile_evidence_ref'):
        read_ref(proof[key])
    required={'path','bytes','sha256','dev','inode','uid','gid','mode','nlink','mtime_ns','ctime_ns'}
    for key,maximum in (('IHK_finalized_object_ref',268435456),('IHK_actual_depfile_ref',2097152)):
        item=proof[key]
        assert required<=set(item) and pathlib.Path(item['path']).is_absolute()
        assert type(item['bytes']) is int and 0<item['bytes']<=maximum and re.fullmatch('[0-9a-f]{64}',item['sha256'])
        assert item['uid']==item['gid']==1000 and item['nlink']==1 and item['mode']=='0o600'
        for name in ('dev','inode'):assert type(item[name]) is int and item[name]>0
        for name in ('mtime_ns','ctime_ns'):assert isinstance(item[name],str) and re.fullmatch('[0-9]+',item[name])
    assert set(proof['retained_kernel_input_refs'])=={'vmlinux','module_common','modpost'}
    for row in q['known_kernel_inputs']:
        item=proof['retained_kernel_input_refs'][row['role']]
        assert required<=set(item) and re.fullmatch('[0-9a-f]{64}',item['sha256'])
        for key,value in row['known_source_metadata'].items():assert item[key]==value
    return proof

def review_and_grant():
    assert len(sys.argv)==5 and sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
    q=json.loads((HERE/'REQUEST.FROZEN.json').read_bytes())
    review_ref=dict(path=str(pathlib.Path(sys.argv[1]).resolve()),sha256=sys.argv[2])
    review=read_ref(review_ref)
    assert review['schema']==q['operation_review_schema'] and review['reviewer'].startswith(q['independent_reviewer_prefix'])
    assert review['decision']==q['exact_GO_decision']
    cap_ref=dict(path=str(HERE/'CAPTURE-REQUEST.json'),sha256=sha(HERE/'CAPTURE-REQUEST.json'))
    expected=dict(request_sha256=REQUEST_SHA256,run_root_once_sha256=sha(HERE/'run_root_once.py'),
        capture_root_once_sha256=sha(HERE/'capture_root_once.py'),capture_request_sha256=cap_ref['sha256'],
        profile_sha256=q['profile']['sha256'],input_manifest_sha256=q['input_manifest']['sha256'],
        official_acquisition_body_sha256=q['official_body']['sha256'],bounded_capture_body_sha256=q['capture_body']['sha256'],
        official_source_GO_sha256=q['official_source_GO_ref']['sha256'])
    assert review['approved_sha256']==expected
    cap=read_ref(cap_ref)
    assert cap['request']['sha256']==REQUEST_SHA256 and cap['parent']['sha256']==expected['run_root_once_sha256'] and cap['outer']['sha256']==expected['capture_root_once_sha256']
    ap=pathlib.Path(sys.argv[3]);st=ap.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1
    grant_ref=dict(path=str(ap.resolve()),sha256=sys.argv[4])
    grant=read_ref(grant_ref)
    assert set(grant)==set(q['admission_fields'])
    assert grant['schema']==q['admission_schema'] and grant['Root_thread_id']==q['Root_thread_id'] and grant['invocation']==q['invocation']
    assert grant['same_Root_finite_credit_run_id']==q['finite_credit_run_id']
    assert grant['request_sha256']==REQUEST_SHA256 and grant['runtime_operation_review']==review_ref
    assert grant['capture_request_sha256']==cap_ref['sha256']
    assert grant['protected_parent_sha256']==expected['run_root_once_sha256'] and grant['protected_outer_capture_sha256']==expected['capture_root_once_sha256']
    assert grant['normal_profile_sha256']==q['profile']['sha256'] and grant['source_manifest_sha256']==q['input_manifest']['sha256']
    assert grant['account_consumer_ref']==q['account_consumer_ref']
    assert grant['current_owner_private_ref']==q['current_owner_ref']
    assert grant['source_view_verified'] is True and grant['complete_owner_accounting'] is True and grant['native_and_historical_unknowns_preserved'] is True
    assert grant['no_exclusive_other_owner_scope'] is True and isinstance(grant['allowed_running_container_ids'],list) and all(re.fullmatch('[0-9a-f]{64}',x) for x in grant['allowed_running_container_ids'])
    assert grant['charge']==q['charge'] and grant['new_parent_capture_overhead_reserved_bytes']==0
    policy=q['shared_resource_policy']
    assert policy['work_memory_ceiling_bytes']==30064771072 and policy['host_memory_ceiling_bytes']==10737418240
    assert policy['non_host_reservation_bytes']==19327352832 and policy['machine_reserve_bytes']==2147483648
    assert policy['host_cpu_affinity']==[0,6,7] and policy['host_max_jobs']==5
    assert policy['retained_HOST_bytes']==4697620480 and policy['retained_HOST_jobs']==4
    resource_evidence=read_ref(grant['scoped_resource_evidence'])
    for key in ('work_memory_ceiling_bytes','host_memory_ceiling_bytes','non_host_reservation_bytes','machine_reserve_bytes','host_cpu_affinity','host_max_jobs','MemTotal_bytes'):
        assert resource_evidence[key]==policy[key], 'current selected shared resource mismatch: '+key
    measured_total=next(int(line.split()[1])*1024 for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:'))
    assert measured_total==policy['MemTotal_bytes']==33199697920
    assert policy['work_memory_ceiling_bytes']+policy['machine_reserve_bytes']<=measured_total
    assert policy['non_host_reservation_bytes']+policy['host_memory_ceiling_bytes']==policy['work_memory_ceiling_bytes']
    assert type(grant['current_HOST_jobs_before']) is int and policy['retained_HOST_jobs']<=grant['current_HOST_jobs_before']<policy['host_max_jobs']
    for key in ('other_current_HOST_payload_reserved_bytes','current_owned_controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes'):
        assert type(grant[key]) is int and grant[key]>=0
    assert grant['other_current_HOST_payload_reserved_bytes']>=policy['retained_HOST_bytes']
    assert grant['current_HOST_jobs_before']+q['charge']['jobs']<=policy['host_max_jobs']
    host_family_total=grant['other_current_HOST_payload_reserved_bytes']+grant['current_owned_controller_worker_overhead_bytes']+q['charge']['planning_bytes']
    assert host_family_total<=policy['host_memory_ceiling_bytes']
    assert policy['non_host_reservation_bytes']+host_family_total<=policy['work_memory_ceiling_bytes']
    assert grant['MemAvailable_bytes']>=26*2**30 and grant['host_free_bytes']>=16*2**30+q['capture_headroom_bytes'] and grant['scratch_free_bytes']>=12*2**30+q['capture_headroom_bytes']
    assert 0<=(time.time_ns()-grant['issued_utc_ns'])/1e9<=60 and 0<=(time.monotonic_ns()-grant['issued_mono_ns'])/1e9<=60
    assert grant['host_boot_id']==pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    read_ref(grant['current_owner_validation_ref'])
    assert isinstance(grant['actual_source_service_permission_evidence_refs'],list) and grant['actual_source_service_permission_evidence_refs']
    for item in grant['actual_source_service_permission_evidence_refs']:read_ref(item)
    verify_pending_consumer_qualification(q,grant)
    verify_module_actual_inputs(q,grant)
    return q,grant,grant_ref,review_ref

# Functional McKernel OS/apps/Rust only; NO SECURITY TESTING.
# Exact created supplier CID and one original protected parent only.
state={'pidfd':None,'signal_attempted':False,'signal_returned':False}

# Functional McKernel OS/apps/Rust only; NO SECURITY TESTING.
# Cancel only these three current own-operation roles. No normal-wait claim.
ROLE_ORDER=['supplier_parent','supplier_outer_original_parent_owner','Root_exec_wait_wrapper_original_outer_owner']
CANCEL_STATE={name:dict(pidfd=None,signal_attempted=False,signal_returned=False,terminal=False) for name in ROLE_ORDER}

# Private diagnostic boundary only; no alternative account observation route.
ACCOUNT_REFUSAL_CONTEXTS=[]

def main():
    global ENV,CREATED_OUTPUT
    q,grant,grant_ref,review_ref=review_and_grant()
    assert os.sched_getaffinity(0)=={7} and not OUT.exists()
    ENV=dict(q['host_environment'])
    os.umask(0o077);OUT.mkdir(mode=0o700);CREATED_OUTPUT=True;subreaper()
    argv=['/usr/bin/taskset','-c','7','/usr/bin/python3','-B',str(HERE/'run_root_once.py'),sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]]
    save('ROOT-ARGV.json',dict(argv=argv,request_sha256=REQUEST_SHA256,review=review_ref,grant=grant_ref))
    stdout,stderr=query('Root-parent',argv,q['limits']['parent_seconds'],16384,16384)
    assert not stderr and len(clients)==1 and not pending_calls and not ACTIVE_CONTEXTS
    result=json.loads((pathlib.Path(q['paths']['execution'])/'RESULT.json').read_bytes())
    assert result['status']=='PASS_PAIRED_MODULE_LINK_MODPOST_PROTECTED_LD_CHECKPOINT_ONLY' and result['request_sha256']==REQUEST_SHA256
    assert len(result['clients'])==9 and result['remaining_direct_children']==[]
    assert result['created_and_terminal_profile_verified'] is True and result['terminal_exit0_nonOOM_Pid0'] is True
    assert result['removed'] is True and result['exact_absence'] is True and result['original_held_input_FDs_closed'] is True
    assert len(result['module_refs'])==2
    assert result['BTF_signing_load_native_workload_lifecycle_original_acceptance_UNPROVED'] is True
    remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not remaining
    save('RESULT.json',dict(status='PASS_PAIRED_MODULE_LINK_MODPOST_ROOT_CAPTURE_ONLY',clients=clients,
        root_parent_argv=argv,remaining_direct_children=remaining,all_prior_holds_unchanged=True,
        full_original_Root_initial_terminal_and_independent_actual_Q_required=True,automatic_resource_retirement=False,
        no_cached_family_or_source_retirement_or_original_acceptance=True))
    print(stdout.decode(),end='');return 0

if __name__=='__main__':
    assert sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
    outer_q=json.loads((HERE/'REQUEST.FROZEN.json').read_bytes())
    selected(outer_q['qualified_same_handle_keeper'],['keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody'])
    try:
        sys.exit(entry_once_with_original_custody())
    finally:
        for context in tuple(ACTIVE_CONTEXTS):
            finish_late_original_capture(context)
        # Qualified five original-Popen keeper bodies execute unchanged above.
        # This additional exact-supplier boundary also retains open capture FDs
        # and raw owning frames after any late wait/report failure.
        while True:
            try:
                if not ACTIVE_CONTEXTS and not DATA_CONTEXTS and not HELD_CONTAINERS:break
                retain_supplier_context_nonescaping()
            except BaseException as error:
                record_raw('supplier-after-qualified-original-waits',error)
