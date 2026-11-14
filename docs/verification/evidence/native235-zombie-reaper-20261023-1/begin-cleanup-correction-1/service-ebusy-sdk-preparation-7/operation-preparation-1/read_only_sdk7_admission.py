"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fresh read-only admission for the repaired host SDK tuple; no native authorization.
"""
import fcntl
import ast,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ENGINE=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/matched-image-terminal-preparation-1/bound-matched-image-terminal-source-2/cleanup_pass_image.py')
EXPECTED='59efab0bc29fa5784dc855743cec397237552821bc150b60ea1d6c2e5f7ac00d'
def need(v,m):
 if not v:raise RuntimeError(m)
def run(a):
 p=subprocess.run(a,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12)
 if p.returncode or p.stderr or len(p.stdout)>4*1024**2:
  sys.stderr.write(json.dumps(dict(argv=a,returncode=p.returncode,stdout_bytes=len(p.stdout),stderr=p.stderr[:65536].decode('utf-8','replace'),stderr_total_bytes=len(p.stderr)))+'\n')
  raise RuntimeError('bounded read-only command')
 return p.stdout.decode()
need(os.geteuid()==0,'authenticated root read-only admission')
b=ENGINE.read_bytes();need(hashlib.sha256(b).hexdigest()==EXPECTED,'accepted census source')
code=next(ast.literal_eval(n.value) for n in ast.parse(b).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROC_CODE' for t in n.targets))
pid=os.getpid();start=Path('/proc/self/stat').read_text().rpartition(') ')[2].split()[19]
proc=json.loads(run(['/usr/bin/python3','-I','-B','-c',code,'service-ebusy-sdk7-current-live-admission-20261023-1',str(pid),start]))
need(proc['status']=='COMPLETE' and proc['failure'] is None and proc['publishers']==[] and len(proc['snapshots'])==2,'complete publisher-free census')
root=Path('/home/holden/mckernel-work/scratch');backing=Path('/home/holden/mckernel-work/scratch.ext4');bs=backing.stat();host=os.statvfs('/home/holden/mckernel');scratch=os.statvfs(root)
need(bs.st_ino==47468427 and bs.st_size==118111600640,'110GiB backing identity')
mount=json.loads(run(['/usr/bin/findmnt','-J','-o','TARGET,UUID','-T',str(root)]))['filesystems']
need(mount==[dict(target=str(root),uuid='2a5768c8-718d-4914-bdc0-6b32c5a92a52')],'scratch UUID')
lock=Path('/run/lock/mckernel-development.lock').stat();need((lock.st_dev,lock.st_ino,lock.st_uid,lock.st_gid,lock.st_nlink)==(27,4,0,0,1),'permanent mutex')
key=f'{os.major(lock.st_dev):02x}:{os.minor(lock.st_dev):02x}:{lock.st_ino}'
locks=[l for l in Path('/proc/locks').read_text().splitlines() if key in l.split()];need(not locks,'permanent mutex currently held')
mutex_fd=os.open('/run/lock/mckernel-development.lock',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW);need((os.fstat(mutex_fd).st_dev,os.fstat(mutex_fd).st_ino)==(27,4),'stable27:4FD');fcntl.flock(mutex_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
paths=['/home/holden/mckernel-work/scratch/native-running-external-modules.lease.json', '/home/holden/mckernel-work/scratch/native-running-external-modules-operational-exclusion.json', '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/lease.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/image-lease.json'];need(all(not os.path.lexists(p) for p in paths),'fresh exact current SDK/image/launcher ownership paths absent')
cid='7fb3c3f709b38f2ba890079f3911b0a48d3a76059a200672763639abe493a0b8'
need(run(['/usr/bin/docker','ps','-aq','--no-trunc','--filter','id='+cid])=='','latest retired container absent')
need(run(['/usr/bin/docker','ps','-aq','--no-trunc','--filter','name=^/mckernel-external-43564e4861f0414a8c25b31a7ee7d9dd$'])=='','fresh exactnonce name absent')
need(run(['/usr/bin/docker','ps','-aq','--no-trunc','--filter','label=mckernel.owner=43564e4861f0414a8c25b31a7ee7d9dd'])=='','fresh exactnonce label absent')
need(not os.path.lexists('/home/holden/mckernel-work/host-preparation/native-running-modules-host-output/native-running-modules-owner-43564e4861f0414a8c25b31a7ee7d9dd'),'fresh exact M05 attempt absent')
running=run(['/usr/bin/docker','ps','-q','--no-trunc']);need(not running,'competing running container')
freehost=host.f_bavail*host.f_frsize;freescratch=scratch.f_bavail*scratch.f_frsize;growth=bs.st_size-bs.st_blocks*512;minimum=16*2**30+growth+536870912+679477248
need(freehost>=minimum and freescratch>=14101250048,'full capacity growth/reserves')
mem=int(next(l for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')).split()[1])*1024
need(mem>=19*2**30,'aggregate available memory')
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());need(state['phase']=='running' and state['stop_reason'] is None,'launcher active')
expected_cgroup={'/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us': '100000', '/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us': '400000', '/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes': '12884901888', '/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy': '1', '/sys/fs/cgroup/pids/mckernel-dev/pids.max': '512'}
cgroup={p:Path(p).read_text().strip() for p in expected_cgroup};need(cgroup==expected_cgroup,'unchanged reviewed cgroup profile')

# Reuse actual unchanged SDK7 owner guards for staged request identity, mount,
# full sparse growth and output-allocation bounds. No lifecycle starts here.
import importlib.util
sys.path.insert(0,'/home/holden/mckernel/scripts')
REQUEST=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/service-ebusy-sdk-preparation-7/prepared-sdk/request.json');OWNER=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/service-ebusy-sdk-preparation-7/prepared-sdk/derived-runtime/native_running_external_modules_owner.py')
need(hashlib.sha256(REQUEST.read_bytes()).hexdigest()=='3878c1fbcbeb75f12e03050cbb9ec343bdbdd919f64c181b1ee7ebb2d754ca73','exact staged SDK7 request')
need(hashlib.sha256(OWNER.read_bytes()).hexdigest()=='b48a27d974d68a369ab9c566dd1d35406fe82beaf48f07097ee2359c72b81555','exact coherent SDK7 owner')
spec=importlib.util.spec_from_file_location('sdk7_admission_owner',OWNER)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
sdk7_request=json.loads(REQUEST.read_text())
sdk7_mount=module.live_admission(sdk7_request)
sdk7_resources=module.measure(sdk7_request)

print(json.dumps(dict(sdk7_request_sha256='3878c1fbcbeb75f12e03050cbb9ec343bdbdd919f64c181b1ee7ebb2d754ca73',sdk7_mount=sdk7_mount,sdk7_resources=sdk7_resources,status='PASS_FRESH_READ_ONLY_NATIVE235_CURRENT_LIVE_ADMISSION',sdk_predecessor={'path': '/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/eventfd-sdk-preparation-6/postbuild-preparation-1/INDEPENDENT-ACTUAL-SDK6-ARTIFACT-AND-PHYSICAL-ACCEPTANCE.ROOT-RECORD.json', 'sha256': '9159dcbd13c816f50d42390a05223e08a479b5f85d8183c4f61579bda20bc176', 'bytes': 11743},latest_physical={'path': '/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/next-live-observation-221b-1/physical-preparation-1/INDEPENDENT-ACTUAL-FAILED221B-PHYSICAL-ACCEPTANCE.ROOT-RECORD.json', 'sha256': '738f2cd8e58f02ac1d0b0592ff110cda33d7b0732161b7745e084984889c6e5e', 'bytes': 1892},current_live_postjoin='FAILED_SETTLEMENT_LONG_221B_POSITIVELY_RETIRED',host_device=os.stat('/home/holden/mckernel').st_dev,scratch_device=root.stat().st_dev,proc=proc,mount=mount,backing=dict(dev=bs.st_dev,inode=bs.st_ino,size=bs.st_size,allocated=bs.st_blocks*512),host_available=freehost,scratch_available=freescratch,minimum_host=minimum,memory_available=mem,affinity=sorted(os.sched_getaffinity(0)),root_lock=[lock.st_dev,lock.st_ino],ownership_paths_absent=paths,running_containers=[],cgroup=cgroup,mutation=False,at_unix=time.time()),sort_keys=True))
