# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# One finite HOST controls child, using existing E088 and same-Popen keeper bodies.
# Rejected worker01a1c48d/turn01a1ce01 signal/frame/xstate collector task stays excluded.
import argparse, ast, datetime, hashlib, json, os, pathlib, re, resource
import shutil, signal, stat, subprocess, sys, time, traceback
ROOT=pathlib.Path('/home/holden/mckernel')
HERE=pathlib.Path(__file__).resolve().parent
OUT=None
ROOT_ID='01a18bc3-e072-7810-9426-75101b0856c0'
INVOCATION='invocation20261112T094452Z-12a4bea0'
CREDIT_RUN='7c6ef3604bfb4008a917bba8cfb6cfaa'
GIB=2**30
REQUEST_SHA256='a093f654a70656e8d6427d4c2bd6f9fe115a273fcf132ca718f8ab78d5d2bdbf'
clients=[]
pending_calls={}
held={}
sequence=0
keeper_capture_errors=[]
OUTER_RETENTION_ERRORS=[]
OUTER_ORIGINAL_WAITS=[]
expected_owner=None
account_api=None
control=None
grant=None
ENV={}

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def identity(st):
    return tuple(getattr(st,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns'))

def pin(ref, want_bytes=False):
    path = pathlib.Path(ref['path'])
    key = (str(path),ref['sha256'])
    if key in held:
        record = held[key]
    else:
        fd = os.open(str(path),os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            st = os.fstat(fd)
            assert stat.S_ISREG(st.st_mode) and 0 < st.st_size <= 128*2**20, 'bounded regular input required'
            if 'bytes' in ref:
                assert st.st_size == ref['bytes'], 'input size mismatch'
            assert identity(st) == identity(os.stat(str(path),follow_symlinks=False)), 'input path mismatch'
            record = {'fd':fd,'path':str(path),'identity':identity(st),'sha256':ref['sha256']}
            held[key] = record
        except BaseException:
            os.close(fd)
            raise
    os.lseek(record['fd'],0,os.SEEK_SET)
    digest = hashlib.sha256()
    chunks = [] if want_bytes else None
    count = 0
    while True:
        block = os.read(record['fd'],1024*1024)
        if not block:
            break
        count += len(block)
        assert count <= 128*2**20, 'input grew'
        digest.update(block)
        if chunks is not None:
            chunks.append(block)
    assert digest.hexdigest() == ref['sha256'], 'input digest mismatch'
    assert identity(os.fstat(record['fd'])) == record['identity'], 'held input changed'
    assert identity(os.stat(record['path'],follow_symlinks=False)) == record['identity'], 'input path changed'
    return b''.join(chunks) if chunks is not None else None

def read_json_ref(ref):
    return json.loads(pin(ref,True))

def pin_bookend():
    for (path,digest),record in list(held.items()):
        pin({'path':path,'sha256':digest,'bytes':record['identity'][6]})

def save(name,value):
    global sequence
    assert OUT is not None and re.fullmatch(r'[A-Za-z0-9_.-]+',name), 'capture name'
    sequence += 1
    target = OUT/name
    temp = OUT/(name+'.tmp.'+str(os.getpid())+'.'+str(sequence))
    with temp.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(str(temp),str(target))

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

def durable_capture():
 for path in OUT.iterdir():
  if path.is_file():
   fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
   try:os.fsync(fd)
   finally:os.close(fd)
 fd=os.open(str(OUT),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
 try:os.fsync(fd)
 finally:os.close(fd)

base_save=save
def save(name,value):
    base_save(name,value)
    durable_capture()


def select_functions(ref,names):
    raw=pin(ref,True)
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),ref['path'],'exec'),globals())


def verify_tool(ref):
    pin(ref)
    alias=pathlib.Path(ref['argv_path'])
    assert alias.resolve(strict=True)==pathlib.Path(ref['path']), 'argv alias differs from pinned tool'
    st=alias.stat()
    assert (st.st_dev,st.st_ino,st.st_uid,st.st_gid,oct(stat.S_IMODE(st.st_mode)))==(ref['dev'],ref['inode'],ref['uid'],ref['gid'],ref['mode']), 'complete tool identity/mode'


def verify_grant(value,review_ref,own_sha,q):
    assert value['schema']=='mckernel.Root-current-HOST-admission.reporting-eight-controls.v1'
    assert value['Root_thread_id']==ROOT_ID and value['invocation']==INVOCATION and value['same_Root_finite_credit_run_id']==CREDIT_RUN
    assert value['test_operation_request_sha256']==REQUEST_SHA256 and value['protected_capture_parent_sha256']==own_sha
    assert value['normal_profile_sha256']==q['profile']['sha256'] and value['runtime_operation_review']==review_ref
    assert value['account_consumer_ref']==q['account_consumer_ref'] and value['current_owner_private_ref']==q['current_owner_private_ref']
    assert value['fixture_argv_sha256']==hashlib.sha256((json.dumps(q['command']['argv'],sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()
    assert value['pure_HOST_controls_parallel_with_current_recovery'] is True
    assert value['source_view_verified'] is True and value['complete_owner_accounting'] is True and value['native_and_historical_unknowns_preserved'] is True
    assert type(value['current_HOST_jobs_before']) is int and 0<=value['current_HOST_jobs_before']<3
    for key in ('other_current_HOST_payload_reserved_bytes','current_owned_controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes'):
        assert type(value[key]) is int and value[key]>=0
    assert value['MemAvailable_bytes']>=26*GIB and value['host_free_bytes']>=16*GIB+33554432 and value['scratch_free_bytes']>=12*GIB+33554432
    assert value['charge']=={'CPU':[0],'jobs':1,'planning_bytes':268435456,'retired':False,'retire_only_on_actual_positive_closure':True}
    assert value['current_HOST_jobs_before']+1<=3 and value['other_current_HOST_payload_reserved_bytes']+value['current_owned_controller_worker_overhead_bytes']+268435456<=4*GIB
    assert 0<=(time.time_ns()-value['issued_utc_ns'])/1e9<=60 and 0<=(time.monotonic_ns()-value['issued_mono_ns'])/1e9<=60
    pin(value['current_owner_validation_ref']);pin(value['scoped_resource_evidence'])


def admit(q):
    state_guard()
    _,usage,credit,_=account_api['current_account_snapshot'](expected_owner)
    del credit
    measured=measure()
    assert measured['MemAvailable_bytes']>=26*GIB
    assert measured['host_free_bytes']>=16*GIB+33554432 and measured['scratch_free_bytes']>=12*GIB+33554432
    assert grant['current_HOST_jobs_before']+1<=3
    assert grant['other_current_HOST_payload_reserved_bytes']+grant['current_owned_controller_worker_overhead_bytes']+268435456<=4*GIB
    pin_bookend()
    save('ADMISSION.json',{'at':now(),'external_grant_reference':control['external_grant_reference'],'request_sha256':REQUEST_SHA256,'accepted_account_source':usage['source_kind'],'accepted_account_method':usage['source_event'],'account_received_utc_ns':usage['receipt_received_utc_ns'],'account_received_mono_ns':usage['receipt_received_mono_ns'],'actual_current_resources':measured,'all_other_current_retained_charges_and_overhead_in_external_grant':True,'original81012_native12_source_runtime_UNKNOWN_unchanged':True,'pure_controls_not_conditioned_on_native_recovery':True,'no_resource_retirement_by_parent':True})


def run(args):
    global OUT,control,grant,expected_owner,account_api,ENV
    own_sha=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
    q=read_json_ref({'path':str(HERE/'REQUEST.json'),'sha256':REQUEST_SHA256})
    review_ref={'path':str(pathlib.Path(args.operation_review).resolve()),'bytes':pathlib.Path(args.operation_review).stat().st_size,'sha256':args.operation_review_sha}
    assert review_ref['path']==q['review_path']
    review=read_json_ref(review_ref)
    assert review['schema']==q['review_schema'] and review['reviewer'].startswith(q['reviewer_prefix'])
    assert review['decision']==q['required_operation_decision']
    assert review['request_sha256']==REQUEST_SHA256 and review['run_root_once_sha256']==own_sha
    for key in ('fixture','source_pins','profile','oracles','source_GO'):
        assert review[key+'_sha256']==q[key]['sha256']
    grant_ref={'path':str(pathlib.Path(args.admission).resolve()),'bytes':pathlib.Path(args.admission).stat().st_size,'sha256':args.admission_sha}
    assert grant_ref['path']==q['admission_path']
    grant=read_json_ref(grant_ref)
    verify_grant(grant,review_ref,own_sha,q)
    control={'account_consumer_ref':q['account_consumer_ref'],'current_owner_private_ref':q['current_owner_private_ref'],'external_grant_reference':grant_ref}
    account_code=pin(q['account_consumer_ref'],True)
    account_api={'__name__':'mckernel_current_root_account_consumer','__file__':q['account_consumer_ref']['path']}
    exec(compile(account_code,q['account_consumer_ref']['path'],'exec'),account_api)
    expected_owner=read_json_ref(q['current_owner_private_ref'])
    account_api['current_account_snapshot'](expected_owner)
    assert expected_owner['thread_id']==ROOT_ID
    state_guard()
    pin(q['canonical_current_validator_ref'])
    for key in ('fixture','source_pins','oracles','profile','source_GO','expected_stdout','qualified_parent_primitives','qualified_E088','qualified_same_handle_keeper'):
        pin(q[key])
    assert read_json_ref(q['source_GO'])['decision'].startswith('GO_REPORTING_ONLY_SOURCE_DELTA')
    for ref in q['proposal_reuse']:pin(ref)
    sources=read_json_ref(q['source_pins'])
    for ref in list(sources['modules'].values())+[sources['baseline_watchdog']]:pin(ref)
    for ref in q['tool_pins']:verify_tool(ref)
    assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0}
    assert resource.getrlimit(resource.RLIMIT_AS)==(134217728,134217728)
    assert resource.getrlimit(resource.RLIMIT_CPU)==(20,20)
    assert resource.getrlimit(resource.RLIMIT_FSIZE)==(8388608,8388608)
    assert resource.getrlimit(resource.RLIMIT_NOFILE)==(128,128) and resource.getrlimit(resource.RLIMIT_CORE)==(0,0)
    assert not pathlib.Path(q['execution_root']).exists(), 'fresh output namespace required; no replay'
    OUT=pathlib.Path(q['execution_root']);OUT.mkdir(mode=0o700)
    ENV=dict(q['environment'])
    select_functions(q['qualified_E088'],['call'])
    admit(q)
    save('PARENT-IDENTITY.json',{'pid':os.getpid(),'birth':pathlib.Path('/proc/%d/stat'%os.getpid()).read_text().rsplit(')',1)[1].split()[19],'ppid':os.getppid(),'request_sha256':REQUEST_SHA256,'parent_sha256':own_sha,'operation_review_reference':review_ref,'external_grant_reference':grant_ref,'literal_fixture_argv':q['command']['argv'],'Root_full_initial_terminal_tool_wait_streams':'EXTERNAL_REQUIRED','no_native_or_resource_retirement':True})
    raw=call(q['command']['id'],q['command']['argv'],timeout=q['command']['wall_seconds'])
    assert raw==pin(q['expected_stdout'],True) and len(raw)==q['command']['stdout_limit_bytes']
    assert (OUT/(q['command']['id']+'.stderr')).read_bytes()==b''
    assert len(clients)==1 and not pending_calls
    client=clients[0]
    assert client['exit']==0 and client['direct_wait_joined'] is True and client['streams_closed'] is True and client['receipt_persisted'] is True
    assert client['primary_error'] is None and client['secondary_errors']==[] and not client['lifecycle_UNKNOWN'] and not client['resource_charge_retained']
    result=json.loads(raw)
    assert result['status']=='PASS_EIGHT_REPORTING_ONLY_CONTROLS_DATA_NOT_NATIVE_OR_OWNERSHIP_PROOF' and len(result['cases'])==8
    assert result['native_or_IHK_or_account_or_original_process_execution'] is False and result['original81012_and_all_holds_unchanged'] is True
    remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
    assert remaining==[]
    pin_bookend()
    return {'status':'PASS_EIGHT_REPORTING_ONLY_HOST_CONTROLS_PENDING_INDEPENDENT_SAVED_QUALIFICATION_AND_ROOT_WAIT','at':now(),'request_sha256':REQUEST_SHA256,'parent_sha256':own_sha,'operation_review_reference':review_ref,'external_grant_reference':grant_ref,'fixture_result':result,'clients':clients,'remaining_direct_children':remaining,'all_client_waits_streams_positive':True,'Root_full_initial_terminal_tool_wait_streams':'EXTERNAL_REQUIRED','only_new256MiB_charge_retirement_requires_independent_actual_Q_and_full_Root_completion':True,'original81012_runtime_source_native12_UNKNOWN_unchanged':True,'original_acceptance':False,'native_or_ownership_proof':False}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--operation-review',required=True);parser.add_argument('--operation-review-sha',required=True)
    parser.add_argument('--admission',required=True);parser.add_argument('--admission-sha',required=True)
    args=parser.parse_args()
    assert all(re.fullmatch('[0-9a-f]{64}',value) for value in (args.operation_review_sha,args.admission_sha))
    result=None;primary=None;primary_tb=None;close_errors=[]
    try:result=run(args)
    except BaseException as error:
        primary=error;primary_tb=BaseException.__dict__['__traceback__'].__get__(error,type(error))
        retain_outer_error('original-main-primary',error)
    finally:
        while True:
            try:
                if not pending_calls:break
                retain_original_pending_nonescaping()
            except BaseException as custody_error:retain_outer_error('main-finally-original-custody',custody_error)
        for record in list(held.values())[::-1]:
            try:os.close(record['fd'])
            except BaseException as error:close_errors.append({'path':record['path'],'error':type(error).__name__+': '+str(error)})
        held.clear()
    if primary is not None or close_errors:
        failure={'status':'FAILED_REPORTING_CONTROLS_PRESERVED_NO_UNCHANGED_REPLAY','at':now(),'request_sha256':REQUEST_SHA256,'primary_type':type(primary).__name__ if primary is not None else None,'primary_error':str(primary) if primary is not None else None,'primary_traceback':''.join(traceback.format_exception(type(primary),primary,primary_tb)) if primary is not None else None,'own_input_close_errors':close_errors,'clients':clients,'pending_original_attempts':list(pending_calls),'original81012_runtime_source_native12_UNKNOWN_unchanged':True,'automatic_resource_release':False,'original_acceptance':False}
        if OUT is not None:
            try:save('RESULT.json',failure)
            except BaseException as error:sys.stderr.write('RESULT persistence failure: '+repr(error)+'\n')
        if primary is not None:sys.stderr.write(failure['primary_traceback'])
        return 1
    result['own_input_close_errors']=[];result['in_parent_input_FDs_closed']=True
    save('RESULT.json',result)
    print(json.dumps({'status':result['status'],'result_path':str(OUT/'RESULT.json'),'Root_full_wait':'EXTERNAL_REQUIRED','original_acceptance':False},sort_keys=True))
    return 0

def keeper_record(name,value):
 # A reporting failure must not bypass the original process wait. Retain raw
 # exception/TB and try the existing outer captured stderr without new work.
 try:save(name,value)
 except BaseException as error:
  keeper_capture_errors.append((name,error,error.__traceback__))
  try:sys.stderr.write('keeper capture failure '+name+': '+traceback.format_exc())
  except BaseException as diagnostic_error:
   keeper_capture_errors.append(('keeper-stderr',diagnostic_error,diagnostic_error.__traceback__))

def preserve_original_pending_waits():
 # No new Popen, signal, killpg, sudo-client kill, descriptor retry or replay.
 # The original direct Popen object stays reachable while the actual Root
 # source keeper may retain native/runtime custody beyond its initial cap.
 if not pending_calls:return
 keeper_record('SOURCE-KEEPER-UNKNOWN-CUSTODY.json',dict(at=now(),pending_attempts=list(pending_calls),status='RETAIN_ORIGINAL_CAPTURE_PARENT_AND_DIRECT_HANDLES_NO_KILL_OR_REPLAY',current_charge_and_job='RETAINED',native_and_historical_scopes='UNCHANGED'))
 while pending_calls:
  for attempt,process in list(pending_calls.items()):
   try:
    status=process.wait(timeout=30)
   except subprocess.TimeoutExpired:
    continue
   except BaseException as error:
    keeper_record('ORIGINAL-WAIT-FAILURE.json',dict(at=now(),attempt=attempt,pid=process.pid,error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),status='UNKNOWN_RETAINED_NO_NONCHILD_WAIT_OR_SIGNAL_FALLBACK'))
    # A missing wait channel is not repaired by numeric PID guesses. Retain
    # this exact owning context for separately reviewed Root disposition.
    while True:
     try:signal.pause()
     except BaseException:pass
   else:
    pending_calls.pop(attempt,None)
    rec=clients[attempt]
    rec['late_original_direct_wait_joined']=True
    rec['late_original_exit']=status
    rec['late_join_at']=now()
    # Keep the original timeout/UNKNOWN row; a later wait is separate evidence.
    keeper_record('CLIENTS.json',clients)
    keeper_record('LATE-ORIGINAL-DIRECT-WAIT.json',dict(at=now(),attempt=attempt,pid=process.pid,birth=rec.get('birth'),exit=status,original_failure_preserved=True,no_native_or_runtime_release_inferred=True))

def retain_outer_error(label, error):
 try:
  tb=BaseException.__dict__['__traceback__'].__get__(error,type(error))
  OUTER_RETENTION_ERRORS.append((label,error,tb))
 except BaseException:
  # No formatting, report or bookkeeping failure may defeat original custody.
  pass

def retain_original_pending_nonescaping():
 while True:
  try:
   if not pending_calls:return
   try:
    preserve_original_pending_waits()
   except BaseException as error:
    retain_outer_error('existing-retention-path',error)
    # Diagnostic/capture/bookkeeping may be broken before the existing helper
    # reaches its wait. Use only the SAME saved Popen objects and original wait
    # endpoint, with no reporting dependency before a positive direct wait.
    for attempt,process in tuple(pending_calls.items()):
     try:
      status=process.wait(timeout=30)
     except subprocess.TimeoutExpired:
      continue
     except BaseException as wait_error:
      retain_outer_error('original-retention-wait',wait_error)
      continue
     else:
      # Retain the observed positive wait before removing only that same
      # original object. Any later interruption is caught by the whole guard.
      OUTER_ORIGINAL_WAITS.append(dict(attempt=attempt,pid=process.pid,exit=status))
      if pending_calls.get(attempt) is process:pending_calls.pop(attempt)
      if type(attempt) is int and 0<=attempt<len(clients):
       clients[attempt]['outermost_original_direct_wait_joined']=True
       clients[attempt]['outermost_original_exit']=status
  except BaseException as error:
   # This covers the ENTIRE retention/report/record/bookkeeping path, including
   # failures raised outside any per-process wait try. Keep all original refs.
   retain_outer_error('outermost-retention-boundary',error)

def entry_once_with_original_custody():
 primary=None;primary_tb=None;result=None
 try:
  result=main()  # Exactly one main invocation; never retry the native command.
 except BaseException as error:
  primary=error
  primary_tb=BaseException.__dict__['__traceback__'].__get__(error,type(error))
 finally:
  # No main except/finally or diagnostic failure can bypass this outermost
  # boundary. All condition evaluation and keeper code run under its catch.
  while True:
   try:
    if not pending_calls:break
    retain_original_pending_nonescaping()
   except BaseException as error:
    retain_outer_error('entry-finally-retention',error)
 # Only after every original direct child has an actual wait may reporting or
 # the preserved primary leave this process. All UNKNOWN/history stays intact.
 if OUTER_RETENTION_ERRORS or OUTER_ORIGINAL_WAITS:
  try:
   keeper_record('OUTERMOST-ORIGINAL-CUSTODY.json',dict(original_direct_waits=OUTER_ORIGINAL_WAITS,raw_errors=[dict(label=label,error_type=type(error).__name__,error=str(error),traceback=''.join(traceback.format_exception(type(error),error,tb))) for label,error,tb in OUTER_RETENTION_ERRORS],original_main_primary_type=type(primary).__name__ if primary is not None else None,native_runtime_and_historical_release_inferred=False))
  except BaseException as report_error:
   retain_outer_error('postjoin-retention-report',report_error)
 if primary is not None:raise BaseException.with_traceback(primary,primary_tb)
 if OUTER_RETENTION_ERRORS:raise OUTER_RETENTION_ERRORS[0][1]
 return result

if __name__=='__main__':
    sys.exit(entry_once_with_original_custody())
