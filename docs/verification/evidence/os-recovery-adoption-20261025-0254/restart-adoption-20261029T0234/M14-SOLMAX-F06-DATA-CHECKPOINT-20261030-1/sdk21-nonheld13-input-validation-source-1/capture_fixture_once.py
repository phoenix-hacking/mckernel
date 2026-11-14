"""One pure fixture execution; functional McKernel OS only, no security testing.
Retained census function only; no imported old top-level code or arbitrary argv.
"""
import ast, hashlib, json, os, signal, sys, time
from pathlib import Path

D=Path(__file__).resolve().parent
OUT=D/'pure-fixture-1'
MATCH=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/MANUAL-RESUME-M14-20261030-2/perf-counter-runner-successor-1/serial_supervised.py')
EXPECTED={'matcher':'7d8e744c755b37213abb81e9ce8b2220edc2b982fdfcbd9b61b3b45815e1dbfd',
          'fixture':'4a7c7ef3f54cb526ef6a252ae4c0436b9e090257bfda6e2dccd447b489c52405',
          'validator':'c7dfd75f22a1f0bfedf01bc8a95612806e3e8b08f9cdd049d2fec420967edeca',
          'profile':'3e6d2491c509790cea3f2de035e2171858d5efbcb9cc0dca8cc3aaea15007926',
          'proposal':'6cce26d01ae0810160a8964262b6dd5bf8aca09bf88ff8f56cae3b3e42eb40dd',
          'python':'8f122d7bdf820e716491d2be6c3b9f2b85f5fa46b34811e29432fa7cd8fd41fb'}
paths={'matcher':MATCH,'fixture':D/'test_sdk13_input_validation.py','validator':D/'sdk13_input_validation.py',
       'profile':D.parent/'sdk21-nonheld13-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json',
       'proposal':D.parent/'sdk21-nonheld13-admission-successor-1/ADMISSION-SUCCESSOR.SOURCE-ONLY.json',
       'python':Path('/home/holden/anaconda3/bin/python3.9')}
for key,path in paths.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest()==EXPECTED[key], key
raw=MATCH.read_text(); tree=ast.parse(raw)
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('census','leader_state')]
assert {n.name for n in nodes}=={'census','leader_state'}
space={'Path':Path,'os':os}; exec(compile(ast.Module(body=nodes,type_ignores=[]),str(MATCH),'exec'),space)
OUT.mkdir(mode=0o700)
def record(name,value):
    with (OUT/name).open('x') as f: json.dump(value,f,indent=2); f.write('\n')
def proc(pid):
    s=Path('/proc/%s/stat'%pid).read_text().rsplit(')',1)[1].split()
    return {'pid':pid,'state':s[0],'ppid':int(s[1]),'pgid':int(s[2]),'sid':int(s[3]),'start_ticks':int(s[19])}
argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(paths['fixture'])]
record('argv.json',{'argv':argv,'owner_argv':['/usr/bin/taskset','-c','0','/usr/bin/prlimit','--as=536870912:536870912','--cpu=20:20','--nofile=128:128','--fsize=8388608:8388608','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',str(D/'capture_fixture_once.py')],
    'owner_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'wrapper_hashes':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('/usr/bin/taskset','/usr/bin/prlimit')},
    'cwd':str(D),'limits':'inherited CPU0 AS512MiB CPU20s NOFILE128 FSIZE8MiB CORE0; monotonic deadline 30s TERM +5s KILL','inputs':{k:{'path':str(v),'sha256':EXPECTED[k]} for k,v in paths.items()}})
ready_r,ready_w=os.pipe(); gate_r,gate_w=os.pipe()
stdout=(OUT/'stdout').open('xb'); stderr=(OUT/'stderr').open('xb')
start=time.monotonic(); pid=os.fork()
if pid==0:
    try:
        os.close(ready_r); os.close(gate_w); os.setsid()
        os.write(ready_w,b'R'); os.close(ready_w)
        if os.read(gate_r,1)!=b'G': os._exit(121)
        os.close(gate_r); os.dup2(stdout.fileno(),1); os.dup2(stderr.fileno(),2)
        os.chdir(D); os.execv(argv[0],argv)
    except BaseException:
        os._exit(122)
os.close(ready_w); os.close(gate_r); stdout.close(); stderr.close()
assert os.read(ready_r,1)==b'R'; os.close(ready_r)
leader=proc(pid); assert leader['ppid']==os.getpid() and leader['pgid']==pid and leader['sid']==pid
record('started.json',{'owner':proc(os.getpid()),'leader':leader})
os.write(gate_w,b'G'); os.close(gate_w)
term=False; hard=False
while space['leader_state'](pid) is None:
    elapsed=time.monotonic()-start
    if elapsed>=30 and not term:
        current=proc(pid); assert current['start_ticks']==leader['start_ticks'] and current['pgid']==pid and current['sid']==pid
        os.killpg(pid,signal.SIGTERM); term=True
    if elapsed>=35 and not hard:
        current=proc(pid); assert current['start_ticks']==leader['start_ticks'] and current['pgid']==pid and current['sid']==pid
        os.killpg(pid,signal.SIGKILL); hard=True
    time.sleep(0.02)
try:
    members=space['census'](pid); extras=[s for s in members if s['pid']!=pid]
    anchors=[s for s in members if s['pid']==pid]
    closure=(len(anchors)==1 and anchors[0]['state']=='Z' and anchors[0]['start_ticks']==leader['start_ticks'] and not extras)
    census={'members':members,'closed_before_reap':closure,'error':None}
except BaseException as error:
    census={'members':None,'closed_before_reap':False,'error':repr(error)}
record('postterminal-census.json',census)
waited,status,usage=os.wait4(pid,0)
code=os.waitstatus_to_exitcode(status)
result={'pid':waited,'start_ticks':leader['start_ticks'],'pgid':leader['pgid'],'sid':leader['sid'],
        'exit_code':code,'elapsed_seconds':time.monotonic()-start,'user_seconds':usage.ru_utime,
        'system_seconds':usage.ru_stime,'max_rss_kib':usage.ru_maxrss,'timeout_term':term,'timeout_kill':hard,
        'postterminal_group_closed_before_reap':census['closed_before_reap'],
        'scope':'Pure synthetic fixture only; no SDK owner/compiler/native/release acceptance.'}
record('result.json',result)
print(json.dumps(result))
