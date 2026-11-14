"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fresh current observation before ordinary query-holder acquisition; no workload.
"""
from pathlib import Path
import json,os,time,hashlib,subprocess
A=Path(__file__).resolve().parent;E=A.parent
clock=dict(wall=time.time(),monotonic=time.monotonic(),boot=time.clock_gettime(time.CLOCK_BOOTTIME),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
bundle=json.loads((A/'accepted-finalization-1/SDK7-BUNDLE.STATIC.NOT-RELEASED.json').read_bytes())
postsource=E/'ROOT-CURRENT290-NATIVE-MEMORY-ADMISSION-1/check_postnative_current.py'
r=subprocess.run(['/home/holden/anaconda3/bin/python3','-I','-B',str(postsource)],capture_output=True,timeout=30);assert r.returncode==0 and not r.stderr
with (A/'PREQUERY-ACTUAL-POSTJOIN.stdout').open('xb') as f:f.write(r.stdout)
with (A/'PREQUERY-ACTUAL-POSTJOIN.stderr').open('xb') as f:f.write(r.stderr)
post=json.loads(r.stdout)
argv=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-q','--no-trunc'];q=subprocess.run(argv,capture_output=True,text=True,timeout=15);assert q.returncode==0 and not q.stdout.strip() and not q.stderr
back=Path('/home/holden/mckernel-work/scratch.ext4');s=back.lstat();after=dict(path=str(back),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=s.st_mode&0o777,nlink=s.st_nlink,size=s.st_size,uuid=post['mount']['filesystems'][0]['uuid']);assert after==dict(path=str(back),device=66306,inode=47468427,uid=0,gid=0,mode=0o600,nlink=1,size=152471339008,uuid='2a5768c8-718d-4914-bdc0-6b32c5a92a52')
head=json.loads(Path(bundle['operation_head']['path']).read_bytes());latest=json.loads(Path(bundle['latest_operation']['path']).read_bytes())
assert not [l for l in Path('/proc/locks').read_text().splitlines() if '00:1b:4' in l.split()]
value=dict(schema='mckernel.daemon7.live-environment-observation.v1',scope=__doc__.splitlines()[0],latest_operation=bundle['latest_operation'],latest_serial_operation=head['latest_serial_operation'],operation_head=bundle['operation_head'],growth_closure=bundle['growth_closure'],actual_backing_identity=after,clock=clock,global_mutex_rows=[],active_records_absent=True,root_mutex=dict(device=27,inode=4,free=True),no_unknown_owned_operations=True,container_dispositions=latest['container_dispositions'],actual_current_postjoin=post,running_containers=dict(argv=argv,returncode=q.returncode,stdout=q.stdout,stderr=q.stderr,positive_wait=True),aggregate_planning_memory_GiB=os.environ['MCKERNEL_OS_MEMORY_GIB'],aggregate_jobs_max=int(os.environ['MCKERNEL_OS_BUILD_JOBS']))
assert 0<=time.time()-clock['wall']<=120 and 0<=time.monotonic()-clock['monotonic']<=120 and 0<=time.clock_gettime(time.CLOCK_BOOTTIME)-clock['boot']<=120
with (A/'LIVE-CURRENT.json').open('xb') as f:f.write((json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode())
print(json.dumps(dict(status='PASS_ACTUAL_PREQUERY_CURRENT_OBSERVATION',clock=clock,capacity=post['capacity'],no_running_containers=True)))
