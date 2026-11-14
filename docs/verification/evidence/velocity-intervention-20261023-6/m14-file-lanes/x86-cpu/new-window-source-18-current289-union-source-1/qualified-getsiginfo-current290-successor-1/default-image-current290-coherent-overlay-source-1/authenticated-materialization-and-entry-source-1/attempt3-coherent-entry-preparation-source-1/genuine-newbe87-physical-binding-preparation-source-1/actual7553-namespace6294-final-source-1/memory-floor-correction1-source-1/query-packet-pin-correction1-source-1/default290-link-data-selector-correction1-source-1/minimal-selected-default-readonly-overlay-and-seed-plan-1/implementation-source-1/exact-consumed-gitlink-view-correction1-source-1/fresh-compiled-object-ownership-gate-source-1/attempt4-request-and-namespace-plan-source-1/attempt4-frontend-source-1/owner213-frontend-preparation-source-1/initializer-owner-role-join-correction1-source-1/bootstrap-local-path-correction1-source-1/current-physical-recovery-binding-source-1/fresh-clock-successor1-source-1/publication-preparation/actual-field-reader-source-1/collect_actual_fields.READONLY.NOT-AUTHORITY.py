"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only actual-field collector. Output is evidence for independent review, never authority.
No filesystem writes, child processes, locks, signals, admission, or retries.
"""
import ast,hashlib,json,math,os,stat,sys,time
from pathlib import Path
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
COHORT={'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/current-physical-recovery-binding-source-1/fresh-clock-successor1-source-1/publication-preparation/EXPECTED-FRESH-COHORT-BEFORE-LIVE-CLOCK.SOURCE-ONLY.json', 'sha256': '8f9f344379fa11b78f6006502612d7e3e1cc656ab98825962ae7c6c56ad77265', 'bytes': 18879}
EXPECTED_KEYS={'cohort','preparation_grant','namespace_paths','stale_leases','heavy_profile'}
def need(ok,message):
 if not ok:raise RuntimeError('readonly actual fields: '+message)
def pairs(rows):
 out={}
 for key,value in rows:need(key not in out,'duplicate JSON key');out[key]=value
 return out
def decode(raw):return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda v:(_ for _ in ()).throw(RuntimeError('nonfinite JSON '+v)))
def read_regular(path,maximum=1<<20):
 path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=maximum,'bounded unique regular '+str(path));chunks=[];count=0
  while True:
   chunk=os.read(fd,min(65536,maximum+1-count))
   if not chunk:break
   chunks.append(chunk);count+=len(chunk);need(count<=maximum,'metadata byte limit')
  identity=lambda m:(m.st_dev,m.st_ino,m.st_mode,m.st_nlink,m.st_size,m.st_uid,m.st_gid,m.st_mtime_ns,m.st_ctime_ns)
  need(count==before.st_size and identity(before)==identity(os.fstat(fd))==identity(os.stat(path,follow_symlinks=False)),'stable regular bytes '+str(path));return b''.join(chunks)
 finally:os.close(fd)
def reference(path,raw=None):
 raw=read_regular(path) if raw is None else raw;return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def auth(row):
 need(isinstance(row,dict) and set(row)=={'path','sha256','bytes'},'closed exact reference');raw=read_regular(row['path']);need(reference(row['path'],raw)==row,'exact reference bytes '+row['path']);return raw
def document(row):return decode(auth(row))
def load_path(path):raw=read_regular(path);return decode(raw),reference(path,raw)
def captured(row,expected_path):
 need(row['path']==str(expected_path),'capture path');raw=read_regular(row['path']);need(row['sha256']==hashlib.sha256(raw).hexdigest() and row['size']==len(raw) and row['nlink']==1,'capture raw bytes');return raw

def canonical_function(caller):
 source=auth(caller);tree=ast.parse(source);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='canonical'];need(len(nodes)==1,'one actual caller canonical definition');ns={'json':json};exec(compile(ast.Module(body=nodes,type_ignores=[]),caller['path'],'exec'),ns);return ns['canonical']
def closed_child(row):
 need(row['returncode']==0 and row['direct_child_joined'] is True and row['group_absent'] is True and row['closed_streams'] is True and row.get('timed_out',False) is False and row.get('error') is None and row.get('retirement_error') is None,'positive joined closed child')
def load_bundle(expected,cohort):
 cfg=document(cohort['config']);base=Path(cohort['static_expected_P']);capture=Path(cohort['static_expected_capture_root']);static=document(cohort['ready']);prep=document(expected['preparation_grant']);document(prep['context']);auth(cfg['physical']);auth(cfg['postjoin']);auth(cfg['readonly_reuse_inputs']);ready,ready_ref=load_path(capture/'INDEPENDENT-EXECUTION-REVIEW-READY.json');payload=document(ready['payload']);closed=document(ready['closed_census']);receipt=document(closed['receipt']);context=document(payload['root_fill_context']);census=document(closed['stdout']);compact=document(payload['compact_census_request']);five=document(payload['actual_five_query']);initializer=document(cohort['namespace_initialization']);cleanup_review=document(prep['existing_cleanup_source_review']);joins={name:load_path(capture/(name+'.JOIN.json'))[0] for name in ['five','prepare','finish']}
 raw5=[auth(row) for row in payload['fresh_raw_five']];stderr=auth(closed['stderr']);need(stderr==b'','empty census stderr')
 return dict(cohort=cohort,cfg=cfg,static=static,prep=prep,ready=ready,ready_ref=ready_ref,payload=payload,closed=closed,receipt=receipt,context=context,census=census,compact=compact,five=five,initializer=initializer,cleanup_review=cleanup_review,joins=joins,raw5=raw5,census_stderr=stderr,canonical=canonical_function(cohort['caller']))

def check_recorded(expected,b):
 c=b['cohort'];cfg=b['cfg'];s=b['static'];pr=b['prep'];r=b['ready'];p=b['payload'];cl=b['closed'];cx=b['context'];ce=b['census'];f=b['five'];init=b['initializer'];base=Path(c['static_expected_P']);cap=Path(c['static_expected_capture_root'])
 need(set(expected)==EXPECTED_KEYS and len(expected['namespace_paths'])==10 and len(expected['stale_leases'])==7,'closed frozen expected shape')
 need(cfg['P']==str(base) and cfg['capture_root']==str(cap) and cap==base/'actual-entry-1','exact cohort output roots')
 need(r['payload']['path']==str(base/'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FINAL.NOT-RELEASED.json') and r['closed_census']['path']==str(cap/'ROOT-CENSUS-CLOSED.json') and p['root_fill_context']['path']==str(base/'ROOT-CURRENT290-ACTUAL-FETCH-AND-DEVFLOCK-CONTEXT.ACTUAL.json'),'actual metadata paths')
 need(r['caller']==c['caller'] and r['config']==c['config'] and cfg['fill']==c['fill'] and r['scope']==p['scope']==cl['scope']==SCOPE,'actual cohort and scope refs')
 canon=hashlib.sha256(b['canonical'](p)).hexdigest();need(canon==r['canonical_payload_sha256'],'actual caller canonical payload SHA')
 need(pr['census_observer']==s['corrected_census_observer'],'exact static census observer role')
 need(pr['author']=='/root' and pr['decision']=='GRANT_CURRENT290_READONLY_PREPARATION' and pr['caller_sha256']==c['caller']['sha256'] and pr['config_sha256']==c['config']['sha256'] and pr['existing_cleanup_source']==c['cleanup'] and pr['namespace_initialization']==c['namespace_initialization'],'exact preparation grant source roles')
 review=b['cleanup_review'];need(review['decision']=='PASS_SOURCE_EXISTING_SAME_OFD_IMAGE_CLEANUP' and review['implementation_ownership'] is False and review['reviewer'] not in ['/root','',None] and review['source']==pr['existing_cleanup_source'] and review['same_OFD_transport']=='STDIN_FD0_SUDO_A','independent same OFD cleanup source review')
 need(set(cfg['pins'])=={'driver','manifest','owner','provenance','request'} and p['source']==dict(cfg['pins'],host_control_owner=s['host_control_owner']) and cfg['pins']['owner']==c['owner'] and cfg['pins']['request']==c['request'],'exact six actual source roles')
 need(p['argv']==cfg['commands']['owner_entry_unchanged']['argv'] and p['operation_scope']==cfg['operation_scope']==r['operation_scope']=='FROZEN_CURRENT290_IMAGE_READONLY_CONFIGURATION_REUSE_NINE_OBJECT_SEED_NOT_FRESH_CONFIGURE_OR_NATIVE','unchanged owner argv and operation scope')
 for pk,ck,ek in [('current_physical','physical','physical'),('current_live_postjoin','postjoin','physical_postjoin'),('source_namespace_initialization','namespace_initialization','namespace_initialization'),('readonly_reuse_inputs','readonly_reuse_inputs','readonly_seed')]:need(p[pk]==cfg[ck]==c[ek],'exact physical/namespace/seed role '+pk)
 need(p['heavy_profile']==expected['heavy_profile'],'exact heavy profile')
 for key,value in dict(execution_count=1,ordinary_entry_required=True,independent_review=None,fresh_full_configure=False,native_apps=0,wholefile_retirement=False,native_fork_owned_transaction=False,native_executor_pair_acceptance='OPEN',outer_CPU_kill=False,outer_timeout=None).items():need(type(p[key]) is type(value) and p[key]==value,'payload scope '+key)
 need(p['schema']=='mckernel.root.exact-current81-normal-image-release.v1' and p['status']=='ROOT_EXACT_CURRENT290_IMAGE_ONLY_PAYLOAD_AWAITING_INDEPENDENT_EXECUTION_REVIEW','actual payload schema/status')
 closed_child(b['receipt'])
 for joined in b['joins'].values():closed_child(joined)
 need(cl['stdout']['path']==str(cap/'census-observer-capture-1/stdout') and cl['stderr']['path']==str(cap/'census-observer-capture-1/stderr') and cl['receipt']['path']==str(cap/'census-observer-capture-1/receipt.json') and p['actual_five_query']['path']==str(base/'actual-readonly-admission-capture-1/ACTUAL-READONLY-RESULT.json'),'exact dynamic census/five metadata paths')
 need(cl['author']=='/root' and cl['source']==cfg['commands']['compact_census']['source'] and cl['observer_source']==pr['census_observer'],'closed actual census source roles')
 for channel in ['stdout','stderr']:
  row=b['receipt']['captures'][channel];need(row['path']==cl[channel]['path'] and row['sha256']==cl[channel]['sha256'] and row['size']==cl[channel]['bytes'],'census receipt actual stream '+channel)
 need(p['actual_compact_census']==cl['stdout'] and cl['stderr']['bytes']==0 and b['census_stderr']==b'','actual census stdout and empty stderr')
 request=p['compact_census_request'];need(request['path']==str(base/'COMPACT-C252-CENSUS-REQUEST.ACTUAL-FIVE-BOUND.NOT-GRANTED.json') and ce['request']['path']==request['path'] and ce['request']['sha256']==request['sha256'] and ce['request']['normalized_sha256']==hashlib.sha256(json.dumps(b['compact'],sort_keys=True).encode()).hexdigest(),'actual census request raw/normalized binding')
 argv=list(cfg['commands']['compact_census']['argv']);argv[-1]=request['sha256'];need(cl['argv']==argv,'exact actual compact census argv')
 need(ce['schema']=='mckernel.heavy-recovery-census.v1' and ce['status']=='PASS_READ_ONLY' and ce['execution_released'] is False and ce['processes']==ce['containers']==[] and ce['leases']==expected['stale_leases'],'exact read-only census no active workloads and retained leases')
 need(len(f['results'])==len(b['raw5'])==len(p['fresh_raw_five'])==5 and f['admission_or_build_acceptance'] is None,'five finite readonly results')
 for i,result in enumerate(f['results']):
  closed_child(result)
  for channel in ['stdout','stderr']:
   row=result['captures'][channel];need(row['path']==str(base/'actual-readonly-admission-capture-1'/str(i+1)/channel),'exact five stream path');raw=read_regular(row['path']);need(hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['size'],'five stream exact bytes')
   if channel=='stdout':need(p['fresh_raw_five'][i]==reference(row['path'],raw) and raw==b['raw5'][i],'actual raw-five bytes')
   else:need(raw==b'','five stderr empty')
 need(f['finished_at_epoch']==r['five_end_epoch']==p['observations_finished_at_epoch'] and f['started_at_epoch']==p['observations_started_at_epoch'] and r['five_end_epoch']<=cl['started_at_epoch']<=r['census_end_epoch']==cl['finished_at_epoch']<=p['census_completed_at_fill_epoch'],'recorded fresh observation order')
 need(cx['author']=='/root' and cx['actual_devflock_holder']==r['holder'],'held context actual holder')
 for continuity in [p['continuity'],cx['continuity']]:need(continuity['no_heavy_since_latest_physical'] is True and continuity['latest_physical']==c['physical'] and continuity['latest_postjoin']==c['physical_postjoin'] and continuity['permanent_mutex']==dict(campaign_holds_dev_flock=True,device=27,inode=4),'current physical continuity')
 need(cx['actual_current_physical']==c['physical'] and cx['actual_current_live_postjoin']==c['physical_postjoin'],'held context physical pair')
 h=r['holder'];need(h['path']=='/run/lock/mckernel-development.lock' and h['fd']==h['original_holder_fd']==3 and h['transported_fd']==0 and h['transport']=='STDIN_FD0_SUDO_A' and h['identity']==cfg['permanent_mutex'],'exact holder same OFD transport')
 rows=p['namespace']['rows'];need([row['path'] for row in rows]==expected['namespace_paths'] and len(init['identities'])==3,'exact frozen ten namespace paths')
 for actual,original in zip(rows[:3],init['identities']):
  need(actual['exists'] is True and actual['path']==original['path'] and actual['dev']==original['device'] and actual['inode']==original['inode'] and actual['mode']==original['mode']==0o700 and actual['uid']==actual['gid']==original['uid']==original['gid']==1000 and sorted(actual['entries'])==sorted(original['entries']),'three recorded initialized namespace identities')
 need(all(row['exists'] is False for row in rows[3:]) and decode(b['raw5'][4])['rows']==rows,'recorded remaining paths absent and actual raw namespace bytes')
 ag=p['aggregate'];disk=p['disk'];resources=ce['resources'];need(ag['actual_no_other_heavy'] is True and ag['campaign_ceiling_gib']=='22.0485' and ag['minimum']==25501368320 and ag['MemAvailable']>=ag['minimum'] and resources['memory_available']>=ag['minimum'],'aggregate reservation and recorded memory floors')
 need({row['CPU']:row.get('active') for row in ag['slots'] if row['CPU'] in ['0','6']}=={'0':False,'6':False} and set([2,3,4,5])<=set(resources['cpus']),'ordinary slots inactive and observed heavy CPUs')
 need(disk['HOST_available']>=disk['HOST_required'] and resources['host_free']>=disk['HOST_required'] and disk['scratch_available']>=disk['scratch_required'] and resources['scratch_free']>=disk['scratch_required'],'recorded full disk floors')
 need(cfg['maximum_observation_age']==120,'exact unchanged observation TTL');expires=min(r['five_end_epoch']+120,cfg['deadline_epoch']-30)
 return dict(canonical_sha256=canon,expires_at=expires,holder=h)

def read_proc(path,maximum=4<<20):
 fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC)
 try:
  chunks=[];count=0
  while True:
   raw=os.read(fd,65536)
   if not raw:break
   count+=len(raw);need(count<=maximum,'complete proc byte limit');chunks.append(raw)
  return b''.join(chunks)
 finally:os.close(fd)
def check_live(b,recorded):
 r=b['ready'];h=r['holder'];p=b['payload'];need(time.time()<recorded['expires_at'],'expired before live checks');need(os.environ.get('MCKERNEL_OS_MEMORY_GIB')=='22.0485','inherited aggregate planning ceiling')
 pid=h['pid'];raw=read_proc('/proc/'+str(pid)+'/stat').decode();parts=raw[raw.rfind(')')+2:].split();need(parts[0] not in ['Z','X'] and parts[19]==h['starttime'],'current caller exact birth nonzombie')
 suffix=[b['cohort']['caller']['path'],b['expected_preparation_grant']['path'],b['cohort']['config']['path'],b['cohort']['config']['sha256']];cmd=read_proc('/proc/'+str(pid)+'/cmdline').rstrip(b'\0').split(b'\0');need([v.decode() for v in cmd[-4:]]==suffix,'current exact caller argv suffix')
 fdmeta=os.stat('/proc/'+str(pid)+'/fd/3');need((fdmeta.st_dev,fdmeta.st_ino)==(27,4),'actual held FD3 node')
 lock_raw=read_proc('/proc/locks').decode();matching=[]
 for line in lock_raw.splitlines():
  tokens=line.split();index=1
  if len(tokens)>1 and tokens[1]=='->':index=2
  if len(tokens)>=index+7:
   try:major,minor,inode=tokens[index+4].split(':');node=(os.makedev(int(major,16),int(minor,16)),int(inode))
   except (ValueError,IndexError):continue
   if node==(27,4):matching.append(tokens[index:index+7])
 need(matching==[['FLOCK','ADVISORY','WRITE',str(pid),'00:1b:4','0','EOF']],'complete proc locks sole exact caller27:4 holder')
 boot=read_proc('/proc/sys/kernel/random/boot_id',1024).decode().strip();need(boot==h['boot_id']==b['census']['boot_id'],'current same boot')
 for original in b['initializer']['identities']:
  meta=os.lstat(original['path']);need(stat.S_ISDIR(meta.st_mode) and (meta.st_dev,meta.st_ino,stat.S_IMODE(meta.st_mode),meta.st_uid,meta.st_gid)==(original['device'],original['inode'],0o700,1000,1000) and sorted(os.listdir(original['path']))==sorted(original['entries']),'current exact initialized namespace')
 need(all(not os.path.lexists(row['path']) for row in p['namespace']['rows'][3:]),'current seven runtime paths absent')
 available=[int(line.split()[1])*1024 for line in read_proc('/proc/meminfo').decode().splitlines() if line.startswith('MemAvailable:')];need(len(available)==1 and available[0]>=p['aggregate']['minimum'],'fresh memory floor')
 for path,key in [('/home/holden','HOST_required'),('/home/holden/mckernel-work/scratch','scratch_required')]:
  fs=os.statvfs(path);need(fs.f_bavail*fs.f_frsize>=p['disk'][key],'fresh statvfs floor '+key)
 need(p['census_completed_at_fill_epoch']<=time.time(),'recorded checks finished before now');return dict(complete_proc_lock_rows=matching,live_memory_available=available[0])

def collect(expected_path,expected_sha):
 expected_raw=read_regular(expected_path);need(hashlib.sha256(expected_raw).hexdigest()==expected_sha,'frozen expected SHA');expected=decode(expected_raw);need(set(expected)==EXPECTED_KEYS and expected['cohort']==COHORT,'exact closed preclock expected cohort');cohort=document(expected['cohort']);b=load_bundle(expected,cohort);b['expected_preparation_grant']=expected['preparation_grant'];recorded=check_recorded(expected,b);live=check_live(b,recorded)
 need(load_path(b['ready_ref']['path'])[1]==b['ready_ref'] and reference(b['ready']['payload']['path'])==b['ready']['payload'],'READY and raw payload unchanged after checks');now=time.time();need(now<recorded['expires_at'],'expired after all checks')
 return dict(schema='mckernel.readonly-actual-fields.v1',scope=SCOPE,status='READONLY_ACTUAL_FIELDS_PASS_NOT_AUTHORITY',expected_sha256=expected_sha,ready=b['ready_ref'],raw_payload=b['ready']['payload'],canonical_payload_sha256=recorded['canonical_sha256'],closed_census=b['ready']['closed_census'],caller=dict(pid=recorded['holder']['pid'],starttime=recorded['holder']['starttime'],fd=3,node=[27,4]),checked_at=now,expires_at=recorded['expires_at'],remaining_seconds=recorded['expires_at']-now,caller_sha256=cohort['caller']['sha256'],config_sha256=cohort['config']['sha256'],fill_sha256=cohort['fill']['sha256'],operation_scope=b['payload']['operation_scope'],existing_cleanup_source=cohort['cleanup'],reviewer_decision_required=True,new_heavy_admission=False,native_or_retirement_credit=False,live=live)
if __name__=='__main__':
 try:
  need(len(sys.argv)==3,'EXPECTED_JSON path and SHA required');print(json.dumps(collect(sys.argv[1],sys.argv[2]),sort_keys=True,allow_nan=False))
 except Exception as exc:
  print(json.dumps(dict(schema='mckernel.readonly-actual-fields.v1',scope=SCOPE,status='READONLY_ACTUAL_FIELDS_FAIL_NOT_AUTHORITY',error=str(exc),new_heavy_admission=False),sort_keys=True));sys.exit(1)
