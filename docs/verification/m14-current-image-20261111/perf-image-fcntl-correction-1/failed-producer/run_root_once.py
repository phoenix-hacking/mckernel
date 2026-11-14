import sys,ast,datetime,hashlib,json,os,pathlib,re,shutil,signal,subprocess,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');BASE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z');M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110');HERE=pathlib.Path(__file__).parent;PACKET=HERE;OUT=HERE/'execution-1';OUT.mkdir(mode=0o700,exist_ok=False)
prior=M/'f06-default-wiring-p04source-max-1/default-observation-1/run_root_once.py';assert hashlib.sha256(prior.read_bytes()).hexdigest()=='5695c81f42964567652b3a4c0a8ea0c009bc98eb1918ed765c8af88e27ae5f35';tree=ast.parse(prior.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('pins','admit')],type_ignores=[]),str(prior),'exec'))
common=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py';assert hashlib.sha256(common.read_bytes()).hexdigest()=='e6091bb418f619222f7a51ddef718ceeb75bb449f5abd10d62b40018b623db38';tree=ast.parse(common.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save')],type_ignores=[]),str(common),'exec'))
shared=BASE/'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';assert hashlib.sha256(shared.read_bytes()).hexdigest()=='983b8c3ceabcd8dc4d2e1999d75e6edbef91145a5f2ab18bfa1a2dfa6639c822';tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
cap=M/'root-reviewed-capture-correction-1/correction-1/phase-cpu6.py';assert sha(cap)=='7266db32ace8e167a14cc8a97cd91315f35356f117609da2c7a02cf97d7c2db3';exec(compile(cap.read_text(),str(cap),'exec'))
call_source=M/'joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py';assert sha(call_source)=='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4';exec(compile(call_source.read_text(),str(call_source),'exec'));pending_calls={}
ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py');docker=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'];clients=[];phases=[];owned=[];started=now();qpath=PACKET/'REQUEST.json';review=pathlib.Path(sys.argv[1])
try:
 assert sha(qpath)=='766ec460085252c2dbfd5f7b16cbed668ddd1a97d740cdeeb0b38c96f666c18b';assert sha(review)==sys.argv[2];q=json.loads(qpath.read_text());assert json.loads(review.read_text())['decision'].startswith('GO')
 pins(q['inputs']);inputs=json.loads(pathlib.Path(q['inputs']['path']).read_text());pins(inputs['actual_execution_HOST_files']);pins(inputs['immutable_receipt_files']);pins(q['source_binding']);binding=json.loads(pathlib.Path(q['source_binding']['path']).read_text())
 pins(q['mandatory_completed_prerequisites']);proof=q['mandatory_completed_prerequisites']
 rt=json.loads(pathlib.Path(proof['runtime_result']['path']).read_text());assert rt['status']=='PASS_NEW_PERF_ACTUAL18_UNITS_FOUR_FUNCTIONAL_FAMILIES_PENDING_SAVED_QUALIFICATION' and rt['all_waits_streams_joined'] and rt['remaining_direct_children']==[] and [v['exit'] for v in rt['results']]==[0,0]
 qual=json.loads(pathlib.Path(proof['runtime_independent_qualification']['path']).read_text());assert qual['decision']=='GO_QUALIFIED_ACTUAL_CORRECTED18_OWNER_HOST_COMPILE_LINK_AND_ALL_FOUR_FUNCTIONAL_FAMILIES_AND_CURRENT_PROCESS_ONLY_RETIREMENT'
 complete=json.loads(pathlib.Path(proof['runtime_Root_completion']['path']).read_text());assert complete['full_root_tool_terminal'] is True and complete['session_id_remaining'] is None and complete['actual_terminal_exit']==0
 retired=json.loads(pathlib.Path(proof['runtime_current_process_retirement']['path']).read_text());assert retired['decision']=='RETIRED_ONLY_CURRENT_PERF_RUNTIME_PROCESS_CHARGE' and retired['after']=={'bytes':0,'jobs':0} and retired['qualification_sha256']==proof['runtime_independent_qualification']['sha256'] and retired['Root_completion_sha256']==proof['runtime_Root_completion']['sha256'] and retired['historical_UNKNOWN_reservations_unchanged'] is True
 selection=json.loads(pathlib.Path(proof['selection_source_GO']['path']).read_text());assert selection['verdict']=='GO_SELECTION_SOURCE_ONLY'
 for key in ['coherent_material_source_oracle_GO','bounded_fixture_correction_GO']:assert json.loads(pathlib.Path(proof[key]['path']).read_text())['decision'].startswith('GO_')
 integration=json.loads(pathlib.Path(proof['canonical_integration']['path']).read_text());assert integration['actual_runtime_qualification_sha256']==proof['runtime_independent_qualification']['sha256'] and integration['source_GO_sha256']==proof['selection_source_GO']['sha256'] and integration['canonical_files']==[{'path':row['path'],'sha256':row['sha256']} for row in binding['expected_current_source_rows']]
 sdk=inputs['image_scoped_SDK'];assert sdk['immutable_image']=='sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94' and sdk['C_compiler']=={'GCC_include':'/usr/lib/gcc/x86_64-redhat-linux/14/include','path':'/usr/bin/cc','resolved':'/usr/bin/gcc','sha256':'2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2','version':'gcc14.3.1-4.4.el10'}
 for mount in q['build_phase']['expected_mounts']:
  dst=mount['destination'].rstrip('/');assert all(target!=dst and not target.startswith(dst+'/') for target in ('/usr/bin/cc','/usr/bin/gcc'))
 for when in ['before']:
  assert call('source-commit.'+when,['/usr/bin/git','rev-parse','HEAD']).decode().strip()==q['source_commit']=='afb1fced3e3b1ec7d27a5539e085be5f6b841dc6'
  assert call('IHK-commit.'+when,['/usr/bin/git','-C',str(ROOT/'ihk'),'rev-parse','HEAD']).decode().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
  rows=[]
  for row in binding['expected_current_source_rows']:
   p=ROOT/row['path'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'];rows.append(row)
  save('SOURCE-CURRENT.'+when+'.json',rows)
 cache=M/'compute-image-source-1/output/build/CMakeCache.txt';text=cache.read_text()
 for token in q['current_cache_required_fields']:assert token in text,token
 save('PREBUILD-CACHE.json',{'path':str(cache),'sha256':sha(cache),'required_fields':q['current_cache_required_fields'],'cache_not_invalidated':True})
 baseline=json.loads(pathlib.Path(q['preserved_current25']['path']).read_text());assert baseline['all25_inode_independent']
 for row in baseline['files']:assert sha(row['path'])==row['sha256']
 assert not call('running-preflight',docker+['ps','-q']).strip();names=call('names-preflight',docker+['ps','-a','--format','{{.Names}}']).decode().splitlines();a=q['build_phase'];assert a['create_argv'][a['create_argv'].index('--name')+1] not in names
 admit('build',2*2**30);phase('build',a['create_argv'],a['expected_mounts'],2*2**30,256,a['max_wall_seconds'])
 assert call('source-commit.after',['/usr/bin/git','rev-parse','HEAD']).decode().strip()==q['source_commit']
 assert call('IHK-commit.after',['/usr/bin/git','-C',str(ROOT/'ihk'),'rev-parse','HEAD']).decode().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
 for row in binding['expected_current_source_rows']:
  p=ROOT/row['path'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
 save('SOURCE-CURRENT.after.json',binding['expected_current_source_rows']);artifacts=[];b=M/'compute-image-source-1/output/build'
 for rel in ['kernel/mckernel.img','kernel/mckernel.img.map','kernel/rust/mckernel_rust.o','kernel/CMakeFiles/mckernel.img.dir/syscall.c.o']:
  p=b/rel;assert p.is_file() and p.stat().st_size>0
  if not rel.endswith('.map'):assert p.read_bytes()[:6]==b'\x7fELF\x02\x01'
  artifacts.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p),mode=oct(p.stat().st_mode&0o777)))
 left=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not left and not owned and not pending_calls
 result=dict(status='PASS_PERF_OWNER_NORMAL_NAMED_IMAGE_PRODUCER_PENDING_SEPARATE_AFFECTED_READER_AND_WHOLE_QUALIFICATION',started_at=started,finished_at=now(),source_commit=q['source_commit'],request_sha256=sha(qpath),review_sha256=sha(review),phases=phases,clients=clients,all_waits_streams_joined=True,remaining_owned_children=left,actual_artifacts=artifacts,following_reader_executed=False,original_acceptance=False);save('RESULT.json',result);save('RESOURCE-RELEASE.json',dict(at=now(),current_jobs='RELEASED',positive_all_scopes=True,all_historical_native_other_holds_unchanged=True));print(json.dumps(dict(status=result['status'],finished_at=now(),following_reader_executed=False)))
except BaseException as exc:
 cleanup=[]
 for cid in list(owned):
  try:
   state=json.loads(call('failure-inspect-'+cid[:8],docker+['inspect',cid]))[0]['State']
   if state['Running']:call('owned-bounded-stop-'+cid[:8],docker+['kill',cid]);call('owned-bounded-wait-'+cid[:8],docker+['wait',cid]);state=json.loads(call('failure-terminal-'+cid[:8],docker+['inspect',cid]))[0]['State']
   assert not state['Running'] and state['Pid']==0;call('failure-remove-'+cid[:8],docker+['rm',cid]);cleanup.append(dict(CID=cid,removed=True))
  except BaseException as e:cleanup.append(dict(CID=cid,state='UNKNOWN',error=str(e)))
 save('RESULT.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_REPLAY',started_at=started,finished_at=now(),error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),clients=clients,phases=phases,cleanup=cleanup));raise
