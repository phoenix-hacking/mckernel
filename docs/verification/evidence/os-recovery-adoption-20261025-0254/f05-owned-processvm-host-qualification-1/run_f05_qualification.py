"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import ast,datetime,hashlib,json,os,resource,signal,shutil,time
from pathlib import Path
D=Path(__file__).resolve().parent
G=D/'ROOT-ADOPTED-ORDINARY-CPU6-GRANT.json'
E=D.parent
S=E/'m14-f06-selected-residual-implementation-20261026-1/next-process-vm-selected-1/next-prctl-getter-selected-1/actual-host-getter-1/reviewed-account-supervisor-correction-1'
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load_nodes(p,functions,constants=(),imports=False):
 nodes=[]
 for n in ast.parse(p.read_bytes()).body:
  if imports and isinstance(n,(ast.Import,ast.ImportFrom)):nodes.append(n)
  elif isinstance(n,ast.FunctionDef) and n.name in functions:nodes.append(n)
  elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets):nodes.append(n)
 return ast.Module(body=nodes,type_ignores=[])
def save(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def main():
 assert ref(G)['sha256']=='7c98d580e0b9757f84da3ae8ddab5b04f3d5cb2a69fccd82dac86df6213561ee'
 grant=json.loads(G.read_bytes());argv=grant['exact_compiler_argv'];app=Path(argv[-1]);assert not app.exists()
 assert ref(Path(argv[-3]))['sha256']==grant['source_sha256']==ref(D/'app.rs')['sha256']
 oracle=json.loads((D/'primary-oracle.json').read_bytes());assert bytes.fromhex(oracle['stdout_hex'])==(D/'expected.stdout').read_bytes()
 assert ref(S/'accepted_account_policy.py')['sha256']=='d300c64f6df103af42b628eff65db07387f9d7840bc2c842163e06a9d8fdfddc'
 policy={'__file__':str(S/'accepted_account_policy.py')};exec(compile((S/'accepted_account_policy.py').read_bytes(),str(S/'accepted_account_policy.py'),'exec'),policy)
 assert ref(S/'run_sealed.py')['sha256'].startswith('e8b84de39128')
 adm={'Path':Path,'hashlib':hashlib,'json':json,'datetime':datetime,'os':os,'time':time,'ref':ref,'check_account_state':policy['check_account_state']}
 exec(compile(load_nodes(S/'run_sealed.py',{'admission'}),str(S/'run_sealed.py'),'exec'),adm)
 assert ref(H)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 funcs={'need','write','hashed','stop','members','cpu_used','process_start','terminal_unreaped','wait_terminal','owned_capture'}
 consts={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 ns={'__file__':str(H),'__name__':'f05_owned_capture'}
 exec(compile(load_nodes(H,funcs,consts,True),str(H),'exec'),ns)
 assert callable(ns['owned_capture'])
 os.sched_setaffinity(0,{6});assert os.sched_getaffinity(0)=={6}
 os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',LC_ALL='C',RUST_BACKTRACE='0')
 os.chdir(D)
 for n in ns['STOP_SIGNALS']:signal.signal(n,ns['stop'])
 def limits():
  os.sched_setaffinity(0,{6})
  for kind,bound in [(resource.RLIMIT_AS,1<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,64<<20),(resource.RLIMIT_CORE,0)]:resource.setrlimit(kind,(bound,bound))
 commands=[dict(argv=argv,purpose=__doc__+' Exact Root-adopted foreground Rust compiler argv.',wall=90),dict(argv=['/usr/bin/readelf','-W','-h','-l','-d',str(app)],purpose=__doc__+' Read-only executable/static ELF qualification.',wall=90),dict(argv=[str(app)],purpose=__doc__+' Owned Linux parent-child reference against unchanged frozen oracle.',wall=10)]
 tools=[ref(argv[0]),ref('/usr/bin/readelf')]
 captures=D/'actual-capture-1';captures.mkdir(mode=0o700)
 save(D/'SEALED-ACTUAL-COMMANDS.json',dict(scope=__doc__,grant=ref(G),inputs=[ref(Path(argv[-3])),ref(D/'app.rs'),ref(D/'primary-oracle.json'),ref(D/'expected.stdout')],tools=tools,helpers=[ref(H),ref(S/'run_sealed.py'),ref(S/'accepted_account_policy.py')],commands=commands,profile=grant['ordinary_profile']))
 rows=[]
 for i,cmd in enumerate(commands):
  assert ref(Path(argv[-3]))['sha256']==grant['source_sha256']
  assert [ref(argv[0]),ref('/usr/bin/readelf')]==tools
  admission=adm['admission']()
  floors={str(p):shutil.disk_usage(p).free for p in (D,Path('/home/holden/mckernel-work/scratch'))}
  assert min(floors.values())>=12*2**30
  p=captures/str(i);p.mkdir(mode=0o700)
  save(p/'command.json',dict(command=cmd,admission=admission,disk_free_bytes=floors,started_wall=time.time(),started_monotonic=time.monotonic()))
  before=resource.getrusage(resource.RUSAGE_CHILDREN)
  row=ns['owned_capture'](cmd,p,cmd['wall'],limits)
  after=resource.getrusage(resource.RUSAGE_CHILDREN)
  row.update(index=i,argv=cmd['argv'],finished_wall=time.time(),cpu_user_seconds=after.ru_utime-before.ru_utime,cpu_system_seconds=after.ru_stime-before.ru_stime,max_RSS_children_KiB=after.ru_maxrss)
  rows.append(row);save(p/'status.json',row);save(D/'ACTUAL-RESULT.json',dict(status='RUNNING',scope=__doc__,results=rows))
  assert row['returncode']==0 and row['direct_child_joined'] and row['group_absent'] and row['closed_streams'] and not row['error'] and not row['retirement_error'], 'first command failure index '+str(i)
  if i==0:
   save(D/'ACTUAL-EXECUTABLE.json',ref(app));app.chmod(0o555)
  if i==1:
   text=(p/'stdout').read_text();assert 'EXEC (Executable file)' in text and 'Advanced Micro Devices X86-64' in text and 'INTERP' not in text and 'There is no dynamic section' in text, 'ELF static qualification'
  if i==2:
   assert (p/'stdout').read_bytes()==bytes.fromhex(oracle['stdout_hex']) and (p/'stderr').read_bytes()==bytes.fromhex(oracle['stderr_hex']) and row['returncode']==oracle['exit_code'], 'unchanged primary oracle'
 save(D/'ACTUAL-RESULT.json',dict(status='PASS_F05_OWNED_LINUX_REFERENCE_ONLY',scope=__doc__,results=rows,executable=ref(app),source=ref(Path(argv[-3])),oracle=ref(D/'primary-oracle.json'),CPU6_released=True,native_M14_05_05='OPEN',conditional_CLONE_TID_writeproof='OPEN',limits='Linux reference and static ELF/source bindings only; no McKernel/native/default acceptance'))
 print(json.dumps(dict(status='PASS_F05_OWNED_LINUX_REFERENCE_ONLY',commands=len(rows),CPU_seconds=sum(r['cpu_user_seconds']+r['cpu_system_seconds'] for r in rows),wall_seconds=sum(r['seconds'] for r in rows),max_RSS_KiB=max(r['max_RSS_children_KiB'] for r in rows),all_joined=True,all_groups_absent=True,all_streams_closed=True)))
if __name__=='__main__':
 try:main()
 except BaseException as e:
  save(D/'FIRST-ACTUAL-FAILURE.json',dict(scope=__doc__,error=repr(e),CPU6_no_further_commands=True));raise
