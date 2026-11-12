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
REQUEST_SHA='41f8db007b21fce66a41f7b39cb9c218b82d28d90dfe70649dd0f9ff7c3df035'
CALL_SOURCE='/home/holden/mckernel-work/m14-blocker-resolution-20261110/joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py';CALL_SHA='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4'
KEEPER_SOURCE='/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-runtime-native-outer-capture-publicabi-max-1/correction-1/run_root_once.py';KEEPER_SHA='1f668620d63bf7ab4a4b86ee6c8d2128b96d59d4e19c4d0601ab2dc894870657'
GUARD_SOURCE='/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';GUARD_SHA='983b8c3ceabcd8dc4d2e1999d75e6edbef91145a5f2ab18bfa1a2dfa6639c822'
def main():
 assert sha(HERE/'REQUEST.PHASE-C.json')==REQUEST_SHA
 assert len(sys.argv)==5
 review=pathlib.Path(sys.argv[1]);review_sha=sys.argv[2];admission=pathlib.Path(sys.argv[3]);admission_sha=sys.argv[4]
 assert sha(review)==review_sha and json.loads(review.read_text())['decision'].startswith('GO')
 assert sha(admission)==admission_sha
 q=json.loads((HERE/'REQUEST.PHASE-C.json').read_text());a=json.loads(admission.read_text())
 verify(q['inputs']);inputs=json.loads(pathlib.Path(q['inputs']['path']).read_text())
 for r in inputs['files']+[inputs['interpreter']]:verify(r)
 assert resource.getrlimit(resource.RLIMIT_AS)==(134217728,134217728) and resource.getrlimit(resource.RLIMIT_FSIZE)==(8388608,8388608) and os.sched_getaffinity(0)=={0}
 assert a['request_sha256']==REQUEST_SHA and a['review_sha256']==review_sha and a['phase']=='C' and a['standing_authority_instruction_source']==q['standing_authority_instruction_source'] and a['authority_scope_receipt_sha256']==q['authority_scope_receipt']['sha256']
 assert a['existing_9032_current_owner_account_result']=='ACCEPTED' and 0<=time.time()-datetime.datetime.fromisoformat(a['at']).timestamp()<=25
 assert a['current_owned_controller_worker_overhead_bytes']+a['other_current_HOST_payload_reserved_bytes']+q['family_planning_bytes']<=4*2**30 and a['current_HOST_jobs_before']<3 and a['MemAvailable_bytes']>=26*2**30
 assert not OUT.exists();OUT.mkdir(mode=0o700)
 global ENV;ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
 try:
  assert sha(CALL_SOURCE)==CALL_SHA;select_functions(CALL_SOURCE,['call']);assert sha(GUARD_SOURCE)==GUARD_SHA;select_functions(GUARD_SOURCE,['guard','overhead']);guard()
  # Qualified source validator controls are reused at their unchanged scope; do not replay.
  verify(q['helper']);literal=pathlib.Path(q['helper']['path']).read_text();argv=q['Root_command_prefix']+[literal,'C',str(HERE/'REQUEST.PHASE-C.json'),REQUEST_SHA,str(review),review_sha,str(admission),admission_sha]
  assert all(type(x) is str and '\x00' not in x and len(x.encode())+1<131072 for x in argv) and sum(len(x.encode())+1 for x in argv)+65536<131072
  guard();raw=call('exact-current-prelaunch-phase-C',argv,timeout=q['root_helper_timeout_seconds']);value=json.loads(raw)
  assert value['status']==q['expected_phaseC_status'] and value['runtime']=='/usr/bin/python3.8' and value['device']==66306 and value['inode']==1048651 and value['restored_flags']==524288
  assert value['actual_cleanup_pid']>0 and value['actual_cleanup_pid']!=1837769 and value['actual_new_FLOCK']==[value['actual_cleanup_pid'],259,2,1048651,'0','EOF'] and value['original_failure_preserved'] is True
  assert value['NativeParentRetirement_created'] is False and value['native12_historical_source_or_global_release'] is False and value['all_new_own_FDs_closed_runtime_last'] is True
  assert len(clients)==1 and not pending_calls and not pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
  assert all(r['exit']==0 and r['direct_wait_joined'] and r['streams_closed'] and r['receipt_persisted'] and not r['secondary_errors'] and not r['lifecycle_UNKNOWN'] for r in clients)
  assert (OUT/'exact-current-prelaunch-phase-C.stderr').read_bytes()==b''
  save('PHASE-C-RESULT.json',value);save('RESULT.json',dict(status='PHASE_C_EXACT_CURRENT_RUNTIME_RESTORED_PENDING_INDEPENDENT_SAVED_QUALIFICATION',request_sha256=REQUEST_SHA,review_sha256=review_sha,clients=clients,phaseC=value,actual_A_B_qualification=q['actual_A_B_qualification'],original_prelaunch_failure_preserved=True,native12_source_historical_global_release=False,any_resource_release=False));print(json.dumps(dict(status='PHASE_C_CAPTURED_CURRENT_ONLY_RESTORE_PENDING_QUALIFICATION',at=now())))
 except BaseException as error:
  primary=error;tb=error.__traceback__
  try:save('RESULT.json',dict(status='PHASE_C_FAILED_OR_UNKNOWN_NO_REPLAY',error_type=type(error).__name__,error=str(error),traceback=''.join(traceback.format_exception(type(error),error,tb)),clients=clients,all_original_native_runtime_source_unknowns_retained=True,any_resource_release=False))
  except BaseException:pass
  raise BaseException.with_traceback(primary,tb)
if __name__=='__main__':
 assert sha(KEEPER_SOURCE)==KEEPER_SHA
 select_functions(KEEPER_SOURCE,['keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody'])
 entry_once_with_original_custody()
