#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing h990 owned_capture caller for ONE root-granted ordinary source archive.
No compiler, owner import, Docker, root or guest operation.
"""
from pathlib import Path
import datetime,hashlib,json,os,resource,signal,stat,time
M=Path(__file__).parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
EXPECTED_H='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
READY=M/'READY-COMPACT-ADMISSION-FULL-SOURCE-PUBLICATION.NOT-GRANTED.json'
READY_SHA='bf78c14f25af1dec712f0e7b98a968ddd551bdd295e3c492f37b1b6ed2017c06'
DESCRIPTOR=M/'EXACT-ORDINARY-SOURCE-ARCHIVE-COMMAND.NOT-GRANTED.json'
DESCRIPTOR_SHA='74ce43ec2ad36610ae30cea859d49ee2ab208c9a6de383f2ea0e48eda7f75366'
O=M/'actual-source-publication-capture-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def need(c,m):
 if not c:raise RuntimeError(m)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 begin=time.monotonic();start=utc()
 need(os.getuid()==os.geteuid()==1000,'ordinary nonroot identity')
 raw=H.read_bytes();need(hashlib.sha256(raw).hexdigest()==EXPECTED_H,'exact existing h990 capture helper')
 ns={'__name__':'existing_h990_capture_only','__file__':str(H)};exec(compile(raw,str(H),'exec'),ns)
 need(digest(READY)==READY_SHA and digest(DESCRIPTOR)==DESCRIPTOR_SHA,'exact root-granted READY/descriptor')
 ready=json.loads(READY.read_bytes());command=json.loads(DESCRIPTOR.read_bytes())
 need(command['argv'][-1]==ready['publisher']['path'] and ready['publisher']['sha256']=='7bf60472a9f94576cca7fd3506196762175fcc6917b4c391cf299d1a05ebc77b','exact root-granted materializer')
 for path in command['required_absent']:need(not os.path.lexists(path),'fresh absence '+path)
 source=Path(command['source_root_identity']['path']);meta=source.lstat();need(meta.st_dev==66306 and meta.st_ino==59524933 and meta.st_uid==meta.st_gid==1000 and stat.S_IMODE(meta.st_mode)==0o700,'exact actual copied source inode59524933')
 os.sched_setaffinity(0,{6})
 def limits():
  os.sched_setaffinity(0,{6})
  for typ,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_STACK,2<<20),(resource.RLIMIT_CORE,0)]:resource.setrlimit(typ,(value,value))
 limits();os.chdir(command['cwd'])
 tools=[]
 for original in ['/usr/bin/taskset','/usr/bin/python3']:
  resolved=Path(original).resolve(strict=True);row=ns['hashed'](resolved,32<<20);row['argv_path']=original;row['resolved_path']=str(resolved);tools.append(row)
 need(tools[1]['resolved_path']=='/usr/bin/python3.8','explicit observed existing interpreter')
 sourcepins=[]
 for row in command['frozen_inputs']:
  actual=ns['hashed'](Path(row['path']),64<<20);need(actual['sha256']==row['sha256'] and actual['size']==row['bytes'],'exact frozen ordinary input '+row['path']);sourcepins.append(actual)
 host=os.statvfs(M);scratch=os.statvfs('/home/holden/mckernel-work/scratch');hf=host.f_bavail*host.f_frsize;sf=scratch.f_bavail*scratch.f_frsize
 need(hf>=17393502520,'HOST16GiB plus complete worst-case publication/capture floor')
 need(sf>=14091616256,'existing greater scratch preservation floor')
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 need(mem>=2<<30,'available memory covers exact granted2GiB ordinary slot; root owns aggregate accounting')
 O.mkdir(mode=0o700)
 ns['write'](O/'GRANT.json',dict(scope=SCOPE,authority='Root explicit one-shot descriptor74ce43ec/publisher7bf60472/plan86a3ed16 source archive grant',CPU6_release='Root explicitly assigned CPU6 until terminal for this exact ordinary archive operation',operation='NONROOT_SOURCE_ARCHIVE_ONLY',CPU6=True,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,STACK_bytes=2<<20,core=0,no_compiler_or_root_or_Docker=True))
 ns['write'](O/'admission.json',dict(start_utc=start,host_free_bytes=hf,scratch_free_bytes=sf,mem_available_bytes=mem,root_global_jobs=7,root_global_memory_gib='22.2973',this_reserved_jobs=1,this_reserved_AS_bytes=2<<30,actual_global_usage_not_invented=True,frozen_source_commit='eb3ce544eb1f479a56933a5c7fa8300ab6dfe533',tools=tools,sourcepins=sourcepins,readonly_large_metadata_streaming_plan=ready['publication_plan']))
 ns['write'](O/'actual-command.json',command)
 snapshot=O/'source-snapshots';snapshot.mkdir(mode=0o700)
 inputs=[Path(__file__),H,READY,DESCRIPTOR]+[Path(r['path']) for r in command['frozen_inputs']]
 mapping=[]
 for i,p in enumerate(inputs):
  row=dict(ordinal=i,path=str(p),sha256=digest(p),bytes=p.stat().st_size)
  if row['bytes']>32<<20:row.update(retention='immutable existing file hash reference only; NOraw snapshot underF32')
  else:
   target=snapshot/(str(i).zfill(2)+'-'+p.name);target.write_bytes(p.read_bytes());row.update(snapshot=str(target))
  mapping.append(row)
 ns['write'](O/'source-snapshot-map.json',mapping)
 child=O/'00-current230-source-archive';child.mkdir(mode=0o700)
 for num in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(num,ns['stop'])
 record=ns['owned_capture'](command,child,90,limits)
 elapsed=time.monotonic()-begin;cpu=ns['cpu_used']()
 ok=record['returncode']==0 and record['direct_child_joined'] and record['group_absent'] and record['closed_streams'] and not record['timed_out'] and not record['error'] and not record['retirement_error'] and record['captures']['stderr']['size']==0 and cpu<=60
 result=dict(scope=SCOPE,status='PASS_ONE_GRANTED_CURRENT230_SOURCE_ARCHIVE' if ok else 'FAIL_STOPPED_PRESERVE_ALL',start_utc=start,end_utc=utc(),elapsed_seconds=elapsed,total_CPU_seconds=cpu,record=record,root_granted_ready_sha256=READY_SHA,root_granted_descriptor_sha256=DESCRIPTOR_SHA,source_archive_retention_only=True,builds=0,containers=0,native_apps=0)
 ns['write'](O/'WHOLE-JOIN.json',result)
 print(json.dumps(result,sort_keys=True));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
