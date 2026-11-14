import ast,datetime,hashlib,json,os,pathlib,resource,shutil,stat,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');BASE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z');M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110');HERE=pathlib.Path(__file__).parent;OUT=HERE/'execution-1';OUT.mkdir(mode=0o700,exist_ok=False)
common=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py';assert hashlib.sha256(common.read_bytes()).hexdigest()=='e6091bb418f619222f7a51ddef718ceeb75bb449f5abd10d62b40018b623db38';tree=ast.parse(common.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save')],type_ignores=[]),str(common),'exec'))
old=M/'f06-default-wiring-p04source-max-1/default-observation-1/run_root_once.py';assert sha(old)=='5695c81f42964567652b3a4c0a8ea0c009bc98eb1918ed765c8af88e27ae5f35';tree=ast.parse(old.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pins'],type_ignores=[]),str(old),'exec'))
shared=BASE/'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';assert sha(shared)=='983b8c3ceabcd8dc4d2e1999d75e6edbef91145a5f2ab18bfa1a2dfa6639c822';tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
cap=M/'joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py';assert sha(cap)=='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4';exec(compile(cap.read_text(),str(cap),'exec'))
ENV={};clients=[];pending_calls={};started=now();qpath=HERE/'REQUEST.json';held=[];fd_close_dispositions=[];fd_close_errors=[];fd_close_raw=[];first_close_failure=[None];RETAINED_FAILURES=[]
def close_owned_once():
 # Consume each number BEFORE its only close. Retain raw failures immediately;
 # diagnostics, reports and persistence cannot interrupt this remaining drain.
 while held:
  fd=held.pop()
  try:os.close(fd)
  except BaseException:
   info=sys.exc_info()
   if first_close_failure[0] is None:first_close_failure[0]=info
   fd_close_raw.append((fd,info))
  else:fd_close_raw.append((fd,None))
def retained_info(error):
 return (type(error),error,error.__traceback__)
def diagnostic(error,secondary):
 # This is called only after the owned FD drain. Formatting failures remain raw
 # secondary exceptions; they never replace the retained operation primary.
 try:name=type(error).__name__
 except BaseException as failure:
  secondary.append(retained_info(failure));name='BaseException'
 try:message=str(error)
 except BaseException as failure:
  secondary.append(retained_info(failure));message='<diagnostic formatting failed>'
 return {'type':name,'message':message}
def exception_diagnostic(info,secondary):
 assert not held
 result=diagnostic(info[1],secondary)
 try:result['traceback']=''.join(traceback.format_exception(*info))
 except BaseException as failure:
  secondary.append(retained_info(failure));result['traceback']='<traceback formatting failed>'
 return result
def close_diagnostics_after_drain(secondary):
 assert not held
 dispositions=[];errors=[]
 for fd,info in fd_close_raw:
  if info is None:
   record=dict(fd=fd,disposition='CLOSED',ownership_consumed_before_attempt=True)
  else:
   record=exception_diagnostic(info,secondary)
   record.update(fd=fd,disposition='UNKNOWN_NO_NUMERIC_RETRY',ownership_consumed_before_attempt=True)
   errors.append(record)
  dispositions.append(record)
 return dispositions,errors
def rethrow(info,secondary):
 RETAINED_FAILURES.append({'primary':info,'secondary':list(secondary),'raw_FD_close_dispositions':list(fd_close_raw)})
 try:info[1].stage_parent_secondary_exceptions=tuple(secondary)
 except BaseException as failure:RETAINED_FAILURES[-1]['secondary'].append(retained_info(failure))
 raise BaseException.with_traceback(info[1],info[2])
def durable_capture():
 for path in OUT.iterdir():
  if path.is_file():
   fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
   try:os.fsync(fd)
   finally:os.close(fd)
 fd=os.open(str(OUT),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
 try:os.fsync(fd)
 finally:os.close(fd)
def identity(fd):
 s=os.fstat(fd);assert stat.S_ISDIR(s.st_mode)
 return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode))
def mounts_for(path):
 with open('/proc/self/mountinfo','rb') as f:raw=f.read(131073)
 assert len(raw)<=131072
 rows=raw.decode('utf-8','strict').splitlines();hits=[row for row in rows if str(path)==row.split()[4] or str(path).startswith(row.split()[4].rstrip('/')+'/')];assert hits
 return max(hits,key=lambda row:len(row.split()[4]))
def check_parent(expected,require_absent):
 flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC;chain=[];fd=os.open('/',flags);held.append(fd);chain.append(('/',fd,identity(fd)))
 for name in ('home','holden','mckernel-work','scratch','m14-native-c964-a2f00a61-staging-parent'):
  fd=os.open(name,flags,dir_fd=fd);held.append(fd);chain.append((name,fd,identity(fd)))
 assert identity(fd)==expected['identity'] and identity(chain[-2][1])==expected['original_ancestor_identity']
 for i,(name,current,wanted) in enumerate(chain):
  assert identity(current)==wanted
  if i:
   s=os.stat(name,dir_fd=chain[i-1][1],follow_symlinks=False);assert stat.S_ISDIR(s.st_mode) and (s.st_dev,s.st_ino)==(wanted['device'],wanted['inode'])
 assert os.readlink('/proc/self/ns/mnt')==expected['mounts']['namespace'] and mounts_for(expected['path'])==expected['mounts']['ancestor_mount']
 ro='/home/holden/mckernel-work/scratch-readonly-20261105';rfd=os.open('scratch-readonly-20261105',flags,dir_fd=chain[-3][1]);held.append(rfd)
 assert identity(rfd)==expected['protected_RO_identity'] and mounts_for(ro)==expected['mounts']['protected_RO_mount']
 assert os.getuid()==os.geteuid()==1000 and os.access(expected['path'],os.R_OK|os.W_OK|os.X_OK,effective_ids=True,follow_symlinks=False)
 for path in ['/','/home','/home/holden','/home/holden/mckernel-work','/home/holden/mckernel-work/scratch']:assert os.access(path,os.X_OK,effective_ids=True,follow_symlinks=False)
 if require_absent:
  try:os.stat('native-signal-c964-a2f00a61-stage-20261111-1',dir_fd=fd,follow_symlinks=False)
  except FileNotFoundError:pass
  else:raise AssertionError('fresh final output already exists; no overwrite/reroute')
 v=os.fstatvfs(fd);available=v.f_bavail*v.f_frsize;assert available>=13*2**30
 return dict(path=expected['path'],identity=identity(fd),namespace=os.readlink('/proc/self/ns/mnt'),mount=mounts_for(expected['path']),protected_RO_identity=identity(rfd),protected_RO_mount=mounts_for(ro),actual_UID1000_RWX=True,available_bytes=available,final_absent_before_command=require_absent)
try:
 assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0}
 assert resource.getrlimit(resource.RLIMIT_AS)==(268435456,268435456) and resource.getrlimit(resource.RLIMIT_CPU)==(330,330) and resource.getrlimit(resource.RLIMIT_FSIZE)==(8388608,8388608)
 assert sha(qpath)=='1b06530e9b09a2a7530e9753cf71db37059306c247094a3962b657c087fb972a';review=pathlib.Path(sys.argv[1]);assert sha(review)==sys.argv[2] and json.loads(review.read_text())['decision'].startswith('GO');q=json.loads(qpath.read_text());pins(q['immutable_inputs']);pins(q['inputs']);ENV=dict(q['environment'])
 assert json.loads(pathlib.Path(q['actual_parent_independent_qualification']['path']).read_text())['decision'].startswith('GO')
 proofs=q['actual_parent_provisioning_proof'];p=json.loads(pathlib.Path(proofs['actual_provisioning_result']['path']).read_text());r=json.loads(pathlib.Path(proofs['actual_provisioning_receipt']['path']).read_text());full=json.loads(pathlib.Path(proofs['full_Root_completion']['path']).read_text());retired=json.loads(pathlib.Path(proofs['Root_current_process_retirement']['path']).read_text())
 assert p['status']=='PASS_EXACT_SCOPED_PARENT_PROVISION_AND_REAL_UID1000_READBACK_PENDING_INDEPENDENT_RESULT_QUALIFICATION' and p['all_waits_streams_joined'] and p['remaining_direct_children']==[] and p['receipt_sha256']==proofs['actual_provisioning_receipt']['sha256']
 assert r['status']=='PASS_FRESH_SCOPED_PARENT_PROVISIONED_AND_REAL_UID1000_VERIFIED' and r['target_UID1000_readback']==q['exact_scoped_parent']['identity'] and r['target']==q['exact_scoped_parent']['path'] and r['final_output']==q['output_directory'] and r['actual_UID1000_ancestor_search_and_parent_RWX'] and r['all_opened_directory_FDs_closed'] and r['secondary_close_errors']==[]
 assert r['postcheck_actor']['real_effective_saved_UID']==[1000]*3 and r['postcheck_actor']['real_effective_saved_GID']==[1000]*3 and int(r['postcheck_actor']['CapEff'],16)==int(r['postcheck_actor']['CapPrm'],16)==0
 assert full['status']=='POSITIVE_FULL_ROOT_TOOL_COMPLETION' and full['tool_exit_code']==0 and full['tool_session_id'] is None and full['all_owned_clients_and_streams_joined'] and full['remaining_owned_children']==[] and full['result_sha256']==proofs['actual_provisioning_result']['sha256'] and full['receipt_sha256']==proofs['actual_provisioning_receipt']['sha256']
 assert retired['state']=='RETIRED_CURRENT_OPERATOR_PROVISIONING_HOST_PROCESS_ONLY' and retired['actual_full_Root_completion_sha256']==proofs['full_Root_completion']['sha256'] and retired['all_other_native_source_Scratch_UNKNOWN_holds_retained']
 inputs=json.loads(pathlib.Path(q['inputs']['path']).read_text());assert len(inputs['files'])==43 and len(inputs['directories'])==21 and sum(v['source']['size'] for v in inputs['files'])==81798929 and inputs['cohort']['compute_source_commit']=='c964be3917c8f4c5031108aa927c84894584b667' and inputs['cohort']['compute_image_sha256']=='a2f00a6105f20642db8ef95fe12ade0873120594531f325ef363a4bb59f0ff8a'
 before=check_parent(q['exact_scoped_parent'],True);save('PARENT.before.json',before)
 stamp=guard();available=int(next(line.split()[1] for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024;rss=overhead();hf=shutil.disk_usage(ROOT).free
 assert available>=26*2**30 and rss+2**30<=4*2**30 and hf>=17*2**30
 save('ADMISSION.json',dict(at=now(),guard_updated_at=stamp,MemAvailable_bytes=available,all_current_overhead_bytes=rss,new_family_planning_bytes=2**30,HOST_total_bytes=4*2**30,max_jobs=3,CPU=0,host_free_bytes=hf,scratch_actual_parent_free_bytes=before['available_bytes'],other_jobs_owned_and_admitted_by_Root=True,actual_parent_proof=proofs,no_native_or_other_UNKNOWN_release=True))
 raw=call('current-a2f-scoped-stage',q['command'],timeout=300);actual=json.loads(raw)
 assert actual['status']=='PASS_REAL_NAMED_ARTIFACT_BASE_OVERLAY_AND_MANIFEST_ONLY' and actual['input_sha256']==q['inputs']['sha256'] and actual['cohort']==inputs['cohort'] and actual['materialized_base_files']==43 and actual['strict_collector_ELF_guard_ran_in_real_overlay'] is True and actual['native_or_control_action'] is False
 result_path=pathlib.Path(q['output_directory'])/'RESULT.json';assert json.loads(result_path.read_text())==actual
 manifest_ref=actual['native_manifest'];manifest_path=pathlib.Path(manifest_ref['path']);assert manifest_path==pathlib.Path(q['output_directory'])/'native-diagnostic-manifest.json' and sha(manifest_path)==manifest_ref['sha256'] and manifest_path.stat().st_size==manifest_ref['size'];manifest=json.loads(manifest_path.read_text())
 assert manifest['case_id']==inputs['case_id'] and manifest['payload']==inputs['payload'] and manifest['profile']==inputs['profile'] and manifest['artifacts']['mckernel_image']['sha256']==inputs['cohort']['compute_image_sha256'] and manifest['artifacts']['mckernel_image']['size']==13349576
 assert [v['sha256'] for v in manifest['modules']]==['04f5d3e0dbf0c70b7ff5aeb281fabda310751bc45c4916cb582575cf3f81155e','ae67f463920ae6267710624139c56ef5dcfa8d1c60f4fc1a42f0e52604066696','dc46a4f552776d6f9200cbdc8127882ea3f5d69d119f3e5b00672dce234eabcc']
 after=check_parent(q['exact_scoped_parent'],False);save('PARENT.after.json',after);assert after['identity']==before['identity'] and after['mount']==before['mount'] and after['protected_RO_identity']==before['protected_RO_identity'] and after['protected_RO_mount']==before['protected_RO_mount']
 save('STAGING-RECEIPT.json',actual);left=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not left and not pending_calls and len(clients)==1
 close_owned_once()
 if first_close_failure[0] is not None:
  info=first_close_failure[0];raise BaseException.with_traceback(info[1],info[2])
 fd_close_dispositions,fd_close_errors=close_diagnostics_after_drain([])
 save('RESULT.json',dict(status='PASS_CURRENT_C964_A2F_SCOPED_PARENT43INPUT_HOST_BASE_OVERLAY_AND_MANIFEST_PENDING_SAVED_QUALIFICATION',started_at=started,finished_at=now(),request_sha256=sha(qpath),review_sha256=sha(review),source_stager_sha256=q['source']['sha256'],input_sha256=q['inputs']['sha256'],parent_identity=after['identity'],actual_stage_RESULT=dict(path=str(result_path),bytes=result_path.stat().st_size,sha256=sha(result_path)),native_manifest=manifest_ref,all_parent_directory_FDs_closed=True,FD_close_dispositions=fd_close_dispositions,secondary_FD_close_errors=fd_close_errors,clients=clients,all_waits_streams_joined=True,remaining_direct_children=left,no_native_or_program_main_execution=True,original_acceptance=False));save('RESOURCE-RELEASE.json',dict(at=now(),current_process_positive_terminal_only=True,current_jobs='RELEASED',no_historical_native_source_Scratch_outcome_release=True));durable_capture();print(json.dumps(dict(status='PASS_CURRENT_A2F_HOST_STAGE_ONLY',output=q['output_directory'],materialized_files=43,native_execution=False,Root_qualification_pending=True)))
except BaseException:
 # Preserve the actual exception object and raw traceback BEFORE any cleanup or
 # formatting. Each remaining directory FD is then attempted exactly once.
 primary=sys.exc_info()
 close_owned_once()
 secondary=[info for _fd,info in fd_close_raw if info is not None and info[1] is not primary[1]]
 try:
  fd_close_dispositions,fd_close_errors=close_diagnostics_after_drain(secondary)
  primary_diagnostic=exception_diagnostic(primary,secondary)
  save('RESULT.json',dict(status='FAILED_PRESERVED_NO_PERMISSION_OR_AUTH_OR_UNCHANGED_RETRY',started_at=started,finished_at=now(),error=primary_diagnostic['type']+': '+primary_diagnostic['message'],traceback=primary_diagnostic['traceback'],clients=clients,pending_original_attempts=list(pending_calls),secondary_FD_close_errors=fd_close_errors,FD_close_dispositions=fd_close_dispositions,remaining_owned_FD_entries=list(held),FD_close_UNKNOWN_retained=first_close_failure[0] is not None,raw_secondary_exceptions_retained=len(secondary),partial_output_retained_no_delete_or_alternate_route=True))
 except BaseException as failure:
  secondary.append(retained_info(failure))
 try:durable_capture()
 except BaseException as failure:
  secondary.append(retained_info(failure))
 if secondary:
  try:os.write(2,b'Stage parent failed; raw primary and secondary failures retained; no numeric FD retry.\n')
  except BaseException as failure:secondary.append(retained_info(failure))
 rethrow(primary,secondary)
