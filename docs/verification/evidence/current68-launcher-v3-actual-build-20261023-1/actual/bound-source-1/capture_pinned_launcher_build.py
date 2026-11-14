from pathlib import Path
import subprocess,json,time,os,hashlib
q=Path('/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1');b=json.loads((q/'ROOT-FINAL-REQUEST-BINDING-1.json').read_text());r=Path(b['request']['path']);assert hashlib.sha256(r.read_bytes()).hexdigest()==b['request']['sha256'];owner=Path(b['owner_argv'][3]);assert hashlib.sha256(owner.read_bytes()).hexdigest()=='c9eb78a4c1113f6bee6b809fc07d215978b2914f6edefe73d85757e32dea2f42'
c=q/'actual-pinned-build-capture-1';c.mkdir(mode=0o700);t=time.monotonic()
with (c/'stdout').open('xb') as out,(c/'stderr').open('xb') as err:
 p=subprocess.Popen(b['owner_argv'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);start=Path('/proc/'+str(p.pid)+'/stat').read_text().rpartition(') ')[2].split()[19];(c/'child-start.json').write_text(json.dumps(dict(pid=p.pid,start=start,argv=b['owner_argv']),indent=2)+'\n');print('ACTUAL_PINNED_BUILD_OWNER_STARTED',p.pid,start,flush=True);code=p.wait()
try:os.killpg(p.pid,0);absent=False
except ProcessLookupError:absent=True
s=dict(returncode=code,direct_child_joined=True,process_group_absent=absent,streams_closed=True,elapsed_seconds=time.monotonic()-t);(c/'status.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s),flush=True)
