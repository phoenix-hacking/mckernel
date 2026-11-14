import sys,ast,datetime,hashlib,json,os,pathlib,re,resource,shutil,signal,stat,subprocess,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');BASE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z');M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110');HERE=pathlib.Path(__file__).parent;OUT=HERE/'execution-1';OUT.mkdir(mode=0o700,exist_ok=False)
prior=M/'f06-default-wiring-p04source-max-1/default-observation-1/run_root_once.py';assert hashlib.sha256(prior.read_bytes()).hexdigest()=='5695c81f42964567652b3a4c0a8ea0c009bc98eb1918ed765c8af88e27ae5f35';tree=ast.parse(prior.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pins'],type_ignores=[]),str(prior),'exec'))
common=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py';assert hashlib.sha256(common.read_bytes()).hexdigest()=='e6091bb418f619222f7a51ddef718ceeb75bb449f5abd10d62b40018b623db38';tree=ast.parse(common.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save')],type_ignores=[]),str(common),'exec'))
shared=BASE/'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';assert sha(shared)=='983b8c3ceabcd8dc4d2e1999d75e6edbef91145a5f2ab18bfa1a2dfa6639c822';tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
cap=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/M14-time-functional-closure-p04source-max-1/runnable-host-handoff-1')/'phase-cpu7.py';assert sha(cap)=='4ca162e1a0e68d236a1f22abbeb7b88849e04e6ffac62049ce28604646acc01b';exec(compile(cap.read_text(),str(cap),'exec'))
call_source=M/'joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py';assert sha(call_source)=='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4';exec(compile(call_source.read_text(),str(call_source),'exec'));pending_calls={}
admit_source=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/M14-time-functional-closure-p04source-max-1/runnable-host-handoff-1')/'admit_descriptor.py';assert sha(admit_source)=='0a2b43cee8b1411cc0fab195533b92297927a8519b3e0d70f6fe7adfdc5ee159';exec(compile(admit_source.read_text(),str(admit_source),'exec'))
ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py');docker=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'];clients=[];phases=[];owned=[];started=now();qpath=HERE/'REQUEST.json';review=pathlib.Path(sys.argv[1]);artifacts=[];control_rows=[]
durable_source=M/'scratch-scoped-parent-provision-p03-max-1/run_root_once.py';assert sha(durable_source)=='a6b75eea1fac1d1b9c161d7d2a6acaad3e46303e93375b616f5134acd66ce9a9';tree=ast.parse(durable_source.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='durable_capture'],type_ignores=[]),str(durable_source),'exec'))
try:
 assert sha(qpath)=='e73be8d46e6cb3af8d98b3240e16ba513dc3dfd986551ef022f2b13c9e869de0' and sha(review)==sys.argv[2] and json.loads(review.read_text())['decision'].startswith('GO');q=json.loads(qpath.read_text())
 pins(q['inputs']);data=json.loads(pathlib.Path(q['inputs']['path']).read_text());pins(data['actual_execution_HOST_files']);pins(data['immutable_receipt_files'])
 assert resource.getrlimit(resource.RLIMIT_AS)==(resource.RLIM_INFINITY,resource.RLIM_INFINITY) and resource.getrlimit(resource.RLIMIT_FSIZE)==(67108864,67108864)
 assert 7 in os.sched_getaffinity(0)
 def disk_headroom():
  assert shutil.disk_usage(ROOT).free>=20*2**30 and shutil.disk_usage(HERE).free>=16*2**30
 disk_headroom();raw=pathlib.Path(q['virtual_AS_correction']['oracle_reuse']['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==q['virtual_AS_correction']['oracle_reuse']['sha256'];reused=json.loads(raw);pins(reused['actual_stdout']);pins(reused['actual_stderr']);pins(reused['actual_saved_controls']);assert pathlib.Path(reused['actual_stdout']['path']).read_bytes()==pathlib.Path(q['oracle_phase']['expected_stdout']['path']).read_bytes() and pathlib.Path(reused['actual_stderr']['path']).read_bytes()==b''
 control_rows=json.loads(pathlib.Path(reused['actual_stdout']['path']).read_bytes())['rows'];assert control_rows==json.loads(pathlib.Path(reused['actual_saved_controls']['path']).read_text())['rows'];save('TIME-ORACLE-REUSED.json',dict(rows=control_rows,actual_reused_stdout=reused['actual_stdout'],executed_in_current_successor=False,application_executed=False))
 assert not call('running-preflight',docker+['ps','-q']).strip();names=call('names-preflight',docker+['ps','-a','--format','{{.Names}}']).decode().splitlines();a=q['payload_phase'];assert a['create_argv'][a['create_argv'].index('--name')+1] not in names
 for key in ('payload_phase','collector_phase'):assert not os.path.lexists(q[key]['output_root'])
 os.sched_setaffinity(0,{7});assert os.sched_getaffinity(0)=={7};disk_headroom();admit('time-payload',256*2**20);out=pathlib.Path(a['output_root']);out.mkdir(mode=0o700,exist_ok=False)
 phase('time-payload',a['create_argv'],a['expected_mounts'],256*2**20,64,a['max_wall_seconds'])
 for name in q['output_files']:
  p=out/name;st=p.lstat();assert stat.S_ISREG(st.st_mode) and st.st_size>0
  if name=='time.monotonic-libc':assert p.read_bytes()[:6]==b'\x7fELF\x02\x01' and stat.S_IMODE(st.st_mode)==0o755
  artifacts.append(dict(path=str(p),bytes=st.st_size,sha256=sha(p),mode=oct(stat.S_IMODE(st.st_mode))))
 runtime={line.split()[1]:line.split()[0] for line in (out/'input-and-runtime.sha256').read_text().splitlines()}
 assert runtime['/usr/bin/cc']=='2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2' and runtime['/lib64/libc.so.6']=='b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4' and runtime['/lib64/ld-linux-x86-64.so.2']=='0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b'
 assert runtime['/input/time.monotonic-libc.c']==sha(pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/M14-time-functional-closure-p04source-max-1/runnable-host-handoff-1')/'input/time.monotonic-libc.c') and runtime['/output/time.monotonic-libc']==sha(out/'time.monotonic-libc')
 assert not owned and not pending_calls
 os.sched_setaffinity(0,{7});assert os.sched_getaffinity(0)=={7};disk_headroom();admit('time-collector',512*2**20);a=q['collector_phase'];co=pathlib.Path(a['output_root']);co.mkdir(mode=0o700,exist_ok=False);(co/'tmp').mkdir(mode=0o700,exist_ok=False)
 call('collector-compile',a['argv'],timeout=a['max_wall_seconds'])
 for name in a['output_files']:
  p=co/name;st=p.lstat();assert stat.S_ISREG(st.st_mode) and st.st_size>0
  if name=='collector':assert p.read_bytes()[:6]==b'\x7fELF\x02\x01' and stat.S_IMODE(st.st_mode)==0o755
  artifacts.append(dict(path=str(p),bytes=st.st_size,sha256=sha(p),mode=oct(stat.S_IMODE(st.st_mode))))
 call('collector-metadata',a['metadata_argv'],timeout=30)
 pins(data['actual_execution_HOST_files']);pins(data['immutable_receipt_files'])
 left=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not left and not owned and not pending_calls
 result=dict(status='PASS_NEW_TIME_PAYLOAD_COLLECTOR_COMPILE_AND_THREE_ORACLE_CONTROLS_PENDING_SAVED_ELF_QUALIFICATION',started_at=started,finished_at=now(),request_sha256=sha(qpath),review_sha256=sha(review),phases=phases,clients=clients,controls=control_rows,all_waits_streams_joined=True,remaining_owned_children=left,actual_artifacts=artifacts,application_HOST_main_executed=False,collector_main_executed=False,native_executed=False,first_repeat_replayed=False,original_acceptance=False,oracle_controls_reused_from=q['virtual_AS_correction']['oracle_reuse'],oracle_controls_executed_in_this_successor=False);save('RESULT.json',result);save('RESOURCE-DISPOSITION.json',dict(at=now(),current_processes_positive_in_parent=True,current_only_retirement_eligible_after_full_Root_completion=True,Root_actual_external_admission_is_separate_required_proof=True,inner_legacy_overhead_observation_is_not_complete_external_owner_job_audit=True,historical_native_and_other_holds_unchanged=True));durable_capture();print(json.dumps(dict(status=result['status'],finished_at=now())))
except BaseException as exc:
 cleanup=[]
 for cid in list(owned):
  try:
   state=json.loads(call('failure-inspect-'+cid[:8],docker+['inspect',cid]))[0]['State']
   if state['Running']:call('owned-bounded-stop-'+cid[:8],docker+['kill',cid]);call('owned-bounded-wait-'+cid[:8],docker+['wait',cid]);state=json.loads(call('failure-terminal-'+cid[:8],docker+['inspect',cid]))[0]['State']
   assert not state['Running'] and state['Pid']==0;call('failure-remove-'+cid[:8],docker+['rm',cid]);cleanup.append(dict(CID=cid,removed=True))
  except BaseException as e:cleanup.append(dict(CID=cid,state='UNKNOWN',error=str(e)))
 save('RESULT.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_REPLAY',started_at=started,finished_at=now(),error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),clients=clients,phases=phases,controls=control_rows,artifacts=artifacts,cleanup=cleanup));durable_capture();raise
