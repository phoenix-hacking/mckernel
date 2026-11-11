import sys,ast,datetime,hashlib,json,os,pathlib,re,shutil,subprocess,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');BASE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z');M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110');HERE=pathlib.Path(__file__).parent;OUT=HERE/'execution-1';OUT.mkdir(mode=0o700,exist_ok=False)
prior=M/'f06-default-wiring-p04source-max-1/default-observation-1/run_root_once.py';tree=ast.parse(prior.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('pins','admit')],type_ignores=[]),str(prior),'exec'))
common=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py';tree=ast.parse(common.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save','call')],type_ignores=[]),str(common),'exec'))
shared=BASE/'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
cap=M/'root-reviewed-capture-correction-1/correction-1/phase-cpu6.py';assert sha(cap)=='7266db32ace8e167a14cc8a97cd91315f35356f117609da2c7a02cf97d7c2db3';exec(compile(cap.read_text(),str(cap),'exec'))
ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py');docker=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'];clients=[];phases=[];owned=[];started=now();qpath=HERE/'REQUEST.json';review=pathlib.Path(sys.argv[1])
try:
 assert sha(qpath)=='9e1d970a3716168bb66efc7d09324d18ada0da90f6c19d2fe9d50d8cb59f8a63';assert sha(review)==sys.argv[2];q=json.loads(qpath.read_text());assert json.loads(review.read_text())['decision'].startswith('GO')
 pins(q['inputs']);inputs=json.loads(pathlib.Path(q['inputs']['path']).read_text());pins(inputs['actual_execution_HOST_files']);pins(inputs['immutable_receipt_files']);pins(q['source_binding']);binding=json.loads(pathlib.Path(q['source_binding']['path']).read_text())
 sdk=inputs['image_scoped_SDK'];assert sdk['immutable_image']=='sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94' and sdk['C_compiler']=={'GCC_include':'/usr/lib/gcc/x86_64-redhat-linux/14/include','path':'/usr/bin/cc','resolved':'/usr/bin/gcc','sha256':'2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2','version':'gcc14.3.1-4.4.el10'}
 for mount in q['build_phase']['expected_mounts']:
  dst=mount['destination'].rstrip('/');assert all(target!=dst and not target.startswith(dst+'/') for target in ('/usr/bin/cc','/usr/bin/gcc'))
 for when in ['before']:
  assert call('source-commit.'+when,['/usr/bin/git','rev-parse','HEAD']).decode().strip()==q['source_commit']=='7231ce6d17af39e9556ee815980a97f180b70eb1'
  assert call('IHK-commit.'+when,['/usr/bin/git','-C',str(ROOT/'ihk'),'rev-parse','HEAD']).decode().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
  rows=[]
  for row in binding['expected_new_seven_source_rows']:
   p=ROOT/row['path'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'];rows.append(row)
  save('SOURCE-SEVEN.'+when+'.json',rows)
 cache=M/'compute-image-source-1/output/build/CMakeCache.txt';text=cache.read_text()
 for token in q['current_cache_required_fields']:assert token in text,token
 save('PREBUILD-CACHE.json',{'path':str(cache),'sha256':sha(cache),'required_fields':q['current_cache_required_fields'],'cache_not_invalidated':True})
 baseline=json.loads(pathlib.Path(q['recoverable14d_a70_25file_baseline']['path']).read_text());assert baseline['all25_inode_independent']
 for row in baseline['files']:assert sha(row['path'])==row['sha256']
 assert not call('running-preflight',docker+['ps','-q']).strip();names=call('names-preflight',docker+['ps','-a','--format','{{.Names}}']).decode().splitlines();a=q['build_phase'];assert a['create_argv'][a['create_argv'].index('--name')+1] not in names
 admit('build',2*2**30);phase('build',a['create_argv'],a['expected_mounts'],2*2**30,256,a['max_wall_seconds'])
 assert call('source-commit.after',['/usr/bin/git','rev-parse','HEAD']).decode().strip()==q['source_commit']
 assert call('IHK-commit.after',['/usr/bin/git','-C',str(ROOT/'ihk'),'rev-parse','HEAD']).decode().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
 for row in binding['expected_new_seven_source_rows']:
  p=ROOT/row['path'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
 save('SOURCE-SEVEN.after.json',binding['expected_new_seven_source_rows']);artifacts=[];b=M/'compute-image-source-1/output/build'
 for rel in ['kernel/mckernel.img','kernel/mckernel.img.map','kernel/rust/mckernel_rust.o','kernel/CMakeFiles/mckernel.img.dir/syscall.c.o']:
  p=b/rel;assert p.is_file() and p.stat().st_size>0
  if not rel.endswith('.map'):assert p.read_bytes()[:6]==b'\x7fELF\x02\x01'
  artifacts.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p),mode=oct(p.stat().st_mode&0o777)))
 left=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not left and not owned
 result=dict(status='PASS_JOINT7231_NORMAL_NAMED_IMAGE_PRODUCER_PENDING_SEPARATE_AFFECTED_READER_AND_WHOLE_QUALIFICATION',started_at=started,finished_at=now(),source_commit=q['source_commit'],request_sha256=sha(qpath),review_sha256=sha(review),phases=phases,clients=clients,all_waits_streams_joined=True,remaining_owned_children=left,actual_artifacts=artifacts,following_reader_executed=False,original_acceptance=False);save('RESULT.json',result);save('RESOURCE-RELEASE.json',dict(at=now(),current_jobs='RELEASED',positive_all_scopes=True,all_historical_native_other_holds_unchanged=True));print(json.dumps(dict(status=result['status'],finished_at=now(),following_reader_executed=False)))
except BaseException as exc:
 cleanup=[]
 for cid in list(owned):
  try:
   state=json.loads(call('failure-inspect-'+cid[:8],docker+['inspect',cid]))[0]['State']
   if state['Running']:call('owned-bounded-stop-'+cid[:8],docker+['kill',cid]);call('owned-bounded-wait-'+cid[:8],docker+['wait',cid]);state=json.loads(call('failure-terminal-'+cid[:8],docker+['inspect',cid]))[0]['State']
   assert not state['Running'] and state['Pid']==0;call('failure-remove-'+cid[:8],docker+['rm',cid]);cleanup.append(dict(CID=cid,removed=True))
  except BaseException as e:cleanup.append(dict(CID=cid,state='UNKNOWN',error=str(e)))
 save('RESULT.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_REPLAY',started_at=started,finished_at=now(),error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),clients=clients,phases=phases,cleanup=cleanup));raise
