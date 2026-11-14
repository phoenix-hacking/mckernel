import ast,datetime,hashlib,json,os,pathlib,re,shutil,subprocess,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');BASE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z');M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110');HERE=pathlib.Path(__file__).parent;OUT=HERE/'execution-1';OUT.mkdir(mode=0o700,exist_ok=False)
prior=HERE.parent/'run_root_once.py';tree=ast.parse(prior.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pins'],type_ignores=[]),str(prior),'exec'))
common=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py';tree=ast.parse(common.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save','call')],type_ignores=[]),str(common),'exec'))
shared=BASE/'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
cap=M/'root-reviewed-capture-correction-1/correction-1/phase-cpu6.py';assert sha(cap)=='7266db32ace8e167a14cc8a97cd91315f35356f117609da2c7a02cf97d7c2db3';exec(compile(cap.read_text(),str(cap),'exec'))
ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py');docker=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'];clients=[];phases=[];owned=[];started=now();qpath=HERE/'REQUEST.json';review=M/'f06-default-observation-review-p04tests-max-1/postgate-correction-1/REVIEW.json'
try:
 assert sha(qpath)=='8adfa3f79b03bb4e3b393ce0eea3511f048da9ad511ce6bad2a91d5f2ba248f9';assert sha(review)=='286003e89400bd51aecb2d19eb6b12f464db0b094d5c834ca7e45a8bb56cbd86';q=json.loads(qpath.read_text());pins(q['meaningful_changed_input']);pins(q['source_binding']);pins(q['metadata_phase']['helper'])
 assert call('source-commit',['/usr/bin/git','rev-parse','HEAD']).decode().strip()==q['source_commit']=='f37463cdd25f7f25e6c92c3f418c6dce3054a74f'
 stamp=guard();available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;rss=overhead();hf=shutil.disk_usage(ROOT).free;sf=shutil.disk_usage(HERE).free;reservation=1792*2**20
 assert available>=26*2**30 and rss+reservation<=4*2**30 and hf>=25*2**30 and sf>=21*2**30
 save('ADMISSION.json',dict(at=now(),guard_updated_at=stamp,MemAvailable=available,alloverhead=rss,total_planned_caps_including_callback_and_possible_light_guest=reservation,HOST_total=4*2**30,maxjobs=3,CPU=6,this_job_bytes=512*2**20,other_possible_jobs=[dict(CPU=7,bytes=1024*2**20,id='callback8ea5'),dict(CPU=0,bytes=256*2**20,id='guest6_requires_separateGO')],hostfree=hf,scratchfree=sf,extra_total_disk_headroom=9*2**30,old_HOST_current_charges=0,Native_or_other_holds_released=False))
 build=M/'compute-image-source-1/output/build';cache=(build/'CMakeCache.txt').read_text();assert 'ENABLE_RUST_F06_SYSCALL_WHOLE:BOOL=ON' in cache;ko=build/'tmp.resolve_MODULES_END/driver.ko';assert ko.stat().st_size>0 and ko.read_bytes()[:4]==b'\x7fELF'
 helper=pathlib.Path(q['meaningful_changed_input']['postgate_helper']['path']);ns={};exec(compile(helper.read_text(),str(helper),'exec'),ns);records=json.loads((build/'compile_commands.json').read_text());generated=(build/'kernel/config/smp-x86.lds').read_text();template=(ROOT/'kernel/config/smp-x86.lds.in').read_text()
 pg=ns['image_compile_postgate'](records,generated,template);rejects=ns['defined_rejection_checks'](records,generated,template);save('CORRECTED-POSTGATE.json',pg);save('DEFINED-REJECTIONS.json',rejects)
 running=call('running-preflight',docker+['ps','--no-trunc','--format','{{.ID}} {{.Names}}']).decode().splitlines()
 for line in running:
  cid,name=line.split(maxsplit=1);assert name=='mck-m15-sched-callback-type-20261111-1';peer=BASE/'sched-yield-callback-type-tests-sourceacq-max-1/execution-1/payload-OWNED-ID.json';assert json.loads(peer.read_text())['CID']==cid
 a=q['metadata_phase'];argv=a['create_argv'];name=argv[argv.index('--name')+1];assert name not in call('names-preflight',docker+['ps','-a','--format','{{.Names}}']).decode().splitlines()
 meta=pathlib.Path(a['output_root']);assert not meta.exists();meta.mkdir(mode=0o755)
 phase('metadata',argv,a['expected_mounts'],512*2**20,64,a['max_wall_seconds'])
 files=[meta/n for n in a['output_contract']['stdout_files']];assert len(files)==20 and all(f.is_file() and f.stat().st_size>0 for f in files)
 left=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not left and not owned
 result=dict(status='PASS_CORRECTED_POSTGATE_AND_PREVIOUSLY_UNSTARTED_METADATA_PENDING_EFFECTIVE_INPUT_REVIEW',started_at=started,finished_at=now(),source_commit=q['source_commit'],request_sha256=sha(qpath),review_sha256=sha(review),corrected_postgate=pg,defined_rejections=rejects,phases=phases,clients=clients,all_waits_streams_joined=True,remaining_owned_children=left,configure_or_image_replayed=False,original_acceptance=False,metadata=[dict(path=str(f),bytes=f.stat().st_size,sha256=sha(f)) for f in files]);save('RESULT.json',result);save('RESOURCE-RELEASE.json',dict(at=now(),current_job='RELEASED',bytes=512*2**20,jobs=1,positive_whole_scope=True,historical_native_holds_changed=False));print(json.dumps(dict(status=result['status'],metadata_files=len(files),finished_at=now())))
except BaseException as exc:
 cleanup=[]
 for cid in list(owned):
  try:
   state=json.loads(call('failure-inspect-'+cid[:8],docker+['inspect',cid]))[0]['State']
   if state['Running']:call('owned-bounded-stop-'+cid[:8],docker+['kill',cid]);call('owned-bounded-wait-'+cid[:8],docker+['wait',cid]);state=json.loads(call('failure-terminal-'+cid[:8],docker+['inspect',cid]))[0]['State']
   assert not state['Running'] and state['Pid']==0;call('failure-remove-'+cid[:8],docker+['rm',cid]);cleanup.append(dict(CID=cid,removed=True))
  except BaseException as e:cleanup.append(dict(CID=cid,state='UNKNOWN',error=str(e)))
 save('RESULT.json',dict(status='FAILED_PRESERVED_NO_REPLAY',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),clients=clients,phases=phases,cleanup=cleanup));raise
