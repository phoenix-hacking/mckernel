"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Closed data/receipt contract for one existing daemon mock batch. No operations on import.
"""
from pathlib import Path
import hashlib,json,os,re,stat
HERE=Path(__file__).resolve().parent
PREPARATION=HERE/'PREPARATION.SOURCE-ONLY.json'
PREPARATION_SHA='3883db54d0ca1767c3f0379b37fcae945ae79c5619b1c46aa50629d07a703f37'
OUTPUT_PARENT=HERE/'workspace';MIRROR=HERE/'input-mirror';DRIVER=HERE/'repro_driver.py'
OWNER=HERE/'repro_owner.py';CUTOFFS=[1793100290.0,882395.5689528405,897734.6960034363]
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'

def need(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
def pairs(rows):
 d={}
 for k,v in rows:
  need(k not in d,'duplicate JSON key');d[k]=v
 return d

def json_bytes(raw):return json.loads(raw,object_pairs_hook=pairs)
need(sha(PREPARATION.read_bytes())==PREPARATION_SHA,'frozen mock preparation differs')
PREP=json_bytes(PREPARATION.read_bytes());CANDIDATE=sha(canonical(PREP['source_files']))

def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=sha(raw))
def node(path):
 p=Path(path);s=p.lstat();return dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
def regular(path):
 p=Path(path);s=p.lstat();need(not p.is_symlink() and stat.S_ISREG(s.st_mode) and s.st_nlink==1,'regular single-link input required: '+str(p));return s

def source_at(root,row):
 path=Path(root)/row['relative'];s=regular(path);raw=path.read_bytes()
 need(len(raw)==row['source']['bytes'] and sha(raw)==row['source']['sha256'] and stat.S_IMODE(s.st_mode)==row['mode'],'source bytes/mode differ: '+row['relative'])
 need(s.st_uid==s.st_gid==1000,'source UID/GID differs');return path

def verify_mirror(root):
 root=Path(root);need(root.is_absolute() and root.resolve(strict=True)==root and not root.is_symlink(),'canonical mirror root')
 identity=node(root);need(root.is_dir() and identity['uid']==identity['gid']==1000 and identity['mode']==0o700,'private source mirror root')
 expected={row['relative'] for row in PREP['source_files']};files=set()
 output=root/PREP['fixture_output_relative'];need(output.is_dir() and not output.is_symlink() and not list(output.iterdir()),'precreated empty source-side output target')
 for path in root.rglob('*'):
  need(not path.is_symlink(),'source mirror symlink')
  if path.is_file():files.add(str(path.relative_to(root)))
  else:
   s=path.lstat();need(path.is_dir() and s.st_uid==s.st_gid==1000 and stat.S_IMODE(s.st_mode)==0o700,'private mirror directory')
 need(files==expected,'exact source mirror inventory')
 for row in PREP['source_files']:source_at(root,row)
 return sorted(files)

def output_binding(request):
 identity=request['fixture_output_identity'];root=Path(request['candidate_root']);path=root/'fixture-output'
 actual=node(path);need(actual==identity and actual['uid']==actual['gid']==1000 and actual['mode']==0o700 and path.is_dir() and not path.is_symlink(),'fresh output identity differs')
 return dict(schema='mckernel.daemon-mock.precreated-output.v1',path=PREP['container_output'],nonce=request['nonce'],device=actual['device'],inode=actual['inode'],uid=1000,gid=1000,mode=0o700)

def verify_request_inputs(request):
 need(Path(request['input_root'])==MIRROR and node(MIRROR)==request['input_identity'],'exact mirror identity')
 verify_mirror(MIRROR)
 root=Path(request['candidate_root']);need({p.name for p in root.iterdir()}=={'fixture-output'} and not list((root/'fixture-output').iterdir()),'fresh work contains only empty fixture output')
 binding=output_binding(request);reference=request['output_binding'];need(set(reference)=={'path','sha256'},'exact two-key output reference')
 raw=Path(reference['path']).read_bytes();need(sha(raw)==reference['sha256'] and json_bytes(raw)==binding,'actual output binding differs')
 prepdir=Path(request['runtime_preparation_identity']['path']);need(prepdir==OUTPUT_PARENT/('preparation-'+request['nonce']) and node(prepdir)==request['runtime_preparation_identity'],'runtime preparation identity')
 identity=node(prepdir);need(prepdir.is_dir() and not prepdir.is_symlink() and identity['uid']==identity['gid']==1000 and identity['mode']==0o700,'private runtime preparation directory')
 need({p.name for p in prepdir.iterdir()}=={'PREPARATION.SOURCE-ONLY.json','OUTPUT-BINDING.ACTUAL.json'},'runtime preparation inventory')
 need(Path(reference['path'])==prepdir/'OUTPUT-BINDING.ACTUAL.json' and (prepdir/'PREPARATION.SOURCE-ONLY.json').read_bytes()==PREPARATION.read_bytes(),'runtime preparation bytes')
 regular(prepdir/'PREPARATION.SOURCE-ONLY.json');regular(prepdir/'OUTPUT-BINDING.ACTUAL.json')
 return binding

def fixture_command(nonce):
 need(re.fullmatch('[0-9a-f]{32}',str(nonce)) is not None,'exact mock nonce')
 return [x.replace('ACTUAL_REQUEST_NONCE',nonce) for x in PREP['command_template']]

def output_tree_bytes(root,maximum):
 root=Path(root);total=count=0
 if not root.exists():return 0
 for path in root.rglob('*'):
  count+=1;need(count<=4096,'bounded output inventory exceeded')
  s=path.lstat()
  if stat.S_ISLNK(s.st_mode):need(False,'reproducer output symlink refused')
  elif stat.S_ISREG(s.st_mode):total+=s.st_size
  else:need(stat.S_ISDIR(s.st_mode),'output type differs')
  need(total<=maximum,'bounded output bytes exceeded')
 return total

def capture_ok(c, expected_returncode=0):
 return c.get('returncode')==expected_returncode and c.get('direct_child_joined') is True and c.get('group_absent') is True and c.get('closed_streams') is True and c.get('error') is None and c.get('retirement_error') is None and c.get('timed_out') is False and not c.get('unexpected_group_members')

def task_identity(raw,expected_pid):
 need(isinstance(raw,str) and raw.startswith(str(expected_pid)+' ('),'task stat PID differs')
 rest=raw.rsplit(')',1);need(len(rest)==2,'complete task comm required');fields=rest[1].split()
 need(len(fields)>=20 and len(fields[0])==1 and fields[0] in 'RSDZTtXxKWPI' and fields[19].isdecimal() and int(fields[19])>0,'task state/birth missing')
 return dict(pid=expected_pid,state=fields[0],start=int(fields[19]))

def validate_observation(raw,pid,returncode):
 need(type(pid) is int and pid>0 and len(raw)<=1<<20 and raw.endswith(b'\n'),'bounded complete observation')
 records=[json_bytes(line) for line in raw.splitlines()]
 if returncode==2:
  need(records==[dict(status='NOT_REPRODUCED',iterations=256,historical_extra_task_identity=None)],'exact non-reproduction required')
  return 'NOT_REPRODUCED'
 need(returncode==0 and len(records)==5,'complete positive observation required')
 first,joined,middle,final,end=records
 need(joined.get('status')=='OBSERVED_JOINED_TASK_ENUMERATION' and joined.get('real_pthread_join_returned_zero') is True,'positive actual pthread joins required')
 need(type(joined.get('iteration')) is int and 0<=joined['iteration']<256,'bounded iteration')
 workers=joined.get('workers');need(isinstance(workers,list) and len(workers)==2,'two real worker identities')
 identities={}
 for worker in workers:
  tid=worker.get('tid');need(type(tid) is int and tid>0 and tid!=pid and tid not in identities,'distinct worker TID required')
  identities[tid]=task_identity(worker.get('initial_raw_stat'),tid)
 main_birth=None
 for snapshot in (first,middle,final):
  need(snapshot.get('iteration')==joined['iteration'] and snapshot.get('unknown') is False,'snapshot iteration/unknown task differs')
  rows=snapshot.get('rows');need(isinstance(rows,list) and 1<=len(rows)<=3 and snapshot.get('literal_threads')==len(rows),'literal count differs')
  seen=set()
  for row in rows:
   tid=row.get('tid');need(type(tid) is int and tid not in seen and tid in {pid,*identities} and row.get('known_joined_or_main') is True,'unknown or duplicate task')
   seen.add(tid);read=row.get('stat_read');need(type(read) is int and read in (0,1),'wrong stat result')
   if read:
    current=task_identity(row.get('raw_stat'),tid)
    if tid==pid:
     if main_birth is None:main_birth=current['start']
     need(current['start']==main_birth,'main birth changed')
    else:need(current['start']==identities[tid]['start'],'worker birth changed')
   else:need(tid!=pid and row.get('raw_stat')=='','only exact joined worker ENOENT allowed')
  need(pid in seen,'main absent')
 need(first['literal_threads']==joined.get('immediate_literal_threads') and first['literal_threads']>1,'initial joined task was not observed')
 need(final['literal_threads']==1 and final['rows'][0]['tid']==pid and final['rows'][0]['stat_read']==1 and end==dict(status='FINAL_LITERAL_THREAD_CHECK',threads=1),'final literal singleton required')
 return 'OBSERVED_CURRENT_PLATFORM_JOIN_PROCFS_LAG'

def validate_driver_receipt(receipt,request):
 from importlib import util
 kp_path=HERE.parents[1]/'kernel_pids64.py';spec=util.spec_from_file_location('repro_retained_kernel_pids',kp_path);kp=util.module_from_spec(spec);spec.loader.exec_module(kp)
 need(receipt.get('schema')=='mckernel.daemon-join-procfs64-driver-receipt.v1' and receipt.get('status')=='PASS_JOIN_PROCFS64_OBSERVATION_CAPTURE' and receipt.get('scope')==PREP['scope'],'exact reproducer receipt')
 need(receipt.get('nonce')==request['nonce'] and receipt.get('preparation_sha256')==PREPARATION_SHA and receipt.get('commands')==[PREP['command_template'],PREP['execute_argv']],'exact source/commands/nonce')
 need(all(receipt.get(k) is False for k in ['production_main_executed','native_acceptance','provider_Rust_link_closure','M15_file_closure','daemon_acceptance']) and receipt.get('historical_extra_task_identity') is None,'observation scope inflated')
 root=Path(request['candidate_root']);captures=receipt.get('captures');need(isinstance(captures,list) and len(captures)==2,'both real joins required')
 for label,capture in zip(['compile','observe'],captures):
  rc=0 if label=='compile' else capture.get('returncode');need(rc in (0,2) and capture_ok(capture,rc),'child lifecycle unproven')
  need(json_bytes((root/'evidence'/label/'whole-join.json').read_bytes())==capture,'durable child join differs')
  for stream in ['stdout','stderr']:
   reference=capture['captures'][stream];expected='/work/evidence/'+label+'/'+stream;need(reference['path']==expected,'exact stream path')
   path=root/Path(expected).relative_to('/work');regular(path);raw=path.read_bytes()
   need(len(raw)==reference['size'] and sha(raw)==reference['sha256'],'captured stream differs')
   if stream=='stderr' or label=='compile':need(raw==b'','unexpected diagnostic output')
 raw=(root/'evidence/observe/stdout').read_bytes();need(receipt.get('outcome')==validate_observation(raw,captures[1]['pid'],captures[1]['returncode']),'observation outcome differs')
 executable=root/'fixture-output/join-procfs-reproducer';regular(executable);reference=receipt.get('executable',{});actual=ref(executable)
 need(reference==dict(actual,path='/work/fixture-output/join-procfs-reproducer'),'executed binary differs')
 proofs=[]
 for phase in ['before','after']:
  path=root/'evidence'/('kernel-pids64-'+phase+'.json');regular(path);need(ref(path)['sha256']==receipt.get('kernel_pids64_'+phase+'_sha256'),'raw controller proof differs');proofs.append(kp.validate_proof(json_bytes(path.read_bytes())))
 need(proofs[0]['controller_identity']==proofs[1]['controller_identity'] and proofs[0]['selected_mount']==proofs[1]['selected_mount'],'same effective controller required')
 return receipt
