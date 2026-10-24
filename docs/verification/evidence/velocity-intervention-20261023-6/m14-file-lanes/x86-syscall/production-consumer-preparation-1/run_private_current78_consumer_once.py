"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root-granted coherent private78 production Rust/wholeC-TU/ABI/partial consumer.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,re,resource,signal,sys,time
D=Path(__file__).resolve().parent
RECIPE_SHA='3e2eac6955e81e86279f6049fbe16028e1b95501f0ce3f96c19b7aaee057cce8'
P=D/'EXACT-PRIVATE-CURRENT78-F06-PRODUCTION-CONSUMER.NOT-EXECUTED.json'
def pin(p):
 b=Path(p).read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def need(v,m):
 if not v:raise RuntimeError(m)
def write(p,v):
 with Path(p).open('x') as f:json.dump(v,f,sort_keys=True);f.write(chr(10))
def rows(text):return [line.split() for line in text.splitlines() if line.split()]
def unique(text,name,kind):
 found=[x for x in rows(text) if x[-1]==name];need(len(found)==1 and found[0][-2]==kind,'exact unique '+name);return found[0]
need(os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12),'actual interpreter beforechild')
need(pin(P)['sha256']==RECIPE_SHA,'exact production recipe');r=json.loads(P.read_text());ov=json.loads(Path(r['source_overlay']['path']).read_text());need(pin(Path(r['source_overlay']['path']))==r['source_overlay'],'overlaybinding')
for row in ov['inputs'].values():
 need(pin(Path(row['private']['path']))==row['private'],'private78pin');need(pin(Path(row['canonical']['path']))==row['canonical'],'currentcoherentpreimage changed; STOPno refresh')
for row in ov['actual_header_closure']:
 for key in ('private','retained_system_header'):
  if key in row:need(pin(Path(row[key]['path']))==row[key],'realheaderpin')
need(pin(Path(r['compiler']))['sha256']==r['compiler_sha256'],'actual acceptedproductioncompiler')
helper=D/'accepted_ELF64_symtab_RELA.ACTUAL-FUNCTION.py';need(pin(helper)==r['ELF64_exact_helper'],'exact776bELFhelper');e={'Path':Path,'_fail':need};exec(compile(helper.read_text(),str(helper),'exec'),e)
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();need(pin(H)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','ownedcapture990')
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[n for n in ast.parse(raw,str(H)).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
def globals_used(code):
 used={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
 for value in code.co_consts:
  if isinstance(value,type(code)):used.update(globals_used(value))
 return used
deps=set()
for n in functions:deps.update(globals_used(ns[n].__code__))
need(not deps-set(ns)-set(vars(builtins)),'helper global dependencies')
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden/mckernel-work');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
head=dict(MemAvailable=mem,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,backing_size=bs.st_size,full_backing_gap=gap)
used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];need(used<100,'included plan guard');need(mem>=19<<30 and bs.st_size==110<<30 and head['HOST_available']>=head['HOST_required'] and head['scratch_available']>=head['scratch_required'],'fresh aggregate/floors/fullgap')
write(D/'ACTUAL-HEADROOM.json',head);O=D/'output-1';O.mkdir(mode=0o700);C=D/'actual-production-consumer-1';C.mkdir(mode=0o700);os.chdir(O);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
write(D/'ACTUAL-PROFILE.json',dict(scope=__doc__,recipe=pin(P),profile=r['profile'],driver=pin(Path(__file__)),helper=pin(H),globals_missing=[],source_identity=r['source_identity']))
records=[];texts={};objects={};start=time.monotonic();failure=None;signal.setitimer(signal.ITIMER_REAL,96)
try:
 for i,c in enumerate(r['commands']):
  cap=C/str(i).zfill(2);cap.mkdir(mode=0o700);write(cap/'command.json',c);remaining=90-(time.monotonic()-start);need(remaining>0,'whole ordinary wallbound');j=ns['owned_capture'](c,cap,remaining,lambda:None);write(cap/'whole-join.json',j);records.append(dict(label=c['label'],join=j,command=pin(cap/'command.json')))
  need(j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'] and not j['timed_out'],'first failed command '+c['label'])
  texts[c['label']]=(cap/'stdout').read_text()
  if c['label']=='00-current78-F06-Rust-compile':objects['Rust']=ns['hashed'](O/'mckernel_rust.o',32<<20);write(D/'DURABLE-RUST-OBJECT.json',objects['Rust'])
  if c['label']=='actual-partial-link':objects['partial']=ns['hashed'](O/'arch-event-syscall-partial.o',32<<20);write(D/'DURABLE-PARTIAL-OBJECT.json',objects['partial'])
 arch=texts['arch/x86_64/kernel/syscall.c:symbols'];kernel=texts['kernel/syscall.c:symbols'];rust=texts['Rust-global-symbols'];partial=texts['partial-global-symbols']
 need(not [x for x in rows(arch) if x[-1] in ('arch_ptrace_syscall_event','arch_ptrace_syscall_event_bridge') and x[-2] in ('T','t')],'selected C entry/adapter remains')
 unique(kernel,'arch_ptrace_syscall_event','U');unique(kernel,'ptrace_syscall_event','T');unique(rust,'arch_ptrace_syscall_event','T');unique(rust,'arch_ptrace_syscall_event_body_result','T');unique(rust,'ptrace_syscall_event','U');unique(partial,'arch_ptrace_syscall_event','T');unique(partial,'ptrace_syscall_event','T')
 pp=texts['arch-default-selected-preprocess'];need(re.search(r'\barch_ptrace_syscall_event\s*\([^;{}]*\)\s*\{',pp,re.S) is None,'selected preprocessed C entry')
 counts={key:e['_m14_Rust_callback_relocations'](p,t) for key,p,t in [('kernel_to_Rust',O/'kernel-syscall.o',('arch_ptrace_syscall_event',)),('Rust_to_publicevent',O/'mckernel_rust.o',('ptrace_syscall_event',)),('partial_resolved',O/'arch-event-syscall-partial.o',('arch_ptrace_syscall_event','ptrace_syscall_event'))]}
 baseline=Path(r['baseline_nm']['path']);need(pin(baseline)==r['baseline_nm'],'accepted baselineNM');oldT={x[-1] for x in rows(baseline.read_text()) if len(x)>=3 and x[-2]=='T'};newT={x[-1] for x in rows(rust) if len(x)>=3 and x[-2]=='T'};need(not oldT-newT,'prior actualRustT lost')
 write(D/'ACTUAL-EXACT-SYMTAB-RELA-PROOF.json',dict(scope=__doc__,counts=counts,helper=r['ELF64_exact_helper'],source_driver_776b=True,SHF_ALLOC_sh_info_filter=True,exact_target_names=True,substring_matching=False))
 write(D/'ACTUAL-PRODUCTION-CONSUMER-RECEIPT.json',dict(scope=__doc__,status='PASS_PRIVATE78_WHOLE_GCC9_TUS_REAL_ABI_EXACT_SYMBOL_RELA_PARTIAL_ONLY',recipe=pin(P),source_identity=r['source_identity'],objects=objects,records=records,exact_allocated_RELA=counts,preserved_all_prior_Rust_T=True,seconds=time.monotonic()-start,CPU6_released=True,canonical_edits=0,default_GCC14_final_image_native=False))
 print(json.dumps(dict(status='PASS',commands=len(records),seconds=time.monotonic()-start,CPU6_released=True)))
except BaseException as exc:
 write(D/'FIRST-UNEXPECTED-FAILURE.json',dict(scope=__doc__,status='STOP_FIRST_UNEXPECTED_NO_RETRY',error=repr(exc),records=records,objects=objects,CPU6_released=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in records)));raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
