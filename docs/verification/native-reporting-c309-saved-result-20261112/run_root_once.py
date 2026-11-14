import ast,datetime,hashlib,json,os,pathlib,resource,signal,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');HERE=pathlib.Path(__file__).parent;OUT=HERE/'execution-1'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(n,v):(OUT/n).write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n')
def verify(v):
 p=pathlib.Path(v['path']);assert p.is_file() and p.stat().st_size==v['bytes'] and sha(p)==v['sha256'],str(p)
def select_functions(path,names):
 source=pathlib.Path(path).read_text();tree=ast.parse(source);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];assert {n.name for n in nodes}==set(names);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),globals())
clients=[];pending_calls={};keeper_capture_errors=[];OUTER_RETENTION_ERRORS=[];OUTER_ORIGINAL_WAITS=[]
REQUEST_SHA='d4b90faae3e542ca01bfcce4286df9bfa7499f36ccf2d045276f63006367ae22'
CALL_SOURCE='/home/holden/mckernel-work/m14-blocker-resolution-20261110/joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py';CALL_SHA='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4'
KEEPER_SOURCE='/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-runtime-native-outer-capture-publicabi-max-1/correction-1/run_root_once.py';KEEPER_SHA='1f668620d63bf7ab4a4b86ee6c8d2128b96d59d4e19c4d0601ab2dc894870657'
def main():
 assert len(sys.argv)==5 and sha(HERE/'REQUEST.json')==REQUEST_SHA
 review=pathlib.Path(sys.argv[1]);review_sha=sys.argv[2];admission=pathlib.Path(sys.argv[3]);admission_sha=sys.argv[4]
 assert sha(review)==review_sha and sha(admission)==admission_sha
 q=json.loads((HERE/'REQUEST.json').read_text());rev=json.loads(review.read_text());a=json.loads(admission.read_text());assert rev['decision'].startswith('GO')
 verify(q['inputs']);inputs=json.loads(pathlib.Path(q['inputs']['path']).read_text())
 for row in inputs['files']+[inputs['interpreter']]:verify(row)
 assert resource.getrlimit(resource.RLIMIT_AS)==(134217728,134217728) and resource.getrlimit(resource.RLIMIT_CPU)==(90,90) and resource.getrlimit(resource.RLIMIT_FSIZE)==(67108864,67108864) and resource.getrlimit(resource.RLIMIT_NOFILE)==(128,128) and resource.getrlimit(resource.RLIMIT_CORE)==(0,0) and os.sched_getaffinity(0)=={0}
 verify(q['actor']);select_functions(q['actor']['path'],['check','digest_value','reference_shape','fresh_admission']);fresh_admission(a,q,REQUEST_SHA,review_sha)
 assert not OUT.exists() and not pathlib.Path(q['actor_raw_output']).exists();OUT.mkdir(mode=0o700)
 global ENV;ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
 try:
  assert sha(CALL_SOURCE)==CALL_SHA;select_functions(CALL_SOURCE,['call'])
  literal=pathlib.Path(q['actor']['path']).read_text();argv=q['Root_actor_command_prefix']+[literal,str(HERE/'REQUEST.json'),REQUEST_SHA,str(review),review_sha,str(admission),admission_sha]
  assert all(type(x) is str and '\x00' not in x and len(x.encode())+1<131072 for x in argv) and sum(len(x.encode())+1 for x in argv)+65536<131072
  fresh_admission(a,q,REQUEST_SHA,review_sha)
  raw=call('current-c309-saved-result-two-file-projection',argv,timeout=q['root_actor_timeout_seconds']);value=json.loads(raw)
  assert value['status']==q['expected_status'] and value['nonce']==q['nonce'] and value['operation_root']==q['operation_root']
  assert value['original_root_held_FD_identity_join']=='UNPROVED_NOT_SUPPLIED' and value['all_two_saved_reads_enclosed_by_same_directory_and_file_bookends'] and value['all_new_own_FDs_closed'] and not value['own_close_error_types']
  assert value['raw_private_record']['Root_uid0_mode0600_and_directory0700'] and value['original81691_current2GiB_roles_lease_all_native_source_UNKNOWN_retained'] is True and value['disposition_or_resource_release_or_native_or_install_acceptance'] is False and value['additional_proc_namespace_installed30_account_verifier_RPC_signal_flags_or_native_reads'] is False
  assert len(clients)==1 and not pending_calls;rec=clients[0]
  assert rec['exit']==0 and rec['direct_wait_joined'] and rec['streams_closed'] and rec['receipt_persisted'] and rec['primary_error'] is None and not rec['secondary_errors'] and not rec['lifecycle_UNKNOWN'] and not rec['resource_charge_retained']
  assert (OUT/'current-c309-saved-result-two-file-projection.stderr').read_bytes()==b''
  save('SAFE-SAVED-RESULT-PROJECTION.json',value)
  save('RESULT.json',dict(status='CURRENT_C309_SAVED_TWO_FILE_DATA_CAPTURED_PENDING_INDEPENDENT_SAVED_Q',request_sha256=REQUEST_SHA,review_sha256=review_sha,clients=clients,safe_projection=value,original81691_and2GiB_roles_lease_native12_source_globalUNKNOWN_retained=True,any_original_or_native_release=False,new_reader_retirement_requires_actual_fullRoot_and_independent_Q=True));print(json.dumps(dict(status='CURRENT_C309_TWO_FILE_DATA_CAPTURED_NO_DISPOSITION',at=now())))
 except BaseException as error:
  primary=error;tb=error.__traceback__
  try:save('RESULT.json',dict(status='CURRENT_C309_READONLY_CAPTURE_FAILED_UNPROVED_NO_DISPOSITION',error_type=type(error).__name__,error=str(error),traceback=''.join(traceback.format_exception(type(error),error,tb)),clients=clients,original81691_and2GiB_all_holds_retained=True,any_resource_release=False))
  except BaseException:pass
  raise BaseException.with_traceback(primary,tb)
if __name__=='__main__':
 assert sha(KEEPER_SOURCE)==KEEPER_SHA
 select_functions(KEEPER_SOURCE,['keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody'])
 entry_once_with_original_custody()
