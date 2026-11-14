"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root's one bounded read-only resource observation under its existing held reservation.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, time
A=Path(__file__).resolve().parent
B=A.parent
P=B/'M14-CONVERSION-FIRST-PRODUCER-BINDING-1/current-frontier-successor-1'
G=B/'M14-CONVERSION-FIRST-BUILD-GUARD-PREPARATION-1/runtime_guard.py'
def read(p): return json.loads(p.read_text())
def ref(p):
 data=p.read_bytes(); return dict(path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
def put(p,d):
 with p.open('x') as f: f.write(json.dumps(d,indent=2)+'\n')
 return ref(p)
assert os.getuid()==os.geteuid()==1000
spec=importlib.util.spec_from_file_location('actual_conversion_build_guard',G)
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
clocks=guard.guard()
ready_path=A/'HOLDER/HOLDER.READY.json'; ready=read(ready_path); holder=ready['holder']; hp=Path('/proc',str(holder['pid']))
assert int((hp/'stat').read_text().rsplit(')',1)[1].split()[19])==holder['starttime']
fd_target=os.readlink(hp/'fd'/str(holder['fd'])); assert fd_target==holder['path']
st=os.stat(holder['path']); assert (st.st_dev,st.st_ino)==(27,4)
locks=Path('/proc/locks').read_text();token='%02x:%02x:%d'%(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)
assert any(len(v)>=8 and v[1:5]==['FLOCK','ADVISORY','WRITE',str(holder['pid'])] and v[5]==token and v[6:8]==['0','EOF'] for v in map(str.split,locks.splitlines()))
resource=read(B/'ROOT-CURRENT119-BUILD-ADMISSION-1/ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.R2.json')
capacity={}
for name,path in [('host',A),('scratch',Path('/home/holden/mckernel-work/scratch'))]:
 sv=os.statvfs(path);capacity[name]=dict(path=str(path),available_bytes=sv.f_bavail*sv.f_frsize,device=os.stat(path).st_dev)
assert capacity['host']['available_bytes']>=resource['host_required_free_bytes'] and capacity['scratch']['available_bytes']>=resource['scratch_required_free_bytes']
memory={line.split(':')[0]:line.split(':')[1].strip() for line in Path('/proc/meminfo').read_text().splitlines()}
threads=int(Path('/proc/loadavg').read_text().split()[3].split('/')[1]);limit=int(Path('/proc/sys/kernel/threads-max').read_text())
assert int(memory['MemAvailable'].split()[0])*1024>=resource['other_reserved_memory_bytes']+resource['container_memory_bytes']+(4<<30)
assert threads+512+resource['other_reserved_pids']<=limit
cgroups={p:Path(p).read_text().strip() for p in resource['actual_observations']['cgroups']}
assert cgroups['/sys/fs/cgroup/pids/mckernel-dev/pids.current']=='0'
profile=read(P/'PROFILE.SOURCE-ONLY.json'); fields=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
resource.update(author='/root',nonce=ready['nonce'],reservation_owner=ready['nonce'],reservation_holder=holder,reservation_ready_record=ref(ready_path),native_custody_clearance=ready['native_custody_clearance'],native_custody_unchanged=True,cpu_reservation_held=True,fresh_output_root=str(A/'OUTPUT'),observed_clocks=list(clocks),observed_at_epoch=time.time(),runtime_authority='ONE_BUILD_ONLY_RESOURCE_RESERVATION')
resource['actual_observations']=dict(accepted_full_postjoin_capture=ready['native_custody_clearance'],capacity=capacity,cgroups=cgroups,exact_weekly_operation_guard=ref(G),holder_fd_target=fd_target,holder_parent_pid=int((hp/'stat').read_text().rsplit(')',1)[1].split()[1]),host_threads=threads,lock_rows=locks,memory=memory,root_attests_no_post_clearance_native_or_heavy_operation_except_this_holder=True,source_only_origin=profile['origin_source_materialization'],thread_limit=limit,resource_collector=dict(pid=os.getpid(),birth=int(fields[19]),ppid=os.getppid(),process_group=os.getpgrp(),source=ref(Path(__file__).resolve())))
rr=put(A/'ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json',resource)
grant=read(B/'M14-CONVERSION-FIRST-BUILD-ADMISSION-PREPARATION-1/PENDING-GRANT.TEMPLATE.NOT-AUTHORITY.json')
grant.update(author='/root',nonce=ready['nonce'],native_custody_clearance=ready['native_custody_clearance'],input_export_authority=ref(A/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json'),resource_authority=rr,profile=ref(P/'PROFILE.SOURCE-ONLY.json'),runner=ref(P/'run_build_only.py'),worker=ref(P/'build_only_worker.py'))
pr=put(A/'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json',grant)
print(json.dumps(dict(resource=rr,pending_grant=pr,observed_at_epoch=resource['observed_at_epoch'],holder=holder)))
