"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,re,resource,signal,time
E=Path(__file__).resolve().parent;D=Path('/home/holden/mckernel-work/host-preparation/p12-long-mixed-apps-20261023-1');R=Path('/home/holden/mckernel')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
def ref(p):return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
def main():
 start=time.monotonic();os.sched_setaffinity(0,{6});os.environ.update(RUST_MIN_STACK='2097152',PAIR_CPU='6')
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 helper=R/'docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py';raw=helper.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8';nodes=[]
 for node in ast.parse(raw).body:
  if isinstance(node,(ast.Import,ast.ImportFrom)):nodes.append(node)
  elif isinstance(node,ast.FunctionDef) and node.name in {'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}:nodes.append(node)
  elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'} for t in node.targets):nodes.append(node)
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
 signal.setitimer(signal.ITIMER_REAL,90)
 bindings=json.loads((E/'SOURCE-BINDINGS.json').read_text());commands=json.loads((E/'PREPARED-COMMANDS.json').read_text())
 for row in [bindings['compiler'],bindings['original_ASM'],bindings['copied_ASM'],bindings['resource_measurement_tool']]+[x[k] for x in bindings['apps'] for k in ['original_source','original_ELF_unchanged_authority','new_source','expected_stdout','expected_stderr']]:assert sha(Path(row['path']))==row['sha256']
 assert os.statvfs(D).f_bavail*os.statvfs(D).f_frsize>=16*2**30+(128<<20) and os.statvfs('/home/holden/mckernel-work/scratch').f_bavail*os.statvfs('/home/holden/mckernel-work/scratch').f_frsize>=12*2**30
 results=[];error=None;status='FAIL_FIRST_COMMAND_OR_ORACLE_RETAINED';app_results=[]
 def run(command,measure_compiler=False):
  label=command['label'];cap=D/(label+'-capture-1');cap.mkdir(mode=0o700);cmd=dict(command,shell=False)
  if measure_compiler:cmd['compiler_argv']=cmd['argv'];cmd['argv']=['/usr/bin/time','-v','-o',str(cap/'resources.txt'),'--']+cmd['argv']
  write(cap/'command.json',cmd);os.chdir(command['cwd']);remaining=84-(time.monotonic()-start);assert remaining>0
  j=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',j);results.append(dict(label=label,whole_join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'],'failed '+label
  metrics=(cap/'resources.txt').read_text();m=re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)',metrics);assert m and 'Exit status: 0' in metrics
  return cap,j,int(m[1])*1024
 try:
  for command in commands['compile']:run(command,True)
  for i,command in enumerate(commands['Linux_runs']):
   cwd=Path(command['cwd']);cwd.mkdir(mode=0o700);cap,j,rss=run(command)
   assert (cap/'stdout').read_bytes()==(D/f'app{i}.expected.stdout').read_bytes(),'stdout oracle '+str(i)
   assert (cap/'stderr').read_bytes()==(D/f'app{i}.expected.stderr').read_bytes(),'stderr oracle '+str(i)
   assert 3.0<=j['seconds']<10.0,'LONG minimum/original10s ceiling '+str(i)
   assert list(cwd.iterdir())==[],'workspace cleanup '+str(i)
   app_results.append(dict(app=i,ELF=ref(D/f'app{i}-long'),wall_seconds=j['seconds'],max_rss_bytes=rss,stdout=ref(cap/'stdout'),stderr=ref(cap/'stderr'),resources=ref(cap/'resources.txt'),empty_workspace=str(cwd),original_body_once_source_rename_only=True,exit_status=0,Linux_reference_only=True,native_credit=False))
  for app in bindings['apps']:
   for key in ['original_source','original_ELF_unchanged_authority']:assert sha(Path(app[key]['path']))==app[key]['sha256']
  assert sha(Path(bindings['original_ASM']['path']))==bindings['original_ASM']['sha256']
  status='PASS_TWO_LONG_ELFS_AND_STRICT_LINUX_REFERENCE_ONLY'
 except BaseException as exc:error=repr(exc)
 result=dict(scope=__doc__,status=status,error=error,seconds=time.monotonic()-start,combined_cpu_seconds=ns['cpu_used'](),helper=ref(helper),source_bindings=ref(E/'SOURCE-BINDINGS.json'),prepared_commands=ref(E/'PREPARED-COMMANDS.json'),commands=results,apps=app_results,old_seed_sources_and_ELFs_unchanged=True,native_runs=0,native_acceptance=False,P12_acceptance=False,original_reported_round_counts_unchanged=True)
 write(D/'RESULT.json',result)
 for p in [D/'RESULT.json']+[q for cap in D.glob('*-capture-1') for q in cap.iterdir() if q.is_file()]:
  target=E/p.relative_to(D);target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(p.read_bytes())
 signal.setitimer(signal.ITIMER_REAL,0);print(json.dumps({k:result[k] for k in ['status','error','seconds','combined_cpu_seconds','apps']}))
if __name__=='__main__':main()
