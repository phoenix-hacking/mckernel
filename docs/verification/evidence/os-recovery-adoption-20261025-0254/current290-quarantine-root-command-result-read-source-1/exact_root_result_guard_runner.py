"""Functional exact owned-harness exception read only; no security testing.
Fixed profile; root entry has no caller-selected PID/source/command. All target
FD access uses stat/readlink/fdinfo only; never opens/duplicates/acquires its lock.
"""
import argparse,hashlib,json,os,stat,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROFILE=ROOT/'EXACT-ROOT-COMMAND-RESULT-PROFILE.NOT-RELEASED.json'
PROFILE_SHA='c85d1a143b71f8a394abe0d72d8abeae0b6cd59355023f22e61cda6b6202bab3'
class Refusal(RuntimeError):pass
def need(value,message):
 if not value:raise Refusal(message)
def bounded(path,maximum=65536):
 with open(path,'rb') as stream:raw=stream.read(maximum+1)
 need(len(raw)<=maximum,'bounded-read:'+str(path));return raw
def authenticate(ref):
 path=Path(ref['path']);meta=path.lstat();need(stat.S_ISREG(meta.st_mode),'regular-source')
 digest=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1<<20),b''):digest.update(block)
 need(meta.st_size==ref['bytes'] and digest.hexdigest()==ref['sha256'],'exact-source:'+str(path))
 if 'identity' in ref:need(lock_metadata(meta)==ref['identity'],'exact-frozen-file-identity')
 after=path.lstat();need((meta.st_dev,meta.st_ino,meta.st_mode,meta.st_size,meta.st_mtime_ns,meta.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_mode,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'authenticated-file-raced')
def process_identity(expected):
 pid=expected['pid'];root=Path('/proc')/str(pid);raw=bounded(root/'stat');left,sep,right=raw.rpartition(b') ');fields=right.split()
 need(sep and left.startswith(str(pid).encode()+b' (') and len(fields)>=50,'process-stat')
 need(fields[19].decode()==expected['starttime'] and fields[0] not in (b'Z',b'X',b'x',b'T',b't'),'exact-live-nonstopped-birth')
 need(int(fields[1])==expected['ppid'] and int(fields[2])==expected['pgid'],'exact-parent-and-group')
 need(bounded(root/'cmdline')==bytes.fromhex(expected['cmdline_hex']),'exact-process-argv')
 need(os.readlink(root/'exe')==expected['exe'],'exact-process-executable')
 status=bounded(root/'status').decode('ascii');credentials={}
 for key in ('Uid:','Gid:'):
  rows=[line.split()[1:] for line in status.splitlines() if line.startswith(key)]
  need(len(rows)==1 and len(rows[0])==4,'process-credential-shape')
  if expected.get('is_sudo_parent') and key=='Gid:':need(all(value in ('0','1000') for value in rows[0]),'known-sudo-parent-groups')
  else:need(rows[0][1:]==['0']*3 and (rows[0][0]=='0' or expected.get('is_sudo_parent') and rows[0][0]=='1000'),'root-target-credentials')
  credentials[key]=rows[0]
 again=bounded(root/'stat').rpartition(b') ')[2].split()
 need(len(again)>=50 and again[19]==fields[19] and again[0] not in (b'Z',b'X',b'x',b'T',b't'),'process-raced')
 return dict(pid=pid,starttime=expected['starttime'],ppid=int(fields[1]),pgid=int(fields[2]),cmdline_sha256=hashlib.sha256(bytes.fromhex(expected['cmdline_hex'])).hexdigest(),exe=expected['exe'],credentials=credentials)
def lock_metadata(meta):
 return dict(device=meta.st_dev,inode=meta.st_ino,mode=stat.S_IMODE(meta.st_mode),uid=meta.st_uid,gid=meta.st_gid,nlink=meta.st_nlink,size=meta.st_size)
def inspect_held_lock(pid,path,expected):
 named=lock_metadata(os.stat(path,follow_symlinks=False));need(named==expected,'permanent-mutex-name')
 entries=list((Path('/proc')/str(pid)/'fd').iterdir());need(len(entries)<=256,'fd-count-bound');matches=[]
 for entry in entries:
  need(entry.name.isdigit(),'numeric-fd')
  link=os.readlink(entry)
  # stat only; following proc's descriptor link never opens that description.
  meta=lock_metadata(os.stat(entry))
  if (meta['device'],meta['inode'])==(expected['device'],expected['inode']):
   need(link==str(path) and meta==named,'held-mutex-fd-name')
   text=bounded(Path('/proc')/str(pid)/'fdinfo'/entry.name).decode('ascii')
   rows=[line.split()[2:] for line in text.splitlines() if line.startswith('lock:')]
   key='{:02x}:{:02x}:{}'.format(os.major(meta['device']),os.minor(meta['device']),meta['inode'])
   wanted=['FLOCK','ADVISORY','WRITE',str(pid),key,'0','EOF']
   need(rows==[wanted],'held-description-flock')
   global_rows=[line.split()[1:] for line in bounded('/proc/locks',1<<20).decode('ascii').splitlines() if key in line.split()]
   need(global_rows==[wanted],'sole-permanent-global-flock')
   matches.append(dict(fd=int(entry.name),fdinfo=text,link=link,identity=meta,global_lock=wanted))
 need(len(matches)==1,'unique-held-permanent-description')
 need(lock_metadata(os.stat(path,follow_symlinks=False))==named,'mutex-name-raced')
 return matches[0]
def guard(profile):
 need(bounded('/proc/sys/kernel/random/boot_id',128).decode().strip()==profile['boot_id'],'exact-boot')
 actor=process_identity(profile['actor']);parent=process_identity(profile['parent'])
 lock=inspect_held_lock(actor['pid'],profile['mutex']['path'],profile['mutex']['identity'])
 for key in ('quarantine','transaction_plan','transaction_journal','source','release'):authenticate(profile[key])
 # Second exact birth check after FD observations rejects detach/exit/reuse races.
 need(process_identity(profile['actor'])==actor and process_identity(profile['parent'])==parent,'guard-process-race')
 return dict(actor=actor,parent=parent,lock=lock,boot_id=profile['boot_id'])
def readonly_gdb_argv(profile):
 commands=['set pagination off','set confirm off','set may-call-functions off','set may-write-registers off','set may-write-memory off','set may-insert-breakpoints off','set may-insert-fast-tracepoints off','file '+profile['python']['path'],'attach '+str(profile['actor']['pid']),'source '+profile['helper']['path'],'read-exact-root-command-result '+profile['source']['path']+' '+profile['proc_code']['sha256']+' '+str(profile['proc_code']['bytes'])+' '+profile['actor']['starttime'],'detach']
 argv=[profile['gdb']['path'],'-nx','-nh','-batch','-q','-iex','set auto-load off']
 for command in commands:argv+=['-ex',command]
 return argv
def decode_result(stdout,profile):
 answers=[json.loads(line) for line in stdout.decode('utf-8','strict').splitlines() if line.startswith('{')]
 need(len(answers)==1,'unique-json-result');answer=answers[0]
 need(answer.get('status')=='PASS_EXACT_ROOT_COMMAND_RESULT_READ' and answer.get('co_filename')==profile['source']['path'] and answer.get('co_name')=='root_command' and answer.get('local')=='result' and answer.get('exception_type')=='Refusal','exact-result-frame')
 rc=answer.get('returncode');need(type(rc) is int and -(1<<30)<rc<(1<<30),'bounded-child-returncode')
 rows=[]
 for stream in ('stdout','stderr'):
  row=answer.get(stream);need(isinstance(row,dict) and set(row)=={'bytes','sha256','raw_hex'} and type(row['bytes']) is int and 0<=row['bytes']<=4<<20 and isinstance(row['raw_hex'],str) and len(row['raw_hex'])==2*row['bytes'],'bounded-child-byte-result');rows.append(row)
 need(sum(row['bytes'] for row in rows)<=5<<20,'combined-childoutput5MiB-bound')
 for row in rows:
  raw=bytes.fromhex(row['raw_hex']);need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'lossless-child-bytes-binding')
 meta=answer.get('argv') or {};code=profile['proc_code']
 need(meta.get('prefix')==['/usr/bin/python3','-I','-B','-c'] and meta.get('code_sha256')==code['sha256'] and meta.get('code_bytes')==code['bytes'] and meta.get('challenge_bytes')==48 and isinstance(meta.get('challenge_sha256'),str) and len(meta['challenge_sha256'])==64 and meta.get('caller_pid')==1060806 and meta.get('caller_starttime')=='80309560','exact-PROC_CODE-caller-metadata')
 need(rc or answer['stderr']['bytes'] or answer['stdout']['bytes']>profile['root_command_limit_bytes'],'actual-source-failure-condition')
 return answer
def perform(profile,guardfn=guard,runfn=subprocess.run):
 before=guardfn(profile);stdout=stderr=b'';error=None;code=None;after=None
 try:
  try:
   child=runfn(readonly_gdb_argv(profile),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,check=False,env=dict(os.environ,DEBUGINFOD_URLS=''))
   stdout,stderr,code=child.stdout,child.stderr,child.returncode
  except subprocess.TimeoutExpired as exc:stdout,stderr=exc.stdout or b'',exc.stderr or b'';error='owned-debugger-timeout-killed-reaped'
  except Exception as exc:error=type(exc).__name__+':'+str(exc)
 finally:
  # Always observe; never resume/signal/change target if custody is uncertain.
  try:after=guardfn(profile)
  except Exception as exc:error=(error+'; ' if error else '')+'postguard:'+type(exc).__name__+':'+str(exc)
 need(len(stdout)<=profile['limits']['gdb_stdout_bytes'] and len(stderr)<=profile['limits']['gdb_stderr_bytes'],'debugger-output-bound')
 result=dict(status='REFUSED',before=before,after=after,debugger_returncode=code,error=error,
             stdout=dict(bytes=len(stdout),sha256=hashlib.sha256(stdout).hexdigest(),raw_hex=stdout.hex()),
             stderr=dict(bytes=len(stderr),sha256=hashlib.sha256(stderr).hexdigest(),raw_hex=stderr.hex()))
 if error is None:
  try:
   need(code==0 and after==before,'same-custody-and-gdb-exit');result['extraction']=decode_result(stdout,profile);result['status']='PASS_EXACT_OWNED_ROOT_COMMAND_RESULT_READ'
  except Exception as exc:result['error']=type(exc).__name__+':'+str(exc)
 return result
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--execute-exact-root-read',action='store_true');args=parser.parse_args()
 need(args.execute_exact_root_read and os.getuid()==os.geteuid()==0,'exact-root-entry-required')
 raw=PROFILE.read_bytes();need(hashlib.sha256(raw).hexdigest()==PROFILE_SHA,'fixed-profile-sha');profile=json.loads(raw)
 need(profile['actor']['pid']==1060806 and profile['actor']['starttime']=='80309560' and profile['parent']['pid']==1060803 and profile['parent']['starttime']=='80309553','fixed-actor-births')
 for key in ('gdb','python','helper','source','release','quarantine'):authenticate(profile[key])
 result=perform(profile);print(json.dumps(result,sort_keys=True));return 0 if result['status']=='PASS_EXACT_OWNED_ROOT_COMMAND_RESULT_READ' else 1
if __name__=='__main__':raise SystemExit(main())
