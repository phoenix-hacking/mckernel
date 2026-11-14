"""Existing owned capture on actual M05 helper bodies; no PID1/native work."""
import hashlib,json,os,pathlib,resource,signal,struct,time,types
Q=pathlib.Path(__file__).resolve().parent
OUT=Q/'actual-consumer-body-supervisor-capture-1'
OUT.mkdir(mode=0o700)
def js(p,x):
 with p.open('x')as f:json.dump(x,f,sort_keys=True,indent=2);f.write('\n')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
free={}
for name,p,floor in [('host','/home/holden/mckernel',16<<30),('scratch','/home/holden/mckernel-work/scratch',12<<30)]:
 s=os.statvfs(p);available=s.f_bavail*s.f_frsize;assert available>=floor+(700<<20);free[name]=dict(available_bytes=available,floor_bytes=floor,reserve_bytes=700<<20)
js(OUT/'ROOT-ORDINARY-ADMISSION.json',dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',grant='Root existing CPU6 onejob grant covers changed helper actual body/controlpath and changed static compile, no stage/native.',profile=dict(CPU=6,AS_bytes=1073741824,CPU_seconds=30,wall_seconds=35,FSIZE_bytes=67108864,nofile=256,core=0),free=free,time_ns=time.time_ns(),other_job='M07CPU7 sourcecheck only; noheavy/census'))
hp=pathlib.Path('/home/holden/mckernel-work/host-preparation/practical-create-ppd-provider-repair-20261019-1/guest-control-consumer-1/current-fullcrate-owner-1/owned_capture_helpers.py');assert ref(hp)['sha256']=='7834a85da04a3667b86365ec6340a55580b560248dd23fec84e673acc31bea90';h=types.ModuleType('_accepted_owned_capture');h.__file__=str(hp);exec(compile(hp.read_bytes(),str(hp),'exec'),h.__dict__);assert h.CENSUS_SHA=='96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1';h.CENSUS_SOURCE=pathlib.Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py')
for sig in h.STOP_SIGNALS:signal.signal(sig,h.stop)
commands=[]
def capture(label,argv):
 stage=OUT/label;stage.mkdir(mode=0o700);command=dict(argv=argv,cwd=str(Q));js(stage/'command.json',command)
 def limits():
  resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824));resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(67108864,67108864));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 def started(pid):
  fields=pathlib.Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split();r=dict(pid=pid,start=int(fields[19]),pgrp=int(fields[2]));js(stage/'child.json',r);return r['start']
 result=h.owned_capture(command,stage,30,limits,started);js(stage/'owned-result.json',result);commands.append(dict(label=label,result=ref(stage/'owned-result.json')))
 assert result['returncode']==0 and result['direct_child_joined']and result['group_absent']and result['closed_streams']and result['error']is None and result['retirement_error']is None and not result['unexpected_group_members'],label
 return {k:pathlib.Path(v['path']).read_bytes()for k,v in result['captures'].items()}
capture('actual-body-check',['/usr/bin/python3','-B',str(Q/'check_actual_m05_stager_consumer_bodies.py')]);js(OUT/'FINAL-SUPERVISOR-RESULT-1.json',dict(status='PASS_ONE_ACTUAL_M05_STAGER_CONSUMER_COMPONENT_COMMAND',commands=commands,stage_executed=False));print('PASS_ACTUAL_M05_CONSUMER_BODY_CAPTURE_CLOSED')
