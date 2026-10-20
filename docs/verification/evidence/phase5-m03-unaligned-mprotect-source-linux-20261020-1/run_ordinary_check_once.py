"""One finite compile/ELF/Linux chain using the accepted owned-capture helper."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,stat,time
D=Path(__file__).resolve().parent;O=D/'ordinary-check-1'
PROFILE_SHA='4d2a63d7f8df4bfa2f8cdd988e1ff9c2b949e1d781fac380b514a6c8df0b7caf'
fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def checked(r):
 p=Path(r['path']);a=p.stat();data=p.read_bytes();z=p.stat()
 assert stat.S_ISREG(a.st_mode) and all(getattr(a,k)==getattr(z,k) for k in fields)
 assert len(data)==r.get('bytes',r.get('size')) and hashlib.sha256(data).hexdigest()==r['sha256']
 return data
raw=(D/'ORDINARY-CHECK-PROFILE.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==PROFILE_SHA
p=json.loads(raw);assert not O.exists() and os.sched_getaffinity(0)=={6}
for kind,value in [(resource.RLIMIT_AS,1<<30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_CORE,0),(resource.RLIMIT_NOFILE,256)]:
 assert resource.getrlimit(kind)==(value,value)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert state['phase']=='running' and state['stop_reason'] is None and state['last_rate_limits']['primary']['usedPercent']<100
for path,floor in [(D,16<<30),(Path('/home/holden/mckernel-work/scratch'),12<<30)]:
 s=os.statvfs(path);assert s.f_bavail*s.f_frsize>=floor+(64<<20)+(640<<20)
assert int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024>=18<<30
checked(p['source']);expected=checked(p['oracle']);assert len(expected)==73
for r in p['tools'].values():checked(r)
b=json.loads(checked(p['reused_toolchain_binding']));checked(p['reused_static_profile']);rlibs=json.loads(checked(p['reused_target_rlib_record']))['installed_target_rlib_bindings'];assert len(rlibs)==27
# Reuse the accepted content hashes; touch no toolchain/library payload bytes.
retained={**b['installed_static_link_inputs'],**rlibs};identities={}
for path,r in retained.items():
 s=Path(path).stat();assert stat.S_ISREG(s.st_mode) and s.st_size==r['size'];identities[path]=tuple(getattr(s,k) for k in fields)
checked(p['owned_capture_helper']);spec=importlib.util.spec_from_file_location('accepted_owned_capture',p['owned_capture_helper']['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
O.mkdir(mode=0o700)
for name in ('home','tmp','work'):(O/name).mkdir(mode=0o700)
m.write(O/'admitted-command-data.json',p['commands'])
records=[];begin=time.monotonic();failure=None

def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(32<<20,32<<20));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
try:
 for c in p['commands']:
  cap=O/c['label'];cap.mkdir(mode=0o700);m.write(cap/'command.json',c);os.chdir(c['cwd'])
  r=m.owned_capture({'argv':c['argv']},cap,min(c['wall_seconds'],max(.1,32-(time.monotonic()-begin))),limits);records.append(r)
  assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None and r['captures']['stderr']['size']==0
  assert m.cpu_used()<30 and time.monotonic()-begin<32
  if c['label']=='compile-static-rust':(O/'app').chmod(0o700)
  elif c['label']=='inspect-static-ELF':
   elf=(cap/'stdout').read_bytes();assert b'EXEC (Executable file)' in elf and b'Advanced Micro Devices X86-64' in elf and b'INTERP' not in elf and b'NEEDED' not in elf
   lines=elf.decode('ascii').splitlines();stacks=[x.split() for x in lines if x.strip().startswith('GNU_STACK ')];loads=[x.split() for x in lines if x.strip().startswith('LOAD ')]
   assert len(stacks)==1 and 'E' not in ''.join(stacks[0][6:-1]) and loads
   assert all(not ('W' in ''.join(x[6:-1]) and 'E' in ''.join(x[6:-1])) for x in loads)
  else:assert (cap/'stdout').read_bytes()==expected and not list((O/'work').iterdir())
 for path,identity in identities.items():assert tuple(getattr(Path(path).stat(),k) for k in fields)==identity
except BaseException as e:failure=type(e).__name__+': '+str(e)
finally:os.chdir(D)
ok=failure is None and len(records)==3
binary=None
if (O/'app').exists():
 data=(O/'app').read_bytes();binary=dict(path=str(O/'app'),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),mode=oct(stat.S_IMODE((O/'app').stat().st_mode)))
m.write(O/'whole.json',dict(status='PASS_STATIC_ELF_AND_EXACT_LINUX_REFERENCE' if ok else 'FAIL_STOP_PRESERVE',failure=failure,records=records,elapsed_seconds=time.monotonic()-begin,CPU_seconds=m.cpu_used(),source=p['source'],oracle=p['oracle'],binary=binary,target_rlib_content_proof_reused=True,library_metadata_stable=failure is None,guest_runs=0,native_acceptance=False))
print(json.dumps(dict(status='PASS' if ok else 'FAIL',commands=len(records),elapsed_seconds=time.monotonic()-begin)))
raise SystemExit(0 if ok else 1)
