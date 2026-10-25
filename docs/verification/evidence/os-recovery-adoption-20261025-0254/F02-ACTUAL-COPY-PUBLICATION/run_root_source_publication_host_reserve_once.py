#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact source/archive publication, existing h990 capture and limits.
"""
import ast,hashlib,json,os,resource,signal,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
READY=ROOT/'READY.ACTUAL-PURE-PUBLISHER-SOURCES.NOT-PUBLISHED.json'
READY_SHA='7275d6ba38b745d1a8d7bac075898b4b89a7394c54a43515f9c0618e28434955'
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
CAPTURE=ROOT/'actual-root-source-publication-1'
def main():
 raw=READY.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=READY_SHA:raise RuntimeError('READY changed')
 p=json.loads(raw);source=Path(p['publisher_source']['path'])
 if hashlib.sha256(source.read_bytes()).hexdigest()!=p['publisher_source']['sha256']:raise RuntimeError('copier changed')
 if CAPTURE.exists():raise RuntimeError('attempt retained; no replay')
 raw=HELPER.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=HELPER_SHA:raise RuntimeError('h990 changed')
 functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
 assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
 ns={'__file__':str(HELPER)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HELPER),'exec'),ns)
 if os.getuid()!=1000 or os.geteuid()!=1000 or 0 not in os.sched_getaffinity(0):raise RuntimeError('ordinary CPU0 required')
 os.sched_setaffinity(0,{0})
 for key,value in ((resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)):resource.setrlimit(key,(value,value))
 host=os.statvfs('/home/holden'); scratch=os.statvfs('/home/holden/mckernel-work/scratch')
 if host.f_bavail*host.f_frsize<34234793984 or scratch.f_bavail*scratch.f_frsize<13631488000:raise RuntimeError('publication HOST/scratch reserved capacity floor')
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 if mem<6<<30:raise RuntimeError('ordinary memory floor')
 CAPTURE.mkdir(mode=0o700)
 command={'name':'exact-F02-source-and-request-gzip-publication','purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Publish exact28-source archive and compressed request; no compiler/image/guest.', 'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(source)]}
 ns['write'](CAPTURE/'COMMAND.json',command)
 for number in ns['STOP_SIGNALS']:signal.signal(number,ns['stop'])
 signal.setitimer(signal.ITIMER_REAL,96)
 try:
  result=ns['owned_capture'](command,CAPTURE,90,lambda:None)
  ns['write'](CAPTURE/'WHOLE-JOIN.json',result)
 finally:signal.setitimer(signal.ITIMER_REAL,0)
 print(json.dumps(result))
 if result['returncode']!=0 or not result['direct_child_joined'] or not result['group_absent'] or not result['closed_streams'] or result['error'] or result['retirement_error'] or result['timed_out']:raise SystemExit(1)
if __name__=='__main__':main()
