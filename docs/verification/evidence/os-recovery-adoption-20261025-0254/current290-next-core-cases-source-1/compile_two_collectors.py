"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-authorized two sequential ordinary HOST collector compiles only.
"""
import hashlib,json,os,pathlib,time
E=pathlib.Path(__file__).resolve().parent
source=E.parent/'current290-native-retirement-eagain-repair-1/native_diagnostic_guest_collector.c'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='208204ffa5cc407cce0757dbcb797d5a5f646254fe0892608d5e8e36b704ec5b'
rows=[]
for case in ['files','threads']:
 out=E/case;out.mkdir(mode=0o700)
 argv=['/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=536870912:536870912','--cpu=6:6','--fsize=33554432:33554432','--core=0:0','--','/usr/bin/gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-static','-fno-pie','-no-pie','-Wl,-z,noexecstack','-DND_CORE_'+case.upper(),'-MD','-MF',str(out/'collector.d'),str(source),'-o',str(out/'init')]
 started=time.time();startmono=time.monotonic()
 with (out/'compile.stdout').open('xb') as stdout,(out/'compile.stderr').open('xb') as stderr:
  pid=os.fork()
  if not pid:
   os.dup2(stdout.fileno(),1);os.dup2(stderr.fileno(),2);os.execv(argv[0],argv)
  while True:
   got,status,usage=os.wait4(pid,os.WNOHANG)
   if got:break
   if time.monotonic()-startmono>45:
    os.kill(pid,9);got,status,usage=os.wait4(pid,0);break
   time.sleep(.02)
 rc=os.waitstatus_to_exitcode(status)
 row=dict(scope=__doc__.strip(),case=case,argv=argv,pid=pid,started_at=started,finished_at=time.time(),wall_seconds=time.monotonic()-startmono,returncode=rc,CPU_seconds=usage.ru_utime+usage.ru_stime,maximum_child_RSS_KiB=usage.ru_maxrss)
 if rc==0:
  b=(out/'init').read_bytes();row['collector']=dict(path=str(out/'init'),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
 (out/'ACTUAL-COMPILE-RESULT.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
 print(json.dumps(row),flush=True)
 if rc:break
(E/'ACTUAL-TWO-COLLECTOR-COMPILES.json').write_text(json.dumps(dict(scope=__doc__.strip(),authorization='New explicit Root followup assignment; no consumed memory compile grant reused',commands=rows,native_execution=False),indent=2)+'\n')
assert len(rows)==2 and all(x['returncode']==0 for x in rows)
