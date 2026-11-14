#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing h990 owned_capture caller for ONE root-granted ordinary source copy.
No compiler, owner import, Docker, root or guest operation.
"""
from pathlib import Path
import datetime,hashlib,json,math,os,resource,signal,stat,time
M=Path(__file__).parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
EXPECTED_H='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
READY=M/'READY-CURRENT290-MATERIALIZATION-SOURCE-TUPLE.NOT-GRANTED.json'
READY_SHA='91d1b215dd8cadd2cdbb7b515282fd85153ed8b8557fe3e80cadbe7f0fbb48ec'
DESCRIPTOR=M/'EXACT-ORDINARY-MATERIALIZATION-COMMAND.NOT-GRANTED.json'
DESCRIPTOR_SHA='7abb665e8de10591572893f0387571c33745772e4b5c26e09c7b27650581c250'
O=M/'actual-source-materialization-capture-1'
SOURCE_FD_AUTHORITY_SHA='784264413f2adc63fba7cb587f06eef4149f0da591e91965e8e60b38fd1e081c'
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
 raise RuntimeError('UNRELEASED SCRIPTS OWNER: authority and custody are not bound')
 begin=time.monotonic();start=utc()
 need(os.getuid()==os.geteuid()==1000,'ordinary nonroot identity')
 raw=H.read_bytes();need(hashlib.sha256(raw).hexdigest()==EXPECTED_H,'exact existing h990 capture helper')
 ns={'__name__':'existing_h990_capture_only','__file__':str(H)};exec(compile(raw,str(H),'exec'),ns)
 for num in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(num,ns['stop'])
 remaining_wall=90-(time.monotonic()-begin);need(remaining_wall>0,'shared wall budget before input preflight');signal.setitimer(signal.ITIMER_REAL,remaining_wall)
 need(digest(READY)==READY_SHA and digest(DESCRIPTOR)==DESCRIPTOR_SHA,'exact root-granted READY/descriptor')
 ready=json.loads(READY.read_bytes());command=json.loads(DESCRIPTOR.read_bytes())
 need(command['argv'][-1]==ready['materializer']['path'] and ready['materializer']['sha256']=='87010d3c91e3bd6dbbfcf774c4bbfb3e384bb71e174bda4170a96fa53aa23acb','exact root-granted materializer')
 grant_path=M/'ROOT-GRANT.json'
 grant_raw=ns['hashed'](grant_path,1<<20);grant=json.loads(grant_path.read_bytes())
 need(grant['author']=='/root' and grant['decision']=='GRANT_ONE_CURRENT290_SOURCE_MATERIALIZATION' and grant['ready_sha256']==READY_SHA and grant['descriptor_sha256']==DESCRIPTOR_SHA and grant['wrapper_sha256']==digest(Path(__file__)),'fresh exact root one-shot source-copy grant')
 need(grant['scope']==SCOPE and grant['CPU']==6 and grant['ordinary_jobs']==1 and grant['SDK_owned_paths_untouched'] is True,'finite disjoint HOST-only grant')
 need(grant['aggregate_jobs']<=7 and grant['aggregate_jobs']>=1,'actual aggregate jobs within7')
 from decimal import Decimal
 cap=int(min(Decimal('22.2973'),Decimal(os.environ['MCKERNEL_OS_MEMORY_GIB']))*(2**30))
 need(grant['aggregate_reserved_memory_bytes']<=cap and grant['aggregate_reserved_memory_bytes']>=2<<30,'actual aggregate within tighter observed runtime/outer ceiling')
 fd_authority_path=M/'EXACT-FINITE-SOURCE-FD-AUTHORITY.NOT-GRANTED.json'
 need(digest(fd_authority_path)==SOURCE_FD_AUTHORITY_SHA,'exact finite fixed-FD authority')
 fd_authority=json.loads(fd_authority_path.read_bytes());source_preflight=[]
 for row in fd_authority['rows']:
  actual=ns['hashed'](Path(row['path']),row['maximum'])
  need(actual['sha256']==row['sha256'] and actual['size']==row['bytes'] and {key:actual[key] for key in row['identity']}==row['identity'],'exact finite source FD bytes/identity '+row['path']);source_preflight.append(actual)
 for path in command['required_absent_paths']:need(not os.path.lexists(path),'fresh absence '+path)
 os.sched_setaffinity(0,{6})
 remaining_cpu=60-ns['cpu_used']();need(remaining_cpu>0,'shared CPU budget before source preflight')
 def limits():
  os.sched_setaffinity(0,{6})
  for typ,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,max(1,min(60,int(math.ceil(remaining_cpu))))),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_STACK,2<<20),(resource.RLIMIT_CORE,0)]:resource.setrlimit(typ,(value,value))
 limits();os.chdir(command['cwd'])
 tools=[]
 for original in ['/usr/bin/taskset','/usr/bin/python3']:
  resolved=Path(original).resolve(strict=True);row=ns['hashed'](resolved,32<<20);row['argv_path']=original;row['resolved_path']=str(resolved);tools.append(row)
 need(tools[1]['resolved_path']=='/usr/bin/python3.8','explicit observed existing interpreter')
 sourcepins=[]
 for row in command['inputs']:
  actual=ns['hashed'](Path(row['path']),64<<20);need(actual['sha256']==row['sha256'] and actual['size']==row['bytes'],'exact frozen ordinary input '+row['path']);sourcepins.append(actual)
 host=os.statvfs(M);scratch=os.statvfs('/home/holden/mckernel-work/scratch');hf=host.f_bavail*host.f_frsize;sf=scratch.f_bavail*scratch.f_frsize
 need(hf>=max(16*2**30,50248630272)+105804031+(16<<20),'HOST16GiB plus full source copy and capture floor')
 need(sf>=14091616256,'existing greater scratch preservation floor')
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 need(mem>=25501368320,'stronger reviewed aggregate admission minimum; SDK ownership/resources preserved')
 O.mkdir(mode=0o700)
 ns['write'](O/'GRANT.json',dict(scope=SCOPE,actual_root_grant=grant_raw,actual_root_grant_payload=grant,operation='NONROOT_SOURCE_COPY_ONLY',CPU6=True,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,STACK_bytes=2<<20,core=0,no_compiler_or_root_or_Docker=True))
 ns['write'](O/'SOURCE-FD-PREFLIGHT.json',dict(authority_sha256=SOURCE_FD_AUTHORITY_SHA,rows=source_preflight))
 ns['write'](O/'admission.json',dict(start_utc=start,host_free_bytes=hf,scratch_free_bytes=sf,mem_available_bytes=mem,root_global_jobs=7,root_global_memory_gib=os.environ['MCKERNEL_OS_MEMORY_GIB'],this_reserved_jobs=1,this_reserved_AS_bytes=2<<30,actual_global_usage_not_invented=True,frozen_source_commit=ready['candidate_sha'],tools=tools,sourcepins=sourcepins,readonly_large_manifest_hash_reference=ready['source_manifest']))
 ns['write'](O/'actual-command.json',command)
 snapshot=O/'source-snapshots';snapshot.mkdir(mode=0o700)
 inputs=[Path(__file__),H,READY,DESCRIPTOR]+[Path(r['path']) for r in command['inputs']]
 mapping=[]
 for i,p in enumerate(inputs):
  row=dict(ordinal=i,path=str(p),sha256=digest(p),bytes=p.stat().st_size)
  if row['bytes']>32<<20:row.update(retention='immutable existing file hash reference only; NOraw snapshot underF32')
  else:
   target=snapshot/(str(i).zfill(2)+'-'+p.name);target.write_bytes(p.read_bytes());row.update(snapshot=str(target))
  mapping.append(row)
 ns['write'](O/'source-snapshot-map.json',mapping)
 child=O/'00-current290-source-copy';child.mkdir(mode=0o700)
 for num in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(num,ns['stop'])
 remaining_wall=90-(time.monotonic()-begin);remaining_cpu=60-ns['cpu_used']()
 need(remaining_wall>0 and remaining_cpu>0,'shared wall/CPU budget exhausted before dispatch')
 ns['write'](O/'SHARED-BUDGET-BEFORE-DISPATCH.json',dict(shared_wall_seconds=90,shared_CPU_seconds=60,preflight_elapsed_seconds=time.monotonic()-begin,remaining_wall_seconds=remaining_wall,remaining_CPU_seconds=remaining_cpu,retirement_seconds=6))
 record=ns['owned_capture'](command,child,remaining_wall,limits)
 for row in source_preflight:
  st=Path(row['path']).lstat()
  for key,field in [('device','st_dev'),('inode','st_ino'),('uid','st_uid'),('gid','st_gid'),('nlink','st_nlink'),('size','st_size'),('mtime_ns','st_mtime_ns'),('ctime_ns','st_ctime_ns')]:need(row[key]==getattr(st,field),'unchanged fixed source after join '+row['path'])
 elapsed=time.monotonic()-begin;cpu=ns['cpu_used']()
 ok=record['returncode']==0 and record['direct_child_joined'] and record['group_absent'] and record['closed_streams'] and not record['timed_out'] and not record['error'] and not record['retirement_error'] and record['captures']['stderr']['size']==0 and cpu<=60 and elapsed<=90
 result=dict(scope=SCOPE,status='PASS_ONE_GRANTED_CURRENT290_SOURCE_MATERIALIZATION' if ok else 'FAIL_STOPPED_PRESERVE_ALL',start_utc=start,end_utc=utc(),elapsed_seconds=elapsed,total_CPU_seconds=cpu,record=record,root_granted_ready_sha256=READY_SHA,root_granted_descriptor_sha256=DESCRIPTOR_SHA,source_materialization_only=True,builds=0,containers=0,native_apps=0)
 ns['write'](O/'WHOLE-JOIN.json',result)
 print(json.dumps(result,sort_keys=True));return 0 if ok else 1
# Private source-only binding helper; no live process or filesystem action.
# The caller-provided bytes are NOT authenticated by this comparison. They
# must be supplied by a separately authenticated owner/custody channel.
SCRIPT_UNION_SHA='48b2c25266784641b28100c08c7c7baa4559d0aaffe670223ee71936f3deaffa'
SCRIPT_BODY_SHA='c3115c13a29dde74f6d316b64d26a6266c5a5cfeed877ef19de088844e09ba37'
SCRIPT_VERIFIER_SHA='34bd9802c507b3408b685c6233f0a2f711edbdf7a6f31c5dcd3eaba70128ba8f'
SCRIPT_ATTEMPT=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002')
SCRIPT_MANIFEST=SCRIPT_ATTEMPT/'m14-scripts-overlay-proposal-1/SCRIPTS-OVERLAY.NOT-RELEASED.json'
SCRIPT_BODY=SCRIPT_ATTEMPT/'m14-scripts-materializer-parent-expert-1/materializer.py'
SCRIPT_VERIFIER=SCRIPT_ATTEMPT/'m14-scripts-materializer-parent-expert-1/verify_scripts_fd.py'
def validate_frozen_scripts_binding(request,manifest_bytes,body_bytes,verifier_bytes):
 need(type(request) is dict and set(request)=={'manifest_path','body_path','verifier_path','source_root','output_root','source_identity','output_identity','release'},'exact binding schema')
 for field,path in [('manifest_path',SCRIPT_MANIFEST),('body_path',SCRIPT_BODY),('verifier_path',SCRIPT_VERIFIER)]:need(request[field]==str(path),'bound path: '+field)
 for data,expected,label in [(manifest_bytes,SCRIPT_UNION_SHA,'manifest'),(body_bytes,SCRIPT_BODY_SHA,'materializer'),(verifier_bytes,SCRIPT_VERIFIER_SHA,'verifier')]:need(type(data) is bytes and hashlib.sha256(data).hexdigest()==expected,'bound bytes: '+label)
 def unique(pairs):
  d={}
  for k,v in pairs:
   need(k not in d,'duplicate JSON key: '+k);d[k]=v
  return d
 doc=json.loads(manifest_bytes,object_pairs_hook=unique)
 need(doc.get('status')=='SOURCE_ONLY_NOT_MATERIALIZED_NOT_RELEASED' and doc.get('authority') is None,'manifest scope')
 need(request['source_root']==doc['base_scripts_candidate'],'source root binding')
 out=request['output_root'];src=request['source_root']
 for name,value in [('source',src),('output',out)]:need(type(value) is str and os.path.isabs(value) and os.path.normpath(value)==value and value!='/','normalized '+name)
 need(not(out==src or out.startswith(src+'/') or src.startswith(out+'/')),'source/output lexical separation')
 need(request['source_identity'] is None and request['output_identity'] is None and request['release'] is None,'live state must remain unbound')
 base=doc['base_members'];adds=doc['additions'];need(type(base) is list and len(base)==1704 and type(adds) is list and len(adds)==6,'exact union extent')
 names=[x['path'] for x in base+adds];need(len(set(names))==len(names),'duplicate union name')
 expected={'derive_f06_origin.py','derive_f06_origin_e6a_guarded.py','f06_origin_command_profile.json','f06_origin_command_profile_e6a_guarded.json','verify_m14_configure_probe.py','verify_m14_elf.py'}
 need(set(x['path'] for x in adds)==expected and all(x['type']=='file' and os.path.isabs(x['source_candidate']) for x in adds),'exact addition sources')
 return {'status':'SOURCE_BINDING_ONLY_LIVE_ENTRY_BLOCKED','source_root':src,'output_candidate':out,'manifest_sha256':SCRIPT_UNION_SHA,'materializer_sha256':SCRIPT_BODY_SHA,'verifier_sha256':SCRIPT_VERIFIER_SHA,'source_identity':None,'output_identity':None,'authority':None,'release':None,'started':False}

# New scripts-specific source branch; ALL physical entry remains blocked.
# This is not the old CURRENT290 command or one-shot grant.
SCRIPTS_CHILD=SCRIPT_ATTEMPT/'m14-scripts-child-receipt-successor-1/child.py'
SCRIPTS_CHILD_SHA='3fb379c312d6bdcb14a829f108157040e1e12a08090aa9211783b0f094cc6938'
SCRIPTS_CAPTURE_PATH=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
SCRIPTS_CAPTURE_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e6bde8'
def _require_scripts_authority():
 raise RuntimeError('UNRELEASED SCRIPTS BRANCH: no authenticated live owner, packet or custody authority')
def _future_scripts_limits():
 raise RuntimeError('UNRELEASED SCRIPTS BRANCH: no reviewed child limits')
def _load_scripts_capture():
 data=SCRIPTS_CAPTURE_PATH.read_bytes()
 need(hashlib.sha256(data).hexdigest()==SCRIPTS_CAPTURE_SHA,'exact historical capture helper bytes')
 ns={'__name__':'scripts_owned_capture_bound_source','__file__':str(SCRIPTS_CAPTURE_PATH)}
 exec(compile(data,str(SCRIPTS_CAPTURE_PATH),'exec'),ns)
 need(callable(ns.get('owned_capture')),'bound capture interface')
 return ns['owned_capture']
def scripts_union_branch(request,manifest_bytes,materializer_bytes,verifier_bytes,child_bytes,capture_dir,wall_seconds):
 # First gate stays unconditional. Live source/target identity, descriptor,
 # stdout/receipt directories, custody and execution release are not supplied.
 _require_scripts_authority()
 binding=validate_frozen_scripts_binding(request,manifest_bytes,materializer_bytes,verifier_bytes)
 need(hashlib.sha256(child_bytes).hexdigest()==SCRIPTS_CHILD_SHA,'exact scripts child bytes')
 need(type(capture_dir) is str and os.path.isabs(capture_dir) and os.path.normpath(capture_dir)==capture_dir,'normalized capture path')
 need(type(wall_seconds) in (int,float) and 0<wall_seconds<=90,'bounded wall argument')
 # The current exact child CLI itself unconditionally refuses. There is no
 # authenticated live descriptor, receipt-FD passing or output custody yet.
 command={'argv':['/usr/bin/python3','-I','-B',str(SCRIPTS_CHILD)]}
 capture=_load_scripts_capture()
 try:
  record=capture(command,Path(capture_dir),wall_seconds,_future_scripts_limits)
 except BaseException as e:
  return {'status':'UNKNOWN_RETAIN_OUTPUT','reason':'capture exception: '+type(e).__name__,'binding':binding,'terminal_proven':False,'receipt_accepted':False,'release':None}
 # The historical capture records child PID/start, direct wait/join and group
 # census. No receipt contents, including success-shaped bytes, are accepted:
 # no independently reviewed receipt durability/custody oracle exists here.
 return {'status':'UNKNOWN_RETAIN_OUTPUT','reason':'scripts custody, durability and authenticated terminal evidence unbound','binding':binding,'capture_record':record,'receipt_accepted':False,'release':None}

if __name__=='__main__':
 try:raise SystemExit(main())
 finally:signal.setitimer(signal.ITIMER_REAL,0)
