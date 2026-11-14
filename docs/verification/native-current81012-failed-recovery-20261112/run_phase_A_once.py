import ast,datetime,hashlib,json,os,pathlib,resource,shutil,signal,stat,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');HERE=pathlib.Path(__file__).parent;OUT=HERE/'execution-1'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(n,v):(OUT/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def verify(v):
 p=pathlib.Path(v['path']);assert p.is_file() and p.stat().st_size==v['bytes'] and sha(p)==v['sha256'],str(p)
def select_functions(path,names):
 source=pathlib.Path(path).read_text();tree=ast.parse(source);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];assert {n.name for n in nodes}==set(names);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),globals())
clients=[];pending_calls={};keeper_capture_errors=[];OUTER_RETENTION_ERRORS=[];OUTER_ORIGINAL_WAITS=[]
REQUEST_SHA='733c7d7c82a40f3dfe6772ce7ff3ea89f2c0f9b2e924e294684ffc14c7847f2d'
CALL_SOURCE='/home/holden/mckernel-work/m14-blocker-resolution-20261110/joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py';CALL_SHA='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4'
KEEPER_SOURCE='/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-runtime-native-outer-capture-publicabi-max-1/correction-1/run_root_once.py';KEEPER_SHA='1f668620d63bf7ab4a4b86ee6c8d2128b96d59d4e19c4d0601ab2dc894870657'
GUARD_SOURCE='/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';GUARD_SHA='983b8c3ceabcd8dc4d2e1999d75e6edbef91145a5f2ab18bfa1a2dfa6639c822'
def main():
 assert sha(HERE/'REQUEST.PHASE-A.json')==REQUEST_SHA
 assert len(sys.argv)==5
 review=pathlib.Path(sys.argv[1]);review_sha=sys.argv[2];admission=pathlib.Path(sys.argv[3]);admission_sha=sys.argv[4]
 assert sha(review)==review_sha and json.loads(review.read_text())['decision'].startswith('GO') and sha(admission)==admission_sha
 q=json.loads((HERE/'REQUEST.PHASE-A.json').read_text());a=json.loads(admission.read_text())
 verify(q['inputs']);inputs=json.loads(pathlib.Path(q['inputs']['path']).read_text())
 for r in inputs['files']+[inputs['interpreter']]:verify(r)
 assert resource.getrlimit(resource.RLIMIT_AS)==(134217728,134217728) and resource.getrlimit(resource.RLIMIT_FSIZE)==(8388608,8388608) and os.sched_getaffinity(0)=={0}
 assert set(a)==set(q['required_parent_actor_admission_keys']) and a['request_sha256']==REQUEST_SHA and a['review_sha256']==review_sha and a['phase']=='A'
 assert a['saved_Root']=='01a18bc3-e072-7810-9426-75101b0856c0' and a['invocation']=='20261112T094452Z-12a4bea0' and a['same_Root_finite_credit_run_id']=='7c6ef3604bfb4008a917bba8cfb6cfaa'
 assert a['schema']==q['fresh_admission_schema'] and a['complete_parent_actor_profile']==q['profile'] and a['action_scope']==q['action_scope'] and a['signal_number']==15 and a['target_pid']==1930708 and a['target_birth']=='58283682' and a['sudo_pid']==1930695 and a['sudo_birth']=='58283676' and a['original_tool_session']==81012
 assert a['actual_current_account_result']=='ACCEPTED' and 0<=time.time()-datetime.datetime.fromisoformat(a['at']).timestamp()<=25 and type(a['issued_monotonic_ns']) is int and 0<=time.monotonic_ns()-a['issued_monotonic_ns']<=25*10**9
 for key in ['actual_current_account_ref','actual_source_permission_resource_ref']:verify(a[key])
 assert a['new_current_family_bytes']==268435456 and a['new_current_jobs']==1 and type(a['current_HOST_jobs_before']) is int and 0<=a['current_HOST_jobs_before']<3
 assert a['current_HOST_payload_reserved_bytes_before']>=1610612736 and a['controller_worker_overhead_bytes']>=0 and a['controller_worker_overhead_bytes']+a['current_HOST_payload_reserved_bytes_before']+268435456<=4*2**30 and a['MemAvailable_bytes']>=26*2**30 and a['host_free_bytes']>=16*2**30+67108864 and a['scratch_free_bytes']>=12*2**30+67108864
 assert a['host_boot_id']=='3ba4f2ca-4323-433d-bfb8-7859268121b6' and a['original_runtime_source_native1_5GiB_native12_and_all_UNKNOWNs_retained'] is True and a['no_C_runtime_restoration_native_reissue_or_resource_release_grant'] is True
 assert not OUT.exists();OUT.mkdir(mode=0o700)
 global ENV;ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
 try:
  assert sha(CALL_SOURCE)==CALL_SHA;select_functions(CALL_SOURCE,['call']);assert sha(GUARD_SOURCE)==GUARD_SHA;select_functions(GUARD_SOURCE,['guard','overhead']);guard()
  available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
  assert available>=26*2**30 and shutil.disk_usage(ROOT).free>=16*2**30+67108864 and shutil.disk_usage(HERE).free>=12*2**30+67108864
  verify(q['helper']);literal=pathlib.Path(q['helper']['path']).read_text();argv=q['Root_command_prefix']+[literal,'A',str(HERE/'REQUEST.PHASE-A.json'),REQUEST_SHA,str(review),review_sha,str(admission),admission_sha]
  assert all(type(x) is str and '\x00' not in x and len(x.encode())+1<131072 for x in argv) and sum(len(x.encode())+1 for x in argv)+65536<131072
  guard();raw=call('exact-current81012-failed-provider-phase-A',argv,timeout=q['root_actor_timeout_seconds']);value=json.loads(raw)
  assert value['status']==q['expected_phaseA_status'] and value['provider_pid']==1930708 and value['birth']=='58283682' and value['signal']==15 and value['pidfd_terminal_observed'] is True and value['original_tool_session']==81012
  assert value['original_sudo_direct_wait_or_streams_proven'] is False and value['runtime_flags_changed'] is False and value['FLOCK_acquired'] is False and value['original_supervisor_waitpid_called'] is False and value['native_or_runtime_or_resource_release'] is False
  assert value['all_new_actor_own_FDs_closed'] and value['new_actor_close_errors']==0 and value['remaining_new_actor_direct_children']==[]
  assert len(clients)==1 and not pending_calls and not pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
  rec=clients[0];assert rec['exit']==0 and rec['direct_wait_joined'] and rec['streams_closed'] and rec['receipt_persisted'] and not rec['secondary_errors'] and not rec['lifecycle_UNKNOWN'] and not rec['resource_charge_retained']
  assert (OUT/'exact-current81012-failed-provider-phase-A.stderr').read_bytes()==b''
  save('PHASE-A-RESULT.json',value);save('RESULT.json',dict(status='PHASE_A_EXACT_PIDFD_OBSERVED_ORIGINAL81012_B_JOINS_AND_SEPARATE_C_PENDING',request_sha256=REQUEST_SHA,review_sha256=review_sha,clients=clients,phaseA=value,original_tool81012_owned_join_required=True,runtime_source_native12_original1_5GiB_and_historical_UNKNOWN_retained=True,any_resource_release=False));print(json.dumps(dict(status='PHASE_A_ONLY_CAPTURED_ORIGINAL81012_B_AND_SEPARATE_C_PENDING',at=now())))
 except BaseException as error:
  primary=error;tb=error.__traceback__
  try:save('RESULT.json',dict(status='PHASE_A_FAILED_OR_UNKNOWN_NO_REPLAY',error_type=type(error).__name__,error=str(error),traceback=''.join(traceback.format_exception(type(error),error,tb)),clients=clients,all_original_native_runtime_source_unknowns_retained=True,any_resource_release=False))
  except BaseException:pass
  raise BaseException.with_traceback(primary,tb)
if __name__=='__main__':
 assert sha(KEEPER_SOURCE)==KEEPER_SHA
 select_functions(KEEPER_SOURCE,['keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody'])
 entry_once_with_original_custody()
