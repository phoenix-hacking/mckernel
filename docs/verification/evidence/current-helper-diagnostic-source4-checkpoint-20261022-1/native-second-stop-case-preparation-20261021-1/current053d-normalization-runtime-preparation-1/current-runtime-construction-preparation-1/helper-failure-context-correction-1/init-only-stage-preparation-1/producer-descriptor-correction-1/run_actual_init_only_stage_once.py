"""One exact dispatcher-granted actual init-only stage; existing owned capture."""
import hashlib,json,os,pathlib,resource,signal,time,types
Q=pathlib.Path(__file__).resolve().parent
OUT=Q/'actual-init-only-stage-capture-1';OUT.mkdir(mode=0o700)
def js(p,x):
 with p.open('x')as f:json.dump(x,f,indent=2);f.write('\n')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
assert os.sched_getaffinity(0)=={6}
for limit,minimum in [(resource.RLIMIT_AS,1073741824),(resource.RLIMIT_CPU,30)]:
 soft,hard=resource.getrlimit(limit);assert soft==-1 or soft>=minimum;assert hard==-1 or hard>=minimum
review=pathlib.Path('/home/holden/mckernel-work/host-preparation/current-focused-progress-recording-20261021-1/current-normalization-review-recording-1/M05-INIT-ONLY-STAGE-EXECUTION-REVIEW.json');assert ref(review)['sha256']=='8e06ac466d123cc8947969ac076e9cfd563c9a668b08be261879a4bc19c5d78f'
cmdfile=Q/'EXACT-STAGE-COMMAND-NOT-AUTHORIZED.json';assert ref(cmdfile)['sha256']=='f161944685c09a270ad0c8159d9adc4ce0a577791cde5049a4e5f34571d43643';command=json.loads(cmdfile.read_bytes())
free={}
for name,p,floor in [('host','/home/holden/mckernel',16<<30),('scratch','/home/holden/mckernel-work/scratch',12<<30)]:
 s=os.statvfs(p);available=s.f_bavail*s.f_frsize;assert available>=floor+679477248+(64<<20);free[name]=dict(available_bytes=available,floor_bytes=floor,reserve_bytes=679477248,bounded_stage_growth_bytes=64<<20)
js(OUT/'ROOT-ACTUAL-ORDINARY-STAGE-GRANT-1.json',dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',grant='Root explicitly grants one actual exactf1619446 M05 init-only stage after genuine8e06ac46 independent execution review.',review=ref(review),source_sha256='60a393dd873c2e644f681cd55eec3634071a59ef43638df2d494aefff925543a',binding_sha256='4eefbd8f9050f5f4fc69528e89fa4de31371e0961f474f5ebda959b728ea7021',command=ref(cmdfile),profile=dict(CPU=6,AS_bytes=1073741824,CPU_seconds=30,wall_seconds=35,FSIZE_bytes=67108864,nofile=256,core=0),free=free,time_ns=time.time_ns(),other_ordinary='M07CPU7 sourcegraph only <=1GiB; no heavy/census',stage_only=True,guest_release=False,normalization_release=False))
hp=pathlib.Path('/home/holden/mckernel-work/host-preparation/practical-create-ppd-provider-repair-20261019-1/guest-control-consumer-1/current-fullcrate-owner-1/owned_capture_helpers.py');assert ref(hp)['sha256']=='7834a85da04a3667b86365ec6340a55580b560248dd23fec84e673acc31bea90';h=types.ModuleType('_accepted_owned_capture');h.__file__=str(hp);exec(compile(hp.read_bytes(),str(hp),'exec'),h.__dict__);h.CENSUS_SOURCE=pathlib.Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py');assert ref(h.CENSUS_SOURCE)['sha256']==h.CENSUS_SHA=='96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1'
js(OUT/'CONFIGURED-EXISTING-HELPER-SOURCES-1.json',dict(helper=ref(hp),configured_source=ref(h.CENSUS_SOURCE)))
for sig in h.STOP_SIGNALS:signal.signal(sig,h.stop)
js(OUT/'command.json',command)
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824));resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(67108864,67108864));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def started(pid):
 fields=pathlib.Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split();r=dict(pid=pid,start=int(fields[19]),pgrp=int(fields[2]));js(OUT/'child.json',r);return r['start']
result=h.owned_capture(command,OUT,35,limits,started);js(OUT/'owned-result.json',result)
closure=all(result[k] for k in ['direct_child_joined','group_absent','closed_streams'])and result['error']is None and result['retirement_error']is None and not result['unexpected_group_members']
js(OUT/'FINAL-ACTUAL-STAGE-CAPTURE-SUMMARY-1.json',dict(returncode=result['returncode'],seconds=result['seconds'],pid=result['pid'],start=result['start'],closure=closure,owned_result=ref(OUT/'owned-result.json'),runtime_release=False))
print(json.dumps(dict(returncode=result['returncode'],seconds=result['seconds'],pid=result['pid'],start=result['start'],closure=closure,captures=result['captures'])))
assert result['returncode']==0 and closure,'actual stage failed; preserve and stop'
