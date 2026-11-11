import sys,ast,datetime,hashlib,json,os,pathlib,re,shutil,signal,subprocess,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');BASE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z');M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110');HERE=pathlib.Path(__file__).parent;OUT=HERE/'execution-1';OUT.mkdir(mode=0o700,exist_ok=False)
prior=M/'f06-default-wiring-p04source-max-1/default-observation-1/run_root_once.py';tree=ast.parse(prior.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('pins','admit')],type_ignores=[]),str(prior),'exec'))
common=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py';tree=ast.parse(common.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save')],type_ignores=[]),str(common),'exec'))
shared=BASE/'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
cap=M/'root-reviewed-capture-correction-1/correction-1/phase-cpu6.py';assert sha(cap)=='7266db32ace8e167a14cc8a97cd91315f35356f117609da2c7a02cf97d7c2db3';exec(compile(cap.read_text(),str(cap),'exec'))
call_source=M/'joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py';assert sha(call_source)=='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4';exec(compile(call_source.read_text(),str(call_source),'exec'));pending_calls={}
ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py');docker=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'];clients=[];phases=[];owned=[];started=now();qpath=HERE/'REQUEST.json';review=pathlib.Path(sys.argv[1])
try:
 assert sha(qpath)=='17fd8f95af324998223aa7a0a35fdd8c7cb128299b08c51b4300a8c15006c2c7';assert sha(review)==sys.argv[2];q=json.loads(qpath.read_text());assert json.loads(review.read_text())['decision'].startswith('GO');pins(q['inputs']);bound=json.loads(pathlib.Path(q['inputs']['path']).read_text());pins(bound['immutable_HOST_files'])
 assert call('source-commit.before',['/usr/bin/git','rev-parse','HEAD']).decode().strip()==q['source_commit']=='7231ce6d17af39e9556ee815980a97f180b70eb1'
 assert call('IHK-commit.before',['/usr/bin/git','-C',str(ROOT/'ihk'),'rev-parse','HEAD']).decode().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
 for row in bound['actual_source_seven']:
  p=ROOT/row['path'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
 gate=bound['producer_receipt_not_yet_available'];pe=pathlib.Path(gate['directory']);proof=pe/'RESULT.json';x=json.loads(proof.read_text());assert x['status']==gate['required_status'] and x['source_commit']==q['source_commit'] and x['request_sha256']==gate['required_request_sha256'] and x['all_waits_streams_joined'] and not x['remaining_owned_children']
 assert len(x['phases'])==1 and x['phases'][0]['phase']=='build' and x['phases'][0]['exit']==0 and not x['phases'][0]['OOMKilled'] and x['phases'][0]['owned_container_removed'] and x['phases'][0]['client_wait_joined']
 expected_labels={'source-commit.before','IHK-commit.before','running-preflight','names-preflight','build-create','build-profile','build-running-inspect','build-payload','build-terminal','build-container-wait','build-owned-remove','source-commit.after','IHK-commit.after'}
 assert len(x['clients'])==13 and {row['label'] for row in x['clients']}==expected_labels
 for row in x['clients']:
  assert row['pid']>0 and int(row['birth'])>0 and row['exit']==0 and row['direct_wait_joined'] and row['streams_closed'] and not row.get('primary_error') and not row.get('secondary_errors') and not row.get('lifecycle_UNKNOWN')
  if row.get('creation_attempted'):assert row['popen_returned'] and row['receipt_persisted']
 release=pe/'RESOURCE-RELEASE.json';assert json.loads(release.read_text())['positive_all_scopes'] and json.loads(release.read_text())['current_jobs']=='RELEASED'
 terminal=pe/'build-TERMINAL.json';state=json.loads(terminal.read_text())['State'];assert state['ExitCode']==0 and not state['Running'] and state['Pid']==0 and not state['OOMKilled']
 completions=[]
 for name in ['ROOT-EXEC-COMPLETION.json','ROOT-EXEC-TOOL.json']:
  path=pe.parent/name
  if path.is_file():
   data=json.loads(path.read_text())
   if data.get('exit_code')==0 and not data.get('session_id'):completions.append(dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path)))
 assert completions
 artifacts=x['actual_artifacts'];assert len(artifacts)==4 and {row['path'] for row in artifacts}==set(gate['required_artifact_paths'])
 for row in artifacts:
  p=pathlib.Path(row['path']);assert row['bytes']>0 and p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
 save('ACTUAL-PRODUCER-BINDING.json',dict(result=dict(path=str(proof),bytes=proof.stat().st_size,sha256=sha(proof)),ResourceRelease=dict(path=str(release),sha256=sha(release)),terminal=dict(path=str(terminal),sha256=sha(terminal)),Rootfullcompletion=completions,new_actual_four_artifacts=artifacts,old14d_a70_not_substituted=True))
 assert not call('running-preflight',docker+['ps','-q']).strip();a=q['metadata_phase'];names=call('names-preflight',docker+['ps','-a','--format','{{.Names}}']).decode().splitlines();assert a['create_argv'][a['create_argv'].index('--name')+1] not in names
 meta=pathlib.Path(a['output_root']);assert not meta.exists();meta.mkdir(mode=0o755)
 admit('metadata',512*2**20);phase('metadata',a['create_argv'],a['expected_mounts'],512*2**20,64,a['max_wall_seconds'])
 assert call('source-commit.after',['/usr/bin/git','rev-parse','HEAD']).decode().strip()==q['source_commit']
 for row in bound['actual_source_seven']:
  p=ROOT/row['path'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
 for row in artifacts:assert sha(row['path'])==row['sha256'] and pathlib.Path(row['path']).stat().st_size==row['bytes']
 files=[meta/n for n in a['output_contract']['required_files']];assert len(files)==45 and all(p.is_file() and p.stat().st_size>0 for p in files)
 left=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not left and not owned and not pending_calls
 result=dict(status='PASS_JOINT7231_AFFECTED48_PASSIVE_READS45_OUTPUTS_PENDING_WHOLE_PROVIDER_ABI_OWNERSHIP_QUALIFICATION',started_at=started,finished_at=now(),source_commit=q['source_commit'],request_sha256=sha(qpath),review_sha256=sha(review),phases=phases,clients=clients,all_waits_streams_joined=True,remaining_owned_children=left,producer_binding_sha256=sha(OUT/'ACTUAL-PRODUCER-BINDING.json'),metadata=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in files],original_acceptance=False);save('RESULT.json',result);save('RESOURCE-RELEASE.json',dict(at=now(),current_jobs='RELEASED',positive_all_scopes=True,all_historical_native_other_holds_unchanged=True));print(json.dumps(dict(status=result['status'],finished_at=now(),metadata_files=len(files))))
except BaseException as exc:
 cleanup=[]
 for cid in list(owned):
  try:
   state=json.loads(call('failure-inspect-'+cid[:8],docker+['inspect',cid]))[0]['State']
   if state['Running']:call('owned-bounded-stop-'+cid[:8],docker+['kill',cid]);call('owned-bounded-wait-'+cid[:8],docker+['wait',cid]);state=json.loads(call('failure-terminal-'+cid[:8],docker+['inspect',cid]))[0]['State']
   assert not state['Running'] and state['Pid']==0;call('failure-remove-'+cid[:8],docker+['rm',cid]);cleanup.append(dict(CID=cid,removed=True))
  except BaseException as e:cleanup.append(dict(CID=cid,state='UNKNOWN',error=str(e)))
 save('RESULT.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_REPLAY',started_at=started,finished_at=now(),error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),clients=clients,phases=phases,cleanup=cleanup));raise
