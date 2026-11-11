import ast,datetime,hashlib,json,os,pathlib,resource,shutil,stat,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');BASE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z');M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110');HERE=pathlib.Path(__file__).parent;OUT=HERE/'execution-1';OUT.mkdir(mode=0o700,exist_ok=False)
common=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py';assert hashlib.sha256(common.read_bytes()).hexdigest()=='e6091bb418f619222f7a51ddef718ceeb75bb449f5abd10d62b40018b623db38';tree=ast.parse(common.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save')],type_ignores=[]),str(common),'exec'))
old=M/'f06-default-wiring-p04source-max-1/default-observation-1/run_root_once.py';assert sha(old)=='5695c81f42964567652b3a4c0a8ea0c009bc98eb1918ed765c8af88e27ae5f35';tree=ast.parse(old.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pins'],type_ignores=[]),str(old),'exec'))
shared=BASE/'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';assert sha(shared)=='983b8c3ceabcd8dc4d2e1999d75e6edbef91145a5f2ab18bfa1a2dfa6639c822';tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
cap=M/'joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py';assert sha(cap)=='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4';exec(compile(cap.read_text(),str(cap),'exec'))
ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py');clients=[];pending_calls={};started=now();qpath=HERE/'REQUEST.json'
def durable_capture():
 for path in OUT.iterdir():
  if path.is_file():
   fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
   try:os.fsync(fd)
   finally:os.close(fd)
 fd=os.open(str(OUT),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
 try:os.fsync(fd)
 finally:os.close(fd)
try:
 assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={7}
 assert resource.getrlimit(resource.RLIMIT_AS)==(268435456,268435456) and resource.getrlimit(resource.RLIMIT_CPU)==(60,60) and resource.getrlimit(resource.RLIMIT_FSIZE)==(8388608,8388608) and resource.getrlimit(resource.RLIMIT_CORE)==(0,0)
 assert sha(qpath)=='3048f317a6fc3ecaaa35451e7742ff87f17b6ed9aa0d0b1f242d58ec7b748dcb';review=pathlib.Path(sys.argv[1]);assert sha(review)==sys.argv[2];assert json.loads(review.read_text())['decision'].startswith('GO');q=json.loads(qpath.read_text());pins(q['immutable_inputs'])
 helper=pathlib.Path(ENV['SUDO_ASKPASS']);hs=os.lstat(helper);assert stat.S_ISREG(hs.st_mode) and not stat.S_ISLNK(hs.st_mode) and os.access(helper,os.X_OK),'existing askpass helper missing/unusable; no other route'
 stamp=guard();available=int(next(line.split()[1] for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024;rss=overhead();host=shutil.disk_usage(ROOT).free;scratch=shutil.disk_usage(M/'compute-image-source-1/output').free
 assert available>=26*2**30 and rss+256*2**20<=4*2**30 and host>=17*2**30 and scratch>=13*2**30
 save('ADMISSION.json',dict(at=now(),guard_updated_at=stamp,MemAvailable_bytes=available,all_current_overhead_bytes=rss,new_family_planning_bytes=256*2**20,HOST_total_bytes=4*2**30,max_jobs=3,CPU=7,host_free_bytes=host,scratch_current_filesystem_free_bytes=scratch,source_operator_authorization='SourcePR6805178926',Root_external_actual_current_payload_zero_required=True,no_native_or_old_UNKNOWN_release=True))
 raw=call('scoped-parent-provision',q['privileged_payload_argv'],timeout=60);receipt=json.loads(raw)
 assert receipt['status'] in ['PASS_FRESH_SCOPED_PARENT_PROVISIONED_AND_REAL_UID1000_VERIFIED','PASS_EXISTING_MATCHING_SCOPED_PARENT_READONLY_RECONCILED']
 assert receipt['source_sha256']==q['provisioner']['sha256'] and receipt['target']==q['exact_target']['target'] and receipt['final_output']==q['exact_target']['final_output_must_remain_absent']
 assert receipt['ancestor_before']==receipt['ancestor_after']==q['exact_target']['ancestor_identity']
 assert receipt['before_mounts']==receipt['after_mounts'] and receipt['RO_before']==receipt['RO_after']
 assert receipt['target_UID1000_readback']==receipt['durable_target_root_readback']==receipt['target_before_fsync'] and receipt['target_UID1000_readback']['uid']==receipt['target_UID1000_readback']['gid']==1000 and receipt['target_UID1000_readback']['mode']==0o700
 assert receipt['actual_UID1000_ancestor_search_and_parent_RWX'] is True and receipt['final_output_absent'] is True and receipt['no_target_files_allocated'] is True and receipt['all_opened_directory_FDs_closed'] and receipt['secondary_close_errors']==[] and receipt['remaining_direct_children']==[] and receipt['other_parent_old_objects_mounts_native_or_hold_mutations'] is False
 assert receipt['postcheck_actor']['real_effective_saved_UID']==[1000]*3 and receipt['postcheck_actor']['real_effective_saved_GID']==[1000]*3 and receipt['postcheck_actor']['supplementary_groups']==[1000] and int(receipt['postcheck_actor']['CapEff'],16)==int(receipt['postcheck_actor']['CapPrm'],16)==0
 if receipt['created']:
  assert [row['action'] for row in receipt['writes_attempted']]==['mkdirat','fchown','fchmod'] and receipt['preexisting'] is False
  assert all(row.get('inode',receipt['target_UID1000_readback']['inode'])==receipt['target_UID1000_readback']['inode'] for row in receipt['writes_attempted'])
 else:assert receipt['preexisting'] is True and receipt['writes_attempted']==[]
 save('PROVISIONING-RECEIPT.json',receipt)
 left=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not left and not pending_calls and len(clients)==1
 save('RESULT.json',dict(status='PASS_EXACT_SCOPED_PARENT_PROVISION_AND_REAL_UID1000_READBACK_PENDING_INDEPENDENT_RESULT_QUALIFICATION',at=now(),started_at=started,request_sha256=sha(qpath),review_sha256=sha(review),provisioner_sha256=q['provisioner']['sha256'],receipt_sha256=sha(OUT/'PROVISIONING-RECEIPT.json'),clients=clients,all_waits_streams_joined=True,remaining_direct_children=left,scope_only_exact_new_parent=True,staging_or_native_not_executed=True,other_holds_released=False));save('RESOURCE-RELEASE.json',dict(at=now(),current_process_positive_terminal_only=True,current_jobs='RELEASED',no_historical_native_source_Scratch_outcome_release=True));durable_capture();print(json.dumps(dict(status='PASS_EXACT_SCOPED_PARENT_ONLY',target=receipt['target'],new_created=receipt['created'],final_output_absent=True,Root_qualification_pending=True)))
except BaseException as error:
 save('RESULT.json',dict(status='FAILED_PRESERVED_NO_PERMISSION_OR_AUTH_OR_UNCHANGED_RETRY',at=now(),started_at=started,error=type(error).__name__+': '+str(error),traceback=traceback.format_exc(),clients=clients,pending_original_attempts=list(pending_calls),target_partial_state_retained=True,no_cleanup_or_alternate_route=True));durable_capture();raise
