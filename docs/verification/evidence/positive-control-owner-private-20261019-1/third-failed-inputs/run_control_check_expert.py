from pathlib import Path
import hashlib,json,os,signal,subprocess,time,resource
R=Path(__file__).resolve().parent;E=R/'check-3'
RUSTC='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
OLD=Path('/home/holden/mckernel-work/scratch/native-fork-carrier-link-20261017-1/test-expert')
COMMANDS=[['compile',[RUSTC,'--edition=2021','--test','-Wrust_2018_idioms','-Dwarnings',str(R/'actual-control-park-expert.rs'),'-C','link-arg='+str(OLD/'guest.o'),'-C','link-arg='+str(OLD/'codec.o'),'-o',str(E/'actual')]],['affected-test',[str(E/'actual'),'actual_control_','--test-threads=1','--nocapture']]]
def main():
 assert os.sched_getaffinity(0)=={6}
 assert resource.getrlimit(resource.RLIMIT_AS)==(1073741824,1073741824)
 assert resource.getrlimit(resource.RLIMIT_CPU)==(30,30)
 assert resource.getrlimit(resource.RLIMIT_FSIZE)==(33554432,33554432)
 assert resource.getrlimit(resource.RLIMIT_NOFILE)==(256,256)
 assert resource.getrlimit(resource.RLIMIT_CORE)==(0,0)
 assert not E.exists();E.mkdir()
 meminfo={line.split(':',1)[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')}
 assert meminfo['MemAvailable']>=2*1024**3
 admission={'memory':meminfo,'affinity':sorted(os.sched_getaffinity(0)),'rlimits':{str(k):resource.getrlimit(k) for k in [resource.RLIMIT_AS,resource.RLIMIT_CPU,resource.RLIMIT_FSIZE,resource.RLIMIT_NOFILE,resource.RLIMIT_CORE]},'capacity':[]}
 for path,floor in [('/home/holden/mckernel',16*1024**3),('/home/holden/mckernel-work/scratch',12*1024**3)]:
  st=os.statvfs(path);avail=st.f_bavail*st.f_frsize;admission['capacity'].append({'path':path,'available':avail,'required':floor+640*1024**2});assert avail>=floor+640*1024**2
 pins=json.loads((R/'fixture-inputs-expert.json').read_text())['inputs']
 pins+=json.loads((R.parent/'focused-tool-object-pins.json').read_text())
 for row in pins:assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
 (E/'admission.json').write_text(json.dumps(admission,indent=2)+'\n')
 deadline=time.monotonic()+28;rows=[]
 usage_before=sum(f.stat().st_size for f in R.rglob('*') if f.is_file())
 for label,cmd in COMMANDS:
  remaining=deadline-time.monotonic();assert remaining>3
  start=time.time_ns();mono=time.monotonic_ns();p=None;timedout=False
  with(E/(label+'.stdout')).open('xb')as out,(E/(label+'.stderr')).open('xb')as err:
   (E/(label+'.command.json')).write_text(json.dumps(cmd)+'\n')
   p=subprocess.Popen(cmd,cwd=R,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','TZ':'UTC','RUST_TEST_THREADS':'1','RUSTC_BOOTSTRAP':'1'},stdout=out,stderr=err,start_new_session=True)
   try:
    try:p.wait(timeout=min(20,remaining-3))
    except subprocess.TimeoutExpired:
     timedout=True;os.killpg(p.pid,signal.SIGTERM)
     try:p.wait(timeout=1)
     except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=1)
   finally:
    if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=1)
    try:os.killpg(p.pid,0);absent=False
    except ProcessLookupError:absent=True
    row={'argv':cmd,'pid':p.pid,'started_unix_ns':start,'finished_unix_ns':time.time_ns(),'elapsed_ns':time.monotonic_ns()-mono,'returncode':p.returncode,'direct_join':True,'closed_streams':{name:{'bytes':(E/(label+'.'+name)).stat().st_size,'sha256':hashlib.sha256((E/(label+'.'+name)).read_bytes()).hexdigest()}for name in ['stdout','stderr']},'process_group_absent':absent,'timedout':timedout}
    (E/(label+'.status.json')).write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
  assert p.returncode==0 and not timedout and absent,(label,p.returncode)
  assert(E/(label+'.stderr')).stat().st_size==0,label
 usage_after=sum(f.stat().st_size for f in R.rglob('*') if f.is_file())
 assert usage_after-usage_before <= 32*1024**2
 assert '4 passed; 0 failed' in(E/'affected-test.stdout').read_text()
 result={'status':'PASS_FOCUSED_ACTUAL_CONTROL_RESPONSE_PARK_BODY','commands':len(rows),'new_tests':4,'source_only':True,'native_authority':False,'full_close_body_executed':False,'restoration_conflict_fault_injection':True,'receipt_or_revoke_authority':False,'current_default_consumer':False,'final_ack_endpoint_executed':False,'all_direct_joined':True,'groups_absent':True}
 (E/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
