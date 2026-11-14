import sys,ast,datetime,hashlib,json,os,pathlib,re,shutil,signal,subprocess,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');BASE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z');M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110');HERE=pathlib.Path(__file__).parent;OUT=HERE/'execution-1';OUT.mkdir(mode=0o700,exist_ok=False)
prior=M/'f06-default-wiring-p04source-max-1/default-observation-1/run_root_once.py';tree=ast.parse(prior.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('pins',)],type_ignores=[]),str(prior),'exec'))
common=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py';tree=ast.parse(common.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save')],type_ignores=[]),str(common),'exec'))
shared=BASE/'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
cap=M/'root-reviewed-capture-correction-1/correction-1/phase-cpu6.py';assert sha(cap)=='7266db32ace8e167a14cc8a97cd91315f35356f117609da2c7a02cf97d7c2db3';exec(compile(cap.read_text(),str(cap),'exec'))
call_source=M/'joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py';assert sha(call_source)=='e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4';exec(compile(call_source.read_text(),str(call_source),'exec'));pending_calls={}
ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py');docker=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'];clients=[];phases=[];owned=[];started=now();qpath=HERE/'REQUEST.json';review=pathlib.Path(sys.argv[1])
def admit(label,need):
    stamp=guard();available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;rss=overhead();hf=shutil.disk_usage(ROOT).free;sf=shutil.disk_usage(HERE).free;r=q['resources'];growth=r['output_disk_reservation_bytes']
    assert available>=r['fresh_MemAvailable_min_bytes'] and rss+need<=r['shared_HOST_alloverhead_bytes'] and hf>=r['host_disk_floor_bytes']+growth and sf>=r['scratch_disk_floor_bytes']+growth
    save(label+'-ADMISSION.json',dict(at=now(),guard_updated_at=stamp,MemAvailable_bytes=available,all_current_overhead_bytes=rss,this_phase_bytes=need,HOST_total=r['shared_HOST_alloverhead_bytes'],maxjobs=r['shared_jobs_max'],hostfree=hf,scratchfree=sf,disk_growth_reserved=growth,current_other_payloads=0,M14producer_reader_positive_retired=True,native_or_other_holds_released=False))
try:
 assert sha(qpath)=='8fc711cbcca8ab7bb58405018d023591a039574ff6ff7930e607324d4e299ae4';assert sha(review)==sys.argv[2];adapter=json.loads(qpath.read_text());assert json.loads(review.read_text())['decision'].startswith('GO');pins(adapter['execution_request']);qp=pathlib.Path(adapter['execution_request']['path']);q=json.loads(qp.read_text());assert sha(qp)=='3f35f5a8378145c1838db89f6801308cb57451de9c4dcd402547d19ebd6d24b5';pins(adapter['inputs']);bound=json.loads(pathlib.Path(adapter['inputs']['path']).read_text());pins(bound['actual_execution_HOST_files']);pins(bound['immutable_metadata_receipts'])
 prior_receipts=[]
 for gate in bound['current_M14_prerequisites']:
  e=pathlib.Path(gate['directory']);p=e/'RESULT.json';x=json.loads(p.read_text());assert x['status']==gate['status'] and x['source_commit']=='7231ce6d17af39e9556ee815980a97f180b70eb1' and x['request_sha256']==gate['request_sha256'] and x['all_waits_streams_joined'] and not x['remaining_owned_children']
  assert len(x['phases'])==1 and x['phases'][0]['phase']==gate['phase'] and x['phases'][0]['exit']==0 and not x['phases'][0]['OOMKilled'] and x['phases'][0]['owned_container_removed'] and x['phases'][0]['client_wait_joined']
  assert len(x['clients'])==gate['clients']
  for row in x['clients']:
   assert row['pid']>0 and int(row['birth'])>0 and row['exit']==0 and row['direct_wait_joined'] and row['streams_closed'] and not row.get('primary_error') and not row.get('secondary_errors') and not row.get('lifecycle_UNKNOWN')
   if row.get('creation_attempted'):assert row['popen_returned'] and row['receipt_persisted']
  release=e/'RESOURCE-RELEASE.json';d=json.loads(release.read_text());assert d['current_jobs']=='RELEASED' and d['positive_all_scopes'];terminal=e/(gate['phase']+'-TERMINAL.json');state=json.loads(terminal.read_text())['State'];assert state['ExitCode']==0 and not state['Running'] and state['Pid']==0 and not state['OOMKilled']
  completions=[]
  for name in ['ROOT-EXEC-COMPLETION.json','ROOT-EXEC-TOOL.json']:
   path=e.parent/name
   if path.is_file():
    data=json.loads(path.read_text())
    if data.get('exit_code')==0 and not data.get('session_id'):completions.append(dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path)))
  assert completions;prior_receipts.append(dict(scope=gate['kind'],result=dict(path=str(p),sha256=sha(p)),release=dict(path=str(release),sha256=sha(release)),terminal=dict(path=str(terminal),sha256=sha(terminal)),Rootfullcompletion=completions))
 save('M14-POSITIVE-RETIREMENT-BINDING.json',prior_receipts)
 assert call('source-commit.before',['/usr/bin/git','rev-parse','HEAD']).decode().strip()=='7231ce6d17af39e9556ee815980a97f180b70eb1'
 assert call('IHK-commit.before',['/usr/bin/git','-C',str(ROOT/'ihk'),'rev-parse','HEAD']).decode().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
 for row in bound['canonical_selected_script_rows']:assert sha(ROOT/row['relative'])==row['sha256']
 assert not call('running-preflight',docker+['ps','-q']).strip();names=call('names-preflight',docker+['ps','-a','--format','{{.Names}}']).decode().splitlines();assert q['create_argv'][q['create_argv'].index('--name')+1] not in names
 for mount in q['expected_mounts']:
  dst=mount['destination'].rstrip('/');assert all(target!=dst and not target.startswith(dst+'/') for target in ('/usr/bin/cc','/usr/bin/gcc','/usr/lib64/libc.so.6'))
 output=pathlib.Path(q['output_root']);assert not output.exists();output.mkdir(mode=0o700);(output/'tmp').mkdir(mode=0o700);(output/'capture').mkdir(mode=0o700)
 admit('scripts',q['resources']['memory_bytes']);phase('scripts',q['create_argv'],q['expected_mounts'],q['resources']['memory_bytes'],q['resources']['pids'],q['max_wall_seconds'])
 proof=output/'RESULT.json';x=json.loads(proof.read_text());assert x['status']=='PASS_THREE_REAL_ROCKY195_PROGRAM_ARTIFACTS_AND_INSTALL_PENDING_SOURCE_ABI_PROVIDER_REPRO_QUALIFICATION' and len(x['artifacts'])==3 and len(x['configs_equal_previous_production_values'])==2 and len(x['ownership'])==8 and not x['old_cases_or_programs_executed'] and not x['actual_target_main_native_device_execution']
 labels=[c['label'] for c in q['commands']];assert [r['label'] for r in x['ownership']]==labels
 for row in x['ownership']:assert int(row['leader'])>0 and int(row['leader_birth'])>0 and row['status']==0 and row['leader_parent_joined'] and row['whole_descendants_joined'] and row['streams_closed'] and not row['timed_out'] and not row['leader_group_signalled'] and not row['adopted_reaps'] and not row['adopted_kills'] and not row['remaining_direct_children'] and row['error'] is None
 for row in x['artifacts']:
  for key in ['built','installed']:
   f=row[key];p=output/pathlib.Path(f['path']).relative_to('/output');assert p.is_file() and p.stat().st_size==f['bytes'] and sha(p)==f['sha256']
  assert row['same_bytes'] and row['installed0755'] and row['built']['sha256']==row['installed']['sha256'] and row['installed']['mode']=='0o755'
 assert call('source-commit.after',['/usr/bin/git','rev-parse','HEAD']).decode().strip()=='7231ce6d17af39e9556ee815980a97f180b70eb1'
 assert call('IHK-commit.after',['/usr/bin/git','-C',str(ROOT/'ihk'),'rev-parse','HEAD']).decode().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
 for row in bound['canonical_selected_script_rows']:assert sha(ROOT/row['relative'])==row['sha256']
 left=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not left and not owned and not pending_calls
 result=dict(status='PASS_THREE_ROCKY195_REPRO_PROGRAMS_EIGHT_INNER_COMMANDS_PENDING_WHOLE_SDK_SOURCE_PROVIDER_QUALIFICATION',started_at=started,finished_at=now(),source_commit='7231ce6d17af39e9556ee815980a97f180b70eb1',request_sha256=sha(qp),adapter_sha256=sha(qpath),review_sha256=sha(review),phases=phases,clients=clients,all_waits_streams_joined=True,remaining_owned_children=left,payload_result=dict(path=str(proof),bytes=proof.stat().st_size,sha256=sha(proof)),old_cases_or_program_main_replayed=False,original_acceptance=False);save('RESULT.json',result);save('RESOURCE-RELEASE.json',dict(at=now(),current_jobs='RELEASED',positive_all_scopes=True,all_historical_native_other_holds_unchanged=True));print(json.dumps(dict(status=result['status'],finished_at=now(),new_programs=3,inner_commands=8)))
except BaseException as exc:
 cleanup=[]
 for cid in list(owned):
  try:
   state=json.loads(call('failure-inspect-'+cid[:8],docker+['inspect',cid]))[0]['State']
   if state['Running']:call('owned-bounded-stop-'+cid[:8],docker+['kill',cid]);call('owned-bounded-wait-'+cid[:8],docker+['wait',cid]);state=json.loads(call('failure-terminal-'+cid[:8],docker+['inspect',cid]))[0]['State']
   assert not state['Running'] and state['Pid']==0;call('failure-remove-'+cid[:8],docker+['rm',cid]);cleanup.append(dict(CID=cid,removed=True))
  except BaseException as e:cleanup.append(dict(CID=cid,state='UNKNOWN',error=str(e)))
 save('RESULT.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_REPLAY',started_at=started,finished_at=now(),error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),clients=clients,phases=phases,cleanup=cleanup));raise
