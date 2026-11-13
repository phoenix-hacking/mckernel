import ast,datetime,hashlib,json,os,pathlib,shutil,signal,stat,subprocess,sys,time,traceback
import resource as _resource
ROOT=pathlib.Path('/home/holden/mckernel');PATCH_ROOT=pathlib.Path(__file__).parent;HERE=PATCH_ROOT.parent.parent;OUT=PATCH_ROOT/'ROOT-ACTUAL-PUBLISHER-ADMISSION-1'
def ref(p):
 b=pathlib.Path(p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save_private(p,x):
 fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def save(n,v):(OUT/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def select_functions(path,names):
 source=pathlib.Path(path).read_text();tree=ast.parse(source);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];assert {n.name for n in nodes}==set(names);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),globals())
clients=[];pending_calls={};keeper_capture_errors=[];OUTER_RETENTION_ERRORS=[];OUTER_ORIGINAL_WAITS=[]
CALL_SOURCE='/home/holden/mckernel-work/m14-blocker-resolution-20261110/joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py';CALL_SHA='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4'
KEEPER_SOURCE='/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-runtime-native-outer-capture-publicabi-max-1/correction-1/run_root_once.py';KEEPER_SHA='1f668620d63bf7ab4a4b86ee6c8d2128b96d59d4e19c4d0601ab2dc894870657'
NORMAL_CALLER_SOURCE='/home/holden/mckernel-work/resume-20261112T094452Z-M15-F08-host-capture-1/actual-readiness-diagnosis-1/provider-context-source-1/passive-source-extraction-1/run_passive_source_once.py';NORMAL_CALLER_SHA='b9ca9c8d9c3ad9df5c8896f1b858c7dd612488d94f99460cae3856e64f2f0311'
LINUX_OWNER_SOURCE='/home/holden/mckernel/scripts/application-tests/linux_diagnostic_container_owner.py';LINUX_OWNER_SHA='3d29c04a0dc7a7474773827e3468566aa72bc380ed4a9a6725c88914ada3fc93'
def main():
 ready=HERE/'PREPARED-SOURCE.json';assert ref(ready)['sha256']=='56399aaeadefe299ca76b34283fd50d14bf3845020169a4588b48864d56ca038'
 r=json.loads(ready.read_bytes())
 for k in ('catalogue','normal_caller','normal_issuer','normal_producer_request','parent_manifest','child_manifest','profile'):
  assert ref(pathlib.Path(r[k]['path']))==r[k],k
 review=HERE/'final-operation-review/OPERATION-REVIEW.json';assert ref(review)['sha256']=='1cbae6165d0828cd6b839de6531c244204106a3c98d3c42d3d73b809179a464a'
 go=json.loads(review.read_bytes());assert set(go)=={'status','scope','proposal_sha256','driver_sha256','parent_manifest_sha256','child_manifest_sha256','native_release','native_currentfree','retire_operation_only'} and go['status']=='PASS_ACTUAL_INSTALL_ONLY' and go['scope']=='ROOT_CODE_INSTALL_ONLY' and go['native_release'] is False and go['native_currentfree'] is None and go['retire_operation_only'] is True
 argv_path=HERE/'final-operation-review/FULL-ARGV.APPROVED.json';assert ref(argv_path)['sha256']=='3e60a661211c8378e5781638a2e7c53d3fce200e817850ece92e0647cecab92d';argv=json.loads(argv_path.read_bytes())['producer_argv'];assert len(argv)==8 and argv[:3]==['/usr/bin/python3','-I','-B'] and argv[4:]==['--operation-review',str(review),'--operation-review-sha256',ref(review)['sha256']]
 assert go['driver_sha256']==r['normal_caller']['sha256'] and go['parent_manifest_sha256']==r['parent_manifest']['sha256'] and go['child_manifest_sha256']==r['child_manifest']['sha256']
 ret=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-time-functional-1/next-time-functional-inputs-1/ROOT-CURRENT-RETIREMENT.TIME4FA-STAGING-ONLY.json');assert ref(ret)['sha256']=='3cc66d4af0a469642ea4213f7ed7daa19602cccd99af70169678859e41516e6f';prior=json.loads(ret.read_bytes());assert prior['current_HOST_payload_bytes_after']==0 and prior['current_HOST_jobs_after']==0 and prior['no_time_mapping_timepage_TSC_runtime_restoration_or_original_acceptance'] is True and prior['no_native12_source_runtime_service_account_normallease_globalUNKNOWN_or_other_scope_release'] is True
 assert not (HERE/'normal-operation-1/ROOT-EXEC-COMPLETION.ACTUAL.json').exists();OUT.mkdir(mode=0o700,exist_ok=False)
 rows={}
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   v=(p/'stat').read_text().rsplit(')',1)[1].split();rows[int(p.name)]={'pid':int(p.name),'ppid':int(v[1]),'birth':v[19],'state':v[0],'comm':(p/'comm').read_text().strip(),'rss_bytes':int(v[21])*os.sysconf('SC_PAGE_SIZE')}
  except FileNotFoundError:continue
 roots={1824289:'56295798',1824291:'56295805',1824293:'56295812',1561218:'51981693',1561217:'51981691'}
 for pid,birth in roots.items():assert rows[pid]['birth']==birth and rows[pid]['state'] not in ('Z','X','x')
 family=set(roots);family.update(pid for pid,row in rows.items() if row['comm'] in ('codex','codex-code-mode','dockerd','containerd','containerd-shim') or row['comm'].startswith(('containerd-shim','qemu-system')))
 while True:
  old=len(family);family.update(pid for pid,row in rows.items() if row['ppid'] in family)
  if len(family)==old:break
 overhead=max(864333824,sum(rows[pid]['rss_bytes'] for pid in family if pid in rows));held=0;jobs=0;new=2147483648
 available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;host=shutil.disk_usage(ROOT).free;scratch=shutil.disk_usage('/home/holden/mckernel-work/scratch').free
 assert held+overhead+new<=4*2**30 and jobs+1<=3 and available>=26*2**30 and host>=17*2**30 and scratch>=13*2**30
 ps_argv=['/usr/bin/taskset','-c','6','/usr/bin/prlimit','--core=0:0','--fsize=67108864:67108864','--nofile=512:512','--','/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','--no-trunc','--format','{{.ID}}']
 assert ref(NORMAL_CALLER_SOURCE)['sha256']==NORMAL_CALLER_SHA and ref(LINUX_OWNER_SOURCE)['sha256']==LINUX_OWNER_SHA
 assert _resource.getrlimit(_resource.RLIMIT_AS)==(_resource.RLIM_INFINITY,_resource.RLIM_INFINITY) and _resource.getrlimit(_resource.RLIMIT_CPU)==(_resource.RLIM_INFINITY,_resource.RLIM_INFINITY)
 assert ref(CALL_SOURCE)['sha256']==CALL_SHA
 select_functions(CALL_SOURCE,['call'])
 global ENV;ENV=os.environ.copy();ENV['PATH']='/usr/sbin:/usr/bin:/sbin:/bin';ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
 context_presence={key:key in os.environ for key in ('HOME','XDG_RUNTIME_DIR','DOCKER_HOST','DOCKER_CONTEXT','DOCKER_CONFIG')}
 try:
  ps_stdout=call('normal-context-docker-ps',ps_argv,timeout=15)
  ps_stderr=(OUT/'normal-context-docker-ps.stderr').read_bytes()
  assert len(clients)==1 and not pending_calls
  ps_client=clients[0]
  assert ps_client['exit']==0 and ps_client['direct_wait_joined'] and ps_client['streams_closed'] and ps_client['receipt_persisted'] and not ps_client['lifecycle_UNKNOWN'] and not ps_client['resource_charge_retained'] and ps_client['primary_error'] is None and not ps_client['secondary_errors']
  assert ps_stdout.strip()==b'' and ps_stderr==b''
  assert not pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
 except BaseException as error:
  primary=error;tb=error.__traceback__
  try:
   save_private(OUT/'DOCKER-PREFLIGHT-FAILURE.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stage':'changed-normal-context-read-only-Docker-ps-before-account-or-publisher','argv':ps_argv,'context_variable_presence_only':context_presence,'uid':os.getuid(),'gid':os.getgid(),'RLIMIT_AS':list(_resource.getrlimit(_resource.RLIMIT_AS)),'clients':clients,'stdout_ref':ref(OUT/'normal-context-docker-ps.stdout') if (OUT/'normal-context-docker-ps.stdout').exists() else None,'stderr_ref':ref(OUT/'normal-context-docker-ps.stderr') if (OUT/'normal-context-docker-ps.stderr').exists() else None,'error_type':type(error).__name__,'error':str(error),'traceback':''.join(traceback.format_exception(type(error),error,tb)),'old_debc79_stderr_remains_unavailable':True,'no_account_admission_nonce_issuer_sudo_installer_or_native_issued':True,'no_permission_or_service_clearance_inferred':True})
  except BaseException as reporting_error:retain_outer_error('preflight-report',reporting_error)
  raise BaseException.with_traceback(primary,tb)
 resource=OUT/'CURRENT-RESOURCE-AND-EXCLUSIVE-LANE.json';save_private(resource,{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_ready':ref(ready),'exact_operation_review':ref(review),'actual_latest_HOST_scoped_retirement':ref(ret),'current_HOST_payload_bytes_before':held,'current_HOST_jobs_before':jobs,'new_current_family_bytes':new,'new_current_jobs':1,'all_controller_worker_overhead_bytes':overhead,'actual_rows':[rows[p] for p in sorted(family) if p in rows],'MemAvailable_bytes':available,'host_free_bytes':host,'scratch_free_bytes':scratch,'actual_running_container_check':{'argv':ps_argv,'exit':ps_client['exit'],'stdout':ps_stdout.decode('utf-8'),'stderr':ps_stderr.decode('utf-8'),'stdout_ref':ref(OUT/'normal-context-docker-ps.stdout'),'stderr_ref':ref(OUT/'normal-context-docker-ps.stderr'),'client_receipt_ref':ref(OUT/'CLIENTS.json'),'context_variable_presence_only':context_presence,'original_wait_and_streams_closed':ps_client['direct_wait_joined'] and ps_client['streams_closed'],'qualified_inherited_context_and_existing_sudo_system_socket_route':True},'all_native12_source_globalUNKNOWN_and_original_raw_failures_preserved':True})
 consumer=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/current-root-owner-1/current_account_snapshot.PROPOSED.py');owner=HERE/'normal-operation-1/CURRENT-ACTUAL-OWNER.json';assert ref(consumer)['sha256']=='fe2c38a7d559e0066c45da9de0fd65b5597b61cebbd5249663c645cfe08c7fe6' and ref(owner)['sha256']=='a51ed92a2b11f7cb65d83189ee0eee80c13537d0c76f2b1b0351dc38293e09a1'
 ns={'__name__':'Root_reporting_normal_publication_current_account'};exec(compile(consumer.read_bytes(),str(consumer),'exec'),ns);state,usage,credit,observed=ns['current_account_snapshot'](json.loads(owner.read_bytes()));sys.path.insert(0,str(ROOT/'scripts'));import os_goal_guard_protocol
 assert os_goal_guard_protocol.recovery_blocker(state,explicit_user=True) is None
 account=OUT/'CURRENT-OWNER-ACCOUNT.PRIVATE.json';save_private(account,{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'ACCEPTED','state':state,'usage':usage,'credit':credit,'independent_owner_ref':ref(owner)})
 admission=OUT/'ROOT-CURRENT-ADMISSION.ACTUAL.json';save_private(admission,{'schema':'mckernel.Root-exact-reporting-normal-publisher-admission.v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issued_utc_ns':time.time_ns(),'issued_monotonic_ns':time.monotonic_ns(),'invocation':'20261112T094452Z-12a4bea0','saved_Root':'01a18bc3-e072-7810-9426-75101b0856c0','same_Root_finite_credit_run_id':'7c6ef3604bfb4008a917bba8cfb6cfaa','operation_review':ref(review),'approved_argv':ref(argv_path),'actual_owner_account':ref(account),'actual_all_owner_resource_and_source_proof':ref(resource),'new_current_family_bytes':new,'new_current_jobs':1,'CPU':[6],'code_install_only':True,'new_native_release':False,'native_currentfree':None,'all_native12_source_global_UNKNOWNs_and_persistent_I_preserved':True,'retire_only_after_genuine_positive_current_full_Root_lease_client_capture_closure_and_independent_Q':True})
 # Keep this pre-issuer admission receipt separate. Only the genuine reviewed issuer
 # writes the normal three completion records to stdout; never trim/filter it.
 os.sched_setaffinity(0,{6});os.execv(argv[0],argv)
if __name__=='__main__':
 assert ref(KEEPER_SOURCE)['sha256']==KEEPER_SHA
 select_functions(KEEPER_SOURCE,['keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody'])
 entry_once_with_original_custody()
