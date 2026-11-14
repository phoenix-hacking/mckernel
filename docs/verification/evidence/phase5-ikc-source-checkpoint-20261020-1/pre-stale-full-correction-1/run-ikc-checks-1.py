import os,resource,subprocess,pathlib,json,hashlib,signal,time
r=pathlib.Path(__file__).resolve().parent
records=[]
os.umask(0o077)
os.environ['RUSTC_BOOTSTRAP']='1'
commands=json.loads((r/'COMMANDS.json').read_text())
for item in commands:
 for ext in ('.stdout','.stderr','.wait-status.json'):
  assert not (r/(item['name']+ext)).exists(),'existing output'
for output in ('actual-native-tests-1','actual-legacy-tests-1','ordinary-check-result-1.json'):
 assert not (r/output).exists(),'existing artifact'
assert int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024>=2*2**30

for item in json.loads((r/'CHECK-PINS.json').read_text()):
 assert hashlib.sha256(pathlib.Path(item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
state=json.loads(pathlib.Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
usage=state.get('last_rate_limits',{}).get('primary',{}).get('usedPercent')
assert state.get('phase')=='running' and not state.get('pause_reason') and isinstance(usage,(int,float)) and usage<100
for path,floor in [('/home/holden',16*2**30),('/home/holden/mckernel-work/scratch',12*2**30)]:
 v=os.statvfs(path);assert v.f_bavail*v.f_frsize>=floor+512*2**20
# Actual source syntax + private actual-function fixture only.
def limits():
 os.sched_setaffinity(0,{6})
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
 resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824))
 resource.setrlimit(resource.RLIMIT_CPU,(30,30))
 resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432))
def run(name,args):
 out=r/(name+'.stdout');err=r/(name+'.stderr');start=time.monotonic()
 with out.open('wb') as o,err.open('wb') as e:
  p=subprocess.Popen(args,cwd=r,stdout=o,stderr=e,preexec_fn=limits,start_new_session=True)
  try: code=p.wait(timeout=35)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try: code=p.wait(timeout=2)
   except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL);code=p.wait()
 try: os.killpg(p.pid,0);group_absent=False
 except ProcessLookupError:group_absent=True
 (r/(name+'.wait-status.json')).write_text(json.dumps({'pid':p.pid,'exit_code':code,'positive_wait':True,'owned_group_absent':group_absent,'elapsed':time.monotonic()-start},sort_keys=True)+'\n')
 rec={'environment':{'RUSTC_BOOTSTRAP':os.environ.get('RUSTC_BOOTSTRAP')},'name':name,'command':list(map(str,args)),'pid':p.pid,'exit_code':code,'elapsed':time.monotonic()-start,'positive_wait':True,'stdout_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256(err.read_bytes()).hexdigest()};records.append(rec)
 (r/'ordinary-check-result-1.json').write_text(json.dumps({'profile':'CPU6 / 1job /1GiBAS /30CPU /35+2wall /32MiBperstream','rustc_sha256':hashlib.sha256(pathlib.Path('/home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc').read_bytes()).hexdigest(),'results':records},indent=2)+'\n')
 # Full logs remain file backed; one final bounded count/status only.
 assert group_absent,'owned process group remains after positive join'
 return code
for item in json.loads((r/'COMMANDS.json').read_text()):
 code=run(item['name'],item['argv'])
 if code!=item['expected_exit']:
  raise SystemExit(1)
print(json.dumps({'joined_commands':len(records),'exit_codes':[x['exit_code']for x in records],'native_tests':5,'legacy_tests':4,'actual_guest_runs':0}))
