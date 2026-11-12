# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# F08-specific protected HOST capture. No body/provider/main/native changes.
# Rejected worker01a1c48d-4d96-7cc3-b733-73a97973152f / turn01a1ce01-20cf-7e03-9442-f6d521fb8b02
# signal/frame/xstate collector stays excluded from replay/rephrasing/reassignment.
import argparse,datetime,hashlib,json,os,pathlib,re,resource,shutil,signal,stat,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel')
HERE=pathlib.Path(__file__).resolve().parent
ROOT_ID='01a18bc3-e072-7810-9426-75101b0856c0'
INVOCATION='invocation20261112T094452Z-12a4bea0'
CREDIT_RUN='7c6ef3604bfb4008a917bba8cfb6cfaa'
GIB=2**30
OUT=None
clients=[]
pending_calls={}
held={}
sequence=0
keeper_capture_errors=[]
OUTER_RETENTION_ERRORS=[]
OUTER_ORIGINAL_WAITS=[]
MAIN_PRIMARY_RAW=None
MAIN_PRIMARY_TB=None
PRIVATE_ACCOUNT_RAW=[]
expected_owner=None
account_api=None
control=None
grant=None
started=None
ENV=os.environ.copy()
ENV['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
docker=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock']


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

def durable_capture():
 for path in OUT.iterdir():
  if path.is_file():
   fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
   try:os.fsync(fd)
   finally:os.close(fd)
 fd=os.open(str(OUT),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
 try:os.fsync(fd)
 finally:os.close(fd)


# Keep the existing save body and call algorithm; make every attempt/returned
# handle receipt durable before its next operation, including birth sampling.

def save(name,value):
 global sequence
 assert OUT is not None and re.fullmatch(r'[A-Za-z0-9_.-]+',name), 'capture name'
 sequence+=1
 target=OUT/name
 temp=OUT/(name+'.tmp.'+str(os.getpid())+'.'+str(sequence))
 with temp.open('x',encoding='utf-8') as stream:
  json.dump(value,stream,indent=2,sort_keys=True)
  stream.write('\n');stream.flush();os.fsync(stream.fileno())
 os.replace(str(temp),str(target))
 durable_capture()


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

def arguments():
 parser=argparse.ArgumentParser()
 for name in ('request-sha256','operation-review','operation-review-sha256','admission','admission-sha256','operation-sha256'):
  parser.add_argument('--'+name,required=True)
 args=parser.parse_args()
 for value in (args.request_sha256,args.operation_review_sha256,args.admission_sha256,args.operation_sha256):
  assert re.fullmatch('[0-9a-f]{64}',value), 'SHA input'
 return args


def source_ref(path,digest):
 return {'path':str(pathlib.Path(path).resolve()),'sha256':digest}


def runtime_profile():
 assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000, 'actual1000 actor'
 assert os.sched_getaffinity(0)=={7}, 'actual HOSTCPU7'
 assert list(resource.getrlimit(resource.RLIMIT_AS))==[-1,-1], 'privileged DockerCLI parent AS must remain infinity'
 assert list(resource.getrlimit(resource.RLIMIT_CORE))==[0,0], 'HOST core0'
 assert list(resource.getrlimit(resource.RLIMIT_FSIZE))==[67108864,67108864], 'HOST fsize64MiB'
 assert list(resource.getrlimit(resource.RLIMIT_NOFILE))==[512,512], 'HOST nofile512'
 assert list(resource.getrlimit(resource.RLIMIT_CPU))==[-1,-1], 'unchanged HOST CPU rlimit'


def load_request(args,kind):
 global control,grant
 runtime_profile()
 control=read_json_ref({'path':str(HERE/'REQUEST.json'),'sha256':args.request_sha256})
 assert control['schema']=='mckernel.m15.f08.minimum-genuine-context-host-request.v1'
 own=control['sources'][kind];assert own['path']==str(pathlib.Path(__file__).resolve());pin(own)
 assert control['invocation']==INVOCATION and control['Root_thread_id']==ROOT_ID
 for ref in control['sources'].values():pin(ref)
 profile=read_json_ref(control['profile'])
 expected_context=read_json_ref(control['expected_context'])
 review_ref=source_ref(args.operation_review,args.operation_review_sha256);review=read_json_ref(review_ref)
 assert review['schema']=='mckernel.M15-F08.minimum-context-independent-operation-review.v1'
 assert review['reviewer'].startswith('/root/functional_delta_review;')
 assert review['decision']=='GO_F08_MINIMUM_GENUINE_CONTEXT_HOST_OPERATION'
 expected={'request_sha256':args.request_sha256,'parent_sha256':control['sources']['parent']['sha256'],
  'outer_sha256':control['sources']['outer']['sha256'],'profile_sha256':control['profile']['sha256'],
  'inside_caller_sha256':control['inside_caller']['sha256'],'inside_owner_sha256':control['inside_owner']['sha256'],
  'pidfd_helper_sha256':control['pidfd_helper']['sha256'],'publisher_guard_sha256':control['publisher_guard']['sha256'],
  'expected_context_sha256':control['expected_context']['sha256'],'source_contract_sha256':control['source_contract']['sha256'],
  'conditional_profile_scope_review_sha256':control['conditional_profile_scope_review']['sha256']}
 assert review['approved']==expected
 grant_ref=source_ref(args.admission,args.admission_sha256);grant=read_json_ref(grant_ref)
 assert set(grant)==set(control['admission_fields']), 'complete real parent/outer field union'
 assert grant['schema']=='mckernel.Root-current-HOST-admission.f08-minimum-genuine-context.v1'
 assert grant['invocation']==INVOCATION and grant['Root_thread_id']==ROOT_ID and grant['same_Root_finite_credit_run_id']==CREDIT_RUN
 assert grant['request_sha256']==args.request_sha256 and grant['approved']==expected and grant['operation_review_ref']==review_ref
 assert grant['profile_sha256']==control['profile']['sha256'] and grant['operation_seed_sha256']==args.operation_sha256
 assert grant['account_consumer_ref']==control['account_consumer_ref'] and grant['current_owner_private_ref']==control['current_owner_private_ref']
 assert grant['source_view_verified'] is True and grant['complete_owner_accounting'] is True and grant['native_and_historical_unknowns_preserved'] is True
 assert grant['no_exclusive_other_owner_scope'] is True and grant['host_boot_id']==pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 assert grant['charge']==control['charge']
 jobs=grant['current_HOST_jobs_before'];other=grant['other_current_HOST_payload_reserved_bytes'];overhead=grant['current_owned_controller_worker_overhead_bytes']
 assert type(jobs) is int and 0<=jobs<3 and type(other) is int and other>=0 and type(overhead) is int and overhead>=0
 assert jobs+1<=3 and other+overhead+control['charge']['planning_bytes']<=4*GIB
 for key in ('MemAvailable_bytes','host_free_bytes','scratch_free_bytes'):
  assert type(grant[key]) is int and grant[key]>=0
 assert grant['MemAvailable_bytes']>=26*GIB and grant['host_free_bytes']>=17*GIB and grant['scratch_free_bytes']>=13*GIB
 assert 0<=(time.time_ns()-grant['issued_utc_ns'])/1e9<=60 and 0<=(time.monotonic_ns()-grant['issued_mono_ns'])/1e9<=60
 for name in ('current_owner_validation_ref','scoped_resource_evidence_ref','retained_owner_dispositions_ref','source_custody_and_actual_permission_checks_ref','provider_lifetime_owner_ref'):
  pin(grant[name])
 assert isinstance(grant['allowed_running_container_ids'],list) and all(re.fullmatch('[0-9a-f]{64}',x) for x in grant['allowed_running_container_ids'])
 seed_ref=dict(control['operation_seed_inputs']);seed_ref['sha256']=args.operation_sha256
 seed=read_json_ref(seed_ref)
 assert set(seed)==set(control['operation_seed_template']), 'closed Root seed fields'
 for key,value in control['operation_seed_template'].items():
  if key not in ('nonce','provider_input_guard'):assert seed[key]==value, 'fixed seed field differs: '+key
 assert type(seed['nonce']) is str and re.fullmatch('[0-9a-f]{64}',seed['nonce']) and seed['nonce']==grant['operation_nonce']
 g=seed['provider_input_guard']
 assert type(g) is dict and set(g)==set(control['provider_input_guard_fields'])
 assert g['schema']=='mckernel.m15.f08.Root-genuine-context-input-guard.v1'
 assert g['Root_thread_id']==ROOT_ID and g['invocation']==INVOCATION and g['operation_nonce']==seed['nonce']
 assert g['profile_sha256']==control['profile']['sha256'] and g['expected_context_sha256']==control['expected_context']['sha256']
 assert g['source_permission_ref']==grant['source_custody_and_actual_permission_checks_ref'] and g['provider_lifetime_owner_ref']==grant['provider_lifetime_owner_ref']
 for name in ('source_permission_ref','provider_lifetime_owner_ref'):
  assert set(g[name])=={'path','bytes','sha256'} and type(g[name]['bytes']) is int and g[name]['bytes']>0
 assert type(g['issued_utc_ns']) is int and type(g['issued_mono_ns']) is int and g['expires_after_seconds']==300
 assert 0<=(time.time_ns()-g['issued_utc_ns'])/1e9<=60 and 0<=(time.monotonic_ns()-g['issued_mono_ns'])/1e9<=60
 permission=read_json_ref(g['source_permission_ref'])
 assert permission['schema']=='mckernel.m15.f08.Root-actual-minimum-context-permission.v1'
 assert permission['Root_thread_id']==ROOT_ID and permission['operation_nonce']==seed['nonce']
 assert permission['request_sha256']==args.request_sha256 and permission['profile_sha256']==control['profile']['sha256']
 assert permission['expected_context_sha256']==control['expected_context']['sha256'] and permission['operator_role']=='Root_WORKSTATION_RUNTIME_OPERATOR'
 assert permission['route']=='existing_local_Docker_host_network_plus_exact_RO_udev_control'
 for name in ('sudo_A_specific_metadata_guard_read_permitted','new_hostnet_and_one_socket_bind_permitted','all_other_profile_scope_unchanged'):
  assert permission[name] is True
 owner=read_json_ref(g['provider_lifetime_owner_ref'])
 assert owner['schema']=='mckernel.m15.f08.Root-existing-provider-lifetime-owner.v1'
 assert owner['Root_thread_id']==ROOT_ID and owner['operation_nonce']==seed['nonce'] and owner['expected_context_sha256']==control['expected_context']['sha256']
 assert owner['operator_role']=='Root_WORKSTATION_RUNTIME_OPERATOR'
 assert owner['existing_service_tuple_lifetime_owned_for_case'] is True and owner['no_service_or_namespace_mutation'] is True
 control['actual_seed_ref']=seed_ref;control['actual_review_ref']=review_ref;control['actual_grant_ref']=grant_ref
 control['loaded_expected_context']=expected_context
 return profile,seed


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

def account_guard():
 try:
  state_guard()
  _,usage,credit,_=account_api['current_account_snapshot'](expected_owner)
  del credit
  return {'source_kind':usage['source_kind'],'source_event':usage['source_event'],
          'receipt_received_utc_ns':usage['receipt_received_utc_ns'],
          'receipt_received_mono_ns':usage['receipt_received_mono_ns']}
 except BaseException as error:
  PRIVATE_ACCOUNT_RAW.append((error,BaseException.__dict__['__traceback__'].__get__(error,type(error))))
  raise RuntimeError('current private account/owner guard failed; raw private exception retained in memory') from None


def current_resources(fresh=False):
 available=next(int(line.split()[1])*1024 for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
 host=shutil.disk_usage(ROOT).free
 scratch=shutil.disk_usage('/home/holden/mckernel-work/scratch').free
 assert available>=(26 if fresh else 22)*GIB, 'HOST available floor'
 assert host>=(17 if fresh else 16)*GIB and scratch>=(13 if fresh else 12)*GIB, 'HOST/scratch disk floors'
 return {'MemAvailable_bytes':available,'host_free_bytes':host,'scratch_free_bytes':scratch}


def initialize_account():
 global account_api,expected_owner
 account_code=pin(control['account_consumer_ref'],True)
 account_api={'__name__':'mckernel_current_root_account_consumer','__file__':control['account_consumer_ref']['path']}
 exec(compile(account_code,control['account_consumer_ref']['path'],'exec'),account_api)
 expected_owner=read_json_ref(control['current_owner_private_ref'])
 assert expected_owner['thread_id']==ROOT_ID
 return account_guard()


def guard():
 usage=account_guard()
 resources=current_resources()
 pin_bookend()
 return usage,resources


def initialize_call():
 helper=control['E088']
 exec(compile(pin(helper,True),helper['path'],'exec'),globals())


def positive_clients():
 assert not pending_calls, 'original direct calls remain pending'
 for row in clients:
  assert row['direct_wait_joined'] is True and row['streams_closed'] is True and row['exit']==0
  assert row['birth'] and row['birth'].isdigit() and int(row['birth'])>0
  assert row['lifecycle_UNKNOWN'] is False and row['resource_charge_retained'] is False and row['receipt_persisted'] is True
  assert row['primary_error'] is None and row['secondary_errors']==[]


def close_inputs():
 errors=[]
 for item in held.values():
  try:os.close(item['fd'])
  except BaseException as error:errors.append((error,BaseException.__dict__['__traceback__'].__get__(error,type(error))))
 assert not errors, 'held input close failed; raw close errors remain in traceback locals'


def main():
 global OUT,started,MAIN_PRIMARY_RAW,MAIN_PRIMARY_TB
 args=arguments()
 os.umask(0o077)
 try:
  profile,seed=load_request(args,'outer')
  usage=initialize_account()
  resources=current_resources(fresh=True)
  execution=pathlib.Path(control['paths']['execution_root'])
  assert execution.parent==HERE and not execution.exists(), 'fresh execution namespace; no replay'
  execution.mkdir(mode=0o700)
  OUT=pathlib.Path(control['paths']['outer_output']);OUT.mkdir(mode=0o700)
  initialize_call();started=now()
  save('ADMISSION.json',{'at':started,'request_sha256':args.request_sha256,
    'review_ref':control['actual_review_ref'],'grant_ref':control['actual_grant_ref'],
    'seed_ref':control['actual_seed_ref'],'current_account_receipt':usage,'resources':resources,
    'charge_is_external':True,'resource_or_native_or_acceptance_release':False})
  argv=['/usr/bin/python3','-I','-B',control['sources']['parent']['path'],
    '--request-sha256',args.request_sha256,'--operation-review',args.operation_review,
    '--operation-review-sha256',args.operation_review_sha256,'--admission',args.admission,
    '--admission-sha256',args.admission_sha256,'--operation-sha256',args.operation_sha256]
  save('ACTUAL-PARENT-ARGV.json',{'argv':argv,'parent_ref':control['sources']['parent']})
  call('f08-protected-parent',argv,timeout=control['limits']['outer_nominal_seconds'])
  positive_clients();guard()
  parent_result_path=pathlib.Path(control['paths']['parent_output'])/'RESULT.json'
  st=parent_result_path.lstat()
  assert stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode) and 0<st.st_size<=16777216
  raw=parent_result_path.read_bytes();assert identity(st)==identity(parent_result_path.lstat())
  result=json.loads(raw)
  assert result['status']=='PASS_F08_ONE_REAL_MAIN_SCENARIO_PENDING_OUTER_ROOT_WAIT_AND_INDEPENDENT_QUALIFICATION'
  assert result['request_sha256']==args.request_sha256 and result['operation_nonce']==seed['nonce']
  assert result['seed_ref']['sha256']==args.operation_sha256
  assert result['actual_monitor_protocol15_group2'] is True
  sealed=read_json_ref(result['operation_ref'])
  assert sealed['nonce']==seed['nonce'] and sealed['provider_context']['static']==control['loaded_expected_context']
  assert result['provider_context_before']['proof']['observed']==result['provider_context_after']['proof']['observed']==control['loaded_expected_context']['observed_tuple']
  assert result['all_original_direct_waits_streams_positive'] is True and result['terminal_exit']==0
  assert result['OOMKilled'] is False and result['terminal_Pid']==0
  assert result['container_wait0'] is True and result['owned_nonforce_removed'] is True and result['exact_ID_absent'] is True
  assert result['whole_F08_or_milestone_acceptance'] is False
  save('RESULT.json',{'status':'PASS_F08_PARENT_AND_ORIGINAL_HOST_WAITS_PENDING_ACTUAL_FULL_ROOT_TOOL_AND_REVIEW',
    'started_at':started,'finished_at':now(),'request_sha256':args.request_sha256,'operation_nonce':seed['nonce'],
    'parent_result_ref':{'path':str(parent_result_path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},
    'original_parent_direct_wait':clients[0],'all_original_clients_waited_streams_closed':True,
    'actual_full_Root_tool_result':'EXTERNAL_REQUIRED_AFTER_THIS_PROCESS_EXITS',
    'resource_retirement':'NONE_BY_OUTER','whole_F08_or_milestone_acceptance':False})
  pin_bookend();close_inputs();durable_capture()
  return 0
 except BaseException as error:
  MAIN_PRIMARY_RAW=error
  MAIN_PRIMARY_TB=BaseException.__dict__['__traceback__'].__get__(error,type(error))
  try:keeper_record('UNKNOWN-OUTER.json',{'status':'FAILED_OR_UNKNOWN_RETAIN_ORIGINAL_PARENT_FAMILY_AND_CHARGE',
     'at':now(),'error_type':type(error).__name__,'error':str(error),
     'traceback':''.join(traceback.format_exception(type(error),error,MAIN_PRIMARY_TB)),
     'pending_original_attempts':list(pending_calls),'resource_release':False})
  except BaseException as capture_error:retain_outer_error('F08-outer-report',capture_error)
  # The exact qualified entry boundary waits every original Popen; it cannot
  # replace/kill a hung owning parent or infer that any container disappeared.
  return 1


if __name__=='__main__':sys.exit(entry_once_with_original_custody())


