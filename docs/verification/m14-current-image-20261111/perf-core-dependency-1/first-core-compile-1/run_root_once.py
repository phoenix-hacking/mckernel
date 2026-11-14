import sys,ast,datetime,hashlib,json,os,pathlib,re,shutil,signal,subprocess,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');BASE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z');M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110');HERE=pathlib.Path(__file__).parent;PACKET=HERE;OUT=HERE/'execution-1';OUT.mkdir(mode=0o700,exist_ok=False)
prior=M/'f06-default-wiring-p04source-max-1/default-observation-1/run_root_once.py';assert hashlib.sha256(prior.read_bytes()).hexdigest()=='5695c81f42964567652b3a4c0a8ea0c009bc98eb1918ed765c8af88e27ae5f35';tree=ast.parse(prior.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('pins','admit')],type_ignores=[]),str(prior),'exec'))
common=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py';assert hashlib.sha256(common.read_bytes()).hexdigest()=='e6091bb418f619222f7a51ddef718ceeb75bb449f5abd10d62b40018b623db38';tree=ast.parse(common.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save')],type_ignores=[]),str(common),'exec'))
shared=BASE/'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';assert hashlib.sha256(shared.read_bytes()).hexdigest()=='983b8c3ceabcd8dc4d2e1999d75e6edbef91145a5f2ab18bfa1a2dfa6639c822';tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
cap=M/'root-reviewed-capture-correction-1/correction-1/phase-cpu6.py';assert sha(cap)=='7266db32ace8e167a14cc8a97cd91315f35356f117609da2c7a02cf97d7c2db3';exec(compile(cap.read_text(),str(cap),'exec'))
call_source=M/'joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py';assert sha(call_source)=='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4';exec(compile(call_source.read_text(),str(call_source),'exec'));pending_calls={}
ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py');docker=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'];clients=[];phases=[];owned=[];started=now();qpath=PACKET/'REQUEST.json';review=pathlib.Path(sys.argv[1])
try:
 assert sha(qpath)=='87afd55bad2355f4d626a215c0299e0fec921d6e25f901cabcde960cdda93824';assert sha(review)==sys.argv[2];assert json.loads(review.read_text())['decision'].startswith('GO');q=json.loads(qpath.read_text())
 pins(q['inputs']);data=json.loads(pathlib.Path(q['inputs']['path']).read_text());pins(data['actual_execution_HOST_files']);pins(data['immutable_receipt_files']);pins(q['repair_contract']);pins(q['completed_failure_and_current_retirement'])
 receipt=q['completed_failure_and_current_retirement'];retired=json.loads(pathlib.Path(receipt['current_process_retirement']['path']).read_text());assert retired['after']=={'bytes':0,'jobs':0} and retired['qualification_sha256']==receipt['independent_failure_qualification']['sha256']
 assert not call('running-preflight',docker+['ps','-q']).strip();names=call('names-preflight',docker+['ps','-a','--format','{{.Names}}']).decode().splitlines();a=q['core_phase'];assert a['create_argv'][a['create_argv'].index('--name')+1] not in names
 admit('core-build',2*2**30);pathlib.Path(a['output_root']).mkdir(mode=0o700,exist_ok=False)
 phase('core-build',a['create_argv'],a['expected_mounts'],2*2**30,256,a['max_wall_seconds'])
 outputs=[]
 for name in q['output_files']:
  p=pathlib.Path(a['output_root'])/name;assert p.is_file() and p.stat().st_size>0
  if name=='core.o':assert p.read_bytes()[:6]==b'\x7fELF\x02\x01'
  outputs.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p),mode=oct(p.stat().st_mode&0o777)))
 for row in data['actual_execution_HOST_files']:assert sha(row['path'])==row['sha256'] and pathlib.Path(row['path']).stat().st_size==row['bytes']
 left=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not left and not owned and not pending_calls
 result=dict(status='PASS_NEW_GENUINE_CORE_DEPENDENCY_COMPILER_PENDING_PROVIDER_AND_CONSUMER_IMAGE_QUALIFICATION',started_at=started,finished_at=now(),request_sha256=sha(qpath),review_sha256=sha(review),phases=phases,clients=clients,all_waits_streams_joined=True,remaining_owned_children=left,actual_artifacts=outputs,kernel_or_consumer_or_native_executed=False,original_acceptance=False);save('RESULT.json',result);save('RESOURCE-RELEASE.json',dict(at=now(),current_jobs='RELEASED',positive_all_scopes=True,all_historical_native_other_holds_unchanged=True));print(json.dumps(dict(status=result['status'],finished_at=now())))
except BaseException as exc:
 cleanup=[]
 for cid in list(owned):
  try:
   state=json.loads(call('failure-inspect-'+cid[:8],docker+['inspect',cid]))[0]['State']
   if state['Running']:call('owned-bounded-stop-'+cid[:8],docker+['kill',cid]);call('owned-bounded-wait-'+cid[:8],docker+['wait',cid]);state=json.loads(call('failure-terminal-'+cid[:8],docker+['inspect',cid]))[0]['State']
   assert not state['Running'] and state['Pid']==0;call('failure-remove-'+cid[:8],docker+['rm',cid]);cleanup.append(dict(CID=cid,removed=True))
  except BaseException as e:cleanup.append(dict(CID=cid,state='UNKNOWN',error=str(e)))
 save('RESULT.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_REPLAY',started_at=started,finished_at=now(),error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),clients=clients,phases=phases,cleanup=cleanup));raise
