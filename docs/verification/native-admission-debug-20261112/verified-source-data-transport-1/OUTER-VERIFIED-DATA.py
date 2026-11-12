import ast,datetime,hashlib,json,os,pathlib,resource,shutil,signal,stat,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel')
M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110')
HERE=pathlib.Path(__file__).parent
OUT=HERE/'execution-1'
common=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py'
assert hashlib.sha256(common.read_bytes()).hexdigest()=='e6091bb418f619222f7a51ddef718ceeb75bb449f5abd10d62b40018b623db38'
tree=ast.parse(common.read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save')],type_ignores=[]),str(common),'exec'))
old=M/'f06-default-wiring-p04source-max-1/default-observation-1/run_root_once.py'
assert sha(old)=='5695c81f42964567652b3a4c0a8ea0c009bc98eb1918ed765c8af88e27ae5f35'
tree=ast.parse(old.read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pins'],type_ignores=[]),str(old),'exec'))
shared=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py')
assert sha(shared)=='983b8c3ceabcd8dc4d2e1999d75e6edbef91145a5f2ab18bfa1a2dfa6639c822'
tree=ast.parse(shared.read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='guard'],type_ignores=[]),str(shared),'exec'))
cap=M/'joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py'
assert sha(cap)=='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4'
exec(compile(cap.read_text(),str(cap),'exec'))
ENV=os.environ.copy()
ENV['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
clients=[]
pending_calls={}
started=now()
keeper_capture_errors=[]


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
base_save=save
def save(name,value):
 base_save(name,value)
 durable_capture()


def read_private_json(path,expected_sha,limit):
 p=pathlib.Path(path)
 st=p.lstat()
 assert stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode)
 assert st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1 and 0<st.st_size<=limit
 raw=p.read_bytes()
 after=p.lstat()
 assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
 assert hashlib.sha256(raw).hexdigest()==expected_sha
 return json.loads(raw),dict(path=str(p),sha256=expected_sha,device=st.st_dev,inode=st.st_ino,size=st.st_size)


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


def main():
 os.umask(0o077)
 assert not os.path.lexists(OUT)
 OUT.mkdir(mode=0o700,exist_ok=False)
 primary=None
 primary_tb=None
 outcome=None
 try:
  assert len(sys.argv)==7
  assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
  assert resource.getrlimit(resource.RLIMIT_AS)==(268435456,268435456)
  assert resource.getrlimit(resource.RLIMIT_FSIZE)==(67108864,67108864)
  assert resource.getrlimit(resource.RLIMIT_NOFILE)==(512,512) and resource.getrlimit(resource.RLIMIT_CORE)==(0,0)
  qpath=HERE/'REQUEST.json'
  assert sha(qpath)=='b954f12416afc468a264357a21a5eea532c26564aed77b4d1622bc06f79fba05'
  q=json.loads(qpath.read_text())
  review_path=pathlib.Path(sys.argv[1])
  assert sha(review_path)==sys.argv[2]
  review=json.loads(review_path.read_text())
  assert review['decision'].startswith('GO')
  pins(q['immutable_inputs'])
  stamp=guard()
  admission,admission_identity=read_private_json(sys.argv[3],sys.argv[4],262144)
  assert admission['request_sha256']==sha(qpath)
  assert admission['invocation']=='20261111T223223Z-fb7f73db'
  assert admission['same_Root_finite_credit_run_id']=='7c6ef3604bfb4008a917bba8cfb6cfaa'
  age=time.time()-datetime.datetime.fromisoformat(admission['at']).timestamp()
  assert 0<=age<=25
  assert admission['existing_9032_current_owner_account_result']=='ACCEPTED'
  pins(admission['current_owner_validation_ref'])
  assert admission['current_source_runtime_and_native_operation_review_sha256']==q['provider_review']['sha256']
  assert admission['source_custody_and_actual_permission_checks_ref']['sha256']
  pins(admission['source_custody_and_actual_permission_checks_ref'])
  jobs=admission['current_HOST_jobs_before']
  overhead=admission['current_owned_controller_worker_overhead_bytes']
  other=admission['other_current_HOST_payload_reserved_bytes']
  assert type(jobs) is int and 0<=jobs<3 and type(overhead) is int and overhead>=0 and type(other) is int and other>=0
  assert overhead+other+q['combined_current_HOST_family_planning_bytes']<=4*2**30
  available=int(next(line.split()[1] for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
  host=shutil.disk_usage(ROOT).free
  scratch=shutil.disk_usage('/home/holden/mckernel-work/scratch').free
  assert available>=26*2**30
  assert host>=16*2**30+q['capture_disk_growth_budget_bytes'] and scratch>=12*2**30+q['capture_disk_growth_budget_bytes']
  askpass=pathlib.Path(ENV['SUDO_ASKPASS'])
  hs=askpass.lstat()
  assert stat.S_ISREG(hs.st_mode) and not stat.S_ISLNK(hs.st_mode) and os.access(askpass,os.X_OK)
  assert shutil.which('sudo',path=ENV['PATH'])=='/usr/bin/sudo'
  template=json.loads(pathlib.Path(q['reviewed_argv_template']['path']).read_text())['argv']
  actual,argv_identity=read_private_json(sys.argv[5],sys.argv[6],1048576)
  argv=actual['argv']
  assert type(argv) is list and len(argv)==len(template)
  assert all(type(value) is str and '\x00' not in value and len(value.encode())+1<131072 for value in argv)
  slots=set(q['actual_unissued_argument_indices'])
  assert all(argv[index]==value for index,value in enumerate(template) if index not in slots)
  assert {str(index):argv[index] for index in sorted(slots)}==admission['actual_argument_values']
  argv_bytes=sum(len(value.encode())+1 for value in argv)
  # sudo1.8.31 also joins command arguments into one SUDO_COMMAND value.
  # Bound the WHOLE source-light command, not only individual source strings.
  assert argv_bytes+q['aggregate_exec_environment_reserve_bytes']<q['aggregate_exec_transport_max_bytes']
  assert argv_bytes+65536<os.sysconf('SC_ARG_MAX')
  # This is the only executable route. No shlex.join, shell=True or giant
  # exec_command.cmd string; Popen receives the actual SHA-bound list directly.
  save('EXACT-ARGV.PRIVATE.json',dict(argv=argv,source_template=q['reviewed_argv_template'],verified_byte_source_transport=q['verified_byte_source_transport'],argv_bytes_including_NUL=argv_bytes,actual_json_identity=argv_identity))
  save('ADMISSION.json',dict(at=now(),source_request_sha256=sha(qpath),review_sha256=sys.argv[2],actual_admission=admission_identity,guard_updated_at=stamp,age_seconds=age,current_HOST_jobs_before=jobs,actual_owned_overhead_bytes=overhead,other_current_reserved_bytes=other,new_combined_family_planning_bytes=q['combined_current_HOST_family_planning_bytes'],MemAvailable_bytes=available,host_free_bytes=host,scratch_free_bytes=scratch,native_pool_static_capacity_not_operation_claim=True,actual_native_input_and_caps_are_Root_materialization_outputs=True))
  try:
   raw=call('native-runtime-provider',argv,timeout=q['outer_initial_wait_seconds'])
  except BaseException as error:
   primary=error;primary_tb=error.__traceback__
   save('ORIGINAL-CALL-FAILURE.json',dict(at=now(),error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),clients=clients,pending_original_attempts=list(pending_calls),no_kill_fallback_or_replay=True))
   preserve_original_pending_waits()
   raw=(OUT/'native-runtime-provider.stdout').read_bytes()
  assert len(raw)<=q['max_raw_stdout_bytes'] and (OUT/'native-runtime-provider.stderr').stat().st_size<=q['max_raw_stderr_bytes']
  reports=[];publisher_reports=[]
  for line in raw.splitlines():
   try:row=json.loads(line)
   except (ValueError,UnicodeDecodeError):continue
   if type(row) is dict and set(row)=={'status','runtime','original_flags','native_functional_exit','native_pool_or_history_release'} and row['status']=='CLOSED_RESTORED':reports.append(row)
   if type(row) is dict and row.get('status')==q['publisher_final_status']:publisher_reports.append(row)
  assert len(clients)==1 and not pending_calls
  client=clients[0]
  actual_exit=client.get('late_original_exit',client['exit'])
  report=reports[0] if len(reports)==1 else None
  publisher_report=publisher_reports[0] if len(publisher_reports)==1 else None
  matching_report=bool(report and report['runtime']=='/usr/bin/python3.8' and report['original_flags']==524288 and type(report['native_functional_exit']) is int and report['native_functional_exit'] in (0,2) and report['native_pool_or_history_release'] is False and actual_exit==report['native_functional_exit'] and publisher_report and type(publisher_report.get('provider_exit')) is int and publisher_report['provider_exit']==actual_exit and publisher_report.get('native_grant_from_DATA') is False and publisher_report.get('native_nonce_or_watchdog_generated_by_publisher') is False)
  remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
  assert not remaining
  # Raw report/status is DATA. Real Root/runtime/native journals and every
  # owned family still need independent actual-result qualification.
  outcome=dict(status='CAPTURED_PROVIDER_RESTORATION_DATA_PENDING_INDEPENDENT_ROOT_NATIVE_QUALIFICATION' if matching_report else 'FAILED_OR_UNKNOWN_PROVIDER_PRESERVED_PENDING_OWNING_ROOT_DISPOSITION',at=now(),started_at=started,source_request_sha256=sha(qpath),clients=clients,provider_report=report,publisher_report=publisher_report,provider_report_matches_exit=matching_report,actual_provider_exit=actual_exit,original_capture_error_preserved=primary is not None,keeper_capture_errors=[dict(label=label,error_type=type(error).__name__,error=str(error),traceback=''.join(traceback.format_exception(type(error),error,tb))) for label,error,tb in keeper_capture_errors],remaining_original_direct_children=remaining,provider_stdout_sha256=sha(OUT/'native-runtime-provider.stdout'),provider_stderr_sha256=sha(OUT/'native-runtime-provider.stderr'),native_or_runtime_or_source_or_historical_release_from_outer=False,application_acceptance=False)
  save('RESULT.json',outcome)
  save('RESOURCE-DISPOSITION.json',dict(at=now(),outer_original_foreground_wait_and_stream_evidence=clients,current_charge_and_job='RETAINED_UNTIL_FULL_ORIGINAL_ROOT_TOOL_AND_INDEPENDENT_CURRENT_NATIVE_RUNTIME_SOURCE_QUALIFICATION',native_pool_and_all_historical_UNKNOWN='UNCHANGED',no_status_dictionary_is_a_grant=True))
  durable_capture()
 except BaseException as error:
  if primary is None:primary=error;primary_tb=error.__traceback__
  else:
   try:save('SECONDARY-CAPTURE-FAILURE.json',dict(at=now(),error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc()))
   except BaseException:pass
  # If a direct keeper is live, this parent must not exit and orphan its
  # original wait ownership merely because capture/persistence failed.
  preserve_original_pending_waits()
  try:
   save('RESULT.json',dict(status='FAILED_CAPTURE_PRESERVED_NO_REPLAY',at=now(),started_at=started,error_type=type(primary).__name__,error=str(primary),traceback=''.join(traceback.format_exception(type(primary),primary,primary_tb)),clients=clients,pending_original_attempts=list(pending_calls),native_and_runtime_and_historical_outcomes='UNCHANGED_OR_UNKNOWN'))
   durable_capture()
  except BaseException:
   while True:
    try:signal.pause()
    except BaseException:pass
 if primary is not None:
  # Preserve actual exit2 as a failed functional outcome. It is never changed
  # to successful application execution or a native pool release.
  expected_two=bool(outcome and outcome['provider_report_matches_exit'] and outcome['actual_provider_exit']==2 and type(primary) is AssertionError and primary.args==(('native-runtime-provider',2),))
  if expected_two:return 2
  raise primary.with_traceback(primary_tb)
 assert outcome and outcome['provider_report_matches_exit']
 return outcome['actual_provider_exit']


# Outermost raw exception and direct-handle custody. These are observations,
# never replacement handles, resource grants or automatic native retirement.
OUTER_RETENTION_ERRORS = []
OUTER_ORIGINAL_WAITS = []


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


if __name__=='__main__':sys.exit(entry_once_with_original_custody())
