import ast,datetime,hashlib,json,os,pathlib,re,shutil,subprocess,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');BASE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z');M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110');HERE=pathlib.Path(__file__).parent;OUT=HERE/'execution-1';OUT.mkdir(mode=0o700,exist_ok=False)
prior=M/'compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py';tree=ast.parse(prior.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save','call')],type_ignores=[]),str(prior),'exec'))
shared=BASE/'exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py';tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
cap=M/'root-reviewed-capture-correction-1/correction-1/phase-cpu6.py';assert sha(cap)=='7266db32ace8e167a14cc8a97cd91315f35356f117609da2c7a02cf97d7c2db3';exec(compile(cap.read_text(),str(cap),'exec'))
ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py');docker=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'];clients=[];phases=[];owned=[];started=now();qpath=HERE/'REQUEST.json';review=M/'f06-default-observation-review-p04tests-max-1/REVIEW.json'
def pins(v):
 if isinstance(v,dict):
  if 'path' in v and 'sha256' in v:
   assert sha(v['path'])==v['sha256'],v['path']
   if 'bytes' in v:assert pathlib.Path(v['path']).stat().st_size==v['bytes']
  for x in v.values():pins(x)
 elif isinstance(v,list):
  for x in v:pins(x)
def admit(label,need):
 stamp=guard();available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;rss=overhead();hf=shutil.disk_usage(ROOT).free;sf=shutil.disk_usage(HERE).free
 assert available>=26*2**30 and rss+need<=4*2**30 and hf>=21*2**30 and sf>=17*2**30
 save(label+'-ADMISSION.json',dict(at=now(),guard_updated_at=stamp,MemAvailable_bytes=available,all_current_overhead_bytes=rss,this_phase_bytes=need,HOST_total=4*2**30,maxjobs=3,hostfree=hf,scratchfree=sf,disk_growth_reserved=5*2**30,current_old_HOST_claims=0,scope_of_zero_claims='Only540/a41 released HOST scopes; historical missingwaits and all Native/other holds remain',other_payloads_active=0))
try:
 assert sha(qpath)=='d17d5e1d972825079e951f596437df4f5b6dcb37ec3cbd516fdaf1a75883753a';assert sha(review)=='7344ef7cb8aaaddfdff49fc9de2d57bdd4c764161966923ff86fbad9654bf70e';q=json.loads(qpath.read_text());pins(q['source_binding']);binding=json.loads(pathlib.Path(q['source_binding']['path']).read_text());pins(binding);pins(q['metadata_phase']['helper'])
 assert call('source-commit',['/usr/bin/git','rev-parse','HEAD']).decode().strip()==q['source_commit']=='f37463cdd25f7f25e6c92c3f418c6dce3054a74f'
 assert call('IHK-commit',['/usr/bin/git','-C',str(ROOT/'ihk'),'rev-parse','HEAD']).decode().strip()=='8d288b8bd81b50cc3a3f814d949b89bf416a6ec7'
 dis=BASE/'host-lane-current-retirement-20261110/ROOT-DISPOSITION.json';assert sha(dis)=='54065796b198ef95d2258e3dd1a290ea5a48335ca1c03857095a04b0a6422257'
 assert not call('running-preflight',docker+['ps','-q']).strip()
 names=call('names-preflight',docker+['ps','-a','--format','{{.Names}}']).decode().splitlines()
 for key in ('configure_phase','metadata_phase'):
  a=q[key]['create_argv'];assert a[a.index('--name')+1] not in names
 meta=pathlib.Path(q['metadata_phase']['output_root']);assert not meta.exists();meta.mkdir(mode=0o755)
 baseline=json.loads(pathlib.Path(binding['stable100d25files']['path']).read_text());before=[]
 for row in baseline['files']:
  f=pathlib.Path(row['source_path']);assert sha(f)==row['sha256'],str(f);before.append(dict(path=str(f),bytes=f.stat().st_size,mode=oct(f.stat().st_mode&0o777),sha256=sha(f)))
 save('PRECONFIGURE-25-IDENTITIES.json',before);admit('configure',2*2**30)
 a=q['configure_phase'];phase('configure',a['create_argv'],a['expected_mounts'],2*2**30,256,a['max_wall_seconds'])
 build=M/'compute-image-source-1/output/build';cache={}
 for line in (build/'CMakeCache.txt').read_text().splitlines():
  if line and not line.startswith(('#','//')) and ':' in line and '=' in line:
   k,v=line.split('=',1);cache[k.split(':',1)[0]]=v
 assert cache['ENABLE_RUST_F06_SYSCALL_WHOLE']=='ON'
 ko=build/'tmp.resolve_MODULES_END/driver.ko';assert ko.stat().st_size>0 and ko.read_bytes()[:4]==b'\x7fELF'
 commands=json.loads((build/'compile_commands.json').read_text());assert len(commands)==10
 maps=[]
 for cmd in commands:
  a=cmd.get('command',' '.join(cmd.get('arguments',[])));found=re.findall(r'(?:-D)MAP_KERNEL_START=(0x[0-9a-fA-F]+)',a);assert len(found)==1;maps.extend(found)
 assert len(set(maps))==1 and int(maps[0],16)>=0xffffffff00000000 and maps[0] in (build/'kernel/config/smp-x86.lds').read_text()
 save('CONFIGURE-STRONG-POSTGATE.json',dict(actual_default='ON',no_explicit_ON_override=True,driver_bytes=ko.stat().st_size,driver_sha256=sha(ko),MAP_KERNEL_START=maps[0],C_AS_compile_rows=len(commands),source_commit=q['source_commit'],native_or_E2_acceptance=False))
 admit('metadata',512*2**20);a=q['metadata_phase'];phase('metadata',a['create_argv'],a['expected_mounts'],512*2**20,64,a['max_wall_seconds'])
 files=[meta/n for n in a['output_contract']['stdout_files']];assert len(files)==20 and all(f.is_file() and f.stat().st_size>0 for f in files)
 remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not remaining and not owned
 result=dict(status='PASS_DEFAULT_CONFIGURE_AND_GENERATED_INPUT_CAPTURE_PENDING_EQUIVALENCE_QUALIFICATION',started_at=started,finished_at=now(),source_commit=q['source_commit'],request_sha256=sha(qpath),review_sha256=sha(review),phases=phases,clients=clients,all_client_waits_streams_joined=True,remaining_owned_children=remaining,conditional_image_build_executed=False,original_acceptance=False,metadata=[dict(path=str(f),bytes=f.stat().st_size,sha256=sha(f)) for f in files]);save('RESULT.json',result);save('RESOURCE-RELEASE.json',dict(at=now(),configure_and_metadata_jobs_released=True,positive_all_owned_waits_streams_terminals_removals=True,historical_or_native_holds_changed=False));print(json.dumps(dict(status=result['status'],finished_at=now(),default='ON',metadata_files=len(files))))
except BaseException as exc:
 cleanup=[]
 for cid in list(owned):
  try:
   state=json.loads(call('failure-inspect-'+cid[:8],docker+['inspect',cid]))[0]['State']
   if state['Running']:call('owned-bounded-container-stop-'+cid[:8],docker+['kill',cid]);call('owned-bounded-container-wait-'+cid[:8],docker+['wait',cid]);state=json.loads(call('failure-terminal-'+cid[:8],docker+['inspect',cid]))[0]['State']
   assert not state['Running'] and state['Pid']==0;call('failure-owned-remove-'+cid[:8],docker+['rm',cid]);cleanup.append(dict(CID=cid,removed=True))
  except BaseException as secondary:cleanup.append(dict(CID=cid,state='UNKNOWN',error=str(secondary)))
 save('RESULT.json',dict(status='FAILED_PRESERVED_NO_REPLAY',started_at=started,finished_at=now(),error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),phases=phases,clients=clients,cleanup=cleanup));raise
