import ast,datetime,hashlib,json,os,pathlib,re,shutil,subprocess,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');BASE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z');M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110');HERE=pathlib.Path(__file__).parent;OUT=HERE/'execution-1';OUT.mkdir(mode=0o700,exist_ok=False)
prior=HERE.parent/'run_root_once.py';tree=ast.parse(prior.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('pins','admit')],type_ignores=[]),str(prior),'exec'))
common=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py';tree=ast.parse(common.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save','call')],type_ignores=[]),str(common),'exec'))
shared=BASE/'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
cap=M/'root-reviewed-capture-correction-1/correction-1/phase-cpu6.py';assert sha(cap)=='7266db32ace8e167a14cc8a97cd91315f35356f117609da2c7a02cf97d7c2db3';exec(compile(cap.read_text(),str(cap),'exec'))
ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py');docker=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'];clients=[];phases=[];owned=[];started=now();qpath=HERE/'REQUEST.json';review=M/'compute-image-operation-review-p03-max-1/default-required-named-image-1/REVIEW.json'
try:
 assert sha(qpath)=='34529bbed5bd00dd844abfe5b0ceedbd35da4c943e743b9cbe23515151287bad';assert sha(review)=='5de5722a74663890f7f19b97ef65ca932ac71b4828269f0926950965963d648e';q=json.loads(qpath.read_text());pins(q['source_binding']);pins(q['hash_phase']['helper']);pins(q['conditional_changed_ELF_phase']['helper'])
 assert call('source-commit',['/usr/bin/git','rev-parse','HEAD']).decode().strip()==q['source_commit']=='f37463cdd25f7f25e6c92c3f418c6dce3054a74f'
 assert json.loads((BASE/'mcstat-sched-yield-matching-provider-build-1/qualified-callback-1/production-execution-1/RESOURCE-RELEASE.json').read_text())['current_job']=='RELEASED'
 assert not call('running-preflight',docker+['ps','-q']).strip();names=call('names-preflight',docker+['ps','-a','--format','{{.Names}}']).decode().splitlines()
 for key in ('build_phase','hash_phase','conditional_changed_ELF_phase'):
  a=q[key]['create_argv'];assert a[a.index('--name')+1] not in names
 for key in ('hash_phase','conditional_changed_ELF_phase'):assert not pathlib.Path(q[key]['output_root']).exists()
 admit('build',2*2**30);a=q['build_phase'];phase('build',a['create_argv'],a['expected_mounts'],2*2**30,256,a['max_wall_seconds'])
 a=q['hash_phase'];meta=pathlib.Path(a['output_root']);meta.mkdir(mode=0o755);admit('hash',512*2**20);phase('hash',a['create_argv'],a['expected_mounts'],512*2**20,64,a['max_wall_seconds'])
 found={}
 for line in (meta/'postbuild-16-identities.sha256').read_text().splitlines():
  h,name=line.split(maxsplit=1);assert re.fullmatch('[0-9a-f]{64}',h) and name not in found;found[name]=h
 expected=q['baseline_expected16_identities'];assert set(found)==set(expected) and len(found)==16
 changed=[k for k in expected if found[k]!=expected[k]];changed_inputs=[k for k in changed if k in ['/work/output/build/config.h','/work/output/build/ihk/config.h','/work/output/build/kernel/config/smp-x86.lds']]
 save('POSTBUILD-COMPARISON.json',dict(actual=found,baseline=expected,changed=changed,immutable_config_or_linker_changes=changed_inputs,all13_artifacts_equal=not changed));assert not changed_inputs,'Immutableconfig/linker changed; stop for exactqualification'
 if changed:
  a=q['conditional_changed_ELF_phase'];meta2=pathlib.Path(a['output_root']);meta2.mkdir(mode=0o755);admit('changed-ELF',512*2**20);phase('changed-ELF',a['create_argv'],a['expected_mounts'],512*2**20,64,a['max_wall_seconds'])
  assert (meta2/'STATUS').read_text().strip()=='PASS_CHANGED_BYTE_PASSIVE_READ_ONLY'
 left=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not left and not owned
 result=dict(status='PASS_REQUIRED_NORMAL_IMAGE_AND_MINIMAL_POSTBUILD_INPUT_CAPTURE_PENDING_WHOLE_E2_REVIEW',started_at=started,finished_at=now(),source_commit=q['source_commit'],request_sha256=sha(qpath),review_sha256=sha(review),phases=phases,clients=clients,all_waits_streams_joined=True,remaining_owned_children=left,postbuild_identities=found,changed_artifacts=changed,unchanged100d_deep_ownership_reused=not changed,conditional_ELF_read_executed=bool(changed),configure_replayed=False,original_acceptance=False);save('RESULT.json',result);save('RESOURCE-RELEASE.json',dict(at=now(),current_jobs='RELEASED',positive_all_scopes=True,all_historical_native_other_holds_unchanged=True));print(json.dumps(dict(status=result['status'],finished_at=now(),changed_artifacts=changed)))
except BaseException as exc:
 cleanup=[]
 for cid in list(owned):
  try:
   state=json.loads(call('failure-inspect-'+cid[:8],docker+['inspect',cid]))[0]['State']
   if state['Running']:call('owned-bounded-stop-'+cid[:8],docker+['kill',cid]);call('owned-bounded-wait-'+cid[:8],docker+['wait',cid]);state=json.loads(call('failure-terminal-'+cid[:8],docker+['inspect',cid]))[0]['State']
   assert not state['Running'] and state['Pid']==0;call('failure-remove-'+cid[:8],docker+['rm',cid]);cleanup.append(dict(CID=cid,removed=True))
  except BaseException as e:cleanup.append(dict(CID=cid,state='UNKNOWN',error=str(e)))
 save('RESULT.json',dict(status='FAILED_PRESERVED_NO_REPLAY',started_at=started,finished_at=now(),error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),clients=clients,phases=phases,cleanup=cleanup));raise
