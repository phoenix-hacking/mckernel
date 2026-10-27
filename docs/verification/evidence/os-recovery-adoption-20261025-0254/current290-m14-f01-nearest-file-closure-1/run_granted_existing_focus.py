"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
New Root-authorized existing eleven-command HOST recipe; no Rust rebuild/native.
"""
import hashlib,importlib.util,json,os,pathlib,resource,signal,subprocess,sys,time
E=pathlib.Path(__file__).resolve().parent;D=E.parent
GUARD=D/'m14-f06-selected-residual-implementation-20261026-1/next-process-vm-selected-1/next-prctl-getter-selected-1/actual-host-getter-1/reviewed-account-supervisor-correction-1'

def ref(p):
 p=pathlib.Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def verify(rows):
 for r in rows:assert ref(r['path'])==r,'frozen input drift: '+r['path']
def main():
 os.sched_setaffinity(0,{6})
 for k,v in [(resource.RLIMIT_AS,2*2**30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,64*2**20),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 assert ref(GUARD/'run_sealed.py')['sha256']=='e8b84de39128433542b213fc3a374dd50d3e12f232bd397dddaa24859349a805'
 sys.path.insert(0,str(GUARD));spec=importlib.util.spec_from_file_location('accepted_f01_admission',GUARD/'run_sealed.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
 plan=json.loads((E/'EXISTING-FOCUSED-MEM-RECIPE.NOT-ADMITTED.json').read_text());verify(plan['fixture_inputs']+[plan['source_script']]);pins=json.loads((E/'SEALED-FOCUSED-INPUTS.json').read_text());verify(pins['inputs']+pins['headers']+pins['tools'])
 A=E/'actual-focused-attempt-1';A.mkdir(mode=0o700);B=A/'output';B.mkdir(mode=0o700);logs=A/'logs';logs.mkdir(mode=0o700)
 results=[];status='RUNNING';failure=None;initial=guard.admission()
 try:
  for index,raw in enumerate(plan['commands']):
   command=[s.replace(str(E/'prospective-output'),str(B)) for s in raw]
   # Linker maps are observation-only outputs required to rule out C stub masking.
   if index in (6,7):command.insert(1,'-Wl,-Map='+str(B/('C.map' if index==6 else 'Rust.map')))
   verify(pins['inputs']+pins['headers']+pins['tools']);admission=guard.admission();started=time.monotonic();wall=time.time()
   stdout_path=B/('C.stdout' if index==8 else 'Rust.stdout') if index in (8,9) else logs/(str(index)+'.stdout')
   with stdout_path.open('xb') as stdout,(logs/(str(index)+'.stderr')).open('xb') as stderr:
    child=subprocess.Popen(command,cwd=pins['cwd'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True,close_fds=True,env={'PATH':'/usr/bin:/bin','LC_ALL':'C','RUST_BACKTRACE':'0'})
    while True:
     pid,exitstatus,usage=os.wait4(child.pid,os.WNOHANG)
     if pid:break
     if time.monotonic()-started>=90:
      os.killpg(child.pid,signal.SIGKILL);pid,exitstatus,usage=os.wait4(child.pid,0);break
     time.sleep(.01)
    child.returncode=os.waitstatus_to_exitcode(exitstatus)
   try:os.killpg(child.pid,0);absent=False
   except ProcessLookupError:absent=True
   row=dict(index=index,argv=command,purpose=__doc__.strip(),pid=child.pid,started_wall=wall,elapsed=time.monotonic()-started,CPU_user=usage.ru_utime,CPU_system=usage.ru_stime,max_RSS_KiB=usage.ru_maxrss,returncode=child.returncode,direct_wait=True,group_absent=absent,admission=admission,stdout=ref(stdout_path),stderr=ref(logs/(str(index)+'.stderr')));results.append(row)
   (A/'RESULTS.json').write_text(json.dumps(dict(status='RUNNING',initial_admission=initial,results=results),indent=2)+'\n')
   if child.returncode or not absent:raise RuntimeError('first compile/link/effect failure index'+str(index))
   if index==7:
    raise RuntimeError('STOP mandatory exact symbol-origin review before effects; no source-only origin acceptance')
  status='PASS_EXISTING_FOCUSED_COMPARATOR_PENDING_SYMBOL_ORIGIN_AND_INDEPENDENT_FILE_REVIEW'
 except BaseException as exc:status='FAIL_STOPPED_FIRST_FAILURE';failure=repr(exc)
 final=dict(status=status,scope=__doc__.strip(),authorization='New directRoot followup grants these11commands only; no consumed prior grant reused',sealed_pins=ref(E/'SEALED-FOCUSED-INPUTS.json'),initial_admission=initial,first_compiler_timestamp=results[0]['started_wall'] if results else None,results=results,failure=failure,whole_file_acceptance=False,runtime_native=False)
 (A/'RESULTS.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(dict(status=status,commands=len(results),failure=failure,all_joined=all(x['direct_wait'] and x['group_absent'] for x in results))))
 if failure:sys.exit(1)
if __name__=='__main__':main()
