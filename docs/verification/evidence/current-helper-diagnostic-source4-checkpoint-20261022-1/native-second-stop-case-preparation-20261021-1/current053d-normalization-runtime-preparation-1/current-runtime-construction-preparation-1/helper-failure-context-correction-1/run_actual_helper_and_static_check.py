"""Existing owned capture on actual M05 helper bodies; no PID1/native work."""
import hashlib,json,os,pathlib,resource,signal,struct,time,types
Q=pathlib.Path(__file__).resolve().parent
OUT=Q/'actual-helper-and-static-check-1'
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
 result=h.owned_capture(command,stage,8,limits,started);js(stage/'owned-result.json',result);commands.append(dict(label=label,result=ref(stage/'owned-result.json')))
 assert result['returncode']==0 and result['direct_child_joined']and result['group_absent']and result['closed_streams']and result['error']is None and result['retirement_error']is None and not result['unexpected_group_members'],label
 return {k:pathlib.Path(v['path']).read_bytes()for k,v in result['captures'].items()}
flags=['/usr/bin/gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-static']
for name in ['original','corrected']:
 argv=flags+(['-DCORRECTED']if name=='corrected'else[])+[str(Q/(name+'.c')),'-o',str(OUT/name)];capture('compile-'+name,argv)
results={};children=0
for mode in ['failure','success','two-failures','bounded']:
 for variant in ['original','corrected']:
  evidence=OUT/(variant+'-'+mode+'-evidence');evidence.mkdir(mode=0o700);(evidence/'boot.kmsg').write_bytes(b'')
  streams=capture(variant+'-'+mode,[str(OUT/variant),str(evidence),mode]);joins=streams['stderr'].decode().splitlines();expected=2 if mode=='two-failures'else 1;assert len(joins)==expected and all(x.startswith('CONTROLLED_HELPER_JOIN pid=')and x.endswith(' direct_child_reaped=true group_absent=true')for x in joins);children+=len(joins)
  raw=streams['stdout'];rows=raw.splitlines(keepends=True)
  if variant=='original'or mode=='success':assert raw==b''
  else:
   assert len(rows)==3 and all(len(x)<=4096 and x.endswith(b'\n')for x in rows)
   prefixes=[b'ND_HELPER_FAILURE ',b'ND_HELPER_FAILURE_STDOUT ',b'ND_HELPER_FAILURE_STDERR ']
   values=[]
   for line,prefix in zip(rows,prefixes):assert line.startswith(prefix);values.append(json.loads(line[len(prefix):]))
   header,out,err=values;assert header['tag']=='boot'and header['raw_wait_status']==7<<8 and header['clean']==1 and header['fault']==header['timeout']==header['stage']==header['errno']==0 and 0<header['started_ns']<=header['reaped_ns']<=header['finished_ns']
   for stream,expected_bytes in [(out,b'A'*1024 if mode=='bounded'else b'failure-out'),(err,b'B'*1024 if mode=='bounded'else b'failure-err')]:
    assert bytes.fromhex(stream['hex'])==expected_bytes and stream['observed']==stream['retained']==len(expected_bytes)and stream['eof']is True and not stream['truncated']and stream['discarded']==0
  results[variant+'-'+mode]=dict(stdout=ref(OUT/(variant+'-'+mode)/'stdout'),child_joins=expected,evidence=str(evidence))
 for suffix in ['stdout','stderr','status','kmsg']:
  name='boot.'+suffix;assert (OUT/('original-'+mode+'-evidence')/name).read_bytes()==(OUT/('corrected-'+mode+'-evidence')/name).read_bytes(),(mode,name)
assert children==10
source=Q/'native-second-stop-collector.helper-failure.c';binary=OUT/'native-second-stop-collector';dep=OUT/'collector.d';capture('compile-actual-changed-static',flags+['-MMD','-MF',str(dep),str(source),'-o',str(binary)])
binary_bytes=binary.read_bytes();assert binary_bytes[:7]==b'\x7fELF\x02\x01\x01';hdr=struct.unpack_from('<16sHHIQQQIHHHHHH',binary_bytes);assert hdr[1]==2 and hdr[2]==62 and hdr[9]==56;types_=[struct.unpack_from('<IIQQQQQQ',binary_bytes,hdr[5]+i*hdr[9])[0]for i in range(hdr[10])];assert 2 not in types_ and 3 not in types_;assert str(source)in dep.read_text()
result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_ACTUAL_M05_HELPER_CONTROL_PATH_FAILURE_EXPORT_AND_CHANGED_STATIC_COMPILE_ONLY',source=ref(source),binary=ref(binary),dependency=ref(dep),ELF64_x86_64_EXEC=True,PT_INTERP=False,PT_DYNAMIC=False,original_negative=True,corrected_positive=True,success_capture_bytes_unchanged=True,first_failure_retained=True,two_actual_1024B_streams=True,controlled_children_direct_reaped_and_group_absent=children,results=results,commands=commands,native_execution=False,stage=None,normalization=None,runtime_release=None,boot_failure_cause_unknown=True)
js(Q/'ACTUAL-M05-HELPER-CONTROL-PATH-AND-STATIC-RESULT-1.json',result);print(json.dumps(dict(status=result['status'],source=result['source'],binary=result['binary'],children=children,commands=len(commands),native_execution=False)))
