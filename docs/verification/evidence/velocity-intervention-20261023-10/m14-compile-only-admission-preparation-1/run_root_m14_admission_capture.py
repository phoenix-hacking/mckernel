"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact read-only root query under accepted990807 owned_capture; no build/guest/create.
"""
import ast,hashlib,json,os,resource,signal,sys
from pathlib import Path
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def need(v,m):
 if not v:raise RuntimeError(m)
need(len(sys.argv)==3,'exact profilepath and profileSHA')
p=Path(sys.argv[1]);need(p.is_absolute() and p.resolve(strict=True)==p,'canonicalprofile')
raw=p.read_bytes();need(len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==sys.argv[2],'profileSHA')
x=json.loads(raw);need(x['schema']=='mckernel.exact-readonly-owned-capture-profile.v1','profileschema')
need(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==x['runner']['sha256'] and str(Path(__file__).resolve())==x['runner']['path'],'actualobserverrunner')
need(os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={7},'rootCPU7observer')
for key,value in [(resource.RLIMIT_AS,2*2**30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32*2**20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:need(resource.getrlimit(key)==(value,value),'exactobserverrlimits')
need(x['CPU']==[7] and x['AS_bytes']==2*2**30 and x['CPU_seconds']==30 and x['wall_seconds']==60 and x['retirement_grace_seconds']==6 and x['FSIZE_bytes']==32*2**20 and x['NOFILE']==256 and x['core']==0,'exactprofilevalues')
need(x['capture_directory']==str(D/'actual-fresh-root-admission-1'),'exactfreshcapturepath')
for row in x['input_sources']:
 f=Path(row['path']);b=f.read_bytes();need(len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],'exactqueryinputsource')
raw=H.read_bytes();need(hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','accepted990807')
names={'need','write','hashed','stop','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'} for t in n.targets)]
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
signal.setitimer(signal.ITIMER_REAL,60)
out=Path(x['capture_directory']);out.mkdir(mode=0o700)
ns['write'](out/'command.json',dict(scope=__doc__,profile=x,profile_sha256=sys.argv[2],argv=x['query_argv']))
def limits():
 os.sched_setaffinity(0,{7})
 for key,value in [(resource.RLIMIT_AS,2*2**30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32*2**20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(key,(value,value))
r=ns['owned_capture'](dict(argv=x['query_argv']),out,60,limits)
signal.setitimer(signal.ITIMER_REAL,0)
ns['write'](out/'ACTUAL-CLOSED-CAPTURE.json',r)
need(r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and r['captures']['stderr']['size']==0,'actualreadonlyquerywholejoin')
observation=json.loads((out/'stdout').read_bytes());need(observation['status']=='PASS_READONLY_M14_ADMISSION_CANDIDATE_ONLY','actualquerystatus')
print(json.dumps(dict(scope=__doc__,status='PASS_ROOT_OWNED_FRESH_M14_READONLY_CAPTURE',profile_sha256=sys.argv[2],closed_capture=r,query_status=observation['status'],native_acceptance=False,execution_release=False),sort_keys=True))
