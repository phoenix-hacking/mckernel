"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual GCC9 header/config and Rust shared-type layout witness, ELF data only.
No exact GCC14 wholeTU, no kernel/defaultlink/native/host-state execution.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,struct,subprocess,time
P=Path(__file__).resolve().parent;F=P/'EXACT-LAYOUT-WITNESS-RECIPE.GRANTED.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
assert sha(F)=='d2ae46b0559a636ac42a4ddfe0f09a4857437ac6314aabc806365961234e173a';recipe=json.loads(F.read_text())
assert sha(Path(recipe['C_argv'][0]))==recipe['C_compiler_expected_sha256']
assert sha(Path(recipe['Rust_argv'][6]))==recipe['Rust_compiler_expected_sha256']
for row in [*recipe['source_files'].values(),*recipe['actual_header_config_closure'].values()]:assert pin(Path(row['path']))==row
assert os.getuid()==os.geteuid()==1000
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
O=P/'output-1';O.mkdir(mode=0o700);CAP=P/'actual-owned-capture-1';CAP.mkdir(mode=0o700)
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;h=os.statvfs('/home/holden');s=os.statvfs('/home/holden/mckernel-work/scratch');back=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,back.st_size-back.st_blocks*512)
capacity=dict(MemAvailable_bytes=mem,minimum_memory_bytes=19<<30,HOST_available_bytes=h.f_bavail*h.f_frsize,scratch_available_bytes=s.f_bavail*s.f_frsize,HOST_floor=16<<30,scratch_floor=12<<30,full_sparse_gap_bytes=gap,HOST_small_output_reserve=64<<20)
assert mem>=19<<30 and capacity['HOST_available_bytes']>=(16<<30)+gap+(64<<20) and capacity['scratch_available_bytes']>=12<<30
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());capacity['included_usage_percent_observed']=state['last_rate_limits']['primary']['usedPercent'];assert capacity['included_usage_percent_observed']<100
write(P/'ACTUAL-CAPACITY.json',capacity)
os.chdir(O);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for sig in STOP_SIGNALS:signal.signal(sig,stop)
def limits():
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
limits();profile=dict(scope=__doc__,authority='Root explicitly clarified GCC9 accepted idle/headerfixture layout witness; exact GCC14wholeTU OPEN',recipe=pin(F),CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=120,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,RUST_MIN_STACK=2097152,tools={x:pin(Path(x)) for x in [recipe['C_argv'][0],recipe['Rust_argv'][0],recipe['Rust_argv'][6],'/usr/bin/nm','/usr/bin/readelf']})
write(P/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,126);records=[]
def run(name,argv):
 cap=CAP/name;cap.mkdir(mode=0o700);cmd=dict(scope=recipe['scope'],purpose=__doc__,argv=argv,cwd=str(O),profile=pin(P/'ACTUAL-PROFILE.json'));write(cap/'command.json',cmd)
 j=owned_capture(cmd,cap,max(.1,120-(time.monotonic()-begin)),limits);write(cap/'whole-join.json',j);records.append(dict(name=name,join=j,command=pin(cap/'command.json')))
 assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
 return j
# ELF object metadata decoder; consumes only our two fixed compiler artifacts.
def object_words(path,name,count):
 raw=path.read_bytes();assert raw[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',raw,16)[0]==1
 off=struct.unpack_from('<Q',raw,40)[0];ents,n=struct.unpack_from('<HH',raw,58);assert ents==64 and 0<n<65535 and off+n*ents<=len(raw)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*ents) for i in range(n)];found=[]
 for sec in sections:
  if sec[1]!=2:continue
  assert sec[9]==24 and sec[6]<n;strings=sections[sec[6]];tab=raw[strings[4]:strings[4]+strings[5]]
  for at in range(sec[4],sec[4]+sec[5],24):
   ni,info,other,idx,value,size=struct.unpack_from('<IBBHQQ',raw,at);end=tab.find(b'\0',ni);assert end>=ni
   if tab[ni:end].decode()==name:
    assert (info&15)==1 and 0<idx<n and size==count*8,(name,info,idx,size)
    target=sections[idx];start=target[4]+value;assert value+size<=target[5] and start+size<=len(raw)
    found.append(struct.unpack_from('<'+'Q'*count,raw,start))
 assert len(found)==1,(name,len(found));return found[0]
try:
 run('00-C-real-header-compile',recipe['C_argv']);run('01-Rust-actual-types-compile',recipe['Rust_argv'])
 objects={name:hashed(O/name,32<<20) for name in ['c-layout.o','rust-layout.o']}
 write(P/'DURABLE-LAYOUT-OBJECTS.json',dict(scope=recipe['scope'],status='BOTH_COMPILERS_PASS_OBJECTS_RETAINED_BEFORE_DATA_OBSERVER',objects=objects,compiler_invocations=dict(C=1,Rust=1),actual_fullcrate=False))
 for i,(tool,args) in enumerate([('/usr/bin/nm',['-S','-g']),('/usr/bin/readelf',['--wide','--syms'])]):
  for language in ['c','rust']:run('%02d-%s-%s'%(2+i*2+(language=='rust'),language,Path(tool).name),[tool,*args,str(O/(language+'-layout.o'))])
 count=len(recipe['witness_rows']);cw=object_words(O/'c-layout.o','M14_C_LAYOUT',count);rw=object_words(O/'rust-layout.o','M14_RUST_LAYOUT',count)
 differences=[dict(index=i,label=recipe['witness_rows'][i]['label'],C=a,Rust=b) for i,(a,b) in enumerate(zip(cw,rw)) if a!=b]
 spinC=object_words(O/'c-layout.o','process_sched_runqueue_offsets',26);spinR=object_words(O/'rust-layout.o','M14_RUST_SPIN',26)
 timerC=object_words(O/'c-layout.o','process_timer_runtime_offsets',15);timerR=object_words(O/'rust-layout.o','M14_RUST_TIMER',15)
 write(P/'ACTUAL-LAYOUT-VALUES.json',dict(scope=recipe['scope'],values=[dict(label=row['label'],C=cw[i],Rust=rw[i]) for i,row in enumerate(recipe['witness_rows'])],differences=differences,actual_spin_C=list(spinC),actual_spin_Rust=list(spinR),actual_timer_C=list(timerC),actual_timer_Rust=list(timerR),no_target_execution=True))
 assert not differences and spinC==spinR and timerC==timerR,dict(differences=differences,spin_equal=spinC==spinR,timer_equal=timerC==timerR)
 assert all(pin(Path(row['path']))==row for row in [*recipe['source_files'].values(),*recipe['actual_header_config_closure'].values()]) and cpu_used()<=60
 result=dict(scope=recipe['scope'],status='PASS_ACTUAL_CURRENT_HEADER_RUST_TYPE_LAYOUT_ONLY',recipe=pin(F),profile=pin(P/'ACTUAL-PROFILE.json'),capacity=pin(P/'ACTUAL-CAPACITY.json'),objects=objects,actual_values=pin(P/'ACTUAL-LAYOUT-VALUES.json'),equal_layout_words=count,equal_actual_spin_initializer_words=26,equal_actual_timer_initializer_words=15,actual_header_files=73,source_positions=recipe['source_positions'],compiler_invocations=dict(C=1,Rust=1),records=records,failures=0,corrections=0,total_CPU_seconds=cpu_used(),seconds=time.monotonic()-begin,CPU6_released=True,not_models=True,no_target_execution=True,C_profile='GCC9 accepted real-header ordinary fixture; exact GCC14wholeprocessTU remains OPEN',Rust_profile='Samepinnednightly1.95/4cfg flags; actualwholeabi.rs and descriptor/constructor types; standalone data witness, no fullcrate recompile',whole_C_TU_default_link_native='OPEN')
 write(P/'ACTUAL-LAYOUT-RECEIPT.json',result);print(json.dumps(dict(status=result['status'],seconds=result['seconds'],equal_words=count,receipt=pin(P/'ACTUAL-LAYOUT-RECEIPT.json'),CPU6_released=True)))
except BaseException as exc:
 write(P/'FAILURE-1.json',dict(scope=recipe['scope'],status='FAIL_PRESERVED_NO_AUTOMATIC_REPLAY',error=type(exc).__name__+': '+str(exc),records=records,objects=locals().get('objects'),CPU6_released=all(row['join']['direct_child_joined'] and row['join']['group_absent'] and row['join']['closed_streams'] for row in records)));raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
