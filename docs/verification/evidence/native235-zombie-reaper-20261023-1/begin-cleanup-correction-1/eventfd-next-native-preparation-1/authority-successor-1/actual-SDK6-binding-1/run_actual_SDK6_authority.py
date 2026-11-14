"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One ordinary CPU6 pure Python authority consumer fixture, no artifactbuild/root/guest.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,sys
D=Path(__file__).resolve().parent;E=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/eventfd-next-native-preparation-1/authority-successor-1/actual-SDK6-binding-1')
h=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=h.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
t=ast.parse(raw);end=next(i for i,n in enumerate(t.body) if isinstance(n,ast.FunctionDef) and n.name=='owned_capture');ns={'__file__':str(h)};exec(compile(ast.Module(body=t.body[:end+1],type_ignores=[]),str(h),'exec'),ns)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
os.sched_setaffinity(0,{6})
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;assert mem>=19<<30
used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())['last_rate_limits']['primary']['usedPercent'];assert used<100
profile=dict(CPU=[6],jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=120,retirement_grace_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,MemAvailable=mem,aggregate_ceiling_bytes=19<<30,included_usage_percent=used)
cap=D/'actual-consumer-fixture-1';cap.mkdir();command=dict(argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'check_actual_SDK6_authority.py')],purpose=__doc__,profile=profile,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.is_file()});ns['write'](cap/'command.json',command)
r=ns['owned_capture'](command,cap,120,lambda:None);ns['write'](cap/'whole-join.json',r)
result=dict(scope=__doc__,status='PASS_ACTUAL_CONTROLLED_AUTHORITY_CONSUMER_WHOLE_JOIN' if r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and not r['error'] and not r['retirement_error'] else 'FAIL_FIRST_CANDIDATE_RETAINED',whole_join=r,profile=profile,CPU6_released=r['direct_child_joined'] and r['group_absent'] and r['closed_streams'],native=False,SDK6_acceptance=None)
ns['write'](D/'ACTUAL-CONSUMER-WHOLE-JOIN.json',result)
for p in [D/'ACTUAL-CONSUMER-WHOLE-JOIN.json',*cap.iterdir(),*[D/n for n in ['ACTUAL-SDK6-AUTHORITY-CONSUMER-RESULT.json'] if (D/n).exists()]]:
 q=E/p.relative_to(D);q.parent.mkdir(parents=True,exist_ok=True)
 with q.open('xb') as f:f.write(p.read_bytes())
print(json.dumps(result))
